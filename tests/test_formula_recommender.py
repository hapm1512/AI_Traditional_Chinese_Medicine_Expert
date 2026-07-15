from pathlib import Path

from tcm_expert.database import ConsultationRepository, DatabaseManager, PatientRepository
from tcm_expert.services.formula_recommender import FormulaRecommender


def test_recommender_never_prescribes_and_always_checks_safety(tmp_path: Path) -> None:
    database = DatabaseManager(tmp_path / "recommend.db")
    database.initialize()
    patient = PatientRepository(database).create(
        {"code": "BN-AI", "full_name": "Nguyễn Văn A", "allergies": "Nhân sâm"}
    )
    consultation = ConsultationRepository(database).create(
        patient["id"], "K-AI", chief_complaint="Mệt mỏi, ăn kém"
    )
    result = FormulaRecommender(database).recommend(consultation["id"])
    assert 1 <= len(result["recommendations"]) <= 3
    assert "không phải đơn thuốc" in result["disclaimer"]
    assert any(
        "Dị ứng" in alert["message"]
        for item in result["recommendations"]
        for alert in item["safety"]
    )
    assert all("dosage" not in item for item in result["recommendations"])
