"""Release guard: size, both payload hashes, file inventory, nested core and locks."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zipfile
from build import digest, inspect_launcher, LIMIT

file=Path(sys.argv[1])
if file.stat().st_size>=LIMIT:raise ValueError('Setup asset is at or above 2 GiB')
with file.open('rb') as source:
    source.seek(-48,2)
    magic,size,expected=struct.unpack('<8sQ32s',source.read(48))
    if magic!=b'SSTSET01' or not 0<size<=file.stat().st_size-48:raise ValueError('Invalid setup footer')
    source.seek(-48-size,2)
    hash=hashlib.sha256();remaining=size
    while remaining:
        chunk=source.read(min(8*1024*1024,remaining));hash.update(chunk);remaining-=len(chunk)
    if hash.digest()!=expected:raise ValueError('Setup payload corruption')
with tempfile.TemporaryDirectory() as folder:
    native=Path(folder)/'ScriptStudio.exe'
    with zipfile.ZipFile(file) as setup:
        if setup.namelist()!=['ScriptStudio.exe']:raise ValueError('Unexpected embedded setup inventory')
        with setup.open('ScriptStudio.exe') as source,native.open('wb') as target:
            import shutil
            shutil.copyfileobj(source,target)
    expanded,manifest=inspect_launcher(native)
    with zipfile.ZipFile(native) as bundle:
        inventory=json.loads(bundle.read('file-inventory.json'))
        expected_names=set(bundle.namelist())-{'file-inventory.json'}
        if set(inventory)!=expected_names:raise ValueError('Inventory does not match payload')
        for name,expected in inventory.items():
            with bundle.open(name) as source:
                if hashlib.file_digest(source,'sha256').hexdigest()!=expected:raise ValueError('File checksum mismatch: '+name)
        with zipfile.ZipFile(bundle.open('source.zip')) as sources:
            for name in sources.namelist():
                if any(p in {'.git','node_modules','artifacts','data','backups','promo','analytics-tools'} for p in Path(name).parts):raise ValueError('Private source path: '+name)
    recorded=file.with_suffix('.exe.sha256').read_text().split()[0]
    if digest(file)!=recorded:raise ValueError('Release checksum mismatch')
print('PASS release size, setup/native payloads, complete hashed inventory, source boundary, checksum')
