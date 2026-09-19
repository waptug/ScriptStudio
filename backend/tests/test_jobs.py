import time
from pathlib import Path
import shutil
import pytest
from studio.db import transaction, Session, Project, Job
from studio.schemas import Settings, uid
from studio.coordinator import GenerationCoordinator
from studio.planner import LocalScriptPlanner
from studio.budget import BudgetService
from studio.providers import SubmissionUnknown, Capabilities


def job_record(pid,**kwargs):
    return Job(id=uid(),project_id=pid,kind='video',provider='runway',fingerprint='abc',inputs={},estimated_cost=1,**kwargs)


def test_budget_counts_pending_unknown_and_canceled(project_id):
    with transaction() as s:
        p=s.get(Project,project_id)
        p.settings={**p.settings,'spending_limit':3}
        s.add_all([job_record(p.id,state='queued'),job_record(p.id,state='submission_outcome_unknown'),job_record(p.id,state='canceled')])
        s.flush()
        assert BudgetService().total(s,p.id)==3
        with pytest.raises(ValueError,match='Spending limit'):
            BudgetService().reserve(s,p,.01)


def test_ambiguous_submission_is_never_resubmitted(project_id,monkeypatch):
    from studio.configuration import ConfigurationService, AdminUpdate
    ConfigurationService().save(AdminUpdate(paid_generation={'enabled':True,'video':True}))
    class Ambiguous:
        capabilities=Capabilities(True,False)
        calls=0
        def submit(self,*args):
            self.calls+=1
            raise SubmissionUnknown('Lost response')
    provider=Ambiguous()
    monkeypatch.setattr('studio.coordinator.get_provider',lambda *args:provider)
    with transaction() as s:
        j=job_record(project_id,state='queued');s.add(j);jid=j.id
    c=GenerationCoordinator();c.process(jid);c.process(jid)
    with Session() as s:
        j=s.get(Job,jid)
        assert j.state=='submission_outcome_unknown'
        assert j.attempts==1 and provider.calls==1


def test_restart_submitting_unknown_and_submitted_resumes(project_id,monkeypatch):
    with transaction() as s:
        a=job_record(project_id,state='submitting',lease_until=time.time()-1)
        b=job_record(project_id,state='submitted',provider_id='existing-task',lease_until=time.time()-1)
        s.add_all([a,b]);aid,bid=a.id,b.id
    class Polling:
        capabilities=Capabilities(True,True)
        def submit(self,*args): raise AssertionError('Must not resubmit')
        def status(self,pid):
            assert pid=='existing-task'
            return {'status':'RUNNING'}
    monkeypatch.setattr('studio.coordinator.get_provider',lambda *args:Polling())
    c=GenerationCoordinator();c.process(aid);c.process(bid)
    with Session() as s:
        assert s.get(Job,aid).state=='submission_outcome_unknown'
        assert s.get(Job,bid).state=='generating'


def test_download_retry_keeps_original_generation(project_id,monkeypatch):
    from studio.configuration import ConfigurationService, AdminUpdate
    ConfigurationService().save(AdminUpdate(paid_generation={'enabled':True,'video':True}))
    from studio.providers import MockVideoProvider
    from studio.storage import LocalStorage
    output=MockVideoProvider().submit(uid(),{'prompt':'Test','duration':2})['local_path']
    class Provider:
        capabilities=Capabilities(True,True)
        calls=0
        def submit(self,*args):self.calls+=1;return {'provider_id':'paid-once'}
        def status(self,pid):return {'status':'SUCCEEDED','output':['https://example.test/a.mp4']}
        def result(self,status):return {'url':status['output'][0]}
    provider=Provider();downloads=[]
    def download(self,url,destination):
        downloads.append(url)
        if len(downloads)==1:raise OSError('Temporary download failure')
        shutil.copyfile(output,destination)
    monkeypatch.setattr('studio.coordinator.get_provider',lambda *args:provider)
    monkeypatch.setattr(LocalStorage,'download',download)
    with transaction() as s:
        j=job_record(project_id,state='queued');s.add(j);jid=j.id
    c=GenerationCoordinator();c.process(jid)
    with transaction() as s:
        j=s.get(Job,jid);assert j.state=='downloading';j.next_run=0
    c.process(jid)
    with Session() as s:
        assert s.get(Job,jid).state=='ready'
        assert s.get(Job,jid).asset_id
        assert s.get(Job,jid).error is None
    assert provider.calls==1 and len(downloads)==2


