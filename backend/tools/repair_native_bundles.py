"""Repair development-era native bundles serialized after OpenShot reader mapping.

No timeline, job, or source media changes. Rebuild native metadata from the original
immutable render inputs, and atomically replace only the portable ZIP.
"""
import json
from pathlib import Path
from studio.db import Session,Job
from studio.storage import LocalStorage,run
from studio.openshot_bundle import OpenShotBundleService

storage=LocalStorage()
with Session() as session:
    for job in session.query(Job).filter_by(kind='render',state='ready'):
        if not job.result.get('openshot_bundle'):continue
        folder=storage.path(job.result['openshot_bundle']).parent
        native=json.loads((folder/'native-project.json').read_text())
        if not any(c.get('reader',{}).get('type')=='FrameMapper' for c in native['clips']):continue
        config=json.loads((folder/'openshot-input.json').read_text());config['serialize_only']=True
        request=folder/'serialize-only.json';request.write_text(json.dumps(config))
        run(['/usr/bin/python3','/app/studio/openshot_runner.py',str(request)])
        OpenShotBundleService().create(session,storage,job.project_id,folder,folder/'output.mp4',job.inputs)
        print('Repaired native reader metadata for render '+job.id,flush=True)
