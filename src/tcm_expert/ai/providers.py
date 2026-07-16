from __future__ import annotations

from typing import Any, Protocol


class Translator(Protocol):
    name: str

    def vi_to_zh(self, text: str) -> str: ...
    def zh_to_vi(self, text: str) -> str: ...


class TCMReasoner(Protocol):
    name: str

    def suggest(self, chinese_context: str) -> dict[str, Any]: ...


class KnowledgeProvider(Protocol):
    name: str

    def retrieve(self, query: str) -> list[dict[str, Any]]: ...


class ProviderUnavailable(RuntimeError):
    pass


class DisabledProvider:
    """Safe placeholder for unconfigured external modules."""

    def __init__(self, name: str):
        self.name = name

    def vi_to_zh(self, text: str) -> str:
        raise ProviderUnavailable(f"{self.name} chưa được cấu hình")

    def zh_to_vi(self, text: str) -> str:
        raise ProviderUnavailable(f"{self.name} chưa được cấu hình")

    def suggest(self, chinese_context: str) -> dict[str, Any]:
        raise ProviderUnavailable(f"{self.name} chưa được cấu hình")

    def retrieve(self, query: str) -> list[dict[str, Any]]:
        raise ProviderUnavailable(f"{self.name} chưa được cấu hình")
