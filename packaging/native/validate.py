"""Run source acceptance checks with the EXE's native runtime and test database."""
import argparse
import json
import os
from pathlib import Path
import runpy
import sys

parser=argparse.ArgumentParser()
parser.add_argument('action', choices=['tests','concurrency','snapshot'])
parser.add_argument('--repo', required=True)
args=parser.parse_args()
root=Path(sys.executable).resolve().parent.parent
repo=Path(args.repo)
data=Path(os.environ['SCRIPTSTUDIO_TEST_DATA'])
config=json.loads((data/'runtime.json').read_text())
sys.path.insert(0,str(root/'backend'))
os.environ['DATABASE_URL']=f"postgresql+psycopg://studio:{config['password']}@127.0.0.1:{config['db_port']}/scriptstudio"
os.environ['MEDIA_ROOT']=str(data/'media')
os.environ['OPENSHOT_PYTHON']=str(root/'openshot/MediaHost.exe')
os.environ['MOCK_FONT']='DejaVuSans.ttf'
os.environ['FFMPEG_FILTER_SCRIPT_OPTION']='-/filter_complex'
os.environ['ESPEAK_DATA_PATH']=str(root/'speech')
os.environ['PATH']=os.pathsep.join(str(root/p) for p in ['ffmpeg/bin','speech','postgres/bin','python','msvc'])+os.pathsep+os.environ.get('SystemRoot',r'C:\Windows')+r'\System32'
os.chdir(root/'backend')
if args.action=='tests':
    import pytest
    raise SystemExit(pytest.main([str(repo/'backend/tests'),'-q','-p','no:cacheprovider']))
if args.action=='concurrency':
    runpy.run_path(str(repo/'backend/tools/postgres_concurrency.py'),run_name='__main__')
if args.action=='snapshot':
    from studio.db import Session,Project
    with Session() as session:
        print(json.dumps(sorted([(p.id,p.revision) for p in session.query(Project)])))
