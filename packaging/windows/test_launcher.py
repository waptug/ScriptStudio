"""Run Windows extraction/rejection tests using a compiled launcher stub in WSL."""
import hashlib
import io
from pathlib import Path
import struct
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/windows/tests'


def win(path):
    return subprocess.check_output(['wslpath','-w',str(path)],text=True).strip()


def package(stub, name, entries, corrupt=False):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:
        for path,data in entries.items(): archive.writestr(path,data)
    payload=stream.getvalue()
    checksum=hashlib.sha256(payload).digest()
    if corrupt: checksum=bytes(32)
    target=OUT/(name+'.exe')
    target.write_bytes(stub+payload+b'SSTPKG01'+struct.pack('<Q',len(payload))+checksum)
    target.chmod(0o755)
    return target


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    stub=Path(sys.argv[1]).resolve().read_bytes()
    required={name:'fixture' for name in ['compose.json','images.tar.gz','images.txt','source.zip','LICENSE.txt','README.txt']}
    for name,entries,corrupt,expected in [
        ('valid',required,False,0),
        ('corrupt',required,True,1),
        ('traversal',{**required,'../escape.txt':'must not escape'},False,1),
        ('missing',{'README.txt':'incomplete'},False,1),
    ]:
        exe=package(stub,name,entries,corrupt)
        report=OUT/(name+'.txt')
        try:
            result=subprocess.run([str(exe),'--verify',win(report)],timeout=120)
        except OSError as error:
            if error.errno!=8: raise
            result=subprocess.run(['/init',str(exe),str(exe),'--verify',win(report)],timeout=120)
        assert result.returncode==expected,(name,result.returncode,report.read_text() if report.exists() else 'No Windows report was written')
        print('PASS Windows process:',name,flush=True)
