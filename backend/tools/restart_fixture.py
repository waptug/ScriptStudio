"""Prepare and verify an already-submitted job across real service restarts."""
import json
from pathlib import Path
import sys
import time
from studio.db import transaction,Session,Project,Job
from studio.schemas import Settings,Item,uid
from studio.providers import MockVideoProvider
from studio.timeline import TimelineService
from studio.storage import LocalStorage

manifest=LocalStorage().path('tmp/restart-fixture.json')
if sys.argv[1]=='prepare':
    jid=uid();inputs={'prompt':'Restart fixture','duration':2,'placeholder_id':uid(),'shot_id':'restart-shot'}
    result=MockVideoProvider().submit(jid,inputs)
    with transaction() as s:
        p=Project(id=uid(),name='Restart recovery acceptance fixture',script='',original_script='',settings=Settings().model_dump())
        s.add(p);s.flush()
        TimelineService().save(s,p,{'items':[Item(id=inputs['placeholder_id'],track='video',duration=48,shot_id='restart-shot').model_dump()]})
        s.add(Job(id=jid,project_id=p.id,kind='video',provider='mock',state='submitted',provider_id=jid,attempts=1,inputs=inputs,result=result,fingerprint='restart-test',estimated_cost=0,lease_until=0))
    manifest.write_text(json.dumps({'job_id':jid,'provider_id':jid}))
    print('Prepared existing submitted job '+jid)
else:
    record=json.loads(manifest.read_text())
    for _ in range(90):
        with Session() as s:
            job=s.get(Job,record['job_id'])
            if job.state=='ready':
                assert job.provider_id==record['provider_id'] and job.attempts==1
                project=s.get(Project,job.project_id)
                assert project.timeline['items'][0]['asset_id']==job.asset_id
                print('PASS: submitted job resumed after service restart, with one submission and one placement')
                break
            if job.state=='failed':raise RuntimeError(job.error)
        time.sleep(1)
    else:raise TimeoutError('Recovery did not finish')
