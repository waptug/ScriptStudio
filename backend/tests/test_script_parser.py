import pytest
from fastapi.testclient import TestClient
from studio.api import app
from studio.planner import LocalScriptPlanner, OllamaScriptPlanner, VisualPlan
from studio.schemas import Settings
from studio.script_parser import parse_script, require_spoken_script
from studio.script_writer import ScriptDraft, ScriptWriter, ScriptBrief

PARK = '[An adult man and woman on a summer park bench. [Wide shot]\n\nLeaves rustle.] Isn’t it just lovely out here today? Absolutely. This cool breeze is really refreshing.'


def test_park_estimate_matches_spoken_words_and_draft(monkeypatch):
    parsed = parse_script(PARK)
    assert parsed.analysis() == dict(word_count=14, estimated_seconds=6, unclosed_direction=False)
    assert parsed.spoken_text == 'Isn’t it just lovely out here today? Absolutely. This cool breeze is really refreshing.'
    class Writer:
        model = 'test'
        def __init__(self, **kwargs): pass
        def generate(self, *args, **kwargs): return ScriptDraft(script=PARK)
    monkeypatch.setattr('studio.script_writer.LocalOllama', Writer)
    assert ScriptWriter().generate(ScriptBrief(prompt='A summer park'), 'Natural')['estimated_seconds'] == 6
    assert TestClient(app).post('/api/script-analysis', json={'script': PARK}).json() == parsed.analysis()


def test_notes_paragraphs_escapes_and_exact_spoken_punctuation():
    script = '[Opening\n\n[wide] camera]\r\n\r\n“I’m here,” she said. [Pan] Stay!\r\n\r\n[Next shot]\r\n\r\nRead \\[this\\] aloud.\n\n[Fade out]'
    parsed = require_spoken_script(script)
    assert [s.narration for s in parsed.scenes] == ['“I’m here,” she said. Stay!', 'Read [this] aloud.']
    assert parsed.scenes[0].directions == ('Opening [wide] camera', 'Pan')
    assert parsed.scenes[1].directions == ('Next shot', 'Fade out')
    board = LocalScriptPlanner().plan(script, Settings())
    assert [s.narration for s in board.scenes] == [s.narration for s in parsed.scenes]
    assert [s.position for s in board.scenes] == [0, 1]
    assert board.scenes[1].shots[0].visual == 'Next shot; Fade out'


@pytest.mark.parametrize('script', ['', ' \r\n ', '[Only directions]', '[nested [notes]]'])
def test_no_speech_is_zero_and_cannot_plan(script):
    assert parse_script(script).analysis()['word_count'] == 0
    with pytest.raises(ValueError, match='spoken narration'):
        LocalScriptPlanner().plan(script, Settings())


def test_unfinished_note_is_excluded_but_requires_review():
    script = 'Hello there. [Camera pans\n\nacross the whole park'
    assert parse_script(script).analysis() == dict(word_count=2, estimated_seconds=1, unclosed_direction=True)
    with pytest.raises(ValueError, match='unfinished'):
        ScriptDraft(script=script)
    with pytest.raises(ValueError, match='unfinished'):
        LocalScriptPlanner().plan(script, Settings())


def mock_plan(monkeypatch, indices):
    def generate(self, schema, instruction, data, **kwargs):
        assert issubclass(schema, VisualPlan)
        assert data['beats'][0]['text'] == '“Isn’t it lovely?”'
        assert 'narration' not in schema.model_json_schema()['$defs']['VisualShot']['properties']
        return schema.model_validate({'shots': [
            {'beat_indices': ids, 'visual': 'A sunny bench', 'prompt': 'A wide shot', 'camera': 'Fixed'}
            for ids in indices]})
    monkeypatch.setattr('studio.local_llm.LocalOllama.__init__', lambda self: None)
    monkeypatch.setattr('studio.local_llm.LocalOllama.generate', generate)


def test_ai_preserves_quotes_and_contractions(monkeypatch):
    script = '[Park] “Isn’t it lovely?”'
    mock_plan(monkeypatch, [[0]])
    board = OllamaScriptPlanner().plan(script, Settings())
    assert board.scenes[0].narration == '“Isn’t it lovely?”'
    assert board.scenes[0].shots[0].narration == '“Isn’t it lovely?”'
    assert board.scenes[0].shots[0].scene_id == board.scenes[0].id
    assert board.scenes[0].shots[0].visual == 'A sunny bench'


@pytest.mark.parametrize('indices', [[[1]], [[0,0]], [[0,1]], [[-1]]])
def test_ai_bad_references_rejected(monkeypatch, indices):
    mock_plan(monkeypatch, indices)
    with pytest.raises(ValueError, match='omitted|reordered'):
        OllamaScriptPlanner().plan('[Park] “Isn’t it lovely?”', Settings())


