"""Build-host entrypoint for isolated bundled Windows Python regression tests."""
import argparse
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'packaging/native'))
from win import run,path
parser=argparse.ArgumentParser()
parser.add_argument('--python',type=Path,required=True)
parser.add_argument('tests',nargs='*')
args=parser.parse_args()
run(str(args.python),'-X','utf8',path(root/'packaging/setup/backend_checks.py'),*args.tests)
