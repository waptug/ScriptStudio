"""Build native Windows x64 EXE from downloaded/extracted pinned runtimes.

See README.md for acquisition. WSL is a build host only; no Linux artifacts or
Docker images enter this payload. Rebuild copies current sources and UI.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import struct
import subprocess
import zipfile
from win import run, path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/native'
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
    STAGE.mkdir(parents=True,exist_ok=True)
    copy(OUT/'python',STAGE/'python')
    pg=OUT/'postgres/pgsql'
    for name in ['bin','lib','share','server_license.txt','commandlinetools_3rd_party_licenses.txt']:
        copy(pg/name,STAGE/'postgres'/name)
    copy(OUT/'ffmpeg/ffmpeg-9.0.1-essentials_build',STAGE/'ffmpeg')
    copy(OUT/'speech/eSpeak NG',STAGE/'speech')
    copy(OUT/'msvc',STAGE/'msvc')
    for dll in (OUT/'msvc').glob('*.dll'):
        for directory in ['python','postgres/bin','speech']:
            copy(dll,STAGE/directory/dll.name)
    # Frozen OpenShot's bytecode is required; do not apply the Python source ignore.
    shutil.copytree(OUT/'openshot/app',STAGE/'openshot',dirs_exist_ok=True,copy_function=copy_file)
    copy(ROOT/'backend',STAGE/'backend')
    copy(ROOT/'frontend/dist',STAGE/'web')
    copy(ROOT/'packaging/native/runtime.py',STAGE/'runtime.py')
    copy(Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),STAGE/'backend/DejaVuSans.ttf')
    for source,target in [('LICENSE','LICENSE.txt'),('NOTICE.md','NOTICE.txt'),('packaging/native/README.md','README.txt')]:
        copy(ROOT/source,STAGE/target)
    run(CSC,'/nologo','/target:exe','/platform:x64','/out:'+path(STAGE/'openshot/MediaHost.exe'),path(ROOT/'packaging/native/MediaHost.cs'))
    credits()
    files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    with zipfile.ZipFile(STAGE/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in sorted(set(files)):
            p=ROOT/name
            if name and p.is_file() and not p.is_symlink():
                if p.name.startswith('.env') and p.name!='.env.example':raise ValueError('Refusing environment file')
                z.write(p,name)
    manifest={'format':'native-windows-x64','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'downloads':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((OUT/'downloads').iterdir()) if p.is_file() and p.name!='ready'},
        'source_sha256':hashlib.sha256((STAGE/'source.zip').read_bytes()).hexdigest()}
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    exe=OUT/'ScriptStudio-Native-Windows-x64.exe'
    run(CSC,'/nologo','/target:winexe','/platform:x64','/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll',
        '/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll','/reference:System.Web.Extensions.dll',
        '/win32icon:'+path(ROOT/'frontend/public/favicon.ico'),'/resource:'+path(ROOT/'frontend/public/favicon.ico')+',ScriptStudio.ico',
        '/out:'+path(exe),path(ROOT/'packaging/native/Launcher.cs'))
    payload=OUT/'payload.zip'
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
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
