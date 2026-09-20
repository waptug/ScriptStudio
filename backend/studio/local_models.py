"""Portable, explicitly requested model installations. No inference imports here."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import threading
import time
import zipfile
import httpx
from .db import AppSetting, Session, transaction
from .configuration import setting

GIB = 1024**3
CATALOG = {
    'kokoro': dict(name='Kokoro-82M', kind='narration', gpu=False, license='Apache-2.0', url='https://huggingface.co/hexgrad/Kokoro-82M', preset='English stock voices · CPU', voices=['af_heart','af_bella','af_nicole','am_adam','am_michael','bf_emma','bm_george']),
    'wan': dict(name='Wan 2.1 T2V-1.3B', kind='video', gpu=True, license='Apache-2.0', url='https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers', preset='480p · 81 frames at 16 fps · CPU offload'),
    'ace_step': dict(name='ACE-Step 1.5', kind='music', gpu=True, license='MIT', url='https://github.com/ace-step/ACE-Step-1.5', preset='Turbo · batch one · CPU offload · instrumental by default'),
    'stable_audio': dict(name='Stable Audio Open Small', kind='sfx', gpu=True, license='Stability AI Community License; commercial conditions apply', url='https://huggingface.co/stabilityai/stable-audio-open-small', preset='English · up to 11 seconds', gated=True),
}


def root():
    path = Path(os.getenv('LOCAL_MODELS_ROOT', str(Path(os.getenv('MEDIA_ROOT','/tmp/scriptstudio-media')).parent / 'local-models')))
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def manifest(name):
    if name not in CATALOG: raise ValueError('Unknown local model')
    file = Path(__file__).with_name('model_locks') / (name+'.json')
    return json.loads(file.read_text()) if file.exists() else None


def state(name):
    with Session() as session:
        row = session.get(AppSetting, 'local_model:'+name)
        return json.loads(row.value) if row else {'state':'not_installed', 'progress':0}


def public_state(saved):
    # Runtime hashes belong to verification, not the repeatedly polled UI payload.
    return {key:value for key,value in saved.items() if key != 'inventory'}


def update(name, **values):
    with transaction() as session:
        row = session.query(AppSetting).filter_by(key='local_model:'+name).with_for_update().one_or_none()
        old = json.loads(row.value) if row else {}
        value = json.dumps({**old, **values, 'updated':time.time()})
        if row: row.value = value
        else: session.add(AppSetting(key='local_model:'+name, value=value))


@contextmanager
def file_reservation(path):
    """Nonblocking, crash-released OS lock, shared by all native processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            if handle.tell()==0: handle.write(b'0'); handle.flush()
            handle.seek(0)
            try: msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError: raise ValueError('Resource busy; wait for the active operation') from None
        else:
            import fcntl
            try: fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise ValueError('Resource busy; wait for the active operation') from None
        try: yield
        finally:
            if os.name == 'nt':
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def digest(path, canceled=None, report=None):
    with path.open('rb') as stream:
        if canceled is None and report is None: return hashlib.file_digest(stream,'sha256').hexdigest()
        checksum=hashlib.sha256()
        while True:
            if canceled and canceled(): raise InterruptedError('Verification canceled; downloaded files are preserved')
            chunk=stream.read(8*1024*1024)
            if not chunk: return checksum.hexdigest()
            checksum.update(chunk)
            if report: report(len(chunk))


def safe_path(base, relative):
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()) or path == base.resolve():
        raise ValueError('Unsafe artifact path')
    return path


