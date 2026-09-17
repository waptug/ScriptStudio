"""Build a single Windows EXE with offline Docker images and matching app source.

Requires the current Compose images, Python, and a Windows .NET Framework C#
compiler reachable through WSL. No credentials, volumes, or user media are read.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/windows'
STAGE = OUT / 'build'


def run(*args, **kwargs):
    try:
        output = subprocess.check_output(args, cwd=ROOT, **kwargs)
    except OSError as error:
        if error.errno != 8 or not str(args[0]).endswith('.exe'):
            raise
        # WSL binfmt registration can be absent in a nested process. Its loader
        # expects both the executable path and original argv[0] (binfmt P flag).
        output = subprocess.check_output(['/init',args[0],args[0],*args[1:]],cwd=ROOT,**kwargs)
    return output.decode().strip()


def windows(path):
    return run('wslpath', '-w', str(path))


def release_compose(images):
    environment = {
        'DATABASE_URL':'postgresql+psycopg://studio:${POSTGRES_PASSWORD:?Missing package database password}@db/studio',
        'REDIS_URL':'redis://redis:6379/0', 'MEDIA_ROOT':'/data',
        'LIVE_GENERATION_ENABLED':'false', 'RUNWAY_API_KEY':'', 'ELEVENLABS_API_KEY':'',
        'OLLAMA_URL':'', 'OLLAMA_MODEL':'', 'SCRIPT_WRITER_MODEL':'', 'PLANNER_URL':'',
        'RUNWAY_MODEL':'gen4.5', 'RUNWAY_USD_PER_SECOND':'0.12',
        'ELEVENLABS_MODEL':'eleven_multilingual_v2', 'ELEVENLABS_USD_PER_CHARACTER':'',
        'DOWNLOAD_HOSTS':'*.runwayml.com,*.cloudfront.net',
    }
    common = {'image':images['api'], 'pull_policy':'never', 'environment':environment,
              'volumes':['media:/data'], 'extra_hosts':['host.docker.internal:host-gateway']}
    dependencies = {'migrate':{'condition':'service_completed_successfully'},'redis':{'condition':'service_healthy'}}
    services = {
        'db':{'image':images['db'],'pull_policy':'never','environment':{'POSTGRES_USER':'studio','POSTGRES_DB':'studio','POSTGRES_PASSWORD':'${POSTGRES_PASSWORD:?Missing package database password}'},
              'volumes':['database:/var/lib/postgresql/data'],'healthcheck':{'test':['CMD-SHELL','pg_isready -U studio'],'interval':'3s','retries':20}},
        'redis':{'image':images['redis'],'pull_policy':'never','healthcheck':{'test':['CMD','redis-cli','ping'],'interval':'3s','retries':20}},
        'migrate':{**common,'command':['alembic','upgrade','head'],'depends_on':{'db':{'condition':'service_healthy'},'redis':{'condition':'service_healthy'}}},
        'api':{**common,'depends_on':dependencies},
        'worker':{**common,'command':['celery','-A','studio.worker:celery','worker','--loglevel=warning','--concurrency=4'],'depends_on':dependencies},
        'beat':{**common,'command':['celery','-A','studio.worker:celery','beat','--loglevel=warning','--schedule=/tmp/celerybeat'],'depends_on':dependencies},
        'web':{'image':images['web'],'pull_policy':'never','ports':['127.0.0.1:${SCRIPTSTUDIO_PORT:-8088}:80'],'depends_on':['api']},
    }
    return {'services':services,'volumes':{'database':{},'media':{}}}


def build():
    STAGE.mkdir(parents=True, exist_ok=True)
    refs = {'api':'scriptstudio-api:latest','web':'scriptstudio-web:latest','db':'postgres:17.4-bookworm','redis':'redis:7.4.2-alpine'}
    metadata = {role:json.loads(run('docker','image','inspect',ref))[0] for role,ref in refs.items()}
    if any(info['Os'] != 'linux' or info['Architecture'] != 'amd64' for info in metadata.values()):
        raise RuntimeError('The Windows x64 package requires Linux amd64 images.')
    # Include only Git-visible source files; ignored .env, media, caches, builds,
    # screenshots, and backups are excluded. No container/volume export occurs.
    paths = run('git','ls-files','--cached','--others','--exclude-standard','-z').split('\0')
    paths = sorted({path for path in paths if path and (ROOT/path).is_file() and not (ROOT/path).is_symlink()})
    forbidden = [path for path in paths if Path(path).name.startswith('.env') and path != '.env.example']
    if forbidden:
        raise RuntimeError('Refusing to package environment files: '+str(forbidden))
    with zipfile.ZipFile(STAGE/'source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(ROOT/path,path)
    source_hash = hashlib.sha256((STAGE/'source.zip').read_bytes()).hexdigest()
    identity = hashlib.sha256((source_hash+''.join(info['Id'] for info in metadata.values())).encode()).hexdigest()[:12]
    previous = json.loads((STAGE/'manifest.json').read_text()) if (STAGE/'manifest.json').exists() else None
    reuse = previous and (STAGE/'images.tar.gz').is_file() and all(previous['images'][role]['id']==metadata[role]['Id'] for role in refs)
    images = {role:previous['images'][role]['tag'] if reuse else f'scriptstudio-release-{role}:{metadata[role]["Id"][7:19]}' for role in refs}
    if not reuse:
        for role, ref in refs.items():
            run('docker','tag',ref,images[role])
    (STAGE/'compose.json').write_text(json.dumps(release_compose(images),indent=2)+'\n')
    (STAGE/'images.txt').write_text(''.join(f'{images[role]} {metadata[role]["Id"]}\n' for role in refs))
    if not reuse:
        print('Saving and compressing four runtime images (shared layers are deduplicated)…',flush=True)
        with (STAGE/'images.tar.gz').open('wb') as target:
            with gzip.GzipFile(fileobj=target,mode='wb',compresslevel=6,mtime=0) as compressed:
                process = subprocess.Popen(['docker','save',*images.values()],cwd=ROOT,stdout=subprocess.PIPE)
                try:
                    shutil.copyfileobj(process.stdout,compressed,1024*1024)
                finally:
                    process.stdout.close()
                if process.wait() != 0:
                    raise RuntimeError('Docker image export failed')
    else:
        print('Reusing the unchanged image archive; refreshing source and launcher.',flush=True)
    for source,target in [('LICENSE','LICENSE.txt'),('NOTICE.md','NOTICE.txt'),('packaging/windows/README.md','README.txt')]:
        shutil.copyfile(ROOT/source,STAGE/target)
    shutil.copyfile(ROOT/'frontend/public/credits/components.json',STAGE/'components.json')
    shutil.copyfile(ROOT/'frontend/public/credits/notices.json',STAGE/'notices.json')
    manifest = {'release':identity,'source_commit':run('git','rev-parse','HEAD'),'source_sha256':source_hash,
                'platform':'windows-x64','runtime':'Linux Docker engine and Compose v2 (not bundled)',
                'images':{role:{'tag':images[role],'id':metadata[role]['Id']} for role in refs}}
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    payload = STAGE/'payload.zip'
    with zipfile.ZipFile(payload,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
        for name in ['images.tar.gz','images.txt','compose.json','source.zip','LICENSE.txt','NOTICE.txt','README.txt','components.json','notices.json','manifest.json']:
            archive.write(STAGE/name,name)
    compiler = Path(os.environ.get('SCRIPTSTUDIO_CSC','/mnt/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe'))
    if not compiler.is_file():
        raise RuntimeError('Set SCRIPTSTUDIO_CSC to the Windows .NET Framework C# compiler path')
    stub=STAGE/'ScriptStudio-launcher.exe'
    print(run(str(compiler),'/nologo','/target:winexe','/platform:x64','/optimize+',
              '/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll',
              '/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll',
              '/win32icon:'+windows(ROOT/'frontend/public/favicon.ico'),
              '/resource:'+windows(ROOT/'frontend/public/favicon.ico')+',ScriptStudio.ico',
              '/out:'+windows(stub),windows(ROOT/'packaging/windows/Launcher.cs')),flush=True)
    output=OUT/'ScriptStudio-Windows-x64.exe'
    digest=hashlib.sha256()
    with output.open('wb') as result:
        with stub.open('rb') as source: shutil.copyfileobj(source,result)
        with payload.open('rb') as source:
            while block:=source.read(1024*1024): digest.update(block); result.write(block)
        result.write(b'SSTPKG01'+struct.pack('<Q',payload.stat().st_size)+digest.digest())
    checksum=hashlib.file_digest(output.open('rb'),'sha256').hexdigest()
    output.chmod(0o755)
    (OUT/'ScriptStudio-Windows-x64.exe.sha256').write_text(checksum+'  '+output.name+'\n')
    shutil.copyfile(STAGE/'manifest.json',OUT/'manifest.json')
    print(f'Built {output} ({output.stat().st_size:,} bytes)\nSHA256 {checksum}',flush=True)


if __name__ == '__main__':
    build()
