import httpx
from fastapi.testclient import TestClient
from studio.api import app
from studio.configuration import setting
from studio.db import transaction, AppSetting
from studio import ollama_discovery as discovery


def reply(url, models):
    return httpx.Response(200, json={'models':models}, request=httpx.Request('GET',url))


def test_detects_host_saves_url_and_excludes_remote_models(monkeypatch):
    calls=[]
    monkeypatch.setattr(discovery,'candidates',lambda:['http://127.0.0.1:11434'])
    def get(url,**kwargs):
        calls.append(url)
        assert kwargs['trust_env'] is False and kwargs['follow_redirects'] is False
        return reply(url,[{'name':'local:4b'},{'name':'big:cloud'},{'name':'remote','remote_host':'ollama.com'}])
    monkeypatch.setattr(httpx,'get',get)
    result=TestClient(app).post('/api/admin/ollama-discover',json={}).json()
    assert result['saved'] and result['models']==['local:4b']
    assert setting('OLLAMA_URL')=='http://127.0.0.1:11434'
    assert calls==['http://127.0.0.1:11434/api/tags']
    assert not setting('OLLAMA_MODEL')  # User chooses the model; no generation/download.


def test_preserves_manual_url_even_when_another_server_is_found(monkeypatch):
    with transaction() as session:session.add(AppSetting(key='OLLAMA_URL',value='http://127.0.0.1:22222'))
    monkeypatch.setattr(discovery,'candidates',lambda:['http://127.0.0.1:11434'])
    monkeypatch.setattr(httpx,'get',lambda url,**kw:reply(url,[]))
    result=discovery.discover()
    assert result['status']=='found' and result['models']==[] and not result['saved']
    assert setting('OLLAMA_URL')=='http://127.0.0.1:22222'
    assert not discovery.save_if_empty('http://127.0.0.1:11434')


def test_unavailable_or_non_ollama_server_does_not_save(monkeypatch):
    monkeypatch.setattr(discovery,'candidates',lambda:['http://127.0.0.1:11434'])
    monkeypatch.setattr(httpx,'get',lambda url,**kw:httpx.Response(200,json={'other':'server'},request=httpx.Request('GET',url)))
    assert discovery.discover()['status']=='unavailable'
    assert not setting('OLLAMA_URL')


def test_public_hosts_are_not_probed(monkeypatch):
    monkeypatch.setattr(discovery,'candidates',lambda:['http://8.8.8.8:11434'])
    def forbidden(*args,**kw):raise AssertionError('Must not probe public host')
    monkeypatch.setattr(httpx,'get',forbidden)
    assert discovery.discover()['status']=='unavailable'


def test_custom_host_port_is_discovered_and_wildcard_is_loopback(monkeypatch):
    monkeypatch.setenv('OLLAMA_HOST','0.0.0.0:12345')
    assert 'http://127.0.0.1:12345' in discovery.candidates()


def test_invalid_host_environment_does_not_block_loopback_discovery(monkeypatch):
    monkeypatch.setenv('OLLAMA_HOST','0.0.0.0:invalid')
    assert 'http://127.0.0.1:11434' in discovery.candidates()
