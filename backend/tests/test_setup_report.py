import json
from studio.setup_report import evidence, model_evidence


def test_setup_evidence_is_versioned_local_and_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv('SCRIPTSTUDIO_RESOURCE_DIR',str(tmp_path/'data'))
    report=tmp_path/'setup-acceptance.json'
    assert evidence(report.name) is None
    report.write_text('{broken')
    assert evidence(report.name) is None
    report.write_text(json.dumps({'contract_version':2,'plan':{}}))
    assert evidence(report.name) is None
    report.write_text(json.dumps({'contract_version':1,'plan':'malformed'}))
    assert model_evidence('kokoro',{})['compatibility_status']=='Unknown'
    report.write_text(json.dumps({'contract_version':1,'plan':{'components':[{'id':'kokoro','status':'Blocked','reason':'CPU unsupported'}]}}))
    info=model_evidence('kokoro',{'state':'not_installed'})
    assert info['compatibility_status']=='Blocked'
    assert info['compatibility_reason']=='CPU unsupported'
    assert info['verification_status']=='not_verified'


def test_runtime_probe_does_not_claim_generation_verification(tmp_path, monkeypatch):
    monkeypatch.setenv('SCRIPTSTUDIO_RESOURCE_DIR',str(tmp_path/'data'))
    info=model_evidence('kokoro',{'state':'ready'})
    assert info['verification_status']=='runtime_verified'
    assert info['generation_verification_status']=='not_verified'
