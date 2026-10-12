"""Download the release matching a cloned tag; verify before retaining the EXE."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import urllib.request

parser=argparse.ArgumentParser()
parser.add_argument('--tag',help='Default: exact Git tag of this source revision')
parser.add_argument('--output',type=Path,default=Path('ScriptStudio-Setup.exe'))
args=parser.parse_args()
tag=args.tag or subprocess.check_output(['git','describe','--tags','--exact-match'],text=True).strip()
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,100}',tag):raise ValueError('Invalid release tag')
base=f'https://github.com/waptug/ScriptStudio/releases/download/{tag}/'
checksum=urllib.request.urlopen(base+'ScriptStudio-Setup.exe.sha256',timeout=30).read().decode().split()[0]
if not re.fullmatch('[a-f0-9]{64}',checksum):raise ValueError('Invalid release checksum')
partial=args.output.with_suffix('.exe.part')
hash=hashlib.sha256();size=0
with urllib.request.urlopen(base+'ScriptStudio-Setup.exe',timeout=60) as source,partial.open('wb') as target:
    while chunk:=source.read(8*1024*1024):
        size+=len(chunk)
        if size>=2*1024**3:raise ValueError('Release exceeds size limit')
        hash.update(chunk);target.write(chunk)
if hash.hexdigest()!=checksum:
    partial.unlink();raise ValueError('Checksum mismatch')
partial.replace(args.output)
print(f'Verified {args.output} ({size} bytes). Run it to review and accept installation.')
