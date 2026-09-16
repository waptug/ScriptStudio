"""Durable state machine. Database leases and reconciliation survive broker restarts."""
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import time
from sqlalchemy import select
from .db import Session, transaction, project_lock, Job, Asset, Project
from .schemas import Settings, Storyboard, Item, uid
from .providers import get_provider, RateLimited, SubmissionUnknown
from .storage import AssetRepository, LocalStorage
from .timeline import TimelineService
from .budget import BudgetService
from .render import RenderService

ACTIVE = ('submitting','submitted','generating','downloading','validating')
TERMINAL = ('ready','failed','canceled','submission_outcome_unknown')


class NarrationService:
    """Convert character alignment or explicitly estimated word timing into frame cues."""
    def cues(self, text, alignment, duration, settings, offset):
        words = []
        if alignment and alignment.get('characters'):
            current, start, end = '', 0.0, 0.0
            for character, a, b in zip(alignment['characters'], alignment['character_start_times_seconds'], alignment['character_end_times_seconds']):
                if character.isspace():
                    if current:
                        words.append((current,start,end))
                        current = ''
                else:
                    if not current: start = a
                    current += character
                    end = b
            if current: words.append((current,start,end))
        else:
            pieces = text.split()
            total = sum(len(w)+1 for w in pieces)
            used = 0
            for word in pieces:
                a = duration * used/total
                used += len(word)+1
                words.append((word,a,duration*used/total))
        return [Item(track='caption', start=offset+settings.frames(a), duration=max(1,settings.frames(b)-settings.frames(a)), text=word).model_dump()
                for word,a,b in words]


