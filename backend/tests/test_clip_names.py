import pytest
from studio.db import transaction, Asset, Project
from studio.storage import AssetRepository
from studio.timeline import Conflict


def test_clip_name_persists_without_changing_media_or_timeline(project_id):
    with transaction() as session:
        asset=Asset(id='clip',project_id=project_id,kind='video',name='generated.mp4',path='original.mp4',checksum='unchanged',duration=2,info={},provenance={})
        session.add(asset)
    with transaction() as session:
        project=session.get(Project,project_id)
        timeline=project.timeline.copy(); revision=project.revision
        AssetRepository.rename(session,project_id,'clip',' River opening ','generated.mp4')
        assert project.timeline==timeline and project.revision==revision
    with transaction() as session:
        asset=session.get(Asset,'clip')
        assert asset.name=='River opening' and asset.path=='original.mp4' and asset.checksum=='unchanged'
        with pytest.raises(Conflict):AssetRepository.rename(session,project_id,'clip','Stale','generated.mp4')
        with pytest.raises(ValueError):AssetRepository.rename(session,'other-project','clip','Bad','River opening')
        with pytest.raises(ValueError):AssetRepository.rename(session,project_id,'clip','   ','River opening')