def test_measured_narration_builds_placeholders_before_video(project_id):
    with transaction() as s:
        p=s.get(Project,project_id)
        p.storyboard=LocalScriptPlanner().plan('The forest wakes. Light moves across the river.',Settings()).model_dump()
        GenerationCoordinator().produce(s,p)
        ids=[j.id for j in s.query(Job).all()]
    c=GenerationCoordinator()
    for jid in ids:c.process(jid)
    with Session() as s:
        p=s.get(Project,project_id)
        narration=[i for i in p.timeline['items'] if i['track']=='narration']
        shots=[i for i in p.timeline['items'] if i['track']=='video']
        assert sum(i['duration'] for i in narration)==sum(i['duration'] for i in shots)
        video_jobs=s.query(Job).filter_by(kind='video').all()
        assert len(video_jobs)==len(shots)>1
        assert all(j.state=='queued' and j.attempts==0 for j in video_jobs)
        assert all(j.inputs['placeholder_id'] in [i['id'] for i in shots] for j in video_jobs)


def test_known_submission_rejection_is_failed_not_unknown(project_id,monkeypatch):
    from studio.configuration import ConfigurationService, AdminUpdate
    ConfigurationService().save(AdminUpdate(paid_generation={'enabled':True,'video':True}))
    class Reject:
        capabilities=Capabilities(True,False)
        def submit(self,*args):raise ValueError('Provider rejected HTTP 400')
    monkeypatch.setattr('studio.coordinator.get_provider',lambda *args:Reject())
    with transaction() as s:
        j=job_record(project_id,state='queued');s.add(j);jid=j.id
    GenerationCoordinator().process(jid)
    with transaction() as s:
        j=s.get(Job,jid)
        assert j.state=='failed' and j.result['safe_to_retry_submission']
        GenerationCoordinator().retry(s,j)
        assert j.state=='queued'


def test_rate_limit_backoff_is_bounded_and_safe_to_retry(project_id,monkeypatch):
    from studio.configuration import ConfigurationService, AdminUpdate
    ConfigurationService().save(AdminUpdate(paid_generation={'enabled':True,'video':True}))
    from studio.providers import RateLimited
    class Limited:
        capabilities=Capabilities(True,False)
        def submit(self,*args):raise RateLimited()
    monkeypatch.setattr('studio.coordinator.get_provider',lambda *args:Limited())
    with transaction() as s:j=job_record(project_id,state='queued');s.add(j);jid=j.id
    c=GenerationCoordinator()
    for attempt in range(5):
        c.process(jid)
        with transaction() as s:
            j=s.get(Job,jid)
            assert j.next_run>time.time()
            j.next_run=0
    with transaction() as s:
        j=s.get(Job,jid)
        assert j.state=='failed' and j.attempts==5
        c.retry(s,j)
        assert j.state=='queued'


def test_regeneration_workflow_retains_selected_take(project_id):
    with transaction() as s:
        p=s.get(Project,project_id)
        p.storyboard=LocalScriptPlanner().plan('A quiet river flows.',Settings()).model_dump()
        GenerationCoordinator().produce(s,p)
        narration_id=s.query(Job).filter_by(kind='narration').one().id
    c=GenerationCoordinator();c.process(narration_id)
    with Session() as s:
        first=s.query(Job).filter_by(kind='video').one();first_id=first.id;shot_id=first.inputs['shot_id']
    c.process(first_id)
    with transaction() as s:
        p=s.get(Project,project_id)
        selected=next(i for i in p.timeline['items'] if i['track']=='video')['asset_id']
        second_id=c.regenerate(s,p,shot_id).id
    c.process(second_id)
    with Session() as s:
        p=s.get(Project,project_id)
        assert next(i for i in p.timeline['items'] if i['track']=='video')['asset_id']==selected
        assert s.get(Job,first_id).asset_id!=s.get(Job,second_id).asset_id
        assert s.get(Job,second_id).state=='ready'
