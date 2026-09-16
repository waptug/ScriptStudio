#!/usr/bin/python3
"""Headless desktop smoke: open an extracted project in the actual OpenShot GUI."""
import os
import json
import re
from pathlib import Path
import subprocess
import sys
import time
from zipfile import ZipFile
from PyQt5.QtWidgets import QApplication

archive=Path(sys.argv[1])
folder=Path('/tmp/openshot-desktop-project')
with ZipFile(archive) as bundle:bundle.extractall(folder)
os.environ['QT_QPA_PLATFORM']='xcb'
os.environ['OMP_NUM_THREADS']='2'
preferences=Path.home()/'.openshot_qt/openshot.settings'
preferences.parent.mkdir(parents=True,exist_ok=True)
if not preferences.exists():
    preferences.write_text(Path('/usr/lib/python3/dist-packages/openshot_qt/settings/_default.settings').read_text())
if preferences.exists():
    entries=json.loads(preferences.read_text())
    for entry in entries:
        if entry.get('setting') in ('tutorial_enabled','send_metrics'):entry['value']=False
    preferences.write_text(json.dumps(entries))
log=Path('/data/tmp/openshot-desktop.log')
with log.open('w') as output:
    process=subprocess.Popen(['/usr/bin/openshot-qt',str(folder/'ScriptStudio.osp')],stdout=output,stderr=subprocess.STDOUT)
    try:
        time.sleep(20)
        if process.poll() is not None:raise RuntimeError('OpenShot exited unexpectedly: '+log.read_text()[-4000:])
        app=QApplication([])
        app.primaryScreen().grabWindow(0).save('/data/tmp/openshot-desktop.png')
        content=log.read_text()
        assert 'INFO main_window: Loaded project '+str(folder/'ScriptStudio.osp') in content,'Project was not loaded'
        # The container is intentionally offline. Only known optional metrics/version
        # network failures are excluded; project/media/GUI tracebacks still fail.
        records=re.split(r'(?m)(?=^(?:INFO|WARNING|ERROR) )',content)
        for record in records:
            if 'Traceback (most recent call last)' in record and not record.startswith('WARNING metrics:'):
                raise RuntimeError('Desktop traceback: '+record[-3000:])
            if record.startswith('ERROR ') and not record.startswith('ERROR version: Failed to get version'):
                raise RuntimeError('Desktop error: '+record[:1000])
        print('PASS: actual OpenShot desktop loaded the portable project; optional offline telemetry/update failures excluded')
    finally:
        process.terminate()
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait()
