"""Native worker: PostgreSQL polling, with the same coordinator and row locks.

No Celery or Redis is needed. A small bounded executor keeps provider polling
responsive during local renders; leases and paid submission recovery stay in the
coordinator. Stop drains active tasks before the database is stopped.
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select
from .db import Session, Job
from .coordinator import GenerationCoordinator, TERMINAL


def serve(stop, workers=2):
    running = {}
    attempted = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        while not stop.is_set():
            for job_id, future in list(running.items()):
                if future.done():
                    try:
                        future.result()
                    except Exception:
                        logging.exception('Native job processing failed: %s', job_id)
                    del running[job_id]
            try:
                with Session() as session:
                    now = time.time()
                    ids = list(session.scalars(select(Job.id).where(
                        Job.state.notin_(TERMINAL), Job.lease_until < now,
                        Job.next_run < now).order_by(Job.created)))
                    projects = set(session.scalars(select(Job.project_id).where(
                        Job.kind == 'narration', Job.state == 'ready')))
                attempted = {key:value for key,value in attempted.items() if key in ids}
                ids.sort(key=lambda key: attempted.get(key, 0))
                for job_id in ids:
                    if len(running) >= workers:
                        break
                    if job_id not in running:
                        attempted[job_id] = time.monotonic()
                        running[job_id] = executor.submit(GenerationCoordinator().process, job_id)
                for project_id in projects:
                    GenerationCoordinator().try_assembly(project_id)
            except Exception:
                logging.exception('Native job reconciliation failed; retrying')
            stop.wait(1)
