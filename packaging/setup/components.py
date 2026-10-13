"""Accepted private Ollama/Gemma installation; no resolvers or development tools."""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.request


def compatible_service(lock, gemma, need_gemma):
    try:
        def get(path):
            with urllib.request.urlopen('http://127.0.0.1:11434'+path,timeout=2) as r:
                return json.load(r)
        version=get('/api/version')['version']
        parts=lambda v: tuple(int(p) for p in v.lstrip('v').split('.')[:3])
        if parts(version) < parts(lock['revision']):
            return False
        if need_gemma and not any(m.get('digest') == gemma['revision'] for m in get('/api/tags').get('models', [])):
            return False
        return True
    except (OSError, ValueError, KeyError):
        return False


def install(storage, selected):
    sys.path.insert(0,str(Path(__file__).resolve().parent/'backend'))
    from studio.local_models import download, extract, safe_path
    locks=Path(__file__).resolve().parent/'backend/studio/model_locks'
    ollama=json.loads((locks/'ollama.json').read_text())
    gemma=json.loads((locks/'gemma.json').read_text())
    base=storage/'local-llm';base.mkdir(exist_ok=True)
    canceled=lambda: (storage/'setup.cancel').exists()
    def report(offset):
        pass  # C# reports phases; byte verification remains mandatory.
    if compatible_service(ollama,gemma,'gemma' in selected):
        state={'contract_version':1,'external_url':'http://127.0.0.1:11434','gemma':'gemma' in selected,'verification':'service_version_and_model_digest'}
    else:
        for artifact in ollama['artifacts']:
            target=safe_path(base,artifact['path'])
            print('Downloading / verifying Ollama '+ollama['revision'],flush=True)
            download(artifact,target,canceled,report)
            import zipfile
            with zipfile.ZipFile(target) as archive:
                if sum(i.file_size+4096 for i in archive.infolist()) > ollama['expanded_bytes']:
                    raise ValueError('Ollama expansion exceeds accepted storage allowance')
            # Install into staging; interrupted extraction never activates a partial runtime.
            import shutil
            staging=base/'runtime.staging'
            if staging.exists():shutil.rmtree(staging)
            staging.mkdir()
            extract(target,staging,canceled)
            if not (staging/'ollama.exe').is_file():raise ValueError('Missing Ollama executable')
            runtime=base/('runtime-'+ollama['revision'])
            if runtime.exists():
                # Never reuse binaries based on a marker. Freshly verified archive repairs them.
                shutil.rmtree(runtime)
            staging.replace(runtime)
        if 'gemma' in selected:
            models=base/'models';models.mkdir(exist_ok=True)
            for artifact in gemma['artifacts']:
                print('Downloading / verifying Gemma blob '+artifact['sha256'][:12],flush=True)
                download(artifact,safe_path(models,artifact['path']),canceled,report)
            manifest=models/'manifests/registry.ollama.ai/library/gemma3/4b'
            manifest.parent.mkdir(parents=True,exist_ok=True)
            manifest.write_text(gemma['manifest_text'])
        state={'contract_version':1,'executable':str(runtime/'ollama.exe'),'models':str(base/'models'),'gemma':'gemma' in selected,'verification':'artifact_sha256','version':ollama['revision']}
    target=base/'service.json';temp=target.with_suffix('.tmp');temp.write_text(json.dumps(state));temp.replace(target)
    print('Ollama component artifacts verified',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--storage',type=Path,required=True)
    parser.add_argument('--gemma',action='store_true')
    args=parser.parse_args()
    install(args.storage,['ollama']+(['gemma'] if args.gemma else []))
