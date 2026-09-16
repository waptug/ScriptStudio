from urllib.parse import unquote

from fastapi.testclient import TestClient

from studio.api import app
from studio.db import Asset, Job, Project, transaction
from studio.schemas import Item, Timeline
from studio.storage import LocalStorage


def test_download_names_capture_project_and_preserve_inline_media(project_id):
    client = TestClient(app)
    with transaction() as session:
        project = session.get(Project, project_id)
        project.name = 'Café / River: dawn'
        project.timeline = Timeline(items=[Item(track='title', text='Hello', duration=24)]).model_dump()
    response = client.post(f'/api/projects/{project_id}/renders', json={'preview':False})
    assert response.status_code == 200
    job_id = response.json()['jobs'][-1]['id']
    storage = LocalStorage()
    path = storage.path(f'{project_id}/export-fixture.mp4')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'fixture')
    with transaction() as session:
        session.get(Project, project_id).name = 'Renamed project'
        job = session.get(Job, job_id)
        job.created = 1789554600  # 2026-09-16 10:30:00 UTC
        job.state = 'ready'
        job.asset_id = job_id
        relative = str(path.relative_to(storage.root))
        job.result = {'srt':relative, 'vtt':relative, 'openshot_bundle':relative}
        session.add(Asset(id=job_id, project_id=project_id, kind='video', name='Render',
                          path=relative, checksum='fixture', duration=1, info={}, provenance={}))
    for route, extension in [('video','mp4'), ('openshot','zip'), ('subtitles/srt','srt'), ('subtitles/vtt','vtt')]:
        result = client.get(f'/api/jobs/{job_id}/{route}')
        assert result.status_code == 200
        assert unquote(result.headers['content-disposition']) == f"attachment; filename*=utf-8''Café _ River_ dawn_2026-09-16_10-30-00Z.{extension}"
    inline = client.get(f'/api/assets/{job_id}/original', headers={'Range':'bytes=0-2'})
    assert inline.status_code == 206
    assert 'content-disposition' not in inline.headers
    # Existing exports without a captured name remain downloadable.
    with transaction() as session:
        job = session.get(Job, job_id)
        job.inputs = {key:value for key,value in job.inputs.items() if key!='project_name'}
    assert 'Renamed project_' in unquote(client.get(f'/api/jobs/{job_id}/video').headers['content-disposition'])
