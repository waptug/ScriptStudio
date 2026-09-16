import json
import httpx
import pytest
from fastapi.testclient import TestClient
from studio.api import app
from studio.configuration import setting
from studio.db import Session, AppSetting, transaction, Job
from studio.schemas import uid
from studio.providers import RunwayVideoProvider


def test_admin_credentials_are_encrypted_write_only_and_used_by_provider(monkeypatch):
    client = TestClient(app)
    key = 'test-only-runway-credential'
    response = client.put('/api/admin/settings', json={
        'values': {'RUNWAY_MODEL': 'configured-model'}, 'credentials': {'RUNWAY_API_KEY': key}})
    assert response.status_code == 200
    assert key not in response.text and response.json()['credentials']['RUNWAY_API_KEY']['configured']
    with Session() as session:
        encrypted = session.get(AppSetting, 'RUNWAY_API_KEY').value
        assert key not in encrypted and encrypted.startswith('gAAAA')
    assert RunwayVideoProvider().headers()['Authorization'] == 'Bearer ' + key
    assert setting('RUNWAY_MODEL') == 'configured-model'
    assert key not in client.get('/api/admin/settings').text
    client.put('/api/admin/settings', json={'credentials': {'RUNWAY_API_KEY': ''}})
    assert setting('RUNWAY_API_KEY') == key
    monkeypatch.setenv('RUNWAY_API_KEY', 'environment-fallback')
    client.put('/api/admin/settings', json={'clear_credentials': ['RUNWAY_API_KEY']})
    assert setting('RUNWAY_API_KEY') == ''  # Clearing also overrides an environment key.


def test_admin_rejects_cross_origin_and_never_echoes_invalid_secrets():
    client = TestClient(app)
    assert client.put('/api/admin/settings', json={}, headers={'Origin': 'https://other.example'}).status_code == 403
    assert client.put('/api/admin/settings', data='{}', headers={'Content-Type': 'text/plain'}).status_code == 415
    response = client.put('/api/admin/settings', json={'credentials': {'RUNWAY_API_KEY': {'secret': 'never-echo-this'}}})
    assert response.status_code == 422 and 'never-echo-this' not in response.text
    assert client.put('/api/admin/settings', json={'values': {'RUNWAY_USD_PER_SECOND': 'nan'}}).status_code == 400
    assert client.put('/api/admin/settings', json={'values': {'OLLAMA_URL': 'http://user:password@localhost:11434'}}).status_code == 400


def test_writer_uses_selected_model_and_does_not_modify_saved_project(project_id, monkeypatch):
    client = TestClient(app)
    client.put('/api/admin/settings', json={'values': {
        'OLLAMA_URL': 'http://127.0.0.1:11434', 'OLLAMA_MODEL': 'planner-model',
        'SCRIPT_WRITER_MODEL': 'writer-model'}})
    before = client.get(f'/api/projects/{project_id}').json()
    def post(url, **kwargs):
        body = kwargs['json']
        assert body['model'] == 'writer-model' and body['stream'] is False and 'format' not in body
        assert 'target_seconds' in body['messages'][1]['content']
        return httpx.Response(200, json={'done': True, 'message': {'content': '[A garden]\n\nGrow a little joy today.'}}, request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx, 'post', post)
    response = client.post(f'/api/projects/{project_id}/script-draft', json={'prompt': 'Urban gardening', 'target_seconds': 30})
    assert response.status_code == 200 and response.json()['model'] == 'writer-model'
    assert response.json()['script'] == '[A garden] Grow a little joy today.'
    after = client.get(f'/api/projects/{project_id}').json()
    assert before == after
    assert client.post(f'/api/projects/{project_id}/script-draft', json={'prompt': '   '}).status_code == 422
    with transaction() as session:
        session.add(Job(id=uid(), project_id=project_id, kind='narration', provider='mock', state='queued', fingerprint='writer-test', inputs={}))
    assert client.post(f'/api/projects/{project_id}/script-draft', json={'prompt': 'New narration'}).status_code == 400


@pytest.mark.parametrize('result', [
    {'message': {'content': ''}},
    {'message': {'content': '[Only visual notes]'}},
    {'done_reason': 'length', 'message': {'content': 'Truncated.'}},
])
def test_writer_invalid_outputs_preserve_script(project_id, monkeypatch, result):
    monkeypatch.setenv('OLLAMA_URL', 'http://127.0.0.1:11434')
    monkeypatch.setenv('OLLAMA_MODEL', 'test-local')
    monkeypatch.setattr(httpx, 'post', lambda url, **kwargs: httpx.Response(200, json=result, request=httpx.Request('POST', url)))
    client = TestClient(app)
    response = client.post(f'/api/projects/{project_id}/script-draft', json={'prompt': 'Garden tour'})
    assert response.status_code == 400
    assert client.get(f'/api/projects/{project_id}').json()['script'] == 'Hello world.'


def test_local_model_discovery_and_cloud_rejection(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(httpx, 'get', lambda url, **kwargs: httpx.Response(200, json={'models': [{'name': 'local:4b'}, {'name': 'large:cloud'}]}, request=httpx.Request('GET', url)))
    response = client.post('/api/admin/ollama-models', json={'url': 'http://127.0.0.1:11434'})
    assert response.json() == {'models': ['local:4b']}
    assert client.put('/api/admin/settings', json={'values': {'SCRIPT_WRITER_MODEL': 'large:cloud'}}).status_code == 400
    assert client.post('/api/admin/ollama-models', json={'url': 'http://8.8.8.8:11434'}).status_code == 400
