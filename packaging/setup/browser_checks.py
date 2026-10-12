"""Windows browser checks against an isolated native runtime, never production."""
import argparse
import json
import os
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,required=True);parser.add_argument('--node',required=True);parser.add_argument('tests',nargs='*');args=parser.parse_args()
ready=json.loads((args.data/'ready.json').read_text())
scratch=args.data/'browser-checks';scratch.mkdir(exist_ok=True)
os.environ.update(TEMP=str(scratch),TMP=str(scratch))
os.environ.update(SCRIPTSTUDIO_URL=ready['url'],SCRIPTSTUDIO_BROWSER=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
raise SystemExit(subprocess.run([args.node,str(root/'frontend/node_modules/@playwright/test/cli.js'),'test',*args.tests],cwd=root/'frontend').returncode)
