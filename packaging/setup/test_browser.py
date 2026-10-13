"""Build-host wrapper for the native Windows browser qualification checks."""
import argparse
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'packaging/native'))
from win import run,path
parser=argparse.ArgumentParser();parser.add_argument('--python',required=True);parser.add_argument('--node',required=True);parser.add_argument('--data',type=Path,required=True);parser.add_argument('tests',nargs='*');args=parser.parse_args()
run(args.python,'-X','utf8',path(root/'packaging/setup/browser_checks.py'),'--data',path(args.data),'--node',path(args.node),*args.tests)