def test_ai_merged_beats_preserve_all_scenes(monkeypatch):
    def generate(self, schema, instruction, data, **kwargs):
        return schema.model_validate({'shots': [{'beat_indices': list(range(len(data['beats']))),
            'visual': 'A continuous shot', 'prompt': 'Summer park', 'camera': 'Fixed'}]})
    monkeypatch.setattr('studio.local_llm.LocalOllama.__init__', lambda self: None)
    monkeypatch.setattr('studio.local_llm.LocalOllama.generate', generate)
    script = '[Park] Isn’t it lovely? Yes! Let’s stay.\n\n[Sky] No rain today.'
    board = OllamaScriptPlanner().plan(script, Settings(reference_assets=['reference-1']))
    for scene, parsed in zip(board.scenes, parse_script(script).scenes):
        assert len(scene.shots) == 1
        assert scene.shots[0].narration == scene.narration == parsed.narration
        assert scene.shots[0].references == ['reference-1']
        assert scene.shots[0].position == 0


@pytest.mark.parametrize('bad_indices', [[1, 0], [0], [0, 0], [0, 1, 2]])
def test_ai_rejection_preserves_saved_project(monkeypatch, project_id, bad_indices):
    client = TestClient(app)
    before = client.get(f'/api/projects/{project_id}').json()
    before = client.put(f'/api/projects/{project_id}', json={'name': before['name'],
        'settings': before['settings'], 'script': '[Park] Hello there. Nice weather!'}).json()
    def generate(self, schema, *args, **kwargs):
        return schema.model_validate({'shots': [
            {'beat_indices': bad_indices, 'visual': 'Park', 'prompt': 'Summer', 'camera': 'Fixed'}]})
    monkeypatch.setattr('studio.local_llm.LocalOllama.__init__', lambda self: None)
    monkeypatch.setattr('studio.local_llm.LocalOllama.generate', generate)
    response = client.post(f'/api/projects/{project_id}/plan?planner=ollama')
    assert response.status_code == 400
    assert client.get(f'/api/projects/{project_id}').json() == before


@pytest.mark.parametrize('error,expected_calls', [
    ('failed to load model vocabulary required for format', 2),
    ('model could not be loaded', 1),
])
def test_only_explicit_format_failure_retries_with_validated_json(monkeypatch, error, expected_calls):
    import httpx
    import json
    monkeypatch.setenv('OLLAMA_URL', 'http://127.0.0.1:11434')
    monkeypatch.setenv('OLLAMA_MODEL', 'test-model')
    calls = []
    def post(url, **kwargs):
        body = kwargs['json']
        calls.append(json.loads(json.dumps(body)))
        if len(calls) == 1:
            return httpx.Response(500, json={'error': error}, request=httpx.Request('POST', url))
        assert 'format' not in body
        assert 'beat_indices' in body['messages'][0]['content']
        return httpx.Response(200, json={'done': True, 'message': {'content': json.dumps({
            'shots': [{'beat_indices': [0], 'visual': 'Park',
                'prompt': 'Summer park', 'camera': 'Fixed'}]})}}, request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx, 'post', post)
    if expected_calls == 1:
        with pytest.raises(ValueError, match='Local AI generation failed'):
            OllamaScriptPlanner().plan('Hello there.', Settings())
    else:
        board = OllamaScriptPlanner().plan('Hello there.', Settings())
        assert board.scenes[0].shots[0].narration == 'Hello there.'
    assert len(calls) == expected_calls
    assert 'format' in calls[0]


@pytest.mark.parametrize('repair_succeeds', [True, False])
def test_prose_mode_repairs_coverage_once_and_never_loses_speech(monkeypatch, repair_succeeds):
    import httpx
    import json
    monkeypatch.setenv('OLLAMA_URL', 'http://127.0.0.1:11434')
    monkeypatch.setenv('OLLAMA_MODEL', 'test-model')
    calls = []
    def post(url, **kwargs):
        calls.append(json.loads(json.dumps(kwargs['json'])))
        if len(calls) == 1:
            return httpx.Response(500, json={'error': 'failed to load model vocabulary required for format'}, request=httpx.Request('POST', url))
        indices = [0, 1] if repair_succeeds and len(calls) == 3 else [0]
        if len(calls) == 3:
            assert 'every beat index exactly once' in calls[-1]['messages'][-1]['content']
        content = json.dumps({'shots': [{'beat_indices': indices, 'visual': 'Park', 'prompt': 'Summer', 'camera': 'Fixed'}]})
        return httpx.Response(200, json={'done': True, 'message': {'content': '```json\n'+content+'\n```'}}, request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx, 'post', post)
    if repair_succeeds:
        board = OllamaScriptPlanner().plan('Hello there. Nice weather!', Settings())
        assert board.scenes[0].shots[0].narration == 'Hello there. Nice weather!'
    else:
        with pytest.raises(ValueError, match='invalid draft'):
            OllamaScriptPlanner().plan('Hello there. Nice weather!', Settings())
    assert len(calls) == 3


@pytest.mark.parametrize('indices', [[True], [0.5]])
def test_reference_indices_must_be_integers(indices):
    with pytest.raises(ValueError):
        VisualPlan.model_validate({'shots': [{'beat_indices': indices, 'visual': 'Park', 'prompt': 'Summer', 'camera': 'Fixed'}]})
