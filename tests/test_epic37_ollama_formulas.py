import json

from tcm_expert.database import (
    ConsultationRepository,
    DatabaseManager,
    PatientRepository,
    SyndromeRepository,
)
from tcm_expert.services.ollama_formula_recommender import OllamaFormulaRecommender


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


def _confirmed_visit(tmp_path):
    database = DatabaseManager(tmp_path / "epic37.db")
    database.initialize()
    patient = PatientRepository(database).create({"code": "BN037", "full_name": "Epic 37"})
    visit = ConsultationRepository(database).create(
        patient["id"], "", chief_complaint="Mệt, ăn ít, đại tiện lỏng"
    )
    syndromes = SyndromeRepository(database)
    syndrome = next(item for item in syndromes.catalogue() if item["code"] == "TYKHIHU")
    syndromes.save(
        visit["id"], syndrome["id"],
        {"confidence": 0.9, "evidence": "Mệt; ăn ít", "is_primary": True,
         "doctor_confirmed": True},
    )
    return database, visit["id"]


def test_qwen_only_selects_catalogue_formulas(tmp_path):
    database, visit_id = _confirmed_visit(tmp_path)
    chat = FakeChat({"suggestions": [
        {"code": "KHONG-TON-TAI", "reason": "bịa đặt"},
        {"code": "TQTH", "reason": "Phù hợp phép trị kiện tỳ ích khí"},
    ]})
    outcome = OllamaFormulaRecommender(database, chat=chat).recommend(visit_id)

    assert outcome.source == "ollama"
    assert [item["code"] for item in outcome.result["recommendations"]] == ["TQTH"]
    assert outcome.result["recommendations"][0]["review_required"] is True
    assert "không đưa liều dùng" in chat.prompt


def test_unconfirmed_syndrome_blocks_qwen(tmp_path):
    database = DatabaseManager(tmp_path / "blocked.db")
    database.initialize()
    patient = PatientRepository(database).create({"code": "BN038", "full_name": "Chưa duyệt"})
    visit = ConsultationRepository(database).create(patient["id"], "")
    chat = FakeChat({"suggestions": []})

    outcome = OllamaFormulaRecommender(database, chat=chat).recommend(visit["id"])

    assert outcome.result["eligible"] is False
    assert outcome.source == "rules"
    assert chat.prompt == ""


def test_ollama_failure_uses_rule_fallback(tmp_path):
    database, visit_id = _confirmed_visit(tmp_path)
    outcome = OllamaFormulaRecommender(
        database, chat=FakeChat(error=RuntimeError("Ollama chưa chạy"))
    ).recommend(visit_id)

    assert outcome.source == "rules"
    assert outcome.result["recommendations"]
    assert "Ollama chưa chạy" in outcome.fallback_reason
