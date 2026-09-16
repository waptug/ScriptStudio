"""Validated, atomic local asset ingestion. Provider URLs are never permanent assets."""
import fnmatch
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
from urllib.parse import urlparse
import httpx
from .db import Asset
from .schemas import uid


def run(args, timeout=600):
    result = subprocess.run(args, capture_output=True, timeout=timeout)
    if result.returncode:
        raise ValueError(f'{Path(args[0]).name} failed: {result.stderr.decode(errors="replace")[-3000:]}')
    return result.stdout


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], 30))


class LocalStorage:
    """Only server-generated relative paths enter the storage namespace."""
    def __init__(self, root=None):
        self.root = Path(root or os.getenv('MEDIA_ROOT', '/tmp/scriptstudio-media')).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / 'tmp').mkdir(exist_ok=True)
    def path(self, relative):
        result = (self.root / relative).resolve()
        if not result.is_relative_to(self.root):
            raise ValueError('Invalid storage path')
        return result
    def temporary(self, suffix='.bin'):
        return self.path(f'tmp/{uid()}{suffix}')
    def download(self, url, destination):
        """HTTPS allowlist, public-address checks, no redirects; bounded streamed writes."""
        parsed = urlparse(url)
        allowed = os.getenv('DOWNLOAD_HOSTS', '*.runwayml.com,*.cloudfront.net').split(',')
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError('Only HTTPS media URLs on port 443 are allowed')
        if not parsed.hostname or not any(fnmatch.fnmatch(parsed.hostname, p.strip()) for p in allowed if p.strip()):
            raise ValueError('Media host is not in DOWNLOAD_HOSTS; authorize the provider CDN before retrying download')
        for entry in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
            if not ipaddress.ip_address(entry[4][0]).is_global:
                raise ValueError('Private network media targets are prohibited')
        total = 0
        with httpx.stream('GET', url, timeout=120, follow_redirects=False) as response:
            response.raise_for_status()
            with open(destination, 'wb') as output:
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > 512 * 1024 * 1024:
                        raise ValueError('Media exceeds 512 MiB')
                    output.write(chunk)


class AssetRepository:
    def __init__(self, storage=None):
        self.storage = storage or LocalStorage()
    def ingest(self, session, project_id, source, name, provenance, asset_id=None):
        info = probe(source)
        streams = info.get('streams', [])
        videos = [s for s in streams if s['codec_type'] == 'video']
        audios = [s for s in streams if s['codec_type'] == 'audio']
        if not videos and not audios:
            raise ValueError('File has no readable audio or video')
        fmt = info.get('format', {})
        duration = float(fmt.get('duration', 0))
        kind = 'video' if videos else 'audio'
        if videos and videos[0].get('codec_name') in ('png', 'mjpeg', 'webp') and (duration == 0 or fmt.get('format_name','').startswith(('image2','png_pipe','jpeg_pipe'))):
            kind = 'image'
        if kind != 'image' and not 0 < duration <= 7200:
            raise ValueError('Media duration must be between zero and two hours')
        if videos and (videos[0].get('width', 0) > 8192 or videos[0].get('height', 0) > 8192):
            raise ValueError('Media dimensions exceed 8192 pixels')
        # Decode the whole media before publishing it, catching truncated files.
        run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(source), '-f', 'null', '-'], 300)
        asset_id = asset_id or uid()
        existing = session.get(Asset, asset_id)
        if existing:
            return existing
        suffix = '.png' if kind == 'image' and videos[0]['codec_name'] == 'png' else Path(source).suffix
        if suffix not in ('.mp4','.mov','.webm','.wav','.mp3','.m4a','.ogg','.flac','.png','.jpg','.jpeg','.bin'):
            suffix = '.bin'
        relative = f'{project_id}/{asset_id}/original{suffix}'
        destination = self.storage.path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with open(source, 'rb') as original:
            digest = hashlib.file_digest(original, 'sha256').hexdigest()
        stage = destination.with_suffix('.partial')
        shutil.copyfile(source, stage)
        os.replace(stage, destination)
        thumbnail = proxy = None
        if videos:
            thumbnail = f'{project_id}/{asset_id}/thumbnail.jpg'
            run(['ffmpeg','-v','error','-y','-i',str(destination),'-frames:v','1','-vf','scale=240:-2',str(self.storage.path(thumbnail))])
            if kind == 'video':
                proxy = f'{project_id}/{asset_id}/proxy.mp4'
                run(['ffmpeg','-v','error','-y','-i',str(destination),'-vf','scale=480:-2','-an','-c:v','libx264','-preset','ultrafast','-crf','28','-movflags','+faststart',str(self.storage.path(proxy))])
        asset = Asset(id=asset_id, project_id=project_id, kind=kind, name=name[:200], path=relative,
                      checksum=digest, duration=duration, info=info, provenance=provenance,
                      thumbnail=thumbnail, proxy=proxy)
        session.add(asset)
        session.flush()
        return asset
