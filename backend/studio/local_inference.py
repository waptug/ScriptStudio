"""Owned inference subprocesses and cross-project GPU/Ollama coordination."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
from sqlalchemy import text
from .db import engine, Session, Job, project_lock
from .local_models import CATALOG, LocalModelService, root, file_reservation, hardware


class GPUWaiting(ValueError): pass


@contextmanager
def gpu_reservation():
    # Session advisory locks survive commits and are released on connection loss.
    # The OS lock also protects against a paused/crashed worker with a live child.
    with engine.connect() as connection:
        postgres=connection.dialect.name=='postgresql'
        if postgres and not connection.scalar(text('SELECT pg_try_advisory_lock(734192061)')):
            raise GPUWaiting('Waiting for another local media or Ollama request')
        try:
            try:
                with file_reservation(root()/'gpu.lock'): yield
            except ValueError as exc:
                if str(exc).startswith('Resource busy'): raise GPUWaiting('Waiting for GPU reservation') from None
                raise
        finally:
            if postgres: connection.execute(text('SELECT pg_advisory_unlock(734192061)'))


def environment():
    env=os.environ.copy()
    for key in ('HF_TOKEN','HUGGING_FACE_HUB_TOKEN','RUNWAY_API_KEY','ELEVENLABS_API_KEY'):
        env.pop(key,None)
    for key,folder in {'HF_HOME':'hf','HUGGINGFACE_HUB_CACHE':'hf/hub','TRANSFORMERS_CACHE':'hf/transformers','TORCH_HOME':'torch','XDG_CACHE_HOME':'cache','TEMP':'scratch','TMP':'scratch','TMPDIR':'scratch','PYTHONPYCACHEPREFIX':'pycache','NUMBA_CACHE_DIR':'numba'}.items():
        path=root()/folder;path.mkdir(parents=True,exist_ok=True);env[key]=str(path)
    env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',PYTHONUTF8='1')
    return env


def command(name,*args):
    return [str(root()/name/'runtime/python.exe'),str(Path(__file__).with_name('local_model_runner.py')),*args]


def probe(name):
    result=subprocess.run(command(name,'--probe',name),env=environment(),capture_output=True,text=True,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        raise ValueError('Native runtime/CUDA probe failed. Check installed NVIDIA driver compatibility; Resume to repair dependencies. '+result.stderr[-600:])


def unload_ollama():
    from .configuration import setting
    if not setting('OLLAMA_URL'): return
    from .local_llm import LocalOllama
    import httpx
    # Validate private/local URL using the same adapter as writing/planning.
    client=LocalOllama()
    try:
        response=httpx.get(client.url+'/api/ps',timeout=10);response.raise_for_status()
        for model in response.json().get('models',[]):
            response=httpx.post(client.url+'/api/generate',json={'model':model['name'],'keep_alive':0},timeout=30)
            response.raise_for_status()
    except (httpx.HTTPError,KeyError,ValueError):
        raise GPUWaiting('Waiting for Ollama to release its idle models') from None


def report(job_id, **changes):
    with Session.begin() as session:
        job=session.get(Job,job_id)
        project_lock(session,job.project_id)
        session.refresh(job)
        if job.state=='canceled': raise InterruptedError('Local inference canceled')
        for key,value in changes.items(): setattr(job,key,value)
        job.updated=time.time();job.lease_until=time.time()+60


def run_inference(name,job_id,request):
    LocalModelService().require_ready(name)
    with file_reservation(root()/(name+'.lock')):
        if CATALOG[name]['gpu']:
            with gpu_reservation():
                unload_ollama()
                gpus=hardware()['gpus']
                if not gpus: raise ValueError('NVIDIA GPU unavailable; verify local model runtime and driver in Admin')
                if gpus[0]['free_mib']<8500: raise GPUWaiting('Waiting for other applications to release GPU memory (8.5 GiB free required)')
                return owned_process(name,job_id,request)
        return owned_process(name,job_id,request)


def owned_process(name,job_id,request):
    from .storage import LocalStorage
    folder=LocalStorage().path('tmp/local-'+job_id);folder.mkdir(parents=True,exist_ok=True)
    request_file=folder/'request.json'; status_file=folder/'status.json'; output=folder/('output.mp4' if name=='wan' else 'output.wav')
    status_file.unlink(missing_ok=True)
    request_file.write_text(json.dumps(dict(request,model_root=str(root()/name),output=str(output),status=str(status_file))),encoding='utf-8')
    started=time.monotonic()
    report(job_id,state='loading',error=None)
    with (folder/'inference.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command(name,name,str(request_file)),env=environment(),stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            while process.poll() is None:
                status={}
                try: status=json.loads(status_file.read_text())
                except (OSError,ValueError): pass
                report(job_id,state=status.get('state','loading'),progress=min(.99,float(status.get('progress',0))),result={'elapsed_seconds':round(time.monotonic()-started),'steps':status.get('steps')})
                time.sleep(1)
            report(job_id,state='validating')
            if process.returncode or not output.is_file():
                raise ValueError('Local inference failed. See the portable media/tmp/local-'+job_id+'/inference.log; verify the model installation.')
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
    return {'provider_id':job_id,'local_path':str(output),'model_revision':request['model_revision'],
            'seed':request['seed'],'elapsed_seconds':round(time.monotonic()-started,2),
            'caption_method':'estimated from measured speech duration' if name=='kokoro' else None}
