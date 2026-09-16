"""Provider contracts and explicit live gates. No SDK performs hidden submission retries."""
from abc import ABC, abstractmethod
import base64
from dataclasses import dataclass, asdict
import hashlib
import math
import os
from .configuration import setting
from pathlib import Path
import re
import httpx
from .storage import LocalStorage, run


@dataclass(frozen=True)
class Capabilities:
    asynchronous: bool
    cancellation: bool
    durations: tuple[int, ...] = ()
    idempotency: bool = False
    alignment: bool = False


class RateLimited(Exception): pass
class SubmissionUnknown(Exception): pass


class Provider(ABC):
    capabilities = Capabilities(False, False)
    def validate(self, request):
        if self.capabilities.durations and request.get('duration') not in self.capabilities.durations:
            raise ValueError('Unsupported provider duration')
    @abstractmethod
    def submit(self, job_id, request) -> dict: ...
    def status(self, provider_id) -> dict:
        return {'status': 'SUCCEEDED'}
    def result(self, state) -> dict:
        return state
    def cancel(self, provider_id):
        raise ValueError('Provider does not support cancellation; charges may already have been incurred')
    def estimate(self, request) -> float | None:
        return None


class VideoProvider(Provider): pass
class NarrationProvider(Provider): pass
class MusicProvider(Provider): pass


def require_live(key):
    if os.getenv('LIVE_GENERATION_ENABLED', 'false').lower() != 'true':
        raise ValueError('Live generation is disabled. Explicit spending authorization is required before enabling it.')
    if not setting(key):
        raise ValueError(f'Configure {key} server-side')


def provider_request(method, url, **kwargs):
    """Network ambiguity is never automatically retried as a paid submission."""
    try:
        response = httpx.request(method, url, timeout=180, **kwargs)
    except httpx.TransportError as exc:
        raise SubmissionUnknown('Provider connection ended without a confirmed outcome') from exc
    if response.status_code == 429:
        raise RateLimited('Provider rate limit; retry with backoff')
    if response.status_code >= 500:
        raise SubmissionUnknown(f'Provider returned HTTP {response.status_code}; submission may have succeeded')
    if response.is_error:
        # Do not log provider response bodies or headers; they can contain sensitive data.
        raise ValueError(f'Provider rejected request with HTTP {response.status_code}; check model, account access, and request settings')
    return response


class MockVideoProvider(VideoProvider):
    capabilities = Capabilities(False, False, tuple(range(2, 11)), True)
    def estimate(self, request): return 0.0
    def submit(self, job_id, request):
        storage = LocalStorage()
        path = storage.path(f'tmp/{job_id}.mp4')
        color = hashlib.sha256(request['prompt'].encode()).hexdigest()[:6]
        # Animated test footage has a visible MOCK label, no claim of AI imagery.
        run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
             f"color=c=0x{color}:s=640x360:r=24:d={request['duration']}",
             '-vf', "drawgrid=w=80:h=60:t=1:c=white@0.12,drawbox=x=40:y=140:w=560:h=80:color=black@0.4:t=fill,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='MOCK FOOTAGE':fontcolor=white:fontsize=28:x=(w-tw)/2:y=(h-th)/2,drawbox=x=20:y=20:w=40:h=40:color=white@0.5:t=fill",
             '-an','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',str(path)])
        return {'provider_id': job_id, 'local_path': str(path)}


class MockNarrationProvider(NarrationProvider):
    capabilities = Capabilities(False, False, idempotency=True)
    def estimate(self, request): return 0.0
    def submit(self, job_id, request):
        storage = LocalStorage()
        text = storage.path(f'tmp/{job_id}.txt')
        text.write_text(request['text'])
        path = storage.path(f'tmp/{job_id}.wav')
        voice = request.get('voice_id', 'en-us')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}', voice):
            raise ValueError('Invalid local eSpeak voice ID')
        run(['espeak-ng', '-v', voice, '-s', '145', '-f', str(text), '-w', str(path)])
        return {'provider_id': job_id, 'local_path': str(path), 'alignment': None,
                'caption_method': 'estimated word durations proportional to character count; not forced alignment'}


class MockMusicProvider(MusicProvider):
    capabilities = Capabilities(False, False, idempotency=True)
    def estimate(self, request): return 0.0
    def submit(self, job_id, request):
        path = LocalStorage().path(f'tmp/{job_id}.wav')
        base = 196 if request.get('mood') == 'calm' else 220
        expression = '+'.join(f'0.035*sin(2*PI*{f}*t)' for f in [base,base*1.25,base*1.5])
        run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'aevalsrc={expression}:s=48000:d={request["duration"]}',
             '-af','afade=t=in:d=2,afade=t=out:st='+str(max(0,request['duration']-3))+':d=3',str(path)])
        return {'provider_id': job_id, 'local_path': str(path)}


