"""Native render-session resource reservation with an independent recovery process.

The guardian owns every host mutation and journals intent before applying it.
Closing its command pipe (including a crashed parent) triggers restoration.
"""
import json
import logging
import os
from pathlib import Path
import re
import queue
import threading
import subprocess
import sys
import time


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class Host:
    def __init__(self, config):
        self.config = config
        self.mutex = None
        self.locked = False
        self.docker = (['wsl.exe', '-d', config.get('wsl_distribution', 'Ubuntu'), '--', 'docker']
                       if os.name == 'nt' else ['docker'])

    def acquire(self):
        if os.name != 'nt' or self.locked:
            return
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
        if self.mutex is None:
            self.mutex = kernel.CreateMutexW(None, False, r'Local\ScriptStudioRenderResources')
            if not self.mutex:
                raise ctypes.WinError(ctypes.get_last_error())
        outcome = kernel.WaitForSingleObject(self.mutex, 0)
        if outcome == 258:
            raise ResourcePreparationPending('Another native session owns host resources')
        if outcome not in (0, 128):
            raise ctypes.WinError(ctypes.get_last_error())
        self.kernel = kernel
        self.locked = True

    def release(self):
        if self.locked:
            if not self.kernel.ReleaseMutex(self.mutex):
                raise RuntimeError('Cannot release host resource reservation')
            self.locked = False

    def run(self, args):
        return subprocess.run(args, check=True, capture_output=True, text=True, timeout=45,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.strip()

    def powershell(self, script):
        executable = str(Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe')
        return self.run([executable, '-NoProfile', '-NonInteractive', '-Command',
                         "$ErrorActionPreference='Stop'; " + script])

    def snapshot(self, owner):
        actions = []
        names = self.config.get('containers', [])
        if names:
            # Snapshot only explicitly selected, currently running and unpaused IDs.
            rows = json.loads(self.run(self.docker + ['container', 'inspect', *names]))
            for row in rows:
                if row['State']['Running'] and not row['State']['Paused']:
                    actions.append({'kind': 'container', 'id': row['Id'], 'name': row['Name']})
        if os.name == 'nt':
            if self.config.get('high_performance', True):
                scheme = self.run(['powercfg.exe', '/getactivescheme'])
                guid = re.search(r'[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}', scheme)
                if not guid:
                    raise RuntimeError('Cannot identify current power scheme')
                actions.append({'kind': 'power', 'original': guid.group()})
            if self.config.get('above_normal_priority', True):
                original = json.loads(self.powershell(
                    f'$p=Get-Process -Id {int(owner)}; '
                    '@{priority=$p.PriorityClass.ToString();ticks=$p.StartTime.Ticks.ToString()} | ConvertTo-Json'))
                actions.append({'kind': 'priority', 'pid': owner, **original})
        return actions

    def apply(self, item):
        if item['kind'] == 'container':
            self.run(self.docker + ['pause', item['id']])
        elif item['kind'] == 'power':
            self.run(['powercfg.exe', '/setactive', 'SCHEME_MIN'])
        else:
            self.priority(item, 'AboveNormal')

    def priority(self, item, value):
        if value not in ('Normal', 'Idle', 'High', 'RealTime', 'BelowNormal', 'AboveNormal'):
            raise ValueError('Invalid saved priority')
        self.powershell(f'$p=Get-Process -Id {int(item["pid"])} -ErrorAction SilentlyContinue; '
                        'if(-not $p){exit 0}; '
                        f'if($p.StartTime.Ticks.ToString() -eq "{int(item["ticks"])}")'
                        '{ $p.PriorityClass="' + value + '" }')

    def restore(self, item):
        if item['kind'] == 'container':
            # Listing IDs distinguishes a removed container from an unavailable daemon.
            ids = self.run(self.docker + ['ps', '-aq', '--no-trunc']).splitlines()
            if item['id'] not in ids:
                return
            row = json.loads(self.run(self.docker + ['inspect', item['id']]))[0]
            if row['State']['Paused']:
                self.run(self.docker + ['unpause', item['id']])
        elif item['kind'] == 'power':
            self.run(['powercfg.exe', '/setactive', item['original']])
        else:
            self.priority(item, item['priority'])


class Reservation:
    def __init__(self, directory, host):
        self.path = Path(directory) / 'resource-state.json'
        self.host = host
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {'pending': [], 'active': False}

    def save(self):
        self.state['updated'] = time.time()
        atomic_json(self.path, self.state)

    def restore(self):
        if self.state['pending']:
            self.host.acquire()
        errors = []
        for item in list(reversed(self.state['pending'])):
            try:
                self.host.restore(item)
                self.state['pending'].remove(item)
                self.save()
            except Exception as exc:
                errors.append(str(exc))
        self.state.update(active=False, errors=errors)
        self.save()
        if errors:
            raise RuntimeError('Resource restoration pending: ' + '; '.join(errors))
        self.host.release()

    def begin(self, owner):
        if self.state['active']:
            return
        self.restore()
        self.host.acquire()
        try:
            actions = self.host.snapshot(owner)
            for item in actions:
                self.state['pending'].append(item)
                self.save()  # Intent survives interruption during the command.
                self.host.apply(item)
            self.state.update(active=True, errors=[])
            self.save()
        except Exception:
            self.restore()
            raise


def guardian(directory, owner):
    from .platform_runtime import exclusive_file_lock
    directory = Path(directory)
    config = json.loads((directory / 'resource-optimization.json').read_text(encoding='utf-8-sig'))
    with exclusive_file_lock(directory / 'resource-optimization.lock'):
        reservation = Reservation(directory, Host(config))
        try:
            # Recover any previous process's journal before accepting new work.
            reservation.restore()
            for line in sys.stdin:
                try:
                    if line.strip() == 'begin':
                        reservation.begin(owner)
                    else:
                        reservation.restore()
                    print(json.dumps({'ok': True}), flush=True)
                except Exception as exc:
                    print(json.dumps({'ok': False, 'error': str(exc),
                                      'pending': isinstance(exc, ResourcePreparationPending)}), flush=True)
        finally:
            # Keep a live retry owner if Docker/WSL is temporarily unavailable.
            while True:
                try:
                    reservation.restore()
                    break
                except Exception:
                    time.sleep(5)


class ResourcePreparationPending(Exception):
    pass


class RenderResources:
    def __init__(self):
        self.process = None
        self.active = False
        self.pending = None
        self.responses = queue.Queue()
        self.directory = os.getenv('SCRIPTSTUDIO_RESOURCE_DIR')

    def update(self, needed):
        if not self.directory:
            return
        directory = Path(self.directory)
        config_path = directory / 'resource-optimization.json'
        if not config_path.exists():
            atomic_json(config_path, {'enabled': True, 'containers': [], 'wsl_distribution': 'Ubuntu',
                                     'high_performance': True, 'above_normal_priority': True})
        config = json.loads(config_path.read_text(encoding='utf-8-sig'))
        needed = needed and config.get('enabled', True)
        if self.process is not None and self.process.poll() is not None:
            self.process = None
            self.active = False
            self.pending = None
        if self.process is None:
            self.process = subprocess.Popen(
                [sys.executable, '-c',
                 'import sys; sys.path.insert(0, sys.argv[1]); '
                 'from studio.resource_optimization import guardian; guardian(sys.argv[2], int(sys.argv[3]))',
                 str(Path(__file__).resolve().parents[1]), str(directory), str(os.getpid())],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.responses = queue.Queue()
            def read_responses(process, responses):
                for line in process.stdout:
                    responses.put(line)
                responses.put('')
            threading.Thread(target=read_responses, args=(self.process, self.responses), daemon=True).start()
            # Even an idle startup must recover a stale reservation.
            self.active = None
        if self.pending is None:
            if needed == self.active:
                return
            self.process.stdin.write('begin\n' if needed else 'restore\n')
            self.process.stdin.flush()
            self.pending = needed
        try:
            response = self.responses.get(timeout=.2)
        except queue.Empty:
            raise ResourcePreparationPending('Resource guardian is preparing or restoring the session')
        if not response:
            raise RuntimeError('Resource guardian exited before acknowledgement')
        result = json.loads(response)
        acknowledged = self.pending
        self.pending = None
        if not result['ok']:
            if result.get('pending'):
                raise ResourcePreparationPending(result['error'])
            raise RuntimeError(result['error'])
        self.active = acknowledged
        if self.active != needed:
            self.update(needed)

    def close(self):
        if self.process:
            # EOF restores after the executor has drained. Guardian may outlive us
            # to retry restoration without depending on the application database.
            self.process.stdin.close()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logging.warning('Resource guardian is still restoring host operations')
            # The response reader owns stdout while a delayed recovery is alive.


if __name__ == '__main__':
    guardian(sys.argv[1], int(sys.argv[2]))
