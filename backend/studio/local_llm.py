"""Validated connection to the operator's local Ollama server; no cloud fallback."""
import ipaddress
import json
import os
import re
import socket
from urllib.parse import urlparse
import httpx
from pydantic import ValidationError
from .configuration import setting


def parse_model_response(response, schema, structured):
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError('Invalid model response')
    if result.get('done') is False or result.get('done_reason') == 'length':
        raise ValueError('Incomplete model output')
    content = result['message']['content']
    if structured and isinstance(content, str):
        # Accept one complete JSON fence, never extract JSON from commentary.
        fence = re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*', content, re.DOTALL | re.IGNORECASE)
        if fence:
            content = fence.group(1)
    return schema.model_validate_json(content) if structured else schema.model_validate({'script': content})


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
                # Some installed models cannot initialize Ollama's grammar
                # vocabulary. Retry only this explicit pre-generation failure,
                # still requiring exactly the same validated JSON contract.
                if structured and response.status_code == 500:
                    try:
                        format_unavailable = response.json().get('error') == 'failed to load model vocabulary required for format'
                    except (ValueError, AttributeError):
                        format_unavailable = False
                    if format_unavailable:
                        body.pop('format')
                        body['messages'][0]['content'] += '\nReturn only a JSON object matching this schema, without markdown fences:\n' + json.dumps(schema.model_json_schema())
                        response = httpx.post(self.url + '/api/chat', json=body, timeout=180)
                response.raise_for_status()
                if structured and 'format' not in body:
                    try:
                        return parse_model_response(response, schema, structured)
                    except (ValueError, KeyError, TypeError) as validation_error:
                        try:
                            result = response.json()
                        except ValueError:
                            result = {}
                        # One bounded JSON repair for prose-mode local models.
                        # Truncated output and malformed transport data still fail.
                        if not isinstance(result, dict):
                            result = {}
                        message = result.get('message')
                        content = message.get('content') if isinstance(message, dict) else None
                        if isinstance(content, str) and result.get('done') is not False and result.get('done_reason') != 'length':
                            feedback = ('; '.join(error['msg'] for error in validation_error.errors(include_input=False, include_url=False))
                                        if isinstance(validation_error, ValidationError) else str(validation_error))
                            body['messages'].extend([
                                {'role': 'assistant', 'content': content},
                                {'role': 'user', 'content': 'The previous response is invalid. Correct the following validation error and return only the complete corrected JSON object matching the required schema.\n' + feedback[:1500]},
                            ])
                            response = httpx.post(self.url + '/api/chat', json=body, timeout=180)
                            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ValueError('Local AI generation failed or timed out. Check that Ollama is reachable and the configured model is installed; your script was not changed.') from exc
        try:
            return parse_model_response(response, schema, structured)
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError('The local model returned an incomplete or invalid draft. Try again or revise the prompt; your script was not changed.') from exc
