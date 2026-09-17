"""Validate the actual native Windows extractor with tiny hostile fixtures."""
import hashlib
import io
import os
from pathlib import Path
import struct
import subprocess
import zipfile
from win import run, path

root=Path(__file__).resolve().parents[2]
out=Path(os.environ.get('SCRIPTSTUDIO_EXTRACT_TEST_DIR', str(root/'artifacts/native/extraction-tests')))
out.mkdir(parents=True,exist_ok=True)
launcher=out/'launcher.exe'
run('/mnt/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe',
    '/nologo','/target:exe','/platform:x64',
    '/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll',
    '/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll',
    '/reference:System.Web.Extensions.dll','/out:'+path(launcher),path(root/'packaging/native/Launcher.cs'))
stub=launcher.read_bytes()
required={p:'fixture' for p in ['runtime.py','python/python.exe','postgres/bin/postgres.exe',
    'openshot/MediaHost.exe','source.zip','LICENSE.txt','README.txt']}
for name,entries,corrupt,expected in [
    ('valid',required,False,0),('corrupt',required,True,1),
    ('traversal',{**required,'../escape.txt':'escape'},False,1),
    ('drive-path',{**required,'C:/escape.txt':'escape'},False,1),
    ('missing',{'README.txt':'incomplete'},False,1),
    ('low-space',required,False,3),
]:
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        for path,data in entries.items():z.writestr(path,data)
    payload=stream.getvalue()
    if name=='low-space':
        # Advertise >4 TiB expanded size using many huge entries. The preflight
        # must refuse before opening their deliberately tiny compressed content.
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            for index in range(2048):z.writestr(str(index),b'x')
        payload=bytearray(stream.getvalue())
        cursor=0
        while True:
            cursor=payload.find(b'PK\x01\x02',cursor)
            if cursor<0:break
            struct.pack_into('<I',payload,cursor+24,0xfffffffe)
            cursor+=46
        payload=bytes(payload)
    digest=bytes(32) if corrupt else hashlib.sha256(payload).digest()
    folder=out/name
    folder.mkdir(exist_ok=True)
    target=folder/(name+'.exe')
    target.write_bytes(stub+payload+b'SSTPKG01'+struct.pack('<Q',len(payload))+digest)
    target.chmod(0o755)
    try:
        result=run(str(target),'--verify',timeout=120)
        code=result.returncode
    except subprocess.CalledProcessError as error:
        code=error.returncode
    assert code==expected,(name,code)
    print('PASS native extraction:',name,flush=True)

assert not (out/'low-space'/'ScriptStudioNative').exists(), 'Low disk check wrote files before refusing'
assert (out/'valid'/'ScriptStudioNative'/'packages').is_dir(), 'Runtime not beside EXE'
print('PASS no files created on low space; extraction stays beside EXE',flush=True)

checks=out/'StorageChecks.exe'
run('/mnt/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe',
    '/nologo','/target:exe','/platform:x64','/main:StorageChecks',
    '/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll',
    '/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll',
    '/reference:System.Web.Extensions.dll','/out:'+path(checks),
    path(root/'packaging/native/Launcher.cs'),path(root/'packaging/native/StorageChecks.cs'))
checks.chmod(0o755)
run(str(checks))
