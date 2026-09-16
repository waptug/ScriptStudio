"""Local single-user API. Business rules live in services, not HTTP handlers."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import time
from fastapi import FastAPI, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from .db import Session, transaction, Project, Asset, Job, public, project_lock
from .schemas import CreateProject, Edit, Settings, Storyboard, RenderRequest, Timeline, uid
from .planner import LocalScriptPlanner, HttpScriptPlanner, OllamaScriptPlanner
from .timeline import TimelineService, Conflict
from .coordinator import GenerationCoordinator
from .storage import LocalStorage, AssetRepository
from .render import RenderService
from .budget import BudgetService
from .providers import get_provider, SubmissionUnknown, RateLimited

app = FastAPI(title='ScriptStudio', version='0.1.0',openapi_url='/api/openapi.json',docs_url='/api/docs')

@app.exception_handler(SubmissionUnknown)
@app.exception_handler(RateLimited)
async def provider_problem(request, exc):
    return JSONResponse(status_code=502,content={'detail':str(exc)})


@app.exception_handler(ValueError)
async def invalid(request, exc):
    return JSONResponse(status_code=409 if isinstance(exc,Conflict) else 400,content={'detail':str(exc)})


class UpdateProject(BaseModel):
    name: str = Field(min_length=1,max_length=200)
    script: str = Field(max_length=50000)
    settings: Settings


class ReconcileRequest(BaseModel):
    provider_id: str = Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')


class StoryboardUpdate(BaseModel):
    storyboard: Storyboard


def detail(session, project_id):
    project = session.get(Project,project_id)
    if not project: raise HTTPException(404,'Project not found')
    data = public(project)
    data['assets'] = [public(a) for a in session.scalars(select(Asset).where(Asset.project_id==project_id).order_by(Asset.created))]
    jobs = []
    for job in session.scalars(select(Job).where(Job.project_id==project_id).order_by(Job.created)):
        entry = public(job)
        # Provider output URLs and inline reference data stay server-side.
        entry['inputs'] = {k:v for k,v in entry['inputs'].items() if k not in ('prompt_image','timeline')}
        entry['result'] = {k:v for k,v in entry['result'].items() if k not in ('url','local_path')}
        jobs.append(entry)
    data['jobs'] = jobs
    data['reserved_cost'] = BudgetService().total(session,project_id)
    return data


@app.get('/api/health')
def health():
    with Session() as session:
        session.execute(select(Project.id).limit(1))
    return {'status':'ok','live_enabled':os.getenv('LIVE_GENERATION_ENABLED','false')=='true'}


@app.get('/api/providers')
def providers():
    return {'live_enabled':os.getenv('LIVE_GENERATION_ENABLED','false')=='true',
            'ollama_configured':bool(os.getenv('OLLAMA_URL') and os.getenv('OLLAMA_MODEL')),
            'runway_configured':bool(os.getenv('RUNWAY_API_KEY')),
            'elevenlabs_configured':bool(os.getenv('ELEVENLABS_API_KEY')),
            'suno':{'enabled':False,'reason':'Official API documentation and account access have not been verified. Import music instead.'},
            'caption_note':'Mock captions use estimated word timing. ElevenLabs uses returned character alignment when available.'}


@app.get('/api/sample')
def sample():
    return {'script':Path('/app/samples/demo.txt').read_text() if Path('/app/samples/demo.txt').exists() else DEMO}

DEMO = '''[Golden light across a mountain valley] Before the city wakes, the forest is already moving. A quiet breeze travels through the branches, carrying the scent of rain and earth. Every leaf catches a different shade of morning light.

[A river winding through mossy stones] Follow the water and a hidden world begins to appear. Tiny streams gather into a river, shaping the landscape one patient moment at a time. Along its banks, small creatures find shelter among the roots.

[Close view of a fern opening] Nature rarely asks us to hurry. A fern unfolds, a bird pauses, and sunlight moves slowly across the forest floor. These ordinary moments remind us how much there is to notice when we stop and listen.

[Wide view of the valley at sunrise] Take a breath and look around. The world beyond our screens is full of stories, waiting in places we pass every day. Sometimes the beginning of an adventure is simply choosing a different path home.'''


@app.get('/api/projects')
def projects():
    with Session() as session:
        return [{'id':p.id,'name':p.name,'created':p.created,'revision':p.revision,'settings':p.settings} for p in session.scalars(select(Project).order_by(Project.created.desc()))]


@app.post('/api/projects')
def create(payload: CreateProject):
    with transaction() as session:
        project = Project(id=uid(),name=payload.name,script=payload.script,original_script=payload.script,settings=payload.settings.model_dump())
        session.add(project)
        session.flush()
        return detail(session,project.id)


@app.get('/api/projects/{project_id}')
def get_project(project_id: str):
    with Session() as session: return detail(session,project_id)


@app.put('/api/projects/{project_id}')
def update_project(project_id: str, payload: UpdateProject):
    with transaction() as session:
        project = project_lock(session,project_id)
        old = Settings.model_validate(project.settings)
        if project.timeline['items'] and (old.fps_num,old.fps_den)!=(payload.settings.fps_num,payload.settings.fps_den):
            raise ValueError('Frame rate is fixed once production begins. Create a new project to change it.')
        if payload.settings.spending_limit + 1e-8 < BudgetService().total(session,project_id):
            raise ValueError('Spending limit cannot fall below existing reservations')
        if project.script!=payload.script:
            project.script_revision += 1
            if not project.original_script:project.original_script=payload.script
        project.name=payload.name
        project.script=payload.script
        project.settings=payload.settings.model_dump()
        TimelineService().save(session,project,project.timeline)
        return detail(session,project_id)


@app.post('/api/projects/{project_id}/plan')
def plan(project_id: str, planner: str='local'):
    with transaction() as session:
        project=project_lock(session,project_id)
        if session.query(Job).filter_by(project_id=project_id,kind='narration').count():
            raise ValueError('Production has started; planning would invalidate existing scene jobs. Create a new project.')
        if planner not in ('local','gateway','ollama'): raise ValueError('Unknown planner')
        service = {'local':LocalScriptPlanner,'gateway':HttpScriptPlanner,'ollama':OllamaScriptPlanner}[planner]()
        project.storyboard = service.plan(project.script,Settings.model_validate(project.settings)).model_dump()
        return detail(session,project_id)


@app.put('/api/projects/{project_id}/storyboard')
def storyboard(project_id: str, payload: StoryboardUpdate):
    with transaction() as session:
        project=project_lock(session,project_id)
        board = payload.storyboard
        if session.query(Job).filter_by(project_id=project_id,kind='narration').count():
            def timing_structure(document):
                clone=json.loads(json.dumps(document))
                for scene in clone['scenes']:
                    for shot in scene['shots']:
                        for field in ('visual','prompt','camera','references'):shot.pop(field,None)
                return clone
            if timing_structure(board.model_dump())!=timing_structure(project.storyboard):
                raise ValueError('After production starts, only visual descriptions, prompts, camera instructions, and references may change. Narration and shot timing are fixed.')
        ids = [scene.id for scene in board.scenes]+[shot.id for scene in board.scenes for shot in scene.shots]
        if len(set(ids)) != len(ids): raise ValueError('Storyboard IDs must be unique')
        for scene in board.scenes:
            if not scene.shots: raise ValueError('Every scene must have a shot')
            if any(s.scene_id!=scene.id for s in scene.shots): raise ValueError('Shot scene association is invalid')
        project.storyboard=board.model_dump()
        return detail(session,project_id)


@app.post('/api/projects/{project_id}/produce')
def produce(project_id: str):
    with transaction() as session:
        project=project_lock(session,project_id)
        GenerationCoordinator().produce(session,project)
        return detail(session,project_id)


@app.post('/api/projects/{project_id}/shots/{shot_id}/regenerate')
def regenerate(project_id: str,shot_id: str):
    with transaction() as session:
        project=project_lock(session,project_id)
        GenerationCoordinator().regenerate(session,project,shot_id)
        return detail(session,project_id)


@app.post('/api/projects/{project_id}/timeline')
def edit(project_id: str,payload: Edit):
    with transaction() as session:
        project=project_lock(session,project_id)
        TimelineService().edit(session,project,payload)
        return detail(session,project_id)


@app.post('/api/projects/{project_id}/assets')
def upload(project_id: str, file: UploadFile):
    with Session() as session:
        if not session.get(Project,project_id): raise HTTPException(404,'Project not found')
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ('.mp4','.mov','.webm','.wav','.mp3','.m4a','.ogg','.flac','.png','.jpg','.jpeg'):
        raise ValueError('Upload MP4/MOV/WebM video, WAV/MP3/M4A/OGG/FLAC audio, or PNG/JPEG images')
    storage=LocalStorage()
    temp=storage.temporary(suffix)
    total=0
    try:
        with open(temp,'wb') as output:
            while chunk:=file.file.read(1024*1024):
                total+=len(chunk)
                if total>512*1024*1024: raise ValueError('Upload exceeds 512 MiB')
                output.write(chunk)
        with transaction() as session:
            project_lock(session,project_id)
            AssetRepository(storage).ingest(session,project_id,temp,Path(file.filename).name,{'provider':'import','original_name':Path(file.filename).name})
            return detail(session,project_id)
    finally:
        temp.unlink(missing_ok=True)


@app.get('/api/assets/{asset_id}/{variant}')
def media(asset_id: str, variant: str):
    with Session() as session:
        asset=session.get(Asset,asset_id)
        if not asset: raise HTTPException(404,'Asset not found')
        relative={'original':asset.path,'thumbnail':asset.thumbnail,'proxy':asset.proxy}.get(variant)
        if not relative: raise HTTPException(404,'Asset variant not available')
        return FileResponse(LocalStorage().path(relative))


@app.post('/api/projects/{project_id}/renders')
def render(project_id: str, payload: RenderRequest):
    with transaction() as session:
        project=project_lock(session,project_id)
        RenderService().validate(session,project_id,Timeline.model_validate(project.timeline),payload.draft)
        inputs={**payload.model_dump(),'timeline':project.timeline,'settings':project.settings,'revision':project.revision}
        job=Job(id=uid(),project_id=project_id,kind='render',provider='ffmpeg',model='h264-aac',state='queued',
                fingerprint=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest(),inputs=inputs,estimated_cost=0)
        session.add(job)
        session.flush()
        return detail(session,project_id)


@app.get('/api/jobs/{job_id}/subtitles/{extension}')
def subtitles(job_id: str,extension: str):
    if extension not in ('srt','vtt'): raise HTTPException(404)
    with Session() as session:
        job=session.get(Job,job_id)
        if not job or job.state!='ready' or extension not in job.result: raise HTTPException(404,'Render subtitles not ready')
        return FileResponse(LocalStorage().path(job.result[extension]),filename=f'captions.{extension}')


@app.post('/api/jobs/{job_id}/{action}')
def job_action(job_id: str,action: str):
    with transaction() as session:
        job=session.get(Job,job_id)
        if not job: raise HTTPException(404)
        project=project_lock(session,job.project_id)
        if action=='retry': GenerationCoordinator().retry(session,job)
        elif action=='cancel':
            if job.state in ('ready','canceled'): raise ValueError('Job already finished')
            if job.state=='submitting' or job.state=='submission_outcome_unknown':
                raise ValueError('Submission outcome is uncertain. Reconcile before canceling; charges may already be incurred.')
            if job.provider_id and job.provider not in ('mock','ffmpeg'):
                get_provider(job.kind,job.provider).cancel(job.provider_id)
            if job.attempts==0:job.reported_cost=0
            job.state='canceled'
            job.error='Canceled locally; existing cost reservation retained because charges may already be incurred.'
            job.lease_until=0
        else: raise HTTPException(404)
        return detail(session,project.id)


@app.put('/api/jobs/{job_id}/reconcile')
def reconcile(job_id: str,payload: ReconcileRequest):
    with transaction() as session:
        job=session.get(Job,job_id)
        if not job: raise HTTPException(404)
        project=project_lock(session,job.project_id)
        if job.state!='submission_outcome_unknown' or job.provider!='runway':
            raise ValueError('Task-ID reconciliation is supported for uncertain Runway submissions only. Other synchronous providers require an imported result from provider history.')
        # Verify task ID with the account before associating it; never issue another generation request.
        get_provider(job.kind,job.provider).status(payload.provider_id)
        job.provider_id=payload.provider_id
        job.state='submitted'
        job.error=None
        job.lease_until=0
        job.next_run=0
        return detail(session,project.id)


@app.get('/api/projects/{project_id}/events')
async def events(project_id: str,request: Request):
    async def stream():
        previous=None
        while not await request.is_disconnected():
            with Session() as session:
                data=detail(session,project_id)
            encoded=json.dumps(data,sort_keys=True)
            digest=hashlib.sha256(encoded.encode()).hexdigest()
            if digest!=previous:
                yield f'id: {digest}\nevent: project\ndata: {encoded}\n\n'
                previous=digest
            else:
                yield ': heartbeat\n\n'
            await asyncio.sleep(1)
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


@app.get('/api/jobs/{job_id}/openshot')
def openshot_bundle(job_id: str):
    with Session() as session:
        job=session.get(Job,job_id)
        if not job or job.state!='ready' or not job.result.get('openshot_bundle'):
            raise HTTPException(404,'Complete a final render before downloading its OpenShot project')
        return FileResponse(LocalStorage().path(job.result['openshot_bundle']),filename='ScriptStudio-OpenShot.zip')


class RecoveredAsset(BaseModel):
    asset_id: str


@app.put('/api/jobs/{job_id}/recovered-asset')
def recover_asset(job_id: str,payload: RecoveredAsset):
    with transaction() as session:
        job=session.get(Job,job_id)
        if not job:raise HTTPException(404,'Job not found')
        project=project_lock(session,job.project_id)
        if job.state not in ('failed','submission_outcome_unknown'):
            raise ValueError('Only failed or uncertain jobs can be reconciled with imported media')
        asset=session.get(Asset,payload.asset_id)
        if not asset or asset.project_id!=project.id:
            raise ValueError('Import the recovered result into this project first')
        expected='video' if job.kind=='video' else 'audio'
        if job.kind not in ('video','narration','music') or asset.kind!=expected:
            raise ValueError('Recovered media type does not match the generation job')
        job.result={**job.result,'recovered_asset_id':asset.id,'caption_method':'estimated from imported recovered audio; alignment unavailable'}
        job.error=None
        GenerationCoordinator().complete(session,project,job,asset)
        pid=project.id
    GenerationCoordinator().try_assembly(pid)
    with Session() as session:return detail(session,pid)
