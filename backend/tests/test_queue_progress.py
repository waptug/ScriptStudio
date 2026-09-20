from pathlib import Path
from types import SimpleNamespace
import pytest
from studio.queue_progress import record, apply_changes, loading_detail


def job(provider='wan', state='queued'):
    return SimpleNamespace(provider=provider,state=state,result={},progress=0)


def test_phases_persist_through_provider_result_replacement_without_rewinding():
    j=job()
    record(j)
    apply_changes(j,{'state':'loading'},contact=True)
    apply_changes(j,{'state':'generating','result':{'steps':{'current':8,'total':30}}},fraction=8/30)
    p=j.result['queue_progress']
    assert p['completed']==['queued','prepare']
    assert p['phase']=='generate'
    apply_changes(j,{'result':{'local_path':'private.wav'}},phase='transfer',detail='Saving audio')
    apply_changes(j,{'state':'validating'})
    apply_changes(j,{'state':'submitted','result':{'provider_id':'saved-id'}})
    assert j.result['queue_progress']['phase']=='validate'
    assert j.result['provider_id']=='saved-id'
    apply_changes(j,{'state':'ready'})
    assert j.result['queue_progress']['completed']==list(j.result['queue_progress']['phases'])


def test_contact_is_not_activity_and_unknown_progress_stays_indeterminate(monkeypatch):
    from studio import queue_progress
    clock=[100.0]
    monkeypatch.setattr(queue_progress.time,'time',lambda:clock[0])
    j=job(state='loading');record(j,detail='Checkpoint shards 1 / 5',contact=True)
    clock[0]=120;record(j,detail='Checkpoint shards 1 / 5',contact=True)
    p=j.result['queue_progress']
    assert p['last_activity_at']==100
    assert p['last_contact_at']==120
    assert p['fraction'] is None
    clock[0]=125;record(j,detail='Checkpoint shards 2 / 5',contact=True)
    assert j.result['queue_progress']['last_activity_at']==125


def test_retry_resets_only_when_work_restarts_and_failure_retains_history():
    j=job(state='generating');record(j,fraction=.5)
    apply_changes(j,{'state':'failed','result':{'retry_state':'submitted'}})
    assert j.result['queue_progress']['phase']=='generate'
    apply_changes(j,{'state':'submitted'})
    assert j.result['queue_progress']['phase']=='generate'
    j.state='queued';record(j,reset=True)
    assert j.result['queue_progress']['completed']==[]
    assert j.result['queue_progress']['phase']=='queued'
    assert j.result['queue_progress']['fraction'] is None


def test_mock_skips_unobservable_loading_and_transfer():
    j=job(provider='mock',state='submitting');record(j)
    assert j.result['queue_progress']['phases']==['queued','generate','validate','ready']
    assert j.result['queue_progress']['phase']=='generate'


@pytest.mark.parametrize('log,expected',[
    ('Loading checkpoint shards: 40%|xx| 2/5 [01:02]', 'Checkpoint shards 2 / 5'),
    ('Loading checkpoint shards: 100%|xx| 5/5 [10:02]\rLoading pipeline components...: 80%|xx| 4/5 [11:01]\rLoading checkpoint shards: 50%|xx| 1/2 [03:59]', 'Checkpoint shards 1 / 2'),
    ('Loading pipeline components...: 100%|xx| 5/5 [16:13]', 'Pipeline components 5 / 5'),
    ('Loading checkpoint shards: 40%|xx| 2/', None),
    ('Loading checkpoint shards: 40%|xx| 8/5 [01:02]', None),
    ('secret URL https://private.invalid/token=secret', None),
])
def test_loading_details_are_bounded_sanitized_and_handle_counter_resets(tmp_path,log,expected):
    p=tmp_path/'inference.log';p.write_text('old secret\n'*6000+log)
    assert loading_detail(p)==expected


def test_stopped_job_updates_do_not_invent_an_unobserved_phase():
    j=job(state='failed');record(j)
    assert 'queue_progress' not in j.result


def test_waiting_for_gpu_returns_to_gray_queue_without_claiming_model_loaded():
    j=job(state='submitting');record(j)
    apply_changes(j,{'state':'waiting_for_gpu'})
    assert j.result['queue_progress']['phase']=='queued'
    assert j.result['queue_progress']['completed']==[]


def test_download_retry_keeps_completed_generation_and_provider_result():
    j=job(provider='runway',state='downloading');record(j,fraction=.4)
    apply_changes(j,{'state':'failed','result':{'retry_state':'downloading','url':'private-url'}})
    apply_changes(j,{'state':'downloading'})
    assert j.result['queue_progress']['phase']=='transfer'
    assert j.result['queue_progress']['fraction']==.4
    assert j.result['url']=='private-url'
