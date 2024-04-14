from __future__ import annotations

import re
import json
import base64
import uuid

from ..typing import AsyncResult, Messages, ImageType, Cookies
from .base_provider import AsyncGeneratorProvider, ProviderModelMixin
from .helper import format_prompt
from ..image import ImageResponse, to_bytes, is_accepted_format
from ..requests import StreamSession, FormData, raise_for_status
from .you.har_file import get_dfp_telemetry_id

class You(AsyncGeneratorProvider, ProviderModelMixin):
    url = "https://you.com"
    working = True
    supports_gpt_35_turbo = True
    supports_gpt_4 = True
    default_model = "gpt-3.5-turbo"
    models = [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4-turbo",
        "claude-instant",
        "claude-2",
        "claude-3-opus",
        "claude-3-sonnet",
        "gemini-pro",
        "zephyr",
        "dall-e",
    ]
    model_aliases = {
        "claude-v2": "claude-2"
    }
    _cookies = None
    _cookies_used = 0

    @classmethod
    async def create_async_generator(
        cls,
        model: str,
        messages: Messages,
        stream: bool = True,
        image: ImageType = None,
        image_name: str = None,
        proxy: str = None,
        timeout: int = 240,
        chat_mode: str = "default",
        **kwargs,
    ) -> AsyncResult:
        if image is not None:
            chat_mode = "agent"
        elif not model or model == cls.default_model:
            ...
        elif model.startswith("dall-e"):
            chat_mode = "create"
            messages = [messages[-1]]
        else:
            chat_mode = "custom"
            model = cls.get_model(model)
        async with StreamSession(
            proxies={"all": proxy},
            impersonate="chrome",
            timeout=(30, timeout)
        ) as session:
            cookies = await cls.get_cookies(session) if chat_mode != "default" else None
            
            upload = json.dumps([await cls.upload_file(session, cookies, to_bytes(image), image_name)]) if image else ""
            headers = {
                "Accept": "text/event-stream",
                "Referer": f"{cls.url}/search?fromSearchBar=true&tbm=youchat",
            }
            data = {
                "userFiles": upload,
                "q": format_prompt(messages),
                "domain": "youchat",
                "selectedChatMode": chat_mode,
            }
            params = {
                "userFiles": upload,
                "selectedChatMode": chat_mode,
            }
            if chat_mode == "custom":
                params["selectedAIModel"] = model.replace("-", "_")
            async with (session.post if chat_mode == "default" else session.get)(
                f"{cls.url}/api/streamingSearch",
                data=data,
                params=params,
                headers=headers,
                cookies=cookies
            ) as response:
                await raise_for_status(response)
                async for line in response.iter_lines():
                    if line.startswith(b'event: '):
                        event = line[7:].decode()
                    elif line.startswith(b'data: '):
                        if event in ["youChatUpdate", "youChatToken"]:
                            data = json.loads(line[6:])
                        if event == "youChatToken" and event in data:
                            yield data[event]
                        elif event == "youChatUpdate" and "t" in data and data["t"] is not None:
                            match = re.search(r"!\[fig\]\((.+?)\)", data["t"])
                            if match:
                                yield ImageResponse(match.group(1), messages[-1]["content"])
                            else:
                                yield data["t"]                         

    @classmethod
    async def upload_file(cls, client: StreamSession, cookies: Cookies, file: bytes, filename: str = None) -> dict:
        async with client.get(
            f"{cls.url}/api/get_nonce",
            cookies=cookies,
        ) as response:
            await raise_for_status(response)
            upload_nonce = await response.text()
        data = FormData()
        data.add_field('file', file, content_type=is_accepted_format(file), filename=filename)
        async with client.post(
            f"{cls.url}/api/upload",
            data=data,
            headers={
                "X-Upload-Nonce": upload_nonce,
            },
            cookies=cookies
        ) as response:
            await raise_for_status(response)
            result = await response.json()
        result["user_filename"] = filename
        result["size"] = len(file)
        return result

    @classmethod
    async def get_cookies(cls, client: StreamSession) -> Cookies:

        if not cls._cookies or cls._cookies_used >= 5:
            cls._cookies = await cls.create_cookies(client)
            cls._cookies_used = 0
        cls._cookies_used += 1
        return cls._cookies        

    @classmethod
    def get_sdk(cls) -> str:
        return base64.standard_b64encode(json.dumps({
            "event_id":f"event-id-{str(uuid.uuid4())}",
            "app_session_id":f"app-session-id-{str(uuid.uuid4())}",
            "persistent_id":f"persistent-id-{uuid.uuid4()}",
            "client_sent_at":"","timezone":"",
            "stytch_user_id":f"user-live-{uuid.uuid4()}",
            "stytch_session_id":f"session-live-{uuid.uuid4()}",
            "app":{"identifier":"you.com"},
            "sdk":{"identifier":"Stytch.js Javascript SDK","version":"3.3.0"
        }}).encode()).decode()

    def get_auth() -> str:
        auth_uuid = "507a52ad-7e69-496b-aee0-1c9863c7c819"
        auth_token = f"public-token-live-{auth_uuid}:public-token-live-{auth_uuid}"
        auth = base64.standard_b64encode(auth_token.encode()).decode()
        return f"Basic {auth}"

    @classmethod
    async def create_cookies(cls, client: StreamSession) -> Cookies:
        user_uuid = str(uuid.uuid4())
        async with client.post(
            "https://web.stytch.com/sdk/v1/passwords",
            headers={
                "Authorization": cls.get_auth(),
                "X-SDK-Client": cls.get_sdk(),
                "X-SDK-Parent-Host": cls.url,
                "Origin": "https://you.com",
                "Referer": "https://you.com/"
            },
            json={
                "dfp_telemetry_id": await get_dfp_telemetry_id(),
                "email": f"{user_uuid}@gmail.com",
                "password": f"{user_uuid}#{user_uuid}",
                "session_duration_minutes": 129600
            }
        ) as response:
            await raise_for_status(response)
            session = (await response.json())["data"]

        return {
            "stytch_session": session["session_token"],
            'stytch_session_jwt': session["session_jwt"],
            'ydc_stytch_session': session["session_token"],
            'ydc_stytch_session_jwt': session["session_jwt"],
        }
