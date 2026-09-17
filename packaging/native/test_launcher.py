"""Validate the actual native Windows extractor with tiny hostile fixtures."""
import hashlib
import io
from pathlib import Path
import struct
import subprocess
import zipfile
from win import run

root=Path(__file__).resolve().parents[2]
out=root/'artifacts/native/extraction-tests'
out.mkdir(parents=True,exist_ok=True)
exe=(root/'artifacts/native/ScriptStudio-Native-Windows-x64.exe').read_bytes()
length=struct.unpack('<Q',exe[-40:-32])[0]
stub=exe[:-48-length]
required={p:'fixture' for p in ['runtime.py','python/python.exe','postgres/bin/postgres.exe',
    'openshot/MediaHost.exe','source.zip','LICENSE.txt','README.txt']}
for name,entries,corrupt,expected in [
    ('valid',required,False,0),('corrupt',required,True,1),
    ('traversal',{**required,'../escape.txt':'escape'},False,1),
    ('drive-path',{**required,'C:/escape.txt':'escape'},False,1),
    ('missing',{'README.txt':'incomplete'},False,1),
]:
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        for path,data in entries.items():z.writestr(path,data)
    payload=stream.getvalue()
    digest=bytes(32) if corrupt else hashlib.sha256(payload).digest()
    target=out/(name+'.exe')
    target.write_bytes(stub+payload+b'SSTPKG01'+struct.pack('<Q',len(payload))+digest)
    target.chmod(0o755)
    try:
        result=run(str(target),'--verify',timeout=120)
        code=result.returncode
    except subprocess.CalledProcessError as error:
        code=error.returncode
    assert code==expected,(name,code)
    print('PASS native extraction:',name,flush=True)
