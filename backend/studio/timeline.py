"""One revision-controlled timeline for UI edits and asynchronous assembly."""
from copy import deepcopy
from .db import Asset, Revision, Project
from .schemas import Timeline, Item, Edit, Settings, uid


class Conflict(ValueError):
    pass


class TimelineService:
    def save(self, session, project, document, manual=False):
        doc = Timeline.model_validate(document).model_dump()
        if manual:
            project.undo = (project.undo + [deepcopy(project.timeline)])[-100:]
            project.redo = []
        project.timeline = doc
        project.revision += 1
        session.add(Revision(id=f'{project.id}:{project.revision}', project_id=project.id,
                             number=project.revision, document=deepcopy(doc), settings=deepcopy(project.settings)))
        return doc

    def edit(self, session, project, edit: Edit):
        if edit.revision != project.revision:
            raise Conflict('Timeline changed. Refresh and reapply your edit.')
        if edit.operation in ('undo','redo'):
            stack_name, other = ('undo','redo') if edit.operation == 'undo' else ('redo','undo')
            stack = getattr(project, stack_name)
            if not stack:
                raise ValueError(f'Nothing to {edit.operation}')
            target = deepcopy(stack[-1])
            setattr(project, stack_name, stack[:-1])
            setattr(project, other, (getattr(project, other) + [deepcopy(project.timeline)])[-100:])
            return self.save(session, project, target)
        doc = deepcopy(project.timeline)
        if edit.operation == 'add':
            item = Item.model_validate(edit.values)
            self.validate_asset(session, project.id, item)
            doc['items'].append(item.model_dump())
        else:
            item = next((i for i in doc['items'] if i['id'] == edit.item_id), None)
            if item is None:
                raise ValueError('Timeline item no longer exists')
            if item['locked'] and not (edit.operation == 'update' and edit.values == {'locked': False}):
                raise ValueError('Unlock this item before editing')
            if edit.operation == 'delete':
                doc['items'].remove(item)
            elif edit.operation == 'duplicate':
                clone = deepcopy(item)
                clone.update(id=uid(), start=item['start'] + item['duration'])
                # Duplicated placeholders are not additional automatic generation targets.
                clone['shot_id'] = None
                doc['items'].append(clone)
            elif edit.operation == 'split':
                at = int(edit.values['at'])
                left = at - item['start']
                if not 0 < left < item['duration']:
                    raise ValueError('Split must lie inside the selected item')
                clone = deepcopy(item)
                clone.update(id=uid(), start=at, source_in=item['source_in'] + left, duration=item['duration'] - left, shot_id=None)
                item['duration'] = left
                doc['items'].append(clone)
            else:
                allowed = set(Item.model_fields) - {'id','shot_id','selected_take','asset_id'}
                values = dict(edit.values)
                if edit.operation == 'select_take':
                    values = {'asset_id': values['asset_id'], 'selected_take': values['asset_id']}
                    asset = session.get(Asset, values['asset_id'])
                    if not asset or asset.project_id != project.id:
                        raise ValueError('Take not found in this project')
                    if item['shot_id'] and asset.provenance.get('shot_id') != item['shot_id']:
                        raise ValueError('Take belongs to another shot')
                elif not set(values).issubset(allowed):
                    raise ValueError('Unsupported item fields')
                item.update(values)
                parsed = Item.model_validate(item)
                self.validate_asset(session, project.id, parsed)
        return self.save(session, project, doc, manual=True)

    def validate_asset(self, session, project_id, item):
        if item.asset_id:
            asset = session.get(Asset, item.asset_id)
            if not asset or asset.project_id != project_id:
                raise ValueError('Asset not found in this project')
            settings=Settings.model_validate(session.get(Project,project_id).settings)
            if asset.kind!='image' and settings.seconds(item.source_in)>=asset.duration:
                raise ValueError('Source in must be earlier than the end of the source media')
            expected = 'audio' if item.track in ('music','narration','sfx') else None
            if expected and asset.kind != expected:
                raise ValueError('This track requires an audio asset')
            if item.track in ('video','overlay') and asset.kind not in ('image','video'):
                raise ValueError('This track requires visual media')

    def fill(self, session, project, placeholder_id, asset):
        """Never insert, move, trim, unlock, or replace a user-selected take."""
        if not project.settings.get('auto_assemble', True):
            return False
        doc = deepcopy(project.timeline)
        item = next((i for i in doc['items'] if i['id'] == placeholder_id), None)
        if item is None or item['locked'] or item['asset_id'] or item['selected_take']:
            return False
        item['asset_id'] = asset.id
        item['selected_take'] = asset.id
        # Keep later undo/redo focused on manual edits, without discarding a newly
        # arrived take. Never insert into snapshots that deleted the placeholder.
        def preserve_fill(snapshot):
            snapshot=deepcopy(snapshot)
            prior=next((i for i in snapshot['items'] if i['id']==placeholder_id),None)
            if prior and not prior['locked'] and not prior['asset_id'] and not prior['selected_take']:
                prior['asset_id']=asset.id
                prior['selected_take']=asset.id
            return snapshot
        project.undo=[preserve_fill(snapshot) for snapshot in project.undo]
        project.redo=[preserve_fill(snapshot) for snapshot in project.redo]
        self.save(session, project, doc)
        return True
