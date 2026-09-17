"""WSL build/test helper only; never bundled or used by the Windows application."""
import subprocess
from pathlib import Path

def path(value):
    return subprocess.check_output(['wslpath','-w',str(Path(value).resolve())],text=True).strip()

def run(exe,*args,**kwargs):
    command=[str(exe),*map(str,args)]
    try:return subprocess.run(command,check=True,**kwargs)
    except OSError as error:
        if error.errno != 8:raise
        return subprocess.run(['/init',str(exe),*command],check=True,**kwargs)

if __name__=='__main__':
    import sys
    run(sys.argv[1],*sys.argv[2:])
