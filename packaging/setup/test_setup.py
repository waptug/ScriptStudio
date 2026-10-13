"""Exercise actual C# policy and wizard on the Windows build host."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'packaging/native'))
from win import run,path
out=ROOT/'artifacts/setup'
exe=out/'SetupChecks.exe'
run('/mnt/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/target:exe','/platform:x64','/main:SetupChecks',
    '/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll','/reference:System.IO.Compression.dll',
    '/reference:System.IO.Compression.FileSystem.dll','/reference:System.Web.Extensions.dll','/reference:Microsoft.CSharp.dll',
    '/out:'+path(exe),path(ROOT/'packaging/native/Launcher.cs'),path(ROOT/'packaging/setup/Setup.cs'),path(ROOT/'packaging/setup/SetupChecks.cs'))
exe.chmod(0o755)
run(str(exe),path(out/'setup-manifest.json'),timeout=120)
