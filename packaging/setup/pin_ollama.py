"""Maintainer-only resolver; setup never follows a mutable release/tag."""
import hashlib
import json
from pathlib import Path
import urllib.request

locks = Path(__file__).resolve().parents[2] / 'backend/studio/model_locks'
release = json.load(urllib.request.urlopen('https://api.github.com/repos/ollama/ollama/releases/tags/v0.40.3', timeout=20))
asset = next(a for a in release['assets'] if a['name'] == 'ollama-windows-amd64.zip')
if not asset.get('digest', '').startswith('sha256:'):
    raise ValueError('Official release has no artifact digest')
(locks/'ollama.json').write_text(json.dumps(dict(revision=release['tag_name'], python_tag='none',
    expanded_bytes=6*1024**3, license='MIT', source='https://github.com/ollama/ollama',
    expansion_basis='Conservative 6 GiB allowance; archive uncompressed bytes checked before extraction',
    artifacts=[dict(url=asset['browser_download_url'],path='downloads/ollama-windows-amd64.zip',size=asset['size'],sha256=asset['digest'][7:],extract='runtime')]),indent=2))
raw = urllib.request.urlopen('https://registry.ollama.ai/v2/library/gemma3/manifests/4b',timeout=20).read()
manifest = json.loads(raw)
artifacts=[]
for blob in [manifest['config'],*manifest['layers']]:
    sha=blob['digest'][7:]
    artifacts.append(dict(url='https://registry.ollama.ai/v2/library/gemma3/blobs/'+blob['digest'],path='blobs/sha256-'+sha,size=blob['size'],sha256=sha))
(locks/'gemma.json').write_text(json.dumps(dict(revision=hashlib.sha256(raw).hexdigest(),python_tag='none',license='Gemma terms: https://ai.google.dev/gemma/terms',
    source='https://ollama.com/library/gemma3:4b',expanded_bytes=sum(a['size'] for a in artifacts),
    manifest_text=raw.decode(),artifacts=artifacts),indent=2))
print('Pinned official Ollama archive and immutable Gemma blob hashes')
