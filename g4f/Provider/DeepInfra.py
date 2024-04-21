from __future__ import annotations

import requests
from ..typing import AsyncResult, Messages, ImageType
from ..image import to_data_uri
from .needs_auth.Openai import Openai

class DeepInfra(Openai):
    label = "DeepInfra"
    url = "https://deepinfra.com"
    working = True
    has_auth = True
    supports_stream = True
    supports_message_history = True
    default_model = "meta-llama/Meta-Llama-3-70b-instruct"
    default_vision_model = "llava-hf/llava-1.5-7b-hf"
    model_aliases = {
        'mixtral-8x22b': 'HuggingFaceH4/zephyr-orpo-141b-A35b-v0.1'
    }

    @classmethod
    def get_models(cls):
        if not cls.models:
            url = 'https://api.deepinfra.com/models/featured'
            models = requests.get(url).json()
            cls.models = [model['model_name'] for model in models if model["type"] == "text-generation"]
        return cls.models

    @classmethod
    def create_async_generator(
        cls,
        model: str,
        messages: Messages,
        stream: bool,
        image: ImageType = None,
        api_base: str = "https://api.deepinfra.com/v1/openai",
        temperature: float = 0.7,
        max_tokens: int = 1028,
        **kwargs
    ) -> AsyncResult:
        headers = {
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US',
            'Connection': 'keep-alive',
            'Origin': 'https://deepinfra.com',
            'Referer': 'https://deepinfra.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'X-Deepinfra-Source': 'web-embed',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }
        if image is not None:
            if not model:
                model = cls.default_vision_model
            messages[-1]["content"] = [
                {
                    "type": "image_url",
                    "image_url": {"url": to_data_uri(image)}
                },
                {
                    "type": "text",
                    "text": messages[-1]["content"]
                }
            ]
        return super().create_async_generator(
            model, messages,
            stream=stream,
            api_base=api_base,
            temperature=temperature,
            max_tokens=max_tokens,
            headers=headers,
            **kwargs
        )