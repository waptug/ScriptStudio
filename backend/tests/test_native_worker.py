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
