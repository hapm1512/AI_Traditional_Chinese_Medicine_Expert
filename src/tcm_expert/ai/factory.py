from __future__ import annotations

from typing import Any

from tcm_expert.ai.adapters import ChatTranslator, HttpKnowledgeProvider, OpenAICompatibleTCMChat
from tcm_expert.ai.workflow import AIWorkflow
from tcm_expert.database.settings_repository import SettingsRepository


def create_ai_workflow(database: Any) -> AIWorkflow:
    settings = SettingsRepository(database).ai_settings()
    enabled = bool(settings.get("enabled"))
    if settings.get("mode", "offline") != "connected":
        return AIWorkflow(database, enabled=enabled)
    chat = OpenAICompatibleTCMChat(
        str(settings.get("chat_base_url", "")),
        str(settings.get("chat_model", "tcmchat")),
        float(settings.get("timeout_seconds", 20)),
    )
    knowledge = tuple(
        HttpKnowledgeProvider(name, str(settings.get(field, "")), chat.timeout)
        for name, field in (
            ("OpenTCM GraphRAG", "opentcm_url"),
            ("TCMBank", "tcmbank_url"),
            ("SymMap", "symmap_url"),
        )
    )
    return AIWorkflow(
        database,
        enabled=enabled,
        translator=ChatTranslator(chat),
        reasoner=chat,
        knowledge=knowledge,
    )
