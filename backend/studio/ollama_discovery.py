"""Bounded host discovery: list models only, never download or generate."""
import os
from pathlib import Path
from urllib.parse import urlparse
import httpx
from .configuration import setting
from .db import AppSetting, engine, transaction
from .local_llm import LocalOllama


def candidates():
    values = [setting('OLLAMA_URL', ''), os.getenv('OLLAMA_HOST', '')]
    if os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
                values.append(winreg.QueryValueEx(key, 'OLLAMA_HOST')[0])
        except OSError:
            pass
    values += ['http://127.0.0.1:11434', 'http://[::1]:11434']
    if Path('/.dockerenv').exists():
        values.append('http://host.docker.internal:11434')
    result = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip().rstrip('/')
        if '://' not in value:
            value = 'http://' + value
        try:
            parsed = urlparse(value)
            port = parsed.port
            if parsed.hostname in ('0.0.0.0', '::'):
                value = f'http://127.0.0.1:{port or 11434}'
        except ValueError:
            continue
        if value not in result:
            result.append(value)
    return result


def local_models(url, timeout=2):
    parsed = urlparse(url)
    if parsed.query or parsed.fragment:
        raise ValueError('Invalid local Ollama URL')
    client = LocalOllama(url=url, model='local-model-discovery')
    try:
        response = httpx.get(client.url + '/api/tags', timeout=timeout,
                            follow_redirects=False, trust_env=False)
        response.raise_for_status()
        rows = response.json()['models']
        if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get('name'), str) for row in rows):
            raise ValueError('Invalid Ollama model list')
        return sorted({row['name'] for row in rows if 'cloud' not in row['name'].lower()
                       and not row.get('remote_host') and not row.get('remote_model')})
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise ValueError('Cannot list local models. Check that Ollama is running and its URL is reachable.') from exc



def save_if_empty(url):
    # Atomic conditional upsert: discovery never replaces a concurrent manual save.
    if engine.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    with transaction() as session:
        statement = insert(AppSetting).values(key='OLLAMA_URL', value=url)
        session.execute(statement.on_conflict_do_update(index_elements=['key'],
            set_={'value': url}, where=AppSetting.value == ''))
    return setting('OLLAMA_URL') == url


def discover():
    configured = setting('OLLAMA_URL', '')
    for url in candidates():
        try:
            models = local_models(url)
        except (httpx.HTTPError, ValueError, KeyError, TypeError, OSError):
            continue
        saved = save_if_empty(url) if not configured else configured.rstrip('/') == url
        return {'status': 'found', 'url': url, 'models': models, 'saved': saved,
                'configured_url': setting('OLLAMA_URL', '')}
    return {'status': 'unavailable', 'url': '', 'models': [], 'saved': False,
            'configured_url': configured}
