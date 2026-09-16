import base64
import httpx
import pytest
from fastapi.testclient import TestClient
from studio.api import app
from studio.db import transaction, Session, Project, Job
from studio.schemas import uid
from studio.providers import RunwayVideoProvider, ElevenLabsNarrationProvider, SunoMusicProvider, SubmissionUnknown
from studio.storage import run, LocalStorage


def test_live_gate_and_suno_boundary():
    with pytest.raises(ValueError,match='disabled'):
        RunwayVideoProvider().validate({'duration':5,'ratio':'1280:720','prompt':'Test'})
    with pytest.raises(ValueError,match='Suno disabled'):
        SunoMusicProvider().submit(uid(),{})


def test_runway_documented_contract_with_transport_mock(monkeypatch):
    monkeypatch.setenv('LIVE_GENERATION_ENABLED','true')
    monkeypatch.setenv('RUNWAY_API_KEY','test-only-not-a-real-key')
    requests=[]
    def request(method,url,**kwargs):
        requests.append((method,url,kwargs))
        body={'id':'task-123'} if method=='POST' else {'status':'SUCCEEDED','output':['https://cdn.example/media.mp4']}
        return httpx.Response(200,json=body,request=httpx.Request(method,url))
    monkeypatch.setattr(httpx,'request',request)
    provider=RunwayVideoProvider()
    submitted=provider.submit(uid(),{'duration':5,'ratio':'1280:720','prompt':'A river','model':'gen4.5'})
    assert submitted['provider_id']=='task-123'
    assert provider.result(provider.status('task-123'))['url'].endswith('media.mp4')
    provider.cancel('task-123')
    assert requests[0][1]=='https://api.dev.runwayml.com/v1/image_to_video'
    assert requests[0][2]['headers']['X-Runway-Version']=='2024-11-06'
    assert requests[0][2]['json']=={'model':'gen4.5','promptText':'A river','ratio':'1280:720','duration':5}
    assert requests[-1][0]=='DELETE'
    with pytest.raises(ValueError,match='reference'):
        provider.validate({'duration':5,'ratio':'960:960','prompt':'A river'})


def test_elevenlabs_timestamp_response_saved_with_context(monkeypatch):
    monkeypatch.setenv('LIVE_GENERATION_ENABLED','true');monkeypatch.setenv('ELEVENLABS_API_KEY','test-only')
    captured={}
    def request(method,url,**kwargs):
        captured.update(url=url,**kwargs)
        return httpx.Response(200,json={'audio_base64':base64.b64encode(b'fixture').decode(),'alignment':{'characters':['H','i'],'character_start_times_seconds':[0,.1],'character_end_times_seconds':[.1,.2]}},request=httpx.Request(method,url))
    monkeypatch.setattr(httpx,'request',request)
    result=ElevenLabsNarrationProvider().submit(uid(),{'text':'Hi','voice_id':'voice123','model':'eleven_multilingual_v2','voice_settings':{'stability':.5},'previous_text':'Before','next_text':'After'})
    assert captured['url'].endswith('/voice123/with-timestamps')
    assert captured['json']['previous_text']=='Before' and captured['json']['next_text']=='After'
    assert result['alignment']['characters']==['H','i']
    assert LocalStorage().path(result['local_path']).read_bytes()==b'fixture'


def test_api_upload_edit_conflict_and_missing_export(project_id):
    client=TestClient(app)
    settings=client.get(f'/api/projects/{project_id}').json()['settings']
    r=client.put(f'/api/projects/{project_id}',json={'name':'Edited','script':'A new script','settings':settings})
    assert r.status_code==200
    p=r.json()
    r=client.post(f'/api/projects/{project_id}/timeline',json={'revision':p['revision'],'operation':'add','values':{'track':'video','duration':48}})
    assert r.status_code==200
    p=r.json()
    r=client.post(f'/api/projects/{project_id}/timeline',json={'revision':0,'operation':'delete','item_id':p['timeline']['items'][0]['id']})
    assert r.status_code==409
    r=client.post(f'/api/projects/{project_id}/renders',json={'draft':False})
    assert r.status_code==400 and 'missing media' in r.json()['detail']
    storage=LocalStorage();audio=storage.temporary('.wav')
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=duration=1',str(audio)])
    r=client.post(f'/api/projects/{project_id}/assets',files={'file':('../../voice.wav',audio.read_bytes(),'audio/wav')})
    assert r.status_code==200
    asset=r.json()['assets'][0]
    assert asset['name']=='voice.wav' and asset['duration']==1
    response=client.get(f'/api/assets/{asset["id"]}/original',headers={'Range':'bytes=0-15'})
    assert response.status_code==206 and response.content[:4]==b'RIFF'
    assert client.post(f'/api/projects/{project_id}/assets',files={'file':('bad.mp4',b'not media')}).status_code==400


def test_recover_uncertain_narration_from_import_without_resubmit(project_id):
    client=TestClient(app)
    storage=LocalStorage();audio=storage.temporary('.wav')
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=duration=1',str(audio)])
    asset=client.post(f'/api/projects/{project_id}/assets',files={'file':('recovered.wav',audio.read_bytes(),'audio/wav')}).json()['assets'][0]
    with transaction() as s:
        job=Job(id=uid(),project_id=project_id,kind='music',provider='mock',state='submission_outcome_unknown',attempts=1,fingerprint='recovered',inputs={},estimated_cost=1)
        s.add(job);jid=job.id
    r=client.put(f'/api/jobs/{jid}/recovered-asset',json={'asset_id':asset['id']})
    assert r.status_code==200
    job=r.json()['jobs'][0]
    assert job['state']=='ready' and job['attempts']==1 and job['asset_id']==asset['id']


def test_ollama_structured_planning_contract(monkeypatch):
    import json
    from studio.planner import OllamaScriptPlanner,LocalScriptPlanner
    from studio.schemas import Settings
    monkeypatch.setenv('OLLAMA_URL','http://127.0.0.1:11434')
    monkeypatch.setenv('OLLAMA_MODEL','local-test-model')
    board=LocalScriptPlanner().plan('The river flows.',Settings())
    def post(url,**kwargs):
        assert url=='http://127.0.0.1:11434/api/chat'
        body=kwargs['json']
        assert body['stream'] is False and 'properties' in body['format']
        assert body['messages'][1]['role']=='user'
        return httpx.Response(200,json={'message':{'content':board.model_dump_json()}},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx,'post',post)
    result=OllamaScriptPlanner().plan('The river flows.',Settings())
    assert result.scenes[0].narration=='The river flows.'
    assert result.scenes[0].id==result.scenes[0].shots[0].scene_id


def test_postproduction_visual_prompt_edits_preserve_narration(project_id):
    client=TestClient(app)
    project=client.post(f'/api/projects/{project_id}/plan').json()
    assert client.post(f'/api/projects/{project_id}/produce').status_code==200
    board=project['storyboard']
    board['scenes'][0]['shots'][0]['prompt']='A new visual direction'
    assert client.put(f'/api/projects/{project_id}/storyboard',json={'storyboard':board}).status_code==200
    board['scenes'][0]['narration']='Changed narration invalidates measured timing'
    assert client.put(f'/api/projects/{project_id}/storyboard',json={'storyboard':board}).status_code==400
