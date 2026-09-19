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
