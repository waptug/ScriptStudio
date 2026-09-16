"""Portable OpenShot handoff, preserving original sources and the exact revision."""
import json
import os
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED
from sqlalchemy import select
from .db import Asset, Job, public
from .storage import run


class OpenShotBundleService:
    def create(self, session, storage, project_id, folder, output, inputs):
        mix=folder/'finished-audio.m4a'
        run(['ffmpeg','-v','error','-y','-i',str(output),'-vn','-c:a','copy',str(mix)])
        sources=[a for a in session.scalars(select(Asset).where(Asset.project_id==project_id)) if a.provenance.get('provider')!='ffmpeg']
        total_frames=max(i['start']+i['duration'] for i in inputs['timeline']['items'])
        config={'native':str(folder/'native-project.json'),'mix':str(mix),'frames':total_frames,
                'sources':[{'id':a.id,'kind':a.kind,'path':str(storage.path(a.path))} for a in sources],
                'output':str(folder/'bundle-project.json')}
        config_path=folder/'bundle-input.json'
        config_path.write_text(json.dumps(config))
        run(['/usr/bin/python3',str(Path(__file__).with_name('openshot_bundle_runner.py')),str(config_path)])
        document=json.loads((folder/'bundle-project.json').read_text())
        archive=folder/'ScriptStudio-OpenShot.zip'
        with ZipFile(archive.with_suffix('.partial'),'w',ZIP_STORED) as bundle:
            path_map={}
            for entry in document['files']:
                original=entry['path']
                if original not in path_map:
                    path=Path(original)
                    relative=f'media/{len(path_map):04}-{path.name}'
                    path_map[original]=relative
                    bundle.write(path,relative)
            def relocate(value):
                if isinstance(value,dict):return {k:relocate(v) for k,v in value.items()}
                if isinstance(value,list):return [relocate(v) for v in value]
                if isinstance(value,str):return path_map.get(value,value)
                return value
            document=relocate(document)
            bundle.writestr('ScriptStudio.osp',json.dumps(document,indent=2))
            bundle.writestr('scriptstudio-revision.json',json.dumps(inputs,indent=2))
            history=[]
            for job in session.scalars(select(Job).where(Job.project_id==project_id)):
                row=public(job)
                row['inputs']={k:v for k,v in row['inputs'].items() if k!='prompt_image'}
                row['result']={k:v for k,v in row['result'].items() if k not in ('url','local_path')}
                history.append(row)
            bundle.writestr('generation-history.json',json.dumps(history,indent=2))
            bundle.writestr('assets.json',json.dumps([public(a) for a in sources],indent=2))
            for ext in ('srt','vtt'):bundle.write(folder/f'captions.{ext}',f'captions.{ext}')
            bundle.writestr('README.txt',
                'Extract the entire archive, then open ScriptStudio.osp in OpenShot.\n'
                'Visual clips remain individually editable, with native transforms and fade keyframes.\n'
                'Source coverage (trim, loop, hold) is normalized into the timeline clips.\n'
                'Original media and alternate takes are also in the media library.\n'
                'Titles/captions are transparent image clips; edit wording in ScriptStudio and re-export,\n'
                'or replace them with OpenShot titles. Finished audio is one exact mix with ducking/fades baked;\n'
                'original narration, music, and effects remain in the library for further remixing.\n'
                'This is a one-way handoff: desktop edits do not synchronize back to ScriptStudio.\n')
        os.replace(archive.with_suffix('.partial'),archive)
        return str(archive.relative_to(storage.root))
