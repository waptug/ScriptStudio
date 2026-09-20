import pytest
from studio.db import transaction, Session, Project, Job, Asset
from studio.local_demo import create, TEMPLATE
from studio.coordinator import GenerationCoordinator
from studio.render import RenderService

@pytest.fixture
def local_models(monkeypatch):
    monkeypatch.setattr('studio.local_models.LocalModelService.require_ready',lambda self,name: {'revision':'test'})
    monkeypatch.setattr('studio.local_models.manifest',lambda name: {'revision':'test'})


def prepared(duration=50):
    with transaction() as s:
        p=create(s);pid=p.id
        j=s.query(Job).filter_by(project_id=pid,kind='narration').one()
        a=Asset(id='narration',project_id=pid,name='Narration',kind='audio',path='speech.wav',checksum='speech',duration=duration,info={},provenance={'provider':'kokoro'})
        s.add(a);s.flush();j.asset_id=a.id;j.state='ready'
    return pid


def test_demo_is_local_exact_minute_and_idempotent(local_models,monkeypatch):
    pid=prepared();c=GenerationCoordinator();c.try_assembly(pid);c.try_assembly(pid)
    with Session() as s:
        p=s.get(Project,pid);jobs=s.query(Job).filter_by(project_id=pid).all()
        assert len(jobs)==14
        assert {j.provider for j in jobs}=={'kokoro','wan','ace_step'}
        assert p.settings['spending_limit']==0 and p.settings['max_concurrency']==1
        videos=[i for i in p.timeline['items'] if i['track']=='video']
        assert len(videos)==12 and [i['start'] for i in videos]==list(range(0,1440,120))
        assert all(i['duration']==120 for i in videos)
        assert max(i['start']+i['duration'] for i in p.timeline['items'])==1440
        assert all(j.inputs['frames']==81 for j in jobs if j.kind=='video')
        assert not any(j.kind=='render' for j in jobs)
    monkeypatch.setattr(RenderService,'validate',lambda *args:None)
    with transaction() as s:
        for j in s.query(Job).filter_by(project_id=pid):j.state='ready'
    c.try_assembly(pid);c.try_assembly(pid)
    with Session() as s:
        render=s.query(Job).filter_by(project_id=pid,kind='render').one()
        assert render.inputs['demo_template']==TEMPLATE and render.inputs['burn_captions']
        assert render.inputs['timeline']==s.get(Project,pid).timeline


def test_long_narration_not_cut_or_accelerated(local_models):
    pid=prepared(61);GenerationCoordinator().try_assembly(pid)
    with Session() as s:
        assert s.get(Project,pid).timeline['items']==[]
        jobs=s.query(Job).filter_by(project_id=pid).all()
        assert len(jobs)==1 and 'not accelerated or cut' in jobs[0].error


def test_missing_models_creates_nothing(monkeypatch):
    def missing(self,name):raise ValueError('Install '+name)
    monkeypatch.setattr('studio.local_models.LocalModelService.require_ready',missing)
    with pytest.raises(ValueError,match='Install kokoro'):
        with transaction() as s:create(s)
    with Session() as s:assert s.query(Project).count()==0 and s.query(Job).count()==0


def test_failed_clip_never_triggers_export(local_models):
    pid=prepared();c=GenerationCoordinator();c.try_assembly(pid)
    with transaction() as s:
        jobs=s.query(Job).filter_by(project_id=pid).all()
        for j in jobs:j.state='ready'
        next(j for j in jobs if j.kind=='video').state='failed'
    c.try_assembly(pid)
    with Session() as s:assert s.query(Job).filter_by(project_id=pid,kind='render').count()==0
