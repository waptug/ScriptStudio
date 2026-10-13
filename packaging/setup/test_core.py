"""Run setup's own media checks against an already-running isolated native workspace."""
import argparse
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'packaging/native'))
from win import run,path
parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,required=True);args=parser.parse_args()
exe=root/'artifacts/setup/CoreChecks.exe'
run('/mnt/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/target:exe','/platform:x64','/main:CoreChecks',
 '/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll','/reference:System.IO.Compression.dll',
 '/reference:System.IO.Compression.FileSystem.dll','/reference:System.Web.Extensions.dll','/reference:Microsoft.CSharp.dll',
 '/out:'+path(exe),path(root/'packaging/native/Launcher.cs'),path(root/'packaging/setup/Setup.cs'),path(root/'packaging/setup/CoreChecks.cs'))
exe.chmod(0o755);run(str(exe),path(args.data),timeout=1500)
