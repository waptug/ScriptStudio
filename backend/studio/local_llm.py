"""Validated connection to the operator's local Ollama server; no cloud fallback."""
import ipaddress
import json
import os
import socket
from urllib.parse import urlparse
import httpx
from .configuration import setting


class LocalOllama:
    def __init__(self, workflow='planner', url=None, model=None):
        self.url = (url if url is not None else setting('OLLAMA_URL', '')).rstrip('/')
        self.model = model or ((setting('SCRIPT_WRITER_MODEL') if workflow == 'writer' else '') or setting('OLLAMA_MODEL', ''))
        if not self.url or not self.model:
            raise ValueError('Configure OLLAMA_URL and an installed local OLLAMA_MODEL first')
        parsed = urlparse(self.url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Invalid local Ollama server URL')
        if 'cloud' in self.model.lower():
            raise ValueError('Use a local Ollama model; paid cloud generation is not enabled')
        try:
            addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 11434, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise ValueError('Cannot resolve the configured local Ollama server') from exc
        if not addresses or any(ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError('This adapter supports local/private Ollama servers only')

    def generate(self, schema, instruction, data, temperature=0, structured=True):
        body = {'model': self.model, 'stream': False,
                'format': schema.model_json_schema(),
                'options': {'temperature': temperature, 'num_predict': 4096},
                'messages': [
                    {'role': 'system', 'content': instruction},
                    {'role': 'user', 'content': json.dumps(data)},
                ]}
        if not structured:
            # Script prose needs no grammar-constrained JSON. Some installed
            # Ollama models cannot load the vocabulary used by structured output.
            body.pop('format')
        try:
            from .local_inference import gpu_reservation
            with gpu_reservation():
                response = httpx.post(self.url + '/api/chat', json=body, timeout=180)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ValueError('Local AI generation failed or timed out. Check that Ollama is reachable and the configured model is installed; your script was not changed.') from exc
        try:
            result = response.json()
            if result.get('done') is False or result.get('done_reason') == 'length':
                raise ValueError('Incomplete model output')
            content = result['message']['content']
            return schema.model_validate_json(content) if structured else schema.model_validate({'script': content})
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError('The local model returned an incomplete or invalid draft. Try again or revise the prompt; your script was not changed.') from exc
