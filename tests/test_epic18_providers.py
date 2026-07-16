import pytest

from tcm_expert.ai.adapters import (
    ChatTranslator,
    HttpKnowledgeProvider,
    OpenAICompatibleTCMChat,
)
from tcm_expert.database import DatabaseManager, SettingsRepository, ValidationError


def fake_chat(_url, payload, _headers, _timeout):
    assert payload["model"] == "tcmchat"
    return {"choices": [{"message": {"content": "Nội dung tham khảo"}}]}


def test_connected_adapters_parse_bounded_results():
    chat = OpenAICompatibleTCMChat("http://localhost:8000", "tcmchat", transport=fake_chat)
    assert chat.suggest("测试")["summary"] == "Nội dung tham khảo"
    assert ChatTranslator(chat).zh_to_vi("测试") == "Nội dung tham khảo"

    def knowledge(_url, _payload, _headers, _timeout):
        return {"results": [{"source": str(index)} for index in range(8)]}

    rows = HttpKnowledgeProvider("TCMBank", "https://example.test", transport=knowledge).retrieve("x")
    assert len(rows) == 3


def test_ai_configuration_rejects_insecure_remote_url(tmp_path):
    database = DatabaseManager(tmp_path / "epic18.db")
    database.initialize()
    settings = SettingsRepository(database)
    with pytest.raises(ValidationError):
        settings.save_ai_config({"mode": "connected", "chat_base_url": "http://example.test"})
    saved = settings.save_ai_config(
        {
            "mode": "connected",
            "chat_base_url": "http://localhost:8000",
            "chat_model": "tcmchat",
            "timeout_seconds": 25,
        }
    )
    assert saved["mode"] == "connected"
    assert saved["timeout_seconds"] == 25
