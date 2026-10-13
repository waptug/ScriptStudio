"""Create the one-file setup distribution from a freshly built native launcher."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packaging/native'))
from win import run, path
LIMIT = 2 * 1024**3
REQUIRED = {'runtime.py', 'python/python.exe', 'postgres/bin/postgres.exe',
            'openshot/MediaHost.exe', 'ffmpeg/bin/ffmpeg.exe', 'speech/espeak-ng.exe',
            'source.zip', 'LICENSE.txt', 'README.txt', 'manifest.json', 'file-inventory.json', 'setup_components.py'}


def digest(file):
    with Path(file).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect_launcher(file):
    with file.open('rb') as stream:
        stream.seek(-48, 2)
        magic, size, checksum = struct.unpack('<8sQ32s', stream.read(48))
        if magic != b'SSTPKG01' or not 0 < size <= file.stat().st_size - 48:
            raise ValueError('Invalid native footer')
        stream.seek(-48-size, 2)
        h = hashlib.sha256()
        remaining = size
        while remaining:
            chunk = stream.read(min(8*1024*1024, remaining))
            h.update(chunk); remaining -= len(chunk)
        if h.digest() != checksum:
            raise ValueError('Corrupt native payload')
    # ZIP supports an EXE prefix; the native footer is tolerated as trailing data.
    with zipfile.ZipFile(file) as bundle:
        names = set(bundle.namelist())
        if len({name.lower() for name in bundle.namelist()}) != len(bundle.infolist()):
            raise ValueError('Duplicate or case-ambiguous payload path')
        if not REQUIRED <= names:
            raise ValueError(f'Missing core components: {REQUIRED - names}')
        for item in bundle.infolist():
            pieces = item.filename.replace('\\', '/').split('/')
            if item.filename.startswith(('/', '\\')) or '..' in pieces or ':' in item.filename or any(p.endswith((' ', '.')) or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)',p,re.I) for p in pieces):
                raise ValueError('Unsafe payload path')
            if pieces[0].lower() in {'data', 'node_modules', '.git', 'backups', 'browser', 'profile', 'analytics-tools', 'promo'} or '.git' in pieces:
                raise ValueError('Private/development payload content: '+item.filename)
            if any(p.startswith('.env') and p != '.env.example' for p in pieces):
                raise ValueError('Environment file in payload')
        core = json.loads(bundle.read('manifest.json'))
        return sum(i.file_size+4096 for i in bundle.infolist()), core


def make_manifest(launcher):
    expanded, native = inspect_launcher(launcher)
    with launcher.open('rb') as stream:
        stream.seek(-32, 2)
        payload_hash = stream.read(32).hex()
    features = [dict(id='core', source='Embedded native package', license='See embedded LICENSE and runtime notices',
                     revision=native['source_commit'], download_bytes=0, expanded_bytes=expanded)]
    metadata = {
        'kokoro': ('https://huggingface.co/hexgrad/Kokoro-82M', 'Apache-2.0'),
        'wan': ('https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers', 'Apache-2.0'),
        'ace_step': ('https://github.com/ace-step/ACE-Step-1.5', 'MIT'),
        'stable_audio': ('https://huggingface.co/stabilityai/stable-audio-open-small', 'Stability AI Community License; authorized access required'),
    }
    for name, (url, license) in metadata.items():
        lock = json.loads((ROOT/'backend/studio/model_locks'/f'{name}.json').read_text())
        for artifact in lock['artifacts']:
            if not artifact['url'].startswith('https://') or len(artifact['sha256']) != 64 or artifact['size'] <= 0:
                raise ValueError('Unpinned artifact')
        features.append(dict(id=name, source=url, license=license, revision=lock['revision'],
            download_bytes=sum(a['size'] for a in lock['artifacts']), expanded_bytes=lock['expanded_bytes'],
            artifacts=lock['artifacts'], python_tag=lock['python_tag'], model_revision=lock.get('model_revision')))
    for name in ('ollama','gemma'):
        lock = json.loads((ROOT/'backend/studio/model_locks'/f'{name}.json').read_text())
        features.append(dict(id=name, source=lock['source'],license=lock['license'],revision=lock['revision'],
            artifacts=lock['artifacts'],download_bytes=sum(a['size'] for a in lock['artifacts']),expanded_bytes=lock['expanded_bytes']))
    manifest = dict(contract_version=1, target='Windows 11 AMD64', launcher_sha256=digest(launcher),
        launcher_bytes=launcher.stat().st_size, core_expanded_bytes=expanded, features=features,
        source_commit=native['source_commit'], paid_generation_enabled=False, unsigned=True)
    manifest['native_payload_sha256'] = payload_hash
    manifest['manifest_sha256'] = hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--launcher', type=Path, default=ROOT/'artifacts/native/ScriptStudio-Native-Windows-x64.exe')
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/setup')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    manifest = make_manifest(args.launcher)
    args.output.mkdir(parents=True, exist_ok=True)
    source_snapshot=args.output/'setup-source.zip'
    files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    allowed={'backend','frontend','packaging','docs','scripts','samples','.github','README.md','PLAN.md','LICENSE','NOTICE.md','AGENTS.md','compose.yaml','.gitignore','.env.example'}
    with zipfile.ZipFile(source_snapshot,'w',zipfile.ZIP_DEFLATED) as sources:
        for name in sorted(set(files)):
            source=ROOT/name
            if name and name.split('/')[0] in allowed and source.is_file() and not source.is_symlink():
                if source.name.startswith('.env') and source.name!='.env.example':raise ValueError('Environment file in source snapshot')
                sources.write(source,name)
    manifest['native_source_commit']=manifest['source_commit']
    manifest['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    manifest.pop('manifest_sha256',None)
    manifest['setup_source_sha256']=digest(source_snapshot)
    manifest['source_dirty']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    manifest['manifest_sha256']=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    metadata = args.output/'setup-manifest.json'
    metadata.write_text(json.dumps(manifest, indent=2))
    if args.check:
        print('PASS native payload and model manifests');return
    exe = args.output/'ScriptStudio-Setup.exe'
    run('/mnt/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe', '/nologo','/target:winexe','/platform:x64',
        '/main:SetupProgram', '/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll',
        '/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll',
        '/reference:System.Web.Extensions.dll','/reference:Microsoft.CSharp.dll',
        '/resource:'+path(metadata)+',setup-manifest.json','/out:'+path(exe),
        '/resource:'+path(source_snapshot)+',setup-source.zip',
        path(ROOT/'packaging/native/Launcher.cs'),path(ROOT/'packaging/setup/Setup.cs'))
    payload = args.output/'setup-payload.zip'
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_STORED) as bundle:
        bundle.write(args.launcher, 'ScriptStudio.exe')
    size = payload.stat().st_size
    if exe.stat().st_size + size + 48 >= LIMIT:
        raise ValueError('Release asset must be below 2 GiB')
    with exe.open('ab') as target, payload.open('rb') as source:
        shutil.copyfileobj(source,target)
        target.write(struct.pack('<8sQ32s', b'SSTSET01',size,bytes.fromhex(digest(payload))))
    exe.chmod(0o755)
    exe.with_suffix('.exe.sha256').write_text(digest(exe)+'  '+exe.name+'\n')
    print(exe, exe.stat().st_size, digest(exe))

if __name__ == '__main__':
    main()
