from tcm_expert.database import (
    ConsultationRepository,
    DatabaseManager,
    PatientRepository,
    SyndromeRepository,
)
from tcm_expert.services.clinical_decision_support import ClinicalDecisionSupport


def _visit(tmp_path):
    database = DatabaseManager(tmp_path / "epic35.db")
    database.initialize()
    patient = PatientRepository(database).create(
        {"code": "BN035", "full_name": "Kiểm thử Epic 35"}
    )
    visit = ConsultationRepository(database).create(
        patient["id"], "", chief_complaint="Mệt, ăn ít, đại tiện lỏng"
    )
    return database, visit["id"]


def test_formula_suggestions_wait_for_doctor_confirmation(tmp_path):
    database, visit_id = _visit(tmp_path)

    report = ClinicalDecisionSupport(database).build(visit_id)

    assert report["formula_eligible"] is False
    assert report["formula_suggestions"] == []
    assert "bác sĩ xác nhận" in report["formula_blocked_reason"].lower()


def test_confirmed_syndrome_unlocks_reference_formulas(tmp_path):
    database, visit_id = _visit(tmp_path)
    syndromes = SyndromeRepository(database)
    syndrome = next(item for item in syndromes.catalogue() if item["code"] == "TYKHIHU")
    syndromes.save(
        visit_id,
        syndrome["id"],
        {
            "confidence": 0.85,
            "evidence": "Mệt; ăn ít; đại tiện lỏng",
            "is_primary": True,
            "doctor_confirmed": True,
        },
    )

    report = ClinicalDecisionSupport(database).build(visit_id)

    assert report["formula_eligible"] is True
    assert report["formula_suggestions"]
    assert report["formula_suggestions"][0]["name"] == "Tứ Quân Tử Thang"
