"""Run with bundled Python and an isolated container name; test parent-death recovery."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from studio.resource_optimization import Host

container = sys.argv[1]
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
    root = Path(directory)
    config = {'enabled': True, 'containers': [container]}
    (root / 'resource-optimization.json').write_text(json.dumps(config))
    host = Host(config)
    original = host.snapshot(os.getpid())
    child = subprocess.Popen([sys.executable, '-c', '''
import time, sys
sys.path.insert(0, sys.argv[1])
from studio.resource_optimization import RenderResources, ResourcePreparationPending
resources = RenderResources()
while True:
    try:
        resources.update(True)
        break
    except ResourcePreparationPending:
        time.sleep(.2)
print('reserved', flush=True)
time.sleep(300)
''', str(Path(__file__).resolve().parents[1])], env={**os.environ, 'SCRIPTSTUDIO_RESOURCE_DIR': directory}, stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == 'reserved'
        assert json.loads(host.run(host.docker + ['inspect', container]))[0]['State']['Paused']
        child.kill()
        child.wait(10)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            state = json.loads((root / 'resource-state.json').read_text())
            if not state['pending']:
                break
            time.sleep(.25)
        assert not state['pending'], state
        assert host.snapshot(os.getpid()) == original
        print('PASS: abrupt parent death restored container and original power plan')
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(10)
