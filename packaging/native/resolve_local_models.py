"""Resolve portable media runtimes on Windows, with all downloads/cache on the chosen drive.

Produces immutable model_locks consumed by the in-app installer. Run with the
bundled Windows Python; never resolve Windows dependency markers on Linux.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import zipfile

SPECS = {
    'kokoro': {
        'repo': 'hexgrad/Kokoro-82M',
        'requirements': ['torch==2.6.0+cpu', 'kokoro==0.9.4', 'soundfile==0.13.1', 'transformers==4.51.3',
            'https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl'],
        'index': 'https://download.pytorch.org/whl/cpu',
    },
    'wan': {
        'repo': 'Wan-AI/Wan2.1-T2V-1.3B-Diffusers',
        'requirements': ['torch==2.6.0+cu124', 'diffusers==0.35.1', 'transformers==4.51.3',
            'accelerate==1.12.0', 'sentencepiece==0.2.1', 'imageio-ffmpeg==0.6.0',
            'imageio==2.37.0', 'ftfy==6.3.1', 'protobuf==5.29.5'],
        'index': 'https://download.pytorch.org/whl/cu124',
    },
    'ace_step': {
        'repo': 'ACE-Step/Ace-Step1.5',
        'requirements': ['torch==2.7.1+cu126', 'torchaudio==2.7.1+cu126',
            'torchvision==0.22.1+cu126', 'transformers==4.57.6', 'diffusers==0.37.0',
            'accelerate==1.12.0', 'soundfile==0.13.1', 'scipy', 'loguru==0.7.3',
            'einops==0.8.1', 'numba==0.63.1', 'vector-quantize-pytorch==1.27.15',
            'peft==0.18.0', 'PyYAML', 'tqdm', 'matplotlib', 'safetensors', 'psutil'],
        'index': 'https://download.pytorch.org/whl/cu126',
        'source_revision': 'ca1e85fe9430179831e6bc6be790c332190a3866',
    },
    'stable_audio': {
        'repo': 'stabilityai/stable-audio-open-small',
        'requirements': ['torch==2.7.1+cu126', 'torchaudio==2.7.1+cu126',
            'torchvision==0.22.1+cu126', 'numpy==1.26.4',
            'stable-audio-tools==0.0.20', 'transformers==4.57.6', 'soundfile==0.13.1',
            'pytorch-lightning==2.5.5', 'torchmetrics==0.11.4'],
        'index': 'https://download.pytorch.org/whl/cu126',
        'python_version': '3.10.11', 'python_tag': 'python310', 'gated': True,
    },
}
VOICES = {'af_heart', 'af_bella', 'af_nicole', 'am_adam', 'am_michael', 'bf_emma', 'bm_george'}


class PrivateRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urllib.parse.urlparse(req.full_url).netloc != urllib.parse.urlparse(newurl).netloc:
            redirected.remove_header('Authorization')
        return redirected


def get(url):
    headers = {}
    if urllib.parse.urlparse(url).hostname == 'huggingface.co' and os.getenv('HF_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['HF_TOKEN']
    opener = urllib.request.build_opener(PrivateRedirect())
    with opener.open(urllib.request.Request(url, headers=headers), timeout=90) as response:
        return response.read()


def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): return
    part = path.with_suffix(path.suffix + '.part')
    with urllib.request.urlopen(url, timeout=90) as response, part.open('wb') as output:
        while chunk := response.read(1024 * 1024): output.write(chunk)
    part.replace(path)


def artifact(url, path, file=None, **extra):
    if file:
        size = file.stat().st_size
        with file.open('rb') as stream: sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    else:
        payload = get(url)
        size, sha = len(payload), hashlib.sha256(payload).hexdigest()
    return dict(url=url, path=path, size=size, sha256=sha, **extra)


def remote_size(url):
    headers = {'User-Agent': 'pip/26.0', 'Cache-Control': 'no-cache'}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers, method='HEAD'), timeout=90) as response:
            return int(response.headers['Content-Length'])
    except urllib.error.HTTPError as error:
        if error.code not in (403, 405): raise
    # Some artifact CDNs disallow HEAD while permitting the actual download.
    with urllib.request.urlopen(urllib.request.Request(url, headers={**headers, 'Range': 'bytes=0-0'}), timeout=90) as response:
        if response.status == 206:
            return int(response.headers['Content-Range'].rsplit('/', 1)[1])
        return int(response.headers['Content-Length'])


def model_files(name, spec):
    metadata = json.loads(get('https://huggingface.co/api/models/' + spec['repo'] + '?blobs=true'))
    revision = metadata['sha']
    artifacts = []
    for entry in metadata['siblings']:
        filename = entry['rfilename']
        if name == 'kokoro':
            wanted = filename in ('config.json', 'kokoro-v1_0.pth') or filename in {'voices/' + v + '.pt' for v in VOICES}
        elif name == 'wan':
            wanted = filename == 'model_index.json' or filename.split('/')[0] in {'scheduler', 'tokenizer', 'text_encoder', 'transformer', 'vae'}
        elif name == 'ace_step':
            wanted = filename.split('/')[0] in {'acestep-v15-turbo', 'vae', 'Qwen3-Embedding-0.6B'}
        elif name == 'stable_audio':
            wanted = filename in ('model_config.json', 'model.safetensors', 'LICENSE')
        else:
            raise ValueError('Model file selection is not configured')
        if not wanted: continue
        url = f"https://huggingface.co/{spec['repo']}/resolve/{revision}/{filename}"
        # ACE-Step otherwise rewrites checkpoint Python from its source tree
        # on first inference. Pin that exact code at install time instead.
        source_code = name == 'ace_step' and filename.startswith('acestep-v15-turbo/') and filename.endswith('.py')
        if source_code:
            url = f"https://raw.githubusercontent.com/ace-step/ACE-Step-1.5/{spec['source_revision']}/acestep/models/turbo/{Path(filename).name}"
        lfs = entry.get('lfs')
        if lfs and not source_code:
            item = dict(url=url, path='model/' + filename, size=lfs['size'], sha256=lfs['sha256'])
        else:
            item = artifact(url, 'model/' + filename)
        if name == 'ace_step': item['path'] = 'model/checkpoints/' + filename
        if spec.get('gated'): item['gated'] = True
        artifacts.append(item)
    if not artifacts: raise RuntimeError('No model artifacts found')
    if name == 'stable_audio':
        # The frozen text encoder is not included in the audio checkpoint.
        encoder = 'google-t5/t5-base'
        metadata = json.loads(get('https://huggingface.co/api/models/' + encoder + '?blobs=true'))
        wanted = {'config.json', 'model.safetensors', 'spiece.model', 'tokenizer.json'}
        for entry in metadata['siblings']:
            filename = entry['rfilename']
            if filename not in wanted: continue
            url = f"https://huggingface.co/{encoder}/resolve/{metadata['sha']}/{filename}"
            path = 'model/t5-base/' + filename
            lfs = entry.get('lfs')
            artifacts.append(dict(url=url, path=path, size=lfs['size'], sha256=lfs['sha256'])
                             if lfs else artifact(url, path))
            wanted.remove(filename)
        if wanted: raise RuntimeError('Missing T5 encoder artifacts: ' + ', '.join(sorted(wanted)))
    return revision, artifacts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model', choices=SPECS)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--locks', type=Path, required=True)
    parser.add_argument('--reuse-report', action='store_true', help='Reuse a completed report from these exact dependency requirements')
    parser.add_argument('--runtime-only', action='store_true', help='Resolve public runtime dependencies without accessing weights or writing an installable model manifest')
    args = parser.parse_args()
    if os.name != 'nt': raise SystemExit('Resolve on native Windows to evaluate dependency markers correctly')
    spec = SPECS[args.model]
    if spec.get('gated') and not args.runtime_only and not os.getenv('HF_TOKEN'):
        raise SystemExit('Stable Audio requires approved upstream access and the Hugging Face token saved through Admin.')
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    for name in ('scratch', 'pip-cache'): (work/name).mkdir(exist_ok=True)
    env = os.environ.copy()
    for key in ('HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'RUNWAY_API_KEY', 'ELEVENLABS_API_KEY'):
        env.pop(key, None)
    env.update(TEMP=str(work/'scratch'), TMP=str(work/'scratch'), PIP_CACHE_DIR=str(work/'pip-cache'),
               PYTHONUTF8='1', PIP_DISABLE_PIP_VERSION_CHECK='1')
    version = spec.get('python_version', '3.12.10')
    python_tag = spec.get('python_tag', 'python312')
    runtime = work/('resolver-'+python_tag)
    archive = work/f'python-{version}-embed-amd64.zip'
    python_url = f'https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip'
    fetch(python_url, archive)
    if not (runtime/'python.exe').exists():
        with zipfile.ZipFile(archive) as bundle: bundle.extractall(runtime)
    (runtime/(python_tag+'._pth')).write_text(python_tag+'.zip\n.\nLib/site-packages\nimport site\n')
    pip = work/'pip.pyz'
    fetch('https://bootstrap.pypa.io/pip/pip.pyz', pip)
    report = work/(args.model+'-resolution.json')
    command = [str(runtime/'python.exe'), str(pip), 'install', '--dry-run', '--ignore-installed',
               '--only-binary=:all:', '--report', str(report), '--extra-index-url', spec['index'], *spec['requirements']]
    print('Resolving ' + args.model + ' dependencies on Windows', flush=True)
    if not args.reuse_report:
        subprocess.run(command, env=env, check=True)
    if args.runtime_only:
        print('Runtime dependency report prepared: ' + str(report), flush=True)
        return
    artifacts = [artifact(python_url, 'downloads/'+archive.name, archive, extract='runtime')]
    resolution = json.loads(report.read_text(encoding='utf-8'))
    for package in resolution['install']:
        download = package['download_info']
        url = download['url']
        filename = urllib.parse.unquote(urllib.parse.urlparse(url).path.split('/')[-1])
        if not filename.endswith('.whl'): raise RuntimeError('Unpinned source build required: ' + filename)
        print('Pinning ' + filename, flush=True)
        size = remote_size(url)
        archive_info = download['archive_info']
        sha = archive_info.get('hashes', {}).get('sha256')
        if not sha and archive_info.get('hash', '').startswith('sha256='):
            sha = archive_info['hash'].split('=', 1)[1]
        if not sha:
            cached = work / 'wheel-artifacts' / filename
            fetch(url, cached)
            sha = artifact(url, filename, cached)['sha256']
        artifacts.append(dict(url=url, path='downloads/'+filename, size=size,
                              sha256=sha, wheel=True))
    revision, weights = model_files(args.model, spec)
    artifacts.extend(weights)
    python_paths = []
    if spec.get('source_revision'):
        commit = spec['source_revision']
        url = 'https://codeload.github.com/ace-step/ACE-Step-1.5/zip/' + commit
        source_zip = work / ('ace-step-' + commit + '.zip')
        fetch(url, source_zip)
        artifacts.append(artifact(url, 'downloads/' + source_zip.name, source_zip,
                                  extract='runtime/Lib/site-packages/ace-source'))
        python_paths.append('Lib/site-packages/ace-source/ACE-Step-1.5-' + commit)
    encoded = json.dumps(artifacts, sort_keys=True).encode()
    lock = dict(revision=hashlib.sha256(encoded).hexdigest(), model_revision=revision,
                python_tag=python_tag, python_paths=python_paths, artifacts=artifacts,
                expanded_bytes=4*sum(a['size'] for a in artifacts if a.get('wheel') or a.get('extract')))
    args.locks.mkdir(parents=True, exist_ok=True)
    destination = args.locks/(args.model+'.json')
    destination.write_text(json.dumps(lock, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('Pinned ' + str(destination), flush=True)


if __name__ == '__main__': main()
