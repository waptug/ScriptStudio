"""Run repository backend checks using bundled Windows Python, isolated scratch."""
import os
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2]
scratch=root/'artifacts/setup/backend-checks'
scratch.mkdir(parents=True,exist_ok=True)
os.environ.update(TEMP=str(scratch),TMP=str(scratch),TMPDIR=str(scratch),LIVE_GENERATION_ENABLED='false')
runtime=Path(sys.executable).resolve().parent.parent
os.environ.update(OPENSHOT_PYTHON=str(runtime/'openshot/MediaHost.exe'),
    MOCK_FONT='DejaVuSans.ttf', ESPEAK_DATA_PATH=str(runtime/'speech'),
    FFMPEG_FILTER_SCRIPT_OPTION='-/filter_complex')
os.environ['PATH']=os.pathsep.join(str(runtime/p) for p in ['ffmpeg/bin','speech','postgres/bin','python','msvc'])+os.pathsep+os.environ.get('SystemRoot',r'C:\Windows')+r'\System32'
import tempfile
tempfile.tempdir=str(scratch)
sys.path.insert(0,str(root/'backend'))
import pytest
os.chdir(runtime/'backend')
targets=[str(root/'backend/tests'/arg) for arg in sys.argv[1:]] or [str(root/'backend/tests')]
raise SystemExit(pytest.main([*targets,'-q','-p','no:cacheprovider']))
