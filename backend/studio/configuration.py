"""Runtime workflow configuration; credentials are write-only through the API."""
import fcntl
import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field, ConfigDict
from .db import AppSetting, Session, transaction

DEFAULTS = {
    'OLLAMA_URL': '', 'OLLAMA_MODEL': '', 'SCRIPT_WRITER_MODEL': '',
    'RUNWAY_MODEL': 'gen4.5', 'ELEVENLABS_MODEL': 'eleven_multilingual_v2',
    'RUNWAY_USD_PER_SECOND': '0.12', 'ELEVENLABS_USD_PER_CHARACTER': '',
}
SECRETS = {'RUNWAY_API_KEY', 'ELEVENLABS_API_KEY'}


def cipher(create=False):
    folder = Path(os.getenv('MEDIA_ROOT', '/tmp/scriptstudio-media')) / '.credentials'
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = folder / 'master.key'
    if create:
        # All containers share this volume. Serialize first-key creation so two
        # concurrent saves cannot encrypt with different master keys.
        with open(folder / 'key.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if not path.exists():
                with Session() as session:
                    if session.query(AppSetting).filter(AppSetting.key.in_(SECRETS), AppSetting.value != '').first():
                        raise ValueError('Credential encryption key is missing. Restore it from backup before saving keys.')
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(fd, 'wb') as output:
                    output.write(Fernet.generate_key())
    try:
        return Fernet(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise ValueError('Credential encryption key is unavailable. Restore the media-volume backup.') from exc


def setting(key, default=None):
    with Session() as session:
        row = session.get(AppSetting, key)
        if row is not None:
            if key in SECRETS and row.value:
                try:
                    return cipher().decrypt(row.value.encode()).decode()
                except InvalidToken as exc:
                    raise ValueError('Stored credential cannot be decrypted. Restore the matching encryption key.') from exc
            return row.value
    return os.getenv(key, DEFAULTS.get(key, default))


class AdminUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    values: dict[str, str] = Field(default_factory=dict)
    credentials: dict[str, str] = Field(default_factory=dict)
    clear_credentials: list[str] = Field(default_factory=list)


class ConfigurationService:
    def public(self):
        with Session() as session:
            stored = {row.key: row.value for row in session.query(AppSetting)}
        return {
            'values': {key: stored.get(key, os.getenv(key, value)) for key, value in DEFAULTS.items()},
            'credentials': {key: {'configured': bool(stored.get(key, os.getenv(key, ''))),
                                   'source': 'admin' if key in stored else 'environment'} for key in SECRETS},
            'live_enabled': os.getenv('LIVE_GENERATION_ENABLED', 'false').lower() == 'true',
        }

    def save(self, payload):
        if set(payload.values) - DEFAULTS.keys() or (set(payload.credentials) | set(payload.clear_credentials)) - SECRETS:
            raise ValueError('Unsupported configuration field')
        if set(payload.credentials) & set(payload.clear_credentials):
            raise ValueError('Do not replace and clear the same credential')
        values = {key: value.strip() for key, value in payload.values.items()}
        from urllib.parse import urlparse
        for key, value in values.items():
            if len(value) > 500 or '\n' in value or '\r' in value:
                raise ValueError('Configuration values must be short single-line strings')
            if key == 'OLLAMA_URL' and value:
                url = urlparse(value)
                if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment:
                    raise ValueError('Use an HTTP(S) Ollama URL without embedded credentials, query, or fragment')
            if key.endswith('MODEL') and 'cloud' in value.lower() and key in ('OLLAMA_MODEL', 'SCRIPT_WRITER_MODEL'):
                raise ValueError('Choose a local Ollama model; cloud models are disabled')
            if key.endswith(('PER_SECOND', 'PER_CHARACTER')) and value:
                import math
                try: valid = math.isfinite(float(value)) and float(value) > 0
                except ValueError: valid = False
                if not valid: raise ValueError('Cost estimates must be positive finite numbers')
        credentials = {}
        for key, value in payload.credentials.items():
            value = value.strip()
            if not value: continue  # Blank password input means keep existing.
            if len(value) > 4096 or any(c.isspace() for c in value):
                raise ValueError('Credential has an invalid format')
            credentials[key] = cipher(create=True).encrypt(value.encode()).decode()
        values.update(credentials)
        values.update({key: '' for key in payload.clear_credentials})
        with transaction() as session:
            for key, value in values.items():
                row = session.get(AppSetting, key)
                if row: row.value = value
                else: session.add(AppSetting(key=key, value=value))
        return self.public()
