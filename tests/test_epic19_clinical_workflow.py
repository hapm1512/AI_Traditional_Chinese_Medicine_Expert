from tcm_expert.database import (
    ClinicalDecisionRepository,
    ConsultationRepository,
    DatabaseManager,
    PatientRepository,
)
from tcm_expert.services.clinical_decision_support import ClinicalDecisionSupport


def make_report(tmp_path):
    database = DatabaseManager(tmp_path / "epic19.db")
    database.initialize()
    patient = PatientRepository(database).create({"code": "BN019", "full_name": "Epic 19"})
    visit = ConsultationRepository(database).create(patient["id"], "")
    report = ClinicalDecisionSupport(database).build(visit["id"])
    report["ai_proposal"] = {
        "summary": "Chỉ tham khảo; bác sĩ quyết định.",
        "evidence": ["OpenTCM"],
        "warnings": [],
        "provider_trace": ["TCMChat: hoàn tất"],
        "confidence": 0.72,
        "status": "pending",
    }
    return database, visit["id"], report


def test_ai_proposal_history_and_doctor_acceptance(tmp_path):
    database, visit_id, report = make_report(tmp_path)
    repository = ClinicalDecisionRepository(database)
    first = repository.create_ai(visit_id, report)
    second = repository.create_ai(visit_id, report)
    rows = repository.list_for_consultation(visit_id)
    assert [row["id"] for row in rows] == [second, first]
    assert rows[0]["report_type"] == "ai"
    assert rows[0]["ai_confidence"] == 0.72
    repository.decide(second, "BS Nguyễn Văn A", "accepted")
    saved = repository.get(second)
    assert saved["doctor_decision"] == "accepted"
    assert saved["reviewed_by"] == "BS Nguyễn Văn A"


def test_ai_rejection_preserves_reason(tmp_path):
    database, visit_id, report = make_report(tmp_path)
    repository = ClinicalDecisionRepository(database)
    report_id = repository.create_ai(visit_id, report)
    repository.decide(report_id, "BS Nguyễn Văn A", "rejected", "Cần bổ sung Thiết chẩn")
    saved = repository.get(report_id)
    assert saved["doctor_decision"] == "rejected"
    assert saved["decision_reason"] == "Cần bổ sung Thiết chẩn"
