"""Real PostgreSQL row-lock tests; no external provider calls."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from studio.db import transaction, project_lock, Project, Job, Session
from studio.schemas import Settings, uid
from studio.budget import BudgetService
from studio.coordinator import GenerationCoordinator

with transaction() as s:
    p=Project(id=uid(),name='Concurrency acceptance fixture',script='',original_script='',settings=Settings(spending_limit=1,max_concurrency=1).model_dump())
    s.add(p);pid=p.id
barrier=Barrier(2)
def reserve(number):
    barrier.wait()
    try:
        with transaction() as s:
            p=project_lock(s,pid)
            BudgetService().reserve(s,p,.6)
            s.add(Job(id=uid(),project_id=pid,kind='video',provider='mock',state='submission_outcome_unknown',estimated_cost=.6,fingerprint=str(number),inputs={}))
        return True
    except ValueError:return False
with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(reserve,range(2)))
assert sorted(results)==[False,True],results
with transaction() as s:
    jobs=[]
    for number in range(2):
        j=Job(id=uid(),project_id=pid,kind='video',provider='mock',state='queued',estimated_cost=0,fingerprint=str(number),inputs={})
        s.add(j);jobs.append(j.id)
barrier=Barrier(2)
def claim(jid):
    barrier.wait();return GenerationCoordinator().claim(jid)
with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(claim,jobs))
assert sorted(results)==[False,True],results
# Release test leases without making the fixture eligible for production.
with transaction() as s:
    for j in s.query(Job).filter_by(project_id=pid):j.state='canceled';j.lease_until=0
print('PASS: concurrent PostgreSQL reservations cannot bypass budget; queued claims obey max concurrency')
