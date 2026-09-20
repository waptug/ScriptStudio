import zipfile
import hashlib

import pytest

from studio.local_models import extract_wheel


def test_cancel_during_resume_verification_preserves_complete_partial(tmp_path):
    from studio import local_models
    payload = b'completed pinned download'
    target = tmp_path / 'weight.bin'
    partial = target.with_name('weight.bin.part')
    partial.write_bytes(payload)
    artifact = {'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
    with pytest.raises(InterruptedError, match='Verification canceled'):
        local_models.download(artifact, target, lambda: True, lambda n: None)
    assert partial.read_bytes() == payload
    assert not target.exists()


def test_resume_promotes_a_complete_verified_partial_without_redownloading(tmp_path, monkeypatch):
    from studio import local_models
    payload = b'completed pinned download'
    target = tmp_path / 'weight.bin'
    target.with_name('weight.bin.part').write_bytes(payload)
    artifact = {'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
                'url': 'https://example.invalid/weight.bin'}
    def unexpected_network(*args, **kwargs):
        pytest.fail('A complete verified partial must not be downloaded again')
    monkeypatch.setattr(local_models.httpx, 'stream', unexpected_network)
    progress = []
    local_models.download(artifact, target, lambda: False, progress.append)
    assert target.read_bytes() == payload
    assert not target.with_name('weight.bin.part').exists()
    assert progress == [len(payload)]


def test_slow_installation_is_active_until_its_os_lock_is_released(tmp_path, monkeypatch):
    from studio import local_models
    monkeypatch.setattr(local_models, 'root', lambda: tmp_path)
    monkeypatch.setattr(local_models, 'hardware', lambda: {'gpus': []})
    monkeypatch.setattr(local_models, 'manifest', lambda name: None)
    monkeypatch.setattr(local_models, 'state', lambda name: {'state': 'installing', 'updated': 0})
    service = local_models.LocalModelService()
    with local_models.file_reservation(tmp_path / 'kokoro.lock'):
        assert service.catalog()['models'][0]['state'] == 'installing'
    assert service.catalog()['models'][0]['state'] == 'interrupted'


def test_ready_model_catalog_merges_revision_without_exposing_inventory(tmp_path, monkeypatch):
    from studio import local_models
    runtime = tmp_path / 'kokoro/runtime'
    runtime.mkdir(parents=True)
    (runtime / 'python.exe').write_bytes(b'test runtime')
    monkeypatch.setattr(local_models, 'root', lambda: tmp_path)
    monkeypatch.setattr(local_models, 'hardware', lambda: {'gpus': []})
    monkeypatch.setattr(local_models, 'manifest', lambda name: {'revision': 'pinned', 'artifacts': []})
    monkeypatch.setattr(local_models, 'state', lambda name: {
        'state': 'ready', 'revision': 'pinned', 'inventory': {'runtime/python.exe': 'hash'}})
    model = next(m for m in local_models.LocalModelService().catalog()['models'] if m['id'] == 'kokoro')
    assert model['ready'] is True
    assert model['revision'] == 'pinned'
    assert 'inventory' not in model


def test_wheel_installs_library_and_data_in_embedded_runtime(tmp_path):
    wheel = tmp_path / 'example.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr('example/__init__.py', 'VALUE = 42\n')
        archive.writestr('example-1.0.data/purelib/extra.py', 'DATA = True\n')
        archive.writestr('example-1.0.data/data/share/model/config.json', '{}')
    runtime = tmp_path / 'runtime'
    extract_wheel(wheel, runtime, lambda: False)
    assert (runtime / 'Lib/site-packages/example/__init__.py').read_text() == 'VALUE = 42\n'
    assert (runtime / 'Lib/site-packages/extra.py').is_file()
    assert (runtime / 'share/model/config.json').read_text() == '{}'


@pytest.mark.parametrize('entry', ['../../escaped.txt', 'example-1.0.data/purelib/../../escaped.txt'])
def test_wheel_rejects_paths_outside_install_scheme(tmp_path, entry):
    wheel = tmp_path / 'unsafe.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr(entry, 'unsafe')
    with pytest.raises(ValueError, match='Unsafe artifact path'):
        extract_wheel(wheel, tmp_path / 'runtime', lambda: False)
    assert not (tmp_path / 'escaped.txt').exists()


def test_wheel_cancellation_leaves_no_new_files(tmp_path):
    wheel = tmp_path / 'example.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr('example.py', 'VALUE = 42\n')
    with pytest.raises(InterruptedError):
        extract_wheel(wheel, tmp_path / 'runtime', lambda: True)
    assert not (tmp_path / 'runtime').exists()


def test_cached_artifact_reports_completion_without_network(tmp_path, monkeypatch):
    from studio import local_models
    payload = b'already installed weights'
    target = tmp_path / 'model.bin'
    target.write_bytes(payload)
    artifact = {'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
    monkeypatch.setattr(local_models.httpx, 'stream', lambda *a, **k: pytest.fail('Unexpected download'))
    reports = []
    checks = []
    local_models.download(artifact, target, lambda: False, reports.append, checking=checks.append)
    assert reports == [len(payload)]
    assert checks == ['model.bin']


def test_large_archive_reports_bytes_and_can_cancel_mid_file(tmp_path):
    from studio import local_models
    archive = tmp_path / 'runtime.zip'
    payload = b'x' * (3 * 1024 * 1024)
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('large.dll', payload)
    reports = []
    with pytest.raises(InterruptedError):
        local_models.extract(archive, tmp_path / 'canceled', lambda: bool(reports), reports.append)
    assert reports == [1024 * 1024]
    assert (tmp_path / 'canceled/large.dll').stat().st_size == 1024 * 1024
    reports.clear()
    local_models.extract(archive, tmp_path / 'complete', lambda: False, reports.append)
    assert sum(reports) == len(payload)
    assert (tmp_path / 'complete/large.dll').read_bytes() == payload


def test_install_reuses_verified_model_across_service_restarts(tmp_path, monkeypatch):
    from studio import local_models
    runtime = tmp_path / 'kokoro/runtime'
    runtime.mkdir(parents=True)
    (runtime / 'python.exe').write_bytes(b'installed runtime')
    monkeypatch.setattr(local_models, 'root', lambda: tmp_path)
    monkeypatch.setattr(local_models, 'manifest', lambda name: {'revision': 'pinned', 'artifacts': []})
    monkeypatch.setattr(local_models, 'hardware', lambda: {'gpus': []})
    local_models.update('kokoro', state='ready', revision='pinned', progress=1, inventory={'runtime/python.exe': 'hash'})
    monkeypatch.setattr(local_models.LocalModelService, 'install', lambda *a, **k: pytest.fail('Must reuse installation'))
    for _ in range(2):
        service = local_models.LocalModelService()
        assert service.catalog()['models'][0]['ready']
        assert service.action('kokoro', 'install')['state'] == 'ready'
    assert (runtime / 'python.exe').read_bytes() == b'installed runtime'


def test_real_install_reports_unpack_verify_and_probe(tmp_path, monkeypatch):
    from studio import local_models, local_inference
    archive = tmp_path / 'kokoro/runtime.zip'
    archive.parent.mkdir()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('python.exe', b'fake runtime for installer test')
    lock = {'revision': 'pinned', 'expanded_bytes': 100,
            'artifacts': [{'path': 'runtime.zip', 'extract': 'runtime', 'size': archive.stat().st_size,
                           'sha256': local_models.digest(archive)}]}
    monkeypatch.setattr(local_models, 'root', lambda: tmp_path)
    monkeypatch.setattr(local_inference, 'probe', lambda name: None)
    updates = []
    original = local_models.update
    def record(name, **values):
        updates.append(values)
        original(name, **values)
    monkeypatch.setattr(local_models, 'update', record)
    local_models.LocalModelService().install('kokoro', lock)
    assert local_models.state('kokoro')['state'] == 'ready'
    assert any(u.get('phase') == 'extracting' and u.get('progress') == 1 for u in updates)
    assert any(u.get('phase') == 'verifying' and u.get('progress') == 1 for u in updates)
    assert any(u.get('phase') == 'probing' and u.get('progress') is None for u in updates)


def test_installer_heartbeat_continues_during_slow_step(tmp_path, monkeypatch):
    import threading
    import time
    from studio import local_models
    monkeypatch.setattr(local_models, 'root', lambda: tmp_path)
    monkeypatch.setattr(local_models, 'manifest', lambda name: {'revision': 'pinned', 'artifacts': []})
    release = threading.Event()
    entered = threading.Event()
    def slow_install(self, name, lock, verify_only=False):
        entered.set()
        assert release.wait(10)
        local_models.update(name, state='ready')
    monkeypatch.setattr(local_models.LocalModelService, 'install', slow_install)
    service = local_models.LocalModelService()
    service.action('kokoro', 'verify')
    assert entered.wait(2)
    first = local_models.state('kokoro')['heartbeat']
    try:
        deadline = time.monotonic() + 5
        while local_models.state('kokoro')['heartbeat'] == first and time.monotonic() < deadline:
            time.sleep(.05)
        saved = local_models.state('kokoro')
        assert saved['heartbeat'] > first
        assert saved['progress'] is None
        assert saved['state'] == 'verifying'
    finally:
        release.set()
        for thread in threading.enumerate():
            if thread.name == 'model-install-kokoro': thread.join(5)
