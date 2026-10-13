import json
from pathlib import Path
import wave
import pytest
from studio import local_models, local_inference


@pytest.mark.parametrize('silent',[False,True])
def test_real_generation_evidence_requires_non_silent_audio(tmp_path,monkeypatch,silent):
    monkeypatch.setattr(local_models,'root',lambda:tmp_path)
    (tmp_path/'kokoro').mkdir()
    monkeypatch.setattr(local_inference,'environment',lambda:{})
    updates=[]
    monkeypatch.setattr(local_models,'update',lambda name,**values:updates.append(values))
    class Completed:
        returncode=0
        def poll(self): return 0
    def process(command,**kwargs):
        request=json.loads(Path(command[-1]).read_text())
        with wave.open(request['output'],'wb') as output:
            output.setnchannels(1);output.setsampwidth(2);output.setframerate(24000)
            output.writeframes((b'\0\0' if silent else b'\x01\0')*240)
        return Completed()
    monkeypatch.setattr(local_models,'state',lambda name:{})
    monkeypatch.setattr('subprocess.Popen',process)
    if silent:
        with pytest.raises(ValueError,match='silent'):local_models.LocalModelService().test_generation('kokoro')
        assert not any(u.get('generation_verification_status')=='verified' for u in updates)
    else:
        local_models.LocalModelService().test_generation('kokoro')
        assert updates[-1]['generation_verification_status']=='verified'
