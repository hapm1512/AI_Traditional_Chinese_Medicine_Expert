from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tcm_expert.ai.providers import ProviderUnavailable

JsonTransport = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


def _default_transport(
    url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - configured endpoint
            if response.status < 200 or response.status >= 300:
                raise ProviderUnavailable(f"Máy chủ AI trả mã {response.status}")
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProviderUnavailable(f"Không thể kết nối máy chủ AI: {error}") from error
    if not isinstance(result, dict):
        raise ProviderUnavailable("Phản hồi AI không đúng định dạng JSON")
    return result


class OpenAICompatibleTCMChat:
    """TCMChat through a local or HTTPS OpenAI-compatible endpoint."""

    name = "TCMChat"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = 20,
        transport: JsonTransport = _default_transport,
    ):
        self.url = f"{base_url.rstrip('/')}/v1/chat/completions"
        self.model = model
        self.timeout = timeout
        self.transport = transport

    def suggest(self, chinese_context: str) -> dict[str, Any]:
        prompt = (
            "你是中医临床参考助手。只总结辨证依据和待核实问题。"
            "不得诊断、开方、给药剂量或代替医生决定。\n" + chinese_context
        )
        result = self._chat(prompt)
        return {"summary": result}

    def _chat(self, prompt: str) -> str:
        token = os.getenv("TCMCHAT_API_KEY", "").strip()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        result = self.transport(
            self.url,
            {"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            headers,
            self.timeout,
        )
        try:
            text = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderUnavailable("TCMChat thiếu nội dung trả lời") from error
        text = str(text).strip()
        if not text:
            raise ProviderUnavailable("TCMChat trả lời trống")
        return text[:8000]


class ChatTranslator:
    name = "Bộ dịch Việt–Trung"

    def __init__(self, chat: OpenAICompatibleTCMChat):
        self.chat = chat

    def vi_to_zh(self, text: str) -> str:
        return self.chat._chat("Dịch chính xác sang tiếng Trung, chỉ trả bản dịch:\n" + text)

    def zh_to_vi(self, text: str) -> str:
        return self.chat._chat("Dịch chính xác sang tiếng Việt, chỉ trả bản dịch:\n" + text)


class HttpKnowledgeProvider:
    def __init__(
        self,
        name: str,
        url: str,
        timeout: float = 20,
        transport: JsonTransport = _default_transport,
    ):
        self.name = name
        self.url = url
        self.timeout = timeout
        self.transport = transport

    def retrieve(self, query: str) -> list[dict[str, Any]]:
        if not self.url:
            raise ProviderUnavailable(f"{self.name} chưa được cấu hình")
        result = self.transport(self.url, {"query": query, "limit": 3}, {}, self.timeout)
        rows = result.get("results", [])
        if not isinstance(rows, list):
            raise ProviderUnavailable(f"{self.name} trả dữ liệu không hợp lệ")
        return [row for row in rows[:3] if isinstance(row, dict)]
