"""Runtime workflow configuration; credentials are write-only through the API."""
import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field, ConfigDict, StrictBool
from .db import AppSetting, Session, transaction
from .platform_runtime import exclusive_file_lock

DEFAULTS = {
    'OLLAMA_URL': '', 'OLLAMA_MODEL': '', 'SCRIPT_WRITER_MODEL': '',
    'RUNWAY_MODEL': 'gen4.5', 'ELEVENLABS_MODEL': 'eleven_multilingual_v2',
    'RUNWAY_USD_PER_SECOND': '0.12', 'ELEVENLABS_USD_PER_CHARACTER': '',
}
SECRETS = {'RUNWAY_API_KEY', 'ELEVENLABS_API_KEY', 'HF_TOKEN'}
PAID_CATEGORIES = ('text', 'video', 'audio', 'speech', 'music')


def paid_permissions():
    """Read current permissions in one snapshot; only the master has an env fallback."""
    with Session() as session:
        stored = {row.key: row.value for row in session.query(AppSetting).filter(
            AppSetting.key.in_(['LIVE_GENERATION_ENABLED'] + [f'PAID_{kind.upper()}_ENABLED' for kind in PAID_CATEGORIES]))}
    return {'enabled': stored.get('LIVE_GENERATION_ENABLED', os.getenv('LIVE_GENERATION_ENABLED', 'false')).lower() == 'true',
            **{kind: stored.get(f'PAID_{kind.upper()}_ENABLED', 'false') == 'true' for kind in PAID_CATEGORIES}}


def require_paid(category):
    if category not in PAID_CATEGORIES:
        raise ValueError('Unsupported paid generation category')
    policy = paid_permissions()
    if not policy['enabled'] or not policy[category]:
        raise PaidGenerationDisabled(f'Paid {category} generation is disabled in Admin. Enable the master switch and this category before submitting new requests.')


class PaidGenerationDisabled(ValueError):
    """Known local rejection: no paid request was submitted."""


class PaidPermissionsUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: StrictBool | None = None
    text: StrictBool | None = None
    video: StrictBool | None = None
    audio: StrictBool | None = None
    speech: StrictBool | None = None
    music: StrictBool | None = None


def cipher(create=False):
    folder = Path(os.getenv('MEDIA_ROOT', '/tmp/scriptstudio-media')) / '.credentials'
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = folder / 'master.key'
    if create:
        # All containers share this volume. Serialize first-key creation so two
        # concurrent saves cannot encrypt with different master keys.
        with exclusive_file_lock(folder / 'key.lock'):
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
    paid_generation: PaidPermissionsUpdate = Field(default_factory=PaidPermissionsUpdate)


class ConfigurationService:
    def public(self):
        with Session() as session:
            stored = {row.key: row.value for row in session.query(AppSetting)}
        return {
            'values': {key: stored.get(key, os.getenv(key, value)) for key, value in DEFAULTS.items()},
            'credentials': {key: {'configured': bool(stored.get(key, os.getenv(key, ''))),
                                   'source': 'admin' if key in stored else 'environment'} for key in SECRETS},
            'live_enabled': paid_permissions()['enabled'],
            'paid_generation': paid_permissions(),
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
        for category, enabled in payload.paid_generation.model_dump(exclude_none=True).items():
            key = 'LIVE_GENERATION_ENABLED' if category == 'enabled' else f'PAID_{category.upper()}_ENABLED'
            values[key] = 'true' if enabled else 'false'
        with transaction() as session:
            for key, value in values.items():
                row = session.get(AppSetting, key)
                if row: row.value = value
                else: session.add(AppSetting(key=key, value=value))
        return self.public()
