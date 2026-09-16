import pytest
from fastapi.testclient import TestClient
from studio.api import app
from studio.configuration import ConfigurationService, AdminUpdate, paid_permissions, require_paid, PaidGenerationDisabled
from studio.coordinator import GenerationCoordinator
from studio.db import transaction, Session, Job, Project
from studio.providers import Capabilities, RunwayVideoProvider, ElevenLabsNarrationProvider
from studio.schemas import uid


@pytest.mark.parametrize('category', ['text', 'video', 'audio', 'speech', 'music'])
def test_permissions_default_off_persist_and_are_independent(category, monkeypatch):
    monkeypatch.setenv('LIVE_GENERATION_ENABLED', 'false')
    client = TestClient(app)
    assert not any(client.get('/api/admin/settings').json()['paid_generation'].values())
    response = client.put('/api/admin/settings', json={'paid_generation': {'enabled': True, category: True}})
    assert response.status_code == 200
    assert client.get('/api/admin/settings').json()['paid_generation'][category] is True
    require_paid(category)
    for other in set(['text','video','audio','speech','music']) - {category}:
        with pytest.raises(PaidGenerationDisabled): require_paid(other)
    # Master off wins even over a true legacy environment flag, preserving category choices.
    client.put('/api/admin/settings', json={'paid_generation': {'enabled': False}})
    monkeypatch.setenv('LIVE_GENERATION_ENABLED', 'true')
    with pytest.raises(PaidGenerationDisabled): require_paid(category)
    assert paid_permissions()[category] is True
    assert client.get('/api/health').json()['live_enabled'] is False
    assert client.get('/api/providers').json()['paid_generation']['enabled'] is False


def test_invalid_permission_values_and_credentials_do_not_enable_spending():
    client = TestClient(app)
    assert client.put('/api/admin/settings', json={'paid_generation': {'video': 'false'}}).status_code == 422
    assert client.put('/api/admin/settings', json={'paid_generation': {'typo': True}}).status_code == 422
    response = client.put('/api/admin/settings', json={'credentials': {'RUNWAY_API_KEY': 'test-only'}})
    assert response.status_code == 200 and not any(response.json()['paid_generation'].values())


def test_provider_direct_calls_respect_category_and_enabling_does_not_bypass_budget(project_id, monkeypatch):
    monkeypatch.setenv('RUNWAY_API_KEY', 'test-only')
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'test-only')
    request = {'model':'gen4.5','duration':5,'ratio':'1280:720','prompt':'A river'}
    with pytest.raises(PaidGenerationDisabled): RunwayVideoProvider().submit(uid(), request)
    ConfigurationService().save(AdminUpdate(paid_generation={'enabled':True,'video':True}))
    with pytest.raises(PaidGenerationDisabled):
        ElevenLabsNarrationProvider().submit(uid(), {'text':'Hi','voice_id':'voice123'})
    with transaction() as session:
        with pytest.raises(ValueError, match='Spending limit'):
            GenerationCoordinator().enqueue(session, session.get(Project, project_id), 'video', 'runway', request)


def test_disabling_after_enqueue_blocks_submission_then_explicit_retry_works(project_id, monkeypatch):
    service = ConfigurationService()
    service.save(AdminUpdate(paid_generation={'enabled':True,'video':True}))
    class Provider:
        capabilities = Capabilities(True, True)
        calls = 0
        def submit(self, *args):
            self.calls += 1
            return {'provider_id':'fixture-task'}
        def status(self, pid): return {'status':'RUNNING'}
    provider = Provider()
    monkeypatch.setattr('studio.coordinator.get_provider', lambda *args: provider)
    with transaction() as session:
        job = Job(id=uid(), project_id=project_id, kind='video', provider='runway', state='queued', inputs={}, fingerprint='permissions', estimated_cost=1)
        session.add(job); jid = job.id
    service.save(AdminUpdate(paid_generation={'video':False}))
    coordinator = GenerationCoordinator(); coordinator.process(jid)
    with transaction() as session:
        job = session.get(Job, jid)
        assert job.state == 'failed' and job.attempts == 0
        assert job.result['safe_to_retry_submission'] and 'disabled in Admin' in job.error
        assert provider.calls == 0
        coordinator.retry(session, job)
    service.save(AdminUpdate(paid_generation={'video':True}))
    coordinator.process(jid)
    assert provider.calls == 1
    # Disabling does not lose the submitted task or poll by creating another task.
    service.save(AdminUpdate(paid_generation={'enabled':False}))
    with transaction() as session: session.get(Job, jid).next_run = 0
    coordinator.process(jid)
    with Session() as session:
        assert session.get(Job, jid).state == 'generating'
        assert session.get(Job, jid).provider_id == 'fixture-task'
    assert provider.calls == 1


def test_gateway_blocked_but_local_text_is_unaffected(monkeypatch):
    from studio.planner import HttpScriptPlanner, LocalScriptPlanner
    from studio.schemas import Settings
    monkeypatch.setenv('PLANNER_URL', 'http://127.0.0.1:9999')
    with pytest.raises(PaidGenerationDisabled): HttpScriptPlanner().plan('Hello world.', Settings())
    assert LocalScriptPlanner().plan('Hello world.', Settings()).scenes
