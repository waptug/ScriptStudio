"""Native worker: PostgreSQL polling, with the same coordinator and row locks.

No Celery or Redis is needed. A small bounded executor keeps provider polling
responsive during local renders; leases and paid submission recovery stay in the
coordinator. Stop drains active tasks before the database is stopped.
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, or_
from .db import Session, Job
from .coordinator import GenerationCoordinator, TERMINAL
from .resource_optimization import RenderResources, ResourcePreparationPending
from .providers import processing_mode


def serve(stop, workers=2):
    running = {}
    attempted = {}
    resources = RenderResources()
    try:
        _serve(stop, workers, running, attempted, resources)
    finally:
        resources.close()


def _serve(stop, workers, running, attempted, resources):
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
                    unfinished = list(session.execute(select(Job.kind, Job.provider).where(
                        or_(Job.state.notin_(TERMINAL), Job.id.in_(running)))))
                    projects = set(session.scalars(select(Job.project_id).where(
                        Job.kind == 'narration', Job.state == 'ready')))
                resources.update(any(kind == 'render' or processing_mode(provider) == 'local'
                                                     for kind, provider in unfinished))
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
            except ResourcePreparationPending:
                pass
            except Exception:
                logging.exception('Native job reconciliation failed; retrying')
            stop.wait(1)
