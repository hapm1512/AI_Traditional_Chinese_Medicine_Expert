import json

from tcm_expert.database import DatabaseManager, ReferenceRepository
from tcm_expert.services.ollama_syndrome_analyzer import OllamaSyndromeAnalyzer


class FakeChat:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.prompt = ""

    def _chat(self, prompt):
        self.prompt = prompt
        if self.error:
            raise self.error
        return json.dumps(self.payload, ensure_ascii=False)


def catalogue(tmp_path):
    database = DatabaseManager(tmp_path / "epic36.db")
    database.initialize()
    return ReferenceRepository(database).list("tcm_syndromes")


def test_qwen_returns_only_catalogue_syndromes_with_grounded_evidence(tmp_path):
    chat = FakeChat(
        {
            "suggestions": [
                {
                    "code": "TYKHIHU",
                    "confidence": 0.88,
                    "evidence": ["mệt", "ăn ít", "dấu hiệu không có"],
                },
                {"code": "MA_KHONG_TON_TAI", "confidence": 1, "evidence": ["mệt"]},
            ]
        }
    )
    outcome = OllamaSyndromeAnalyzer(chat=chat).analyze(
        "Người bệnh mệt, ăn ít và đại tiện lỏng.", catalogue(tmp_path)
    )

    assert outcome.source == "ollama"
    assert [item["code"] for item in outcome.results] == ["TYKHIHU"]
    assert outcome.results[0]["matched"] == ["mệt", "ăn ít"]
    assert outcome.results[0]["review_required"] is True
    assert "không kê đơn" in chat.prompt


def test_hallucinated_evidence_is_rejected_and_rules_are_used(tmp_path):
    chat = FakeChat(
        {"suggestions": [{"code": "CANUAT", "confidence": 0.9, "evidence": ["đau đầu"]}]}
    )
    outcome = OllamaSyndromeAnalyzer(chat=chat).analyze(
        "Mệt, ăn ít, đại tiện lỏng, lưỡi nhạt.", catalogue(tmp_path)
    )

    assert outcome.source == "rules"
    assert outcome.results[0]["code"] == "TYKHIHU"
    assert outcome.fallback_reason


def test_connection_failure_uses_transparent_rule_fallback(tmp_path):
    chat = FakeChat(error=RuntimeError("Ollama chưa chạy"))
    outcome = OllamaSyndromeAnalyzer(chat=chat).analyze(
        "Đau lưng, ù tai, miệng khô.", catalogue(tmp_path)
    )

    assert outcome.source == "rules"
    assert outcome.results[0]["code"] == "THANAMHU"
    assert "Ollama chưa chạy" in outcome.fallback_reason
    assert all(item["review_required"] for item in outcome.results)
