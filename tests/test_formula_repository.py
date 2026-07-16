from pathlib import Path

import pytest

from tcm_expert.database import (
    ConsultationRepository,
    DatabaseManager,
    FormulaRepository,
    PatientRepository,
)


@pytest.fixture
def database(tmp_path: Path) -> DatabaseManager:
    manager = DatabaseManager(tmp_path / "formula.db")
    manager.initialize()
    return manager


def test_formula_search_and_detail(database: DatabaseManager) -> None:
    repository = FormulaRepository(database)
    rows = repository.search("Tứ Quân")
    assert len(rows) == 1
    assert rows[0]["ingredient_count"] == 2
    detail = repository.detail(rows[0]["id"])
    assert {item["herb_name"] for item in detail["ingredients"]} == {
        "Nhân sâm",
        "Bạch truật",
    }
    assert "tham khảo" in detail["disclaimer"]


def test_recommendation_requires_safety_note_for_approval(
    database: DatabaseManager,
) -> None:
    patient = PatientRepository(database).create({"code": "BN104", "full_name": "Nguyễn Văn A"})
    consultation = ConsultationRepository(database).create(patient["id"], "K-FORMULA")
    repository = FormulaRepository(database)
    formula = repository.search()[0]

    with pytest.raises(ValueError, match="ghi chú an toàn"):
        repository.save_recommendation(consultation["id"], formula["id"], {"doctor_approved": True})

    recommendation_id = repository.save_recommendation(
        consultation["id"],
        formula["id"],
        {"safety_notes": "Đã kiểm tra", "doctor_approved": True},
    )
    rows = repository.list_recommendations(consultation["id"])
    assert rows[0]["id"] == recommendation_id
    assert rows[0]["doctor_approved"] == 1
