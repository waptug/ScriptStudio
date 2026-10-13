"""Prepare a separate test DVD; Windows is installed only into the VM's blank disk."""
import argparse
import hashlib
import json
import secrets
import subprocess
from pathlib import Path
import pycdlib

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, default=Path('/mnt/d/ScriptStudio-VM-Tests/Windows11-Core'))
parser.add_argument('--windows-iso', type=Path)
parser.add_argument('--installer', type=Path, default=Path(__file__).resolve().parents[3]/'artifacts/setup/ScriptStudio-Setup.exe')
args = parser.parse_args()
media = args.root/'media'
media.mkdir(parents=True, exist_ok=True)
if not (args.windows_iso or media/'Windows11-Enterprise-Eval.iso').is_file():
    raise SystemExit('Download and verify the official Windows evaluation ISO first.')
credentials = args.root/'credentials.json'
if (args.root/'media'/'ScriptStudio-Test.iso').exists():
    raise SystemExit('Existing test DVD found. Use a fresh media directory; never overwrite mounted media.')
expected = args.installer.with_suffix('.exe.sha256').read_text().split()[0]
with args.installer.open('rb') as stream:
    if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
        raise SystemExit('Installer does not match the qualification candidate.')
if credentials.exists():
    password = json.loads(credentials.read_text())['password']
else:
    password = secrets.token_urlsafe(24)
    credentials.write_text(json.dumps({'username':'VMTest','password':password}))
    credentials.chmod(0o600)
(media/'candidate.json').write_text(json.dumps({'sha256':expected,'bytes':args.installer.stat().st_size}))
source = Path(__file__).resolve().parent
(media/'Autounattend.xml').write_text((source/'Autounattend.xml.in').read_text().replace('@VM_TEST_PASSWORD@',password))
def windows(path):
    return subprocess.check_output(['wslpath','-w',str(path.resolve())],text=True).strip()
csc = '/mnt/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe'
refs = ['/reference:'+name+'.dll' for name in ['System.Web.Extensions','System.Drawing','System.Windows.Forms','System.Management']]
gac = Path('/mnt/c/Windows/Microsoft.NET/assembly/GAC_MSIL')
for name in ['UIAutomationClient','UIAutomationTypes','WindowsBase']:
    refs.append('/reference:'+windows(next((gac/name).glob('*/'+name+'.dll'))))
command = [csc,'/nologo','/target:exe','/out:'+windows(media/'GuestChecks.exe'),*refs,windows(source/'GuestChecks.cs')]
try:
    subprocess.run(command, check=True)
except OSError as error:
    if error.errno != 8: raise
    subprocess.run(['/init',*command],check=True)
iso=pycdlib.PyCdlib()
iso.new(interchange_level=3,joliet=3,vol_ident='SS_TEST')
for path,name,short in [(media/'Autounattend.xml','Autounattend.xml','AUTOUNAT.XML'),(media/'GuestChecks.exe','GuestChecks.exe','GUESTCHK.EXE'),(args.installer,'ScriptStudio-Setup.exe','SETUP.EXE'),(media/'candidate.json','candidate.json','CANDIDAT.JSN')]:
    iso.add_file(str(path),iso_path='/'+short+';1',joliet_path='/'+name)
iso.write(str(media/'ScriptStudio-Test.iso'))
iso.close()
print('Test DVD prepared. VM-only credentials remain local and must not be committed.')
