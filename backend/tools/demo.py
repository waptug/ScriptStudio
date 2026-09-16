"""Reproducible mock end-to-end demo against the running HTTP API."""
import argparse
import json
from pathlib import Path
import time
import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--url',default='http://api:8000')
parser.add_argument('--project')
parser.add_argument('--no-render',action='store_true')
args=parser.parse_args()
client=httpx.Client(base_url=args.url,timeout=60)
def request(method,path,**kwargs):
    response=client.request(method,path,**kwargs)
    response.raise_for_status()
    return response.json()

if args.project:
    project=request('GET','/api/projects/'+args.project)
else:
    script=Path('/app/samples/demo.txt').read_text()
    project=request('POST','/api/projects',json={'name':'A quieter world • verified demo','script':script})
    pid=project['id']
    request('POST',f'/api/projects/{pid}/plan')
    project=request('POST',f'/api/projects/{pid}/produce')
pid=project['id']
print(json.dumps({'project_id':pid,'stage':'production'}),flush=True)
end=time.time()+600
while time.time()<end:
    project=request('GET',f'/api/projects/{pid}')
    jobs=project['jobs']
    failures=[j for j in jobs if j['state'] in ('failed','submission_outcome_unknown')]
    if failures:raise RuntimeError(json.dumps([{'id':j['id'],'error':j['error']} for j in failures]))
    if any(j['kind']=='video' for j in jobs) and all(j['state']=='ready' for j in jobs):break
    time.sleep(1)
else:raise TimeoutError('Production did not complete')
settings=project['settings']
frames=max(i['start']+i['duration'] for i in project['timeline']['items'])
seconds=frames*settings['fps_den']/settings['fps_num']
assert 50<seconds<85,seconds
assert all(i['asset_id'] for i in project['timeline']['items'] if i['track'] in ('video','narration','music'))
print(json.dumps({'stage':'produced','duration':seconds,'assets':len(project['assets']),'shots':len([i for i in project['timeline']['items'] if i['track']=='video'])}),flush=True)
if not args.no_render:
    for preview in (True,False):
        result=request('POST',f'/api/projects/{pid}/renders',json={'preview':preview,'draft':False,'burn_captions':True})
        jid=result['jobs'][-1]['id']
        deadline=time.time()+600
        while time.time()<deadline:
            project=request('GET',f'/api/projects/{pid}')
            job=next(j for j in project['jobs'] if j['id']==jid)
            if job['state']=='ready':break
            if job['state'] in ('failed','submission_outcome_unknown'):raise RuntimeError(job['error'])
            time.sleep(2)
        else:raise TimeoutError('Render did not finish')
        asset=next(a for a in project['assets'] if a['id']==job['asset_id'])
        assert abs(asset['duration']-seconds)<.1
        media=client.get(f'/api/assets/{asset["id"]}/original',headers={'Range':'bytes=0-63'})
        assert media.status_code==206 and b'ftyp' in media.content
        print(json.dumps({'stage':'preview' if preview else 'export','job_id':jid,'asset_id':asset['id'],'duration':asset['duration'],'engine':job['result'].get('engine')}),flush=True)
    bundle=client.get(f'/api/jobs/{jid}/openshot')
    bundle.raise_for_status()
    assert bundle.content[:2]==b'PK'
    print(json.dumps({'stage':'openshot_bundle','bytes':len(bundle.content)}),flush=True)
