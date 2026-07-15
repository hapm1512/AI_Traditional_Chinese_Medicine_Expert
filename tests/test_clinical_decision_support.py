from pathlib import Path

import pytest

from tcm_expert.database import (
    ClinicalDecisionRepository,
    ConsultationRepository,
    DatabaseManager,
    PatientRepository,
    ValidationError,
)
from tcm_expert.services.clinical_decision_support import ClinicalDecisionSupport


def test_report_is_explainable_persistent_and_requires_doctor(tmp_path: Path) -> None:
    database = DatabaseManager(tmp_path / "clinical.db")
    database.initialize()
    patient = PatientRepository(database).create(
        {"code": "BN-CDS", "full_name": "Nguyễn Văn A", "allergies": ""}
    )
    consultation = ConsultationRepository(database).create(
        patient["id"], "K-CDS", chief_complaint="Đau ngực và khó thở"
    )
    report = ClinicalDecisionSupport(database).build(consultation["id"])
    assert report["risk_level"] == "high"
    assert report["red_flags"]
    assert report["missing_data"]
    assert "không phải chẩn đoán" in report["disclaimer"]

    repository = ClinicalDecisionRepository(database)
    report_id = repository.create(consultation["id"], report)
    assert repository.get(report_id)["report"]["risk_level"] == "high"
    with pytest.raises(ValidationError):
        repository.review(report_id, "")
    repository.review(report_id, "BS Nguyễn")
    assert repository.get(report_id)["status"] == "reviewed"
