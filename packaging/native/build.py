"""Build native Windows x64 EXE from downloaded/extracted pinned runtimes.

See README.md for acquisition. WSL is a build host only; no Linux artifacts or
Docker images enter this payload. Rebuild copies current sources and UI.
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import subprocess
import zipfile
from win import run, path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/native'
INPUT = Path(os.environ.get('SCRIPTSTUDIO_NATIVE_INPUT', str(OUT)))
STAGE = OUT / 'stage'
CSC = '/mnt/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe'


def copy_file(source, target):
    source, target = Path(source), Path(target)
    if not target.exists() or source.stat().st_size != target.stat().st_size or source.stat().st_mtime_ns != target.stat().st_mtime_ns:
        shutil.copy2(source, target)
    return str(target)


def copy(source, target):
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True,
            copy_function=copy_file, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.pytest_cache'))
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        copy_file(source, target)


def normalize_speech_names():
    # Upstream MSI extraction contains af_dict with trailing spaces. Windows
    # aliases such names; normalize at build time, never relax archive safety.
    for file in sorted((STAGE/'speech').rglob('*'), key=lambda p:len(p.parts), reverse=True):
        name=file.name.rstrip(' .')
        if not name: raise ValueError('Empty normalized native filename')
        if name==file.name: continue
        target=file.with_name(name)
        if target.exists():
            if not file.is_file() or not target.is_file() or file.read_bytes()!=target.read_bytes():
                raise ValueError('Native filename normalization collision')
            file.unlink()
        else: file.rename(target)


def credits():
    destination = STAGE / 'web/credits'
    inventory = json.loads((destination / 'components.json').read_text())
    notices = json.loads((destination / 'notices.json').read_text())
    inventory['runtime'] = 'native-windows'
    inventory['scope'] = ('Native Windows package: locked frontend packages, installed Windows API Python distributions, '
        'bundled media and database runtimes. Native runtime files and SHA-256 hashes are in native-files.json. '
        'Upstream OpenShot includes additional libraries without individual package metadata; retain its notices and consult its build sources. '
        'The Windows operating system and its .NET Framework are not redistributed.')
    inventory['components'] = [c for c in inventory['components'] if c['group'].startswith('JavaScript')]
    def add(name, version, license, url, notice='', evidence=''):
        key=hashlib.sha256(notice.encode()).hexdigest() if notice else ''
        if key:notices[key]=notice
        inventory['components'].append(dict(name=name,version=version,license=license,url=url,
            group='Native Windows',role='Bundled runtime',notice=key,evidence=evidence))
    for dist in importlib.metadata.distributions(path=[str(STAGE/'python/Lib/site-packages')]):
        texts=[]
        for file in dist.files or []:
            if any(s in str(file).lower() for s in ['license','copying','notice']):
                p=dist.locate_file(file)
                if p.is_file():texts.append(p.read_text(errors='replace'))
        add(dist.metadata['Name'], dist.version, dist.metadata.get('License-Expression') or dist.metadata.get('License','See notice'),
            dist.metadata.get('Home-page','https://pypi.org/project/'+dist.metadata['Name']), '\n\n'.join(texts), 'Windows wheel metadata')
    for name,version,license,url,notice in [
        ('Microsoft Visual C++ runtime','14.44.35211','Microsoft redistributable license (not open source)','https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files',STAGE/'msvc/license.txt'),
        ('Python','3.12.10','PSF-2.0','https://www.python.org/',STAGE/'python/LICENSE.txt'),
        ('PostgreSQL','17.11','PostgreSQL','https://www.postgresql.org/',STAGE/'postgres/server_license.txt'),
        ('OpenShot Windows runtime','4.0.0 / libopenshot 1.0.0','GPL-3.0 / LGPL-3.0 and bundled component licenses','https://github.com/OpenShot/openshot-qt/releases/tag/v4.0.0',STAGE/'openshot/resources/license.txt'),
        ('FFmpeg essentials','9.0.1','GPL-3.0-or-later and bundled component licenses','https://www.gyan.dev/ffmpeg/builds/',STAGE/'ffmpeg/LICENSE'),
        ('eSpeak NG','1.51','GPL-3.0-or-later','https://github.com/espeak-ng/espeak-ng/releases/tag/1.51',ROOT/'LICENSE'),
        ('DejaVu Sans','2.37','Bitstream Vera / public domain additions','https://dejavu-fonts.github.io/',Path('/usr/share/doc/fonts-dejavu-core/copyright')),
    ]:
        add(name,version,license,url,notice.read_text(errors='replace') if notice.exists() else '')
    for name,license,url in [('libopenshot','LGPL-3.0-or-later','https://github.com/OpenShot/libopenshot'),('libopenshot-audio','LGPL-3.0-or-later','https://github.com/OpenShot/libopenshot-audio'),('PyQt5','GPL-3.0','https://www.riverbankcomputing.com/software/pyqt/'),('Qt5','Module-specific LGPL/GPL','https://www.qt.io/licensing/'),('OpenShot Python ABI','PSF-2.0','https://www.python.org/')]:
        add(name,'Bundled with OpenShot 4.0.0',license,url)
    seen=set()
    for file in sorted((STAGE/'openshot').rglob('*')):
        if file.suffix.lower() not in ('.dll','.pyd') or file.name in seen:continue
        seen.add(file.name)
        add(file.name,'OpenShot 4.0.0 binary distribution','Component-specific; see upstream build and distribution notices','https://github.com/OpenShot/openshot-qt',evidence=str(file.relative_to(STAGE)))
    (destination/'components.json').write_text(json.dumps(inventory,indent=2))
    (destination/'notices.json').write_text(json.dumps(notices))
    files=[{'path':str(p.relative_to(STAGE)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        for folder in ['python','postgres','openshot','ffmpeg','speech','msvc'] for p in sorted((STAGE/folder).rglob('*')) if p.is_file()]
    (destination/'native-files.json').write_text(json.dumps(files,indent=2))


def main():
    finalize='--finalize-staging' in sys.argv
    if finalize:
        if not (STAGE/'manifest.json').is_file() or not (OUT/'ScriptStudio-Native-Windows-x64.exe').is_file():
            raise ValueError('Finalize requires a completed local native build')
        previous_credits={p.name:p.read_bytes() for p in (STAGE/'web/credits').glob('*.json')}
    else:
        STAGE.mkdir(parents=True,exist_ok=True)
        # Always rebuild from a clean allowlisted staging tree.
        if STAGE.exists(): shutil.rmtree(STAGE)
        STAGE.mkdir(parents=True,exist_ok=True)
        copy(INPUT/'python',STAGE/'python')
        pg=INPUT/'postgres/pgsql'
        for name in ['bin','lib','share','server_license.txt','commandlinetools_3rd_party_licenses.txt']:
            copy(pg/name,STAGE/'postgres'/name)
        copy(INPUT/'ffmpeg/ffmpeg-9.0.1-essentials_build',STAGE/'ffmpeg')
        copy(INPUT/'speech/eSpeak NG',STAGE/'speech')
        copy(INPUT/'msvc',STAGE/'msvc')
        for dll in (INPUT/'msvc').glob('*.dll'):
            for directory in ['python','postgres/bin','speech']:
                copy(dll,STAGE/directory/dll.name)
        # Frozen OpenShot's bytecode is required; do not apply the Python source ignore.
        shutil.copytree(INPUT/'openshot/app',STAGE/'openshot',dirs_exist_ok=True,copy_function=copy_file)
    print('Refreshing first-party application sources',flush=True)
    copy(ROOT/'backend',STAGE/'backend')
    copy(ROOT/'frontend/dist',STAGE/'web')
    copy(ROOT/'packaging/native/runtime.py',STAGE/'runtime.py')
    copy(ROOT/'packaging/setup/components.py',STAGE/'setup_components.py')
    normalize_speech_names()
    copy(Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),STAGE/'backend/DejaVuSans.ttf')
    for source,target in [('LICENSE','LICENSE.txt'),('NOTICE.md','NOTICE.txt'),('packaging/native/README.md','README.txt')]:
        copy(ROOT/source,STAGE/target)
    run(CSC,'/nologo','/target:exe','/platform:x64','/out:'+path(STAGE/'openshot/MediaHost.exe'),path(ROOT/'packaging/native/MediaHost.cs'))
    if finalize:
        native_files=json.loads(previous_credits['native-files.json'])
        for item in native_files:
            item['path']='/'.join(p.rstrip(' .') for p in item['path'].replace('\\','/').split('/'))
            if item['path']=='openshot/MediaHost.exe':
                item['sha256']=hashlib.file_digest((STAGE/item['path']).open('rb'),'sha256').hexdigest()
        previous_credits['native-files.json']=json.dumps(native_files,indent=2).encode()
        for name,data in previous_credits.items(): (STAGE/'web/credits'/name).write_bytes(data)
    else:
        credits()
    files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    with zipfile.ZipFile(STAGE/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in sorted(set(files)):
            p=ROOT/name
            if name and p.is_file() and not p.is_symlink():
                if name.split('/')[0] not in {'backend','frontend','packaging','docs','scripts','samples','.github','README.md','PLAN.md','LICENSE','NOTICE.md','AGENTS.md','compose.yaml','.gitignore','.env.example'}: continue
                if p.name.startswith('.env') and p.name!='.env.example':raise ValueError('Refusing environment file')
                z.write(p,name)
    manifest={'format':'native-windows-x64','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'downloads':{p.name:hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in sorted((INPUT/'downloads').iterdir()) if p.is_file() and p.name!='ready'},
        'source_sha256':hashlib.sha256((STAGE/'source.zip').read_bytes()).hexdigest()}
    manifest['source_dirty']=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (STAGE/'file-inventory.json').unlink(missing_ok=True)
    print('Hashing complete embedded inventory',flush=True)
    inventory={str(p.relative_to(STAGE)).replace('\\','/'):hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
               for p in sorted(STAGE.rglob('*')) if p.is_file()}
    (STAGE/'file-inventory.json').write_text(json.dumps(inventory,sort_keys=True))
    exe=OUT/'ScriptStudio-Native-Windows-x64.exe'
    run(CSC,'/nologo','/target:winexe','/platform:x64','/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll',
        '/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll','/reference:System.Web.Extensions.dll',
        '/win32icon:'+path(ROOT/'frontend/public/favicon.ico'),'/resource:'+path(ROOT/'frontend/public/favicon.ico')+',ScriptStudio.ico',
        '/out:'+path(exe),path(ROOT/'packaging/native/Launcher.cs'))
    payload=OUT/'payload.zip'
    print('Compressing native payload',flush=True)
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for p in sorted(STAGE.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(STAGE)))
    digest=hashlib.sha256(payload.read_bytes()).digest()
    with exe.open('ab') as output,payload.open('rb') as source:
        shutil.copyfileobj(source,output)
        output.write(b'SSTPKG01'+struct.pack('<Q',payload.stat().st_size)+digest)
    exe.chmod(0o755)
    checksum=hashlib.sha256(exe.read_bytes()).hexdigest()
    exe.with_suffix('.exe.sha256').write_text(checksum+'  '+exe.name+'\n')
    print(exe,exe.stat().st_size,checksum,flush=True)

if __name__=='__main__':main()
