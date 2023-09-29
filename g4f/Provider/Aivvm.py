from __future__ import annotations
import requests

from .base_provider import BaseProvider
from ..typing import CreateResult

# to recreate this easily, send a post request to https://chat.aivvm.com/api/models
models = {
    'gpt-3.5-turbo': {'id': 'gpt-3.5-turbo', 'name': 'GPT-3.5'},
    'gpt-3.5-turbo-0613': {'id': 'gpt-3.5-turbo-0613', 'name': 'GPT-3.5-0613'},
    'gpt-3.5-turbo-16k': {'id': 'gpt-3.5-turbo-16k', 'name': 'GPT-3.5-16K'},
    'gpt-3.5-turbo-16k-0613': {'id': 'gpt-3.5-turbo-16k-0613', 'name': 'GPT-3.5-16K-0613'},
    'gpt-4': {'id': 'gpt-4', 'name': 'GPT-4'},
    'gpt-4-0613': {'id': 'gpt-4-0613', 'name': 'GPT-4-0613'},
    'gpt-4-32k': {'id': 'gpt-4-32k', 'name': 'GPT-4-32K'},
    'gpt-4-32k-0613': {'id': 'gpt-4-32k-0613', 'name': 'GPT-4-32K-0613'},
}

class Aivvm(BaseProvider):
    url                   = 'https://chat.aivvm.com'
    supports_stream       = True
    working               = True
    supports_gpt_35_turbo = True
    supports_gpt_4        = True

    @classmethod
    def create_completion(cls,
        model: str,
        messages: list[dict[str, str]],
        stream: bool,
        **kwargs
    ) -> CreateResult:
        if not model:
            model = "gpt-3.5-turbo"
        elif model not in models:
            raise ValueError(f"Model is not supported: {model}")

        headers = {
            "accept"            : "*/*",
            "accept-language"   : "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type"      : "application/json",
            "sec-ch-ua"         : "\"Kuki\";v=\"116\", \"Not)A;Brand\";v=\"24\", \"Pici Pocoro\";v=\"102\"",
            "sec-ch-ua-mobile"  : "?0",
            "sec-ch-ua-platform": "\"Bandóz\"",
            "sec-fetch-dest"    : "empty",
            "sec-fetch-mode"    : "cors",
            "sec-fetch-site"    : "same-origin",
            "Referer"           : "https://chat.aivvm.com/",
            "Referrer-Policy"   : "same-origin",
        }

        json_data = {
            "model"       : models[model],
            "messages"    : messages,
            "key"         : "",
            "prompt"      : kwargs.get("system_message", "You are ChatGPT, a large language model trained by OpenAI. Follow the user's instructions carefully. Respond using markdown."),
            "temperature" : kwargs.get("temperature", 0.7)
        }

        response = requests.post(
            "https://chat.aivvm.com/api/chat", headers=headers, json=json_data, stream=True)
        response.raise_for_status()

        for chunk in response.iter_content(chunk_size=None):
            yield chunk.decode('utf-8')

    @classmethod
    @property
    def params(cls):
        params = [
            ('model', 'str'),
            ('messages', 'list[dict[str, str]]'),
            ('stream', 'bool'),
            ('temperature', 'float'),
        ]
        param = ', '.join([': '.join(p) for p in params])
        return f'g4f.provider.{cls.__name__} supports: ({param})'