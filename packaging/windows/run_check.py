"""Invoke the built Windows EXE and retain its report, from WSL."""
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[2]
action=sys.argv[1]
if action not in ('--verify','--runtime-test','--ui-test','--start-test','--stop-test'):
    raise SystemExit('Choose --verify, --runtime-test, --ui-test, --start-test, or --stop-test')
exe=root/'artifacts/windows/ScriptStudio-Windows-x64.exe'
report=root/'artifacts/windows'/('windows-'+action[2:]+'.txt')
report.write_text('')
report_windows=subprocess.check_output(['wslpath','-w',str(report)],text=True).strip()
try:
    result=subprocess.run([str(exe),action,report_windows],timeout=2400)
except OSError as error:
    if error.errno!=8: raise
    result=subprocess.run(['/init',str(exe),str(exe),action,report_windows],timeout=2400)
print(report.read_text() if report.exists() else 'No report was written')
raise SystemExit(result.returncode)
