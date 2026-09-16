from copy import deepcopy
import pytest
from studio.db import transaction, Session, Project, Asset, Revision
from studio.schemas import Item, Edit, uid
from studio.timeline import TimelineService, Conflict


def fake_asset(session,pid,shot='shot-a'):
    asset=Asset(id=uid(),project_id=pid,kind='video',name='Take',path='not-used.mp4',checksum='123',duration=5,info={},provenance={'shot_id':shot})
    session.add(asset)
    session.flush()
    return asset


def test_out_of_order_move_delete_duplicate_completion_and_takes(project_id):
    service=TimelineService()
    with transaction() as s:
        p=s.get(Project,project_id)
        a=Item(track='video',shot_id='shot-a',duration=120)
        b=Item(track='video',shot_id='shot-b',start=120,duration=120)
        c=Item(track='video',shot_id='shot-c',start=240,duration=120)
        service.save(s,p,{'version':1,'items':[i.model_dump() for i in (a,b,c)]})
        service.edit(s,p,Edit(revision=p.revision,operation='move',item_id=a.id,values={'start':400,'duration':60}))
        service.edit(s,p,Edit(revision=p.revision,operation='delete',item_id=c.id))
        take_b=fake_asset(s,p.id,'shot-b')
        assert service.fill(s,p,b.id,take_b)
        take_c=fake_asset(s,p.id,'shot-c')
        assert not service.fill(s,p,c.id,take_c)
        take_a=fake_asset(s,p.id)
        assert service.fill(s,p,a.id,take_a)
        assert not service.fill(s,p,a.id,take_a)
        second=fake_asset(s,p.id)
        assert not service.fill(s,p,a.id,second)
        current=next(i for i in p.timeline['items'] if i['id']==a.id)
        assert (current['start'],current['duration'],current['asset_id'])==(400,60,take_a.id)
        assert len(p.timeline['items'])==2
        service.edit(s,p,Edit(revision=p.revision,operation='select_take',item_id=a.id,values={'asset_id':second.id}))
        assert s.get(Asset,take_a.id) is not None
        assert p.timeline['items'][0]['asset_id']==second.id


def test_lock_conflict_reload_undo_redo_split(project_id):
    service=TimelineService()
    with transaction() as s:
        p=s.get(Project,project_id)
        item=Item(track='video',duration=240)
        service.save(s,p,{'items':[item.model_dump()]})
        service.edit(s,p,Edit(revision=p.revision,operation='update',item_id=item.id,values={'locked':True}))
        assert not service.fill(s,p,item.id,fake_asset(s,p.id))
        with pytest.raises(ValueError,match='Unlock'):
            service.edit(s,p,Edit(revision=p.revision,operation='move',item_id=item.id,values={'start':1}))
        with pytest.raises(Conflict):
            service.edit(s,p,Edit(revision=0,operation='delete',item_id=item.id))
        service.edit(s,p,Edit(revision=p.revision,operation='update',item_id=item.id,values={'locked':False}))
        service.edit(s,p,Edit(revision=p.revision,operation='split',item_id=item.id,values={'at':120}))
        saved_revision=p.revision
    with transaction() as s:
        p=s.get(Project,project_id)
        assert len(p.timeline['items'])==2
        assert p.timeline['items'][1]['source_in']==120
        service.edit(s,p,Edit(revision=p.revision,operation='undo'))
        assert len(p.timeline['items'])==1 and p.timeline['items'][0]['duration']==240
        service.edit(s,p,Edit(revision=p.revision,operation='redo'))
        assert len(p.timeline['items'])==2
        assert s.get(Revision,f'{p.id}:{saved_revision}').document['items'][0]['duration']==120


def test_cross_project_asset_and_wrong_track_rejected(project_id):
    with transaction() as s:
        p=s.get(Project,project_id)
        a=fake_asset(s,p.id)
        with pytest.raises(ValueError,match='audio'):
            TimelineService().edit(s,p,Edit(revision=p.revision,operation='add',values={'track':'music','asset_id':a.id}))


def test_undo_move_preserves_later_automatic_take(project_id):
    with transaction() as s:
        p=s.get(Project,project_id);service=TimelineService();item=Item(track='video',duration=48)
        service.save(s,p,{'items':[item.model_dump()]})
        service.edit(s,p,Edit(revision=p.revision,operation='move',item_id=item.id,values={'start':48}))
        asset=fake_asset(s,p.id)
        service.fill(s,p,item.id,asset)
        service.edit(s,p,Edit(revision=p.revision,operation='undo'))
        assert p.timeline['items'][0]['start']==0
        assert p.timeline['items'][0]['asset_id']==asset.id
        service.edit(s,p,Edit(revision=p.revision,operation='redo'))
        assert p.timeline['items'][0]['start']==48 and p.timeline['items'][0]['asset_id']==asset.id