class RunwayVideoProvider(VideoProvider):
    capabilities = Capabilities(True, True, tuple(range(2, 11)))
    base = 'https://api.dev.runwayml.com/v1'
    def headers(self):
        return {'Authorization': 'Bearer '+setting('RUNWAY_API_KEY', ''), 'X-Runway-Version': '2024-11-06'}
    def validate(self, request):
        super().validate(request)
        require_live('RUNWAY_API_KEY')
        if request['ratio'] not in ('1280:720','720:1280') and not request.get('prompt_image'):
            raise ValueError('Runway gen4.5 text-only supports landscape/portrait. Supply a reference image for square.')
        if len(request['prompt']) > 1000:
            raise ValueError('Runway prompt must be at most 1000 characters')
    def estimate(self, request):
        rate = setting('RUNWAY_USD_PER_SECOND')
        return float(rate) * request['duration'] if rate else None
    def submit(self, job_id, request):
        self.validate(request)
        body = {'model':request['model'], 'promptText':request['prompt'], 'ratio':request['ratio'], 'duration':request['duration']}
        if request.get('prompt_image'):
            body['promptImage'] = request['prompt_image']
        response = provider_request('POST', self.base+'/image_to_video', headers=self.headers(), json=body)
        try:
            return {'provider_id': response.json()['id']}
        except (ValueError, KeyError) as exc:
            raise SubmissionUnknown('Provider accepted submission but returned no readable task ID') from exc
    def status(self, provider_id):
        return provider_request('GET', self.base+'/tasks/'+provider_id, headers=self.headers()).json()
    def result(self, state):
        outputs = state.get('output') or []
        if not outputs:
            raise ValueError('Provider completed without an output URL')
        return {'url': outputs[0]}
    def cancel(self, provider_id):
        provider_request('DELETE', self.base+'/tasks/'+provider_id, headers=self.headers())


class ElevenLabsNarrationProvider(NarrationProvider):
    capabilities = Capabilities(False, False, alignment=True)
    def validate(self, request):
        require_live('ELEVENLABS_API_KEY')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', request['voice_id']):
            raise ValueError('Invalid ElevenLabs voice ID')
        if not 1 <= len(request['text']) <= 5000:
            raise ValueError('Narration segment must contain 1–5000 characters')
        if set(request.get('voice_settings', {})) - {'stability','similarity_boost','style','use_speaker_boost','speed'}:
            raise ValueError('Unsupported voice delivery setting')
    def estimate(self, request):
        rate = setting('ELEVENLABS_USD_PER_CHARACTER')
        return float(rate) * len(request['text']) if rate else None
    def submit(self, job_id, request):
        self.validate(request)
        body = {k: request[k] for k in ('text','voice_settings','previous_text','next_text') if k in request}
        body['model_id'] = request['model']
        response = provider_request('POST', f'https://api.elevenlabs.io/v1/text-to-speech/{request["voice_id"]}/with-timestamps',
                                    headers={'xi-api-key':setting('ELEVENLABS_API_KEY', '')}, json=body)
        try:
            data = response.json()
            path = LocalStorage().path(f'tmp/{job_id}.mp3')
            path.write_bytes(base64.b64decode(data['audio_base64'], validate=True))
            return {'provider_id': response.headers.get('request-id', job_id), 'local_path':str(path),
                    'alignment': data.get('normalized_alignment') or data.get('alignment'),
                    'caption_method':'provider character alignment'}
        except (ValueError, KeyError) as exc:
            raise SubmissionUnknown('Narration response could not be saved; check provider history before retrying') from exc


class SunoMusicProvider(MusicProvider):
    def validate(self, request):
        raise ValueError('Suno disabled: provide verified official API documentation and account entitlement. Import a downloaded music file instead.')
    def submit(self, job_id, request):
        self.validate(request)


def get_provider(kind, name):
    providers = {('video','mock'):MockVideoProvider, ('narration','mock'):MockNarrationProvider,
                 ('music','mock'):MockMusicProvider, ('video','runway'):RunwayVideoProvider,
                 ('narration','elevenlabs'):ElevenLabsNarrationProvider, ('music','suno'):SunoMusicProvider}
    try:
        return providers[(kind,name)]()
    except KeyError:
        raise ValueError('Unsupported provider')