def download(artifact, target, canceled, report, token=None, checking=None):
    """Resume only the immutable artifact; verify bytes before promoting .part."""
    target.parent.mkdir(parents=True, exist_ok=True)
    def checksum(path):
        if checking: checking(path.name)
        return digest(path,canceled)
    if target.exists() and target.stat().st_size==artifact['size'] and checksum(target)==artifact['sha256']:
        report(artifact['size'])
        return
    partial = target.with_name(target.name+'.part')
    offset = partial.stat().st_size if partial.exists() else 0
    if offset == artifact['size'] and checksum(partial) == artifact['sha256']:
        partial.replace(target)
        report(offset)
        return
    if offset >= artifact['size']: partial.unlink(); offset=0
    headers = {'Range':f'bytes={offset}-'} if offset else {}
    if token: headers['Authorization']='Bearer '+token
    try:
        with httpx.stream('GET',artifact['url'],headers=headers,follow_redirects=True,timeout=60) as response:
            if response.status_code in (401,403): raise ValueError('Upstream access denied. Accept the model license and save an authorized Hugging Face token in Admin.')
            response.raise_for_status()
            if offset and response.status_code==206:
                if not response.headers.get('Content-Range','').startswith(f'bytes {offset}-'): raise ValueError('Invalid download resume response')
            elif response.status_code==200: offset=0
            else: raise ValueError('Unexpected download response')
            with partial.open('ab' if offset else 'wb') as output:
                for chunk in response.iter_bytes(1024*1024):
                    if canceled(): raise InterruptedError('Installation canceled; resume preserves partial downloads')
                    offset += len(chunk)
                    if offset > artifact['size']: raise ValueError('Artifact exceeds pinned size')
                    output.write(chunk); report(offset)
        if offset!=artifact['size'] or checksum(partial)!=artifact['sha256']:
            partial.unlink(missing_ok=True)
            raise ValueError('Artifact checksum mismatch; corrupt download discarded')
        partial.replace(target)
    except httpx.HTTPError:
        # Never expose redirect URLs, bearer tokens or response bodies.
        raise ValueError('Download interrupted; use Resume to retry the pinned artifact') from None


def copy_chunks(source, target, canceled, report=None):
    while True:
        if canceled(): raise InterruptedError('Installation canceled')
        chunk = source.read(1024*1024)
        if not chunk: break
        target.write(chunk)
        if report: report(len(chunk))


def extract(archive, destination, canceled, report=None):
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            if canceled(): raise InterruptedError('Installation canceled')
            output = safe_path(destination, info.filename)
            if info.external_attr >> 16 & 0o170000 == 0o120000: raise ValueError('Symlinks are not permitted in runtime archives')
            if info.is_dir(): output.mkdir(parents=True, exist_ok=True); continue
            output.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, output.open('wb') as target: copy_chunks(source,target,canceled,report)


def extract_wheel(archive, runtime, canceled, report=None):
    """Install a pinned wheel without resolving or downloading dependencies.

    Model runtimes are embedded Python distributions. Respect wheel .data
    locations rather than treating a wheel as an ordinary site-packages ZIP.
    """
    library = runtime / 'Lib/site-packages'
    schemes = {'purelib': library, 'platlib': library,
               'scripts': runtime / 'Scripts', 'data': runtime,
               'headers': runtime / 'Include'}
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            if canceled(): raise InterruptedError('Installation canceled')
            parts = Path(info.filename).parts
            if not parts: continue
            if parts[0].endswith('.data'):
                if len(parts) < 3:
                    if info.is_dir(): continue
                    raise ValueError('Invalid wheel data entry')
                if parts[1] not in schemes: raise ValueError('Unknown wheel install scheme')
                base = schemes[parts[1]]
                relative = str(Path(*parts[2:]))
            else:
                base, relative = library, info.filename
            output = safe_path(base, relative)
            if info.external_attr >> 16 & 0o170000 == 0o120000:
                raise ValueError('Symlinks are not permitted in wheels')
            if info.is_dir(): output.mkdir(parents=True, exist_ok=True); continue
            output.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, output.open('wb') as target:
                copy_chunks(source, target, canceled, report)


