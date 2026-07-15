import pytest

from tcm_expert.database import (
    ConsultationRepository,
    DatabaseManager,
    FormulaRepository,
    PatientRepository,
    PrescriptionRepository,
)


@pytest.fixture
def database(tmp_path):
    manager = DatabaseManager(tmp_path / "prescription.db")
    manager.initialize()
    return manager


def consultation(database: DatabaseManager) -> int:
    patient = PatientRepository(database).create(
        {"code": "BN-DT-01", "full_name": "Bệnh nhân thử đơn"}
    )
    visit = ConsultationRepository(database).create(patient["id"], "K-DT-01")
    return int(visit["id"])


def test_prescription_requires_approved_recommendation(database: DatabaseManager) -> None:
    consultation_id = consultation(database)
    formula = FormulaRepository(database)
    formula_id = int(next(row for row in formula.search() if row["ingredient_count"])["id"])
    recommendation_id = formula.save_recommendation(
        consultation_id,
        formula_id,
        {"custom_directions": "Sắc uống", "safety_notes": "Đã kiểm tra"},
    )
    with pytest.raises(ValueError, match="đã được bác sĩ phê duyệt"):
        PrescriptionRepository(database).create(
            recommendation_id,
            {
                "diagnosis": "Khí hư",
                "directions": "Sắc uống",
                "safety_notes": "Theo dõi",
                "doctor_name": "Bác sĩ An",
            },
        )


def test_create_and_approve_prescription(database: DatabaseManager) -> None:
    consultation_id = consultation(database)
    formula = FormulaRepository(database)
    formula_id = int(next(row for row in formula.search() if row["ingredient_count"])["id"])
    recommendation_id = formula.save_recommendation(
        consultation_id,
        formula_id,
        {
            "custom_directions": "Sắc uống",
            "safety_notes": "Đã kiểm tra dị ứng",
            "doctor_approved": True,
        },
    )
    repository = PrescriptionRepository(database)
    prescription_id = repository.create(
        recommendation_id,
        {
            "diagnosis": "Khí huyết hư",
            "directions": "Một thang mỗi ngày",
            "safety_notes": "Theo dõi đáp ứng",
            "doctor_name": "Bác sĩ An",
        },
    )
    detail = repository.detail(prescription_id)
    assert detail["status"] == "draft"
    assert detail["items"]
    repository.approve(prescription_id)
    assert repository.detail(prescription_id)["status"] == "approved"
    with pytest.raises(ValueError, match="đơn nháp"):
        repository.approve(prescription_id)
