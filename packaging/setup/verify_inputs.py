"""Fail closed if a prepared native build input differs from the pinned download."""
import hashlib
import json
import os
from pathlib import Path
root=Path(os.environ.get('SCRIPTSTUDIO_NATIVE_INPUT','artifacts/native'))
locks=json.loads(Path(__file__).with_name('native-inputs.json').read_text())
for name,expected in locks.items():
    with (root/'downloads'/name).open('rb') as source:
        actual=hashlib.file_digest(source,'sha256').hexdigest()
    if actual!=expected:raise ValueError('Native input mismatch: '+name)
print('PASS pinned native download inputs')
