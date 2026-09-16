"""Celery carries wakeups; PostgreSQL carries truth. Beat repairs missed wakeups."""
import os
import time
from celery import Celery
from sqlalchemy import select
from .db import Session, Job
from .coordinator import GenerationCoordinator, TERMINAL

celery = Celery('scriptstudio', broker=os.getenv('REDIS_URL','redis://redis:6379/0'))
celery.conf.update(task_acks_late=True, worker_prefetch_multiplier=1,
                   broker_connection_retry_on_startup=True,
                   beat_schedule={'reconcile-durable-jobs':{'task':'studio.reconcile','schedule':3.0}})

@celery.task(name='studio.process', soft_time_limit=540, time_limit=570)
def process(job_id):
    GenerationCoordinator().process(job_id)

@celery.task(name='studio.reconcile')
def reconcile():
    with Session() as session:
        jobs = list(session.scalars(select(Job).where(Job.state.notin_(TERMINAL),Job.lease_until<time.time(),Job.next_run<time.time()).order_by(Job.created)))
        for job in jobs:
            process.delay(job.id)
        project_ids = set(session.scalars(select(Job.project_id).where(Job.kind=='narration',Job.state=='ready')))
    for project_id in project_ids:
        GenerationCoordinator().try_assembly(project_id)
