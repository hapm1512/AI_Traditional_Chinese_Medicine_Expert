from tcm_expert.database import DatabaseManager, ReferenceRepository
from tcm_expert.services.syndrome_reasoner import suggest


def test_ai_diagnosis_returns_ranked_explainable_suggestions(tmp_path):
    database = DatabaseManager(tmp_path / "epic34.db")
    database.initialize()
    syndromes = ReferenceRepository(database).list("tcm_syndromes")

    results = suggest(
        "Mệt, ăn ít, đại tiện lỏng, lưỡi nhạt, mạch hư; mất ngủ, hay quên",
        syndromes,
    )

    assert len(results) >= 2
    assert results[0]["code"] == "TYKHIHU"
    assert results[0]["evidence_count"] == 5
    assert results[0]["confidence"] >= results[1]["confidence"]
    assert all(item["review_required"] for item in results)


def test_ai_diagnosis_never_marks_doctor_confirmation(tmp_path):
    database = DatabaseManager(tmp_path / "epic34-safety.db")
    database.initialize()
    syndromes = ReferenceRepository(database).list("tcm_syndromes")

    result = suggest("Đau lưng, ù tai, miệng khô", syndromes)[0]

    assert "doctor_confirmed" not in result
    assert result["review_required"] is True
