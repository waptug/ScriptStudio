import json
import pytest
from studio.resource_optimization import Reservation, Host


class FakeHost:
    def __init__(self):
        self.paused = set()
        self.fail_apply = None
        self.fail_restore = None
        self.applied = []

    def acquire(self):
        pass

    def release(self):
        pass

    def snapshot(self, owner):
        return [{'kind': 'container', 'id': name} for name in ['a', 'b'] if name not in self.paused]

    def apply(self, item):
        self.paused.add(item['id'])
        self.applied.append(item['id'])
        if item['id'] == self.fail_apply:
            raise RuntimeError('apply failed after mutation')

    def restore(self, item):
        if item['id'] == self.fail_restore:
            raise RuntimeError('daemon unavailable')
        self.paused.discard(item['id'])


def test_session_is_idempotent_and_preserves_prepaused_work(tmp_path):
    host = FakeHost()
    host.paused.add('b')
    reservation = Reservation(tmp_path, host)
    reservation.begin(1)
    reservation.begin(1)
    assert host.applied == ['a']
    reservation.restore()
    assert host.paused == {'b'}
    assert json.loads(reservation.path.read_text())['pending'] == []


def test_partial_failure_rolls_back_including_uncertain_mutation(tmp_path):
    host = FakeHost()
    host.fail_apply = 'b'
    reservation = Reservation(tmp_path, host)
    with pytest.raises(RuntimeError, match='apply failed'):
        reservation.begin(1)
    assert host.paused == set()
    assert not reservation.state['active']


def test_recovery_survives_restart_and_retries_only_failed_actions(tmp_path):
    host = FakeHost()
    reservation = Reservation(tmp_path, host)
    reservation.begin(1)
    host.fail_restore = 'a'
    with pytest.raises(RuntimeError, match='restoration pending'):
        Reservation(tmp_path, host).restore()
    assert host.paused == {'a'}
    assert [v['id'] for v in json.loads(reservation.path.read_text())['pending']] == ['a']
    host.fail_restore = None
    Reservation(tmp_path, host).restore()
    assert not host.paused


def test_docker_selection_and_identity(monkeypatch):
    host = Host({'containers': ['running', 'stopped', 'already-paused'],
                 'high_performance': False, 'above_normal_priority': False})
    rows = [{'Id': name, 'Name': name, 'State': {'Running': run, 'Paused': pause}}
            for name, run, pause in [('running', True, False), ('stopped', False, False), ('already-paused', True, True)]]
    monkeypatch.setattr(host, 'run', lambda command: json.dumps(rows))
    assert host.snapshot(1) == [{'kind': 'container', 'id': 'running', 'name': 'running'}]


def test_windows_host_reservations_are_exclusive():
    import os
    import subprocess
    import sys
    from pathlib import Path
    from studio.resource_optimization import ResourcePreparationPending
    if os.name != 'nt' or not os.getenv('RESOURCE_TEST_CONTAINER'):
        pytest.skip('Opt-in native host reservation test')
    child = subprocess.Popen([sys.executable, '-c',
        "import sys,time;sys.path.insert(0,sys.argv[1]);from studio.resource_optimization import Host;"
        "host=Host({});host.acquire();print('locked',flush=True);time.sleep(60)",
        str(Path(__file__).resolve().parents[1])], stdout=subprocess.PIPE, text=True)
    host = Host({})
    try:
        assert child.stdout.readline().strip() == 'locked'
        with pytest.raises(ResourcePreparationPending):
            host.acquire()
    finally:
        child.kill()
        child.wait(10)
    # Windows transfers an abandoned mutex without losing the recovery path.
    host.acquire()
    host.release()