class GenerationCoordinator:
    def enqueue(self, session, project, kind, provider_name, inputs):
        provider = get_provider(kind,provider_name)
        provider.validate(inputs)
        estimate = provider.estimate(inputs)
        BudgetService().reserve(session,project,estimate)
        encoded = json.dumps(inputs,sort_keys=True)
        job = Job(id=uid(), project_id=project.id, kind=kind, provider=provider_name,
                  model=inputs.get('model','local'), inputs=deepcopy(inputs), fingerprint=hashlib.sha256(encoded.encode()).hexdigest(),
                  estimated_cost=estimate, state='queued')
        session.add(job)
        session.flush()
        return job

    def produce(self, session, project):
        if project.timeline['items'] or session.query(Job).filter_by(project_id=project.id,kind='narration').count():
            raise ValueError('Production already started. Edit the timeline or regenerate individual shots; create a new project for a fresh production.')
        board = Storyboard.model_validate(project.storyboard)
        if not board.scenes:
            raise ValueError('Plan and review the storyboard first')
        settings = Settings.model_validate(project.settings)
        batch_id = uid()
        for index, scene in enumerate(board.scenes):
            self.enqueue(session,project,'narration',settings.voice_provider, {
                'batch_id':batch_id, 'scene_id':scene.id, 'position':index, 'text':scene.narration,
                'voice_id':settings.voice_id, 'voice_settings':settings.voice_settings,
                'model':os.getenv('ELEVENLABS_MODEL','eleven_multilingual_v2') if settings.voice_provider=='elevenlabs' else 'espeak-ng',
                'previous_text':board.scenes[index-1].narration if index else '',
                'next_text':board.scenes[index+1].narration if index+1<len(board.scenes) else ''})

    def video_request(self, session, project, shot, placeholder_id, duration):
        settings = Settings.model_validate(project.settings)
        request = {'shot_id':shot.id, 'placeholder_id':placeholder_id, 'prompt':f'{shot.prompt}. Camera: {shot.camera}',
                   'duration':max(2,min(10,math.ceil(duration))), 'camera':shot.camera,
                   'references':shot.references, 'model':os.getenv('RUNWAY_MODEL','gen4.5') if settings.video_provider=='runway' else 'mock-video-v1',
                   'ratio':{'landscape':'1280:720','portrait':'720:1280','square':'960:960'}[settings.aspect]}
        if shot.references and settings.video_provider=='runway':
            import base64
            asset = session.get(Asset,shot.references[0])
            if not asset or asset.project_id != project.id or asset.kind != 'image':
                raise ValueError('Reference must be an imported image in this project')
            path = LocalStorage().path(asset.path)
            if path.stat().st_size > 5*1024*1024:
                raise ValueError('Reference image exceeds 5 MiB')
            mime = 'image/png' if asset.info['streams'][0]['codec_name']=='png' else 'image/jpeg'
            request['prompt_image'] = f'data:{mime};base64,'+base64.b64encode(path.read_bytes()).decode()
        return request

    def assemble(self, session, project):
        jobs = list(session.scalars(select(Job).where(Job.project_id==project.id,Job.kind=='narration').order_by(Job.created)))
        if not jobs or any(j.state!='ready' for j in jobs) or jobs[0].result.get('assembled'):
            return
        settings = Settings.model_validate(project.settings)
        board = Storyboard.model_validate(project.storyboard)
        items = deepcopy(project.timeline['items'])
        offset = 0
        video_jobs = []
        for scene in board.scenes:
            job = next(j for j in jobs if j.inputs['scene_id']==scene.id)
            asset = session.get(Asset,job.asset_id)
            # Round narration outward so the final spoken samples are never trimmed.
            frames = math.ceil(asset.duration*settings.fps_num/settings.fps_den)
            items.append(Item(track='narration', start=offset, duration=frames, asset_id=asset.id, selected_take=asset.id).model_dump())
            items += NarrationService().cues(scene.narration,job.result.get('alignment'),asset.duration,settings,offset)
            weights = [max(1,len(s.narration.split())) for s in scene.shots]
            if not weights:
                raise ValueError('Every scene needs at least one shot')
            used_weight = 0
            for shot,weight in zip(scene.shots,weights):
                start = round(frames*used_weight/sum(weights))
                used_weight += weight
                end = round(frames*used_weight/sum(weights))
                shot.assigned_frames = end-start
                # Long coverage is explicit hold-last-frame; speech is never accelerated.
                item = Item(track='video',start=offset+start,duration=max(1,end-start),shot_id=shot.id,coverage='hold')
                items.append(item.model_dump())
                video_jobs.append((shot,item))
            offset += frames
        TimelineService().save(session,project,{**project.timeline,'items':items})
        project.storyboard = board.model_dump()
        # Placeholders are persisted in the same transaction as queued jobs, before any submission.
        for shot,item in video_jobs:
            self.enqueue(session,project,'video',settings.video_provider,self.video_request(session,project,shot,item.id,settings.seconds(item.duration)))
        if settings.music_provider not in ('import','suno'):
            music_item = Item(track='music',duration=offset,volume=.25,fade_in=settings.frames(2),fade_out=settings.frames(3))
            TimelineService().save(session,project,{**project.timeline,'items':project.timeline['items']+[music_item.model_dump()]})
            self.enqueue(session,project,'music',settings.music_provider,{'duration':settings.seconds(offset),'mood':settings.music_mood,'placeholder_id':music_item.id})
        jobs[0].result = {**jobs[0].result,'assembled':True}
        jobs[0].error = None

    def regenerate(self, session, project, shot_id):
        board = Storyboard.model_validate(project.storyboard)
        shot = next((s for scene in board.scenes for s in scene.shots if s.id==shot_id),None)
        if not shot: raise ValueError('Shot not found')
        item = next((i for i in project.timeline['items'] if i['shot_id']==shot_id),None)
        settings = Settings.model_validate(project.settings)
        duration = settings.seconds(item['duration']) if item else shot.estimated_duration
        return self.enqueue(session,project,'video',settings.video_provider,self.video_request(session,project,shot,item['id'] if item else None,duration))

    def complete(self, session, project, job, asset):
        if job.state == 'ready': return
        job.asset_id = asset.id
        job.state = 'ready'
        job.progress = 1
        job.lease_until = 0
        job.updated = time.time()
        if job.kind in ('video','music'):
            TimelineService().fill(session,project,job.inputs.get('placeholder_id'),asset)

    def claim(self, job_id):
        with transaction() as session:
            candidate = session.get(Job,job_id)
            if not candidate: return False
            project = project_lock(session,candidate.project_id)
            job = session.query(Job).filter_by(id=job_id).populate_existing().with_for_update().one()
            now = time.time()
            if job.state in TERMINAL or job.lease_until>now or job.next_run>now: return False
            active = session.query(Job).filter(Job.project_id==project.id,Job.id!=job.id,Job.state.in_(ACTIVE)).count()
            if job.state=='queued' and active>=project.settings['max_concurrency']: return False
            if job.state=='submitting':
                if job.provider=='mock' or job.kind=='render':
                    job.state='queued'
                else:
                    job.state='submission_outcome_unknown'
                    job.error='Worker stopped during submission. Reconcile provider history; do not resubmit blindly.'
                    return False
            if job.state=='queued':
                job.state='submitting'
            job.lease_until = now+600
            return True

    def set(self, job_id, **changes):
        with transaction() as session:
            job = session.get(Job,job_id)
            if job.state=='canceled': return False
            for key,value in changes.items(): setattr(job,key,value)
            job.updated = time.time()
            return True

    def process(self, job_id):
        if not self.claim(job_id): return
        try:
            with Session() as session:
                job = session.get(Job,job_id)
                kind, provider_name, inputs, state = job.kind,job.provider,deepcopy(job.inputs),job.state
                project_id, provider_id, result = job.project_id,job.provider_id,deepcopy(job.result)
                attempts = job.attempts
            if kind=='render':
                self.set(job_id,state='generating')
                def report(value): self.set(job_id,progress=value,lease_until=time.time()+600)
                with Session() as session:
                    output, metadata = RenderService().render(session,project_id,job_id,inputs,report)
                result = {'local_path':str(output),**metadata}
                self.set(job_id,state='validating',result=result)
            else:
                provider = get_provider(kind,provider_name)
                if state=='submitting':
                    self.set(job_id,state='submitting',attempts=attempts+1)
                    result = provider.submit(job_id,inputs)
                    provider_id = result['provider_id']
                    self.set(job_id,state='submitted',provider_id=provider_id,result=result)
                if provider.capabilities.asynchronous and 'local_path' not in result:
                    status = provider.status(provider_id)
                    if status['status'] in ('FAILED','CANCELLED','CANCELED'):
                        raise ValueError('Provider task ended: '+status['status'])
                    if status['status'] != 'SUCCEEDED':
                        self.set(job_id,state='generating',lease_until=0,next_run=time.time()+5)
                        return
                    result = {**result,**provider.result(status)}
                    self.set(job_id,result=result)
                self.set(job_id,state='downloading')
                if result.get('local_path') and Path(result['local_path']).is_file():
                    output = Path(result['local_path'])
                elif result.get('url'):
                    output = LocalStorage().path(f'tmp/{job_id}.mp4')
                    LocalStorage().download(result['url'],output)
                    result = {**result,'local_path':str(output)}
                    self.set(job_id,result=result)
                else:
                    raise ValueError('Provider result is unavailable. Reconcile saved provider task; do not regenerate.')
                self.set(job_id,state='validating')
            # Stable asset ID makes crash-after-ingest recovery idempotent.
            with transaction() as session:
                project = project_lock(session,project_id)
                job = session.get(Job,job_id)
                if job.state=='canceled': return
                provenance = {'job_id':job.id,'provider':job.provider,'model':job.model,
                              'shot_id':inputs.get('shot_id'),'inputs':{k:v for k,v in inputs.items() if k!='prompt_image'},
                              'caption_method':result.get('caption_method'), 'alignment':result.get('alignment')}
                asset = AssetRepository().ingest(session,project_id,output,f'{kind} • {job.id[:8]}',provenance,asset_id=job.id)
                self.complete(session,project,job,asset)
            if kind=='narration':
                self.try_assembly(project_id)
        except RateLimited:
            self.retry_later(job_id,'Provider rate limited the request',safe_submission=True)
        except SubmissionUnknown as exc:
            with Session() as session:
                job = session.get(Job,job_id)
                submitting = job.state=='submitting'
            if submitting:
                self.set(job_id,state='submission_outcome_unknown',error=str(exc),lease_until=0)
            else:
                self.retry_later(job_id,'Provider status request failed; the existing task will be polled again')
        except Exception as exc:
            with Session() as session:
                job = session.get(Job,job_id)
                uncertain = job.state=='submitting' and job.provider!='mock' and not isinstance(exc,ValueError)
                rejected = job.state=='submitting' and job.provider!='mock' and isinstance(exc,ValueError)
                result = deepcopy(job.result)
            if rejected:
                self.set(job_id,state='failed',error=str(exc)[:3000],lease_until=0,
                         result={**result,'retry_state':'queued','safe_to_retry_submission':True})
            elif uncertain:
                self.set(job_id,state='submission_outcome_unknown',error='Uncertain provider submission; reconcile before retrying',lease_until=0)
            else:
                self.retry_later(job_id,str(exc)[:3000])

    def try_assembly(self, project_id):
        try:
            with transaction() as session:
                project = project_lock(session,project_id)
                self.assemble(session,project)
        except ValueError as exc:
            with transaction() as session:
                project = project_lock(session,project_id)
                job = session.query(Job).filter_by(project_id=project_id,kind='narration').order_by(Job.created).first()
                if job: job.error = 'Assembly needs attention: '+str(exc)

    def retry_later(self, job_id, error, safe_submission=False):
        with transaction() as session:
            job = session.get(Job,job_id)
            if job.state=='canceled': return
            job.retries += 1
            job.error = error
            job.lease_until = 0
            # Known rejection is safe; downloads/status keep their provider ID and original stage.
            if safe_submission and not job.provider_id:
                job.state='queued'
                job.result={**job.result,'safe_to_retry_submission':True}
            if job.state=='submitting' and job.provider=='mock': job.state='queued'
            if job.retries>=5:
                job.result = {**job.result,'retry_state':job.state}
                job.state='failed'
            job.next_run = time.time()+min(60,2**job.retries)
            job.updated = time.time()

    def retry(self, session, job):
        if job.state!='failed': raise ValueError('Only failed jobs can be retried')
        if job.provider!='mock' and job.attempts and not job.provider_id and not job.result.get('safe_to_retry_submission'):
            raise ValueError('No provider ID is known. Reconcile submission rather than risk a second paid request.')
        job.state = job.result.get('retry_state','submitted' if job.provider_id else 'queued')
        job.retries=0
        job.next_run=0
        job.lease_until=0
        job.error=None