class LocalModelService:
    def catalog(self):
        models=[]
        for name, info in CATALOG.items():
            lock=manifest(name); saved=state(name)
            if saved.get('state') in ('downloading','verifying','installing') and saved.get('updated',0)<time.time()-120:
                # Large wheels can take minutes to expand or hash. The OS lock
                # identifies a live installer even when its progress is unchanged.
                try:
                    with file_reservation(root()/(name+'.lock')):
                        saved={**saved,'state':'interrupted','error':'Installation interrupted; resume or verify before use'}
                except ValueError:
                    pass
            ready=saved.get('state')=='ready' and bool(lock) and (root()/name/'runtime/python.exe').is_file() and saved.get('revision')==lock['revision']
            models.append({**info,**public_state(saved),'id':name,'ready':ready,
                'supported':os.name=='nt', 'installable':bool(lock),
                'download_bytes':sum(a['size'] for a in lock['artifacts']) if lock else None,
                'installed_bytes':lock.get('expanded_bytes') if lock else None,
                'revision':lock['revision'] if lock else None,
                'guidance':'Install and verify in the native Windows application' if not ready else 'Installed; offline generation available'})
        return {'models':models,'working_allowance_bytes':2*GIB,'hardware':hardware()}

    def require_ready(self,name):
        model=next(m for m in self.catalog()['models'] if m['id']==name)
        if not model['ready']: raise ValueError(f"{model['name']} is unavailable. Open Admin → Local models and install or verify it.")
        return manifest(name)

    def action(self,name,action,accept_license=False):
        lock=manifest(name)
        if action=='cancel':
            update(name,cancel=True); return public_state(state(name))
        if action not in ('install','resume','verify','uninstall'): raise ValueError('Unknown installation action')
        if action!='uninstall' and not lock: raise ValueError('Pinned native artifacts are not available for this model in this build')
        if action=='install':
            saved=state(name)
            if saved.get('state')=='ready' and saved.get('revision')==lock['revision'] and (root()/name/'runtime/python.exe').is_file():
                return public_state(saved)  # Reuse the durable verified installation.
        if action in ('install','resume'):
            if os.name!='nt': raise ValueError('Install local models from the native Windows application')
            if CATALOG[name].get('gated'):
                if not (accept_license or state(name).get('license_accepted')): raise ValueError('Accept the upstream license, including applicable commercial conditions, before installing')
                if not setting('HF_TOKEN'): raise ValueError('Save your authorized Hugging Face token in Admin first')
        # Acquire synchronously: two clicks cannot schedule overlapping mutations.
        reservation=file_reservation(root()/'installation.lock')
        reservation.__enter__()
        model_guard=file_reservation(root()/(name+'.lock'))
        try: model_guard.__enter__()
        except Exception: reservation.__exit__(None,None,None); raise
        update(name,state='verifying' if action=='verify' else 'installing',cancel=False,error=None,
               phase='preparing',detail='Preparing '+action,progress=None,completed_bytes=0,total_bytes=None,
               started_at=time.time(),heartbeat=time.time(),progress_updated=time.time(),
               license_accepted=accept_license or state(name).get('license_accepted',False))
        def work():
            stopped = threading.Event()
            def heartbeat():
                while not stopped.wait(2):
                    update(name,heartbeat=time.time())
            pulse = threading.Thread(target=heartbeat,daemon=True,name='model-heartbeat-'+name)
            pulse.start()
            try:
                if action=='uninstall':
                    shutil.rmtree(root()/name,ignore_errors=True)
                    update(name,state='not_installed',progress=0,inventory=None)
                else: self.install(name,lock,verify_only=action=='verify')
            except InterruptedError as exc: update(name,state='interrupted',error=str(exc))
            except Exception as exc: update(name,state='failed',error=str(exc)[:500])
            finally:
                stopped.set()
                pulse.join()
                model_guard.__exit__(None,None,None); reservation.__exit__(None,None,None)
        threading.Thread(target=work,daemon=True,name='model-install-'+name).start()
        return public_state(state(name))

    def install(self,name,lock,verify_only=False):
        base=root()/name; base.mkdir(parents=True,exist_ok=True)
        last_poll=0.0
        cancel_requested=False
        def canceled():
            nonlocal last_poll,cancel_requested
            now=time.monotonic()
            if now-last_poll>=.5:
                cancel_requested=bool(state(name).get('cancel'))
                last_poll=now
            return cancel_requested
        last_report=0.0
        def report(phase,detail,completed=0,total=None,force=False):
            nonlocal last_report
            now=time.monotonic()
            if force or now-last_report>=.5:
                update(name,phase=phase,detail=detail,completed_bytes=completed,total_bytes=total,
                       progress=min(1,completed/total) if total else None,progress_updated=time.time())
                last_report=now
        if not verify_only:
            remaining=0
            for artifact in lock['artifacts']:
                path=safe_path(base,artifact['path'])
                have=path.stat().st_size if path.exists() else path.with_name(path.name+'.part').stat().st_size if path.with_name(path.name+'.part').exists() else 0
                remaining+=max(0,artifact['size']-have)
            required=remaining+lock['expanded_bytes']+2*GIB
            free=shutil.disk_usage(base).free
            if free<required: raise ValueError(f'Insufficient space: need {required/GIB:.1f} GiB; available {free/GIB:.1f} GiB (includes expanded runtime and 2 GiB allowance)')
            total=sum(a['size'] for a in lock['artifacts']); done=0
            def progress(downloaded):
                report('downloading',artifact['path'],done+downloaded,total,downloaded==artifact['size'])
            for artifact in lock['artifacts']:
                if canceled(): raise InterruptedError('Installation canceled')
                target=safe_path(base,artifact['path'])
                update(name,state='downloading')
                report('downloading',artifact['path'],done,total,True)
                download(artifact,target,canceled,progress,setting('HF_TOKEN') if artifact.get('gated') else None,
                         checking=lambda filename: report('checking_download',filename,force=True))
                done+=artifact['size']
            update(name,state='installing')
            archives=[a for a in lock['artifacts'] if a.get('wheel') or a.get('extract')]
            expanded=0
            for artifact in archives:
                with zipfile.ZipFile(safe_path(base,artifact['path'])) as bundle:
                    expanded+=sum(info.file_size for info in bundle.infolist() if not info.is_dir())
            unpacked=0
            def extracted(count):
                nonlocal unpacked
                unpacked+=count
                report('extracting',artifact['path'],unpacked,expanded,unpacked==expanded)
            for artifact in archives:
                report('extracting',artifact['path'],unpacked,expanded,True)
                if artifact.get('wheel'):
                    extract_wheel(safe_path(base,artifact['path']),base/'runtime',canceled,extracted)
                else:
                    extract(safe_path(base,artifact['path']),safe_path(base,artifact['extract']),canceled,extracted)
            # Embedded Python searches only this portable environment, never global packages.
            python_tag = lock.get('python_tag', 'python312')
            if python_tag not in ('python310', 'python311', 'python312'):
                raise ValueError('Unsupported embedded Python version')
            extra_paths = lock.get('python_paths', [])
            for relative in extra_paths:
                if '\n' in relative or '\r' in relative: raise ValueError('Invalid Python package path')
                safe_path(base/'runtime', relative)
            paths = [python_tag+'.zip', '.', 'Lib/site-packages', *extra_paths, 'import site']
            (base/f'runtime/{python_tag}._pth').write_text('\n'.join(paths)+'\n')
        update(name,state='verifying')
        checked=0
        total_check=sum(a['size'] for a in lock['artifacts'])
        def checked_bytes(count):
            nonlocal checked
            checked+=count
            report('verifying',current_file,checked,total_check,checked==total_check)
        for artifact in lock['artifacts']:
            path=safe_path(base,artifact['path'])
            current_file=artifact['path']
            report('verifying',current_file,checked,total_check,True)
            # Install/resume has already verified the pinned download checksums.
            if not path.is_file() or (verify_only and digest(path,canceled,checked_bytes)!=artifact['sha256']): raise ValueError('Missing or corrupt artifact; Resume to repair')
            if not verify_only: checked+=artifact['size']
            if canceled(): raise InterruptedError('Verification canceled')
        report('inventory','Scanning installed runtime',force=True)
        files=[p for p in (base/'runtime').rglob('*') if p.is_file() and '__pycache__' not in p.parts]
        total_check=sum(p.stat().st_size for p in files)
        checked=0
        inventory={}
        for path in files:
            current_file=str(path.relative_to(base))
            report('verifying',current_file,checked,total_check)
            inventory[current_file]=digest(path,canceled,checked_bytes)
        previous=state(name).get('inventory')
        if verify_only and (not previous or inventory!=previous): raise ValueError('Expanded runtime is missing or changed; Resume to repair')
        if not (base/'runtime/python.exe').is_file(): raise ValueError('Native Python runtime missing')
        from .local_inference import probe
        report('probing','Testing model runtime and device support',force=True)
        probe(name)
        if canceled(): raise InterruptedError('Verification canceled')
        update(name,state='ready',phase='complete',detail='Installation verified',progress=1,revision=lock['revision'],inventory=inventory,error=None)


def hardware():
    import subprocess
    try:
        result=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.free,driver_version','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode: raise ValueError()
        rows=[r.split(',') for r in result.stdout.strip().splitlines()]
        return {'gpus':[dict(name=r[0].strip(),total_mib=int(r[1]),free_mib=int(r[2]),driver=r[3].strip()) for r in rows], 'guidance':'CUDA execution is probed during verification. Target: RTX 3060 12 GB, 32 GB RAM.'}
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return {'gpus':[],'guidance':'NVIDIA GPU not detected. Kokoro uses CPU. Install a compatible NVIDIA driver for GPU models; ScriptStudio does not change drivers.'}
