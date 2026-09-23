import threading
import time
from studio.db import transaction, Session, Job
from studio.native_worker import serve
from studio.schemas import uid


def test_native_worker_polls_durable_jobs_and_drains(project_id):
    """No queue wakeup: a saved local job must still finish and survive shutdown."""
    job_id=uid()
    with transaction() as session:
        session.add(Job(id=job_id,project_id=project_id,kind='music',provider='mock',
            state='queued',fingerprint=job_id,inputs={'duration':1,'mood':'calm'}))
    stop=threading.Event()
    worker=threading.Thread(target=serve,args=(stop,1))
    worker.start()
    try:
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            with Session() as session:
                state=session.get(Job,job_id).state
            if state in ('ready','failed'):
                break
            time.sleep(.1)
        assert state=='ready'
    finally:
        stop.set()
        worker.join(30)
    assert not worker.is_alive()
    with Session() as session:
        job=session.get(Job,job_id)
        assert job.asset_id and job.lease_until==0 and job.progress==1


def test_native_worker_reserves_before_render_and_restores_after_failure(project_id, monkeypatch):
    import studio.native_worker as worker_module
    events = []
    stop = threading.Event()
    job_id = uid()
    with transaction() as session:
        session.add(Job(id=job_id, project_id=project_id, kind='render', provider='local',
                        state='queued', fingerprint=job_id, inputs={}))

    class Resources:
        active = False
        def update(self, needed):
            self.active = needed
            events.append(('resources', needed))
            if not needed and ('process', job_id) in events:
                stop.set()
        def close(self):
            events.append(('closed', True))

    def process(self, key):
        assert events[-1] == ('resources', True)
        events.append(('process', key))
        with transaction() as session:
            session.get(Job, key).state = 'failed'
        raise RuntimeError('Simulated render failure')

    monkeypatch.setattr(worker_module, 'RenderResources', Resources)
    monkeypatch.setattr(worker_module.GenerationCoordinator, 'process', process)
    worker = threading.Thread(target=serve, args=(stop, 1))
    worker.start()
    worker.join(10)
    stop.set()
    worker.join(5)
    assert ('resources', False) in events
    assert events.index(('resources', True)) < events.index(('process', job_id))
    assert events[-1] == ('closed', True)


def test_real_native_render_restores_host(project_id, tmp_path, monkeypatch):
    """Opt-in host integration: real queued export, Windows settings and Docker."""
    import os
    import json
    import pytest
    from studio.resource_optimization import Host
    from studio.schemas import Settings, Timeline, Item
    from studio.storage import probe
    from pathlib import Path
    container = os.getenv('RESOURCE_TEST_CONTAINER')
    if not container:
        pytest.skip('Requires an isolated Docker validation container')
    config = {'enabled': True, 'containers': [container]}
    (tmp_path / 'resource-optimization.json').write_text(json.dumps(config))
    monkeypatch.setenv('SCRIPTSTUDIO_RESOURCE_DIR', str(tmp_path))
    host = Host(config)
    before = host.snapshot(os.getpid())
    job_id = uid()
    settings = Settings(width=320, height=180)
    timeline = Timeline(items=[Item(track='title', text='Resource restoration test', duration=24)])
    with transaction() as session:
        session.add(Job(id=job_id, project_id=project_id, kind='render', provider='local',
            state='queued', fingerprint=job_id, inputs={'timeline': timeline.model_dump(),
                'settings': settings.model_dump(), 'revision': 1, 'draft': True, 'preview': True}))
    import studio.native_worker as module
    original = module.GenerationCoordinator.process
    observed = []
    def process(self, key):
        rows = json.loads(host.run(host.docker + ['inspect', container]))
        observed.append(rows[0]['State']['Paused'])
        return original(self, key)
    monkeypatch.setattr(module.GenerationCoordinator, 'process', process)
    stop = threading.Event()
    worker = threading.Thread(target=serve, args=(stop, 1))
    worker.start()
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            with Session() as session:
                job = session.get(Job, job_id)
                state, result = job.state, job.result
            journal = tmp_path / 'resource-state.json'
            if state in ('ready', 'failed') and journal.exists() and not json.loads(journal.read_text())['pending']:
                break
            time.sleep(.2)
        assert state == 'ready', (state, result)
        assert observed == [True]
        assert not json.loads(journal.read_text())['pending']
        assert host.snapshot(os.getpid()) == before
        assert float(probe(Path(result['local_path']))['format']['duration']) > .9
    finally:
        stop.set()
        worker.join(60)
    assert not worker.is_alive()
