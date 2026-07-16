import pytest

from tcm_expert.ai import AIWorkflow, AIWorkflowDisabled, DoctorDecision
from tcm_expert.ai.models import AIProposal
from tcm_expert.database import ConsultationRepository, DatabaseManager, PatientRepository
from tcm_expert.database.settings_repository import SettingsRepository


def make_visit(tmp_path):
    database = DatabaseManager(tmp_path / "ai.db")
    database.initialize()
    patient = PatientRepository(database).create({"code": "BN001", "full_name": "Thử AI"})
    visit = ConsultationRepository(database).create(patient["id"], "")
    return database, visit["id"]


def test_ai_is_off_by_default(tmp_path):
    database, visit_id = make_visit(tmp_path)
    assert SettingsRepository(database).ai_settings()["enabled"] is False
    with pytest.raises(AIWorkflowDisabled):
        AIWorkflow(database).propose(visit_id)


def test_provider_independent_fallback_requires_doctor(tmp_path):
    database, visit_id = make_visit(tmp_path)
    proposal = AIWorkflow(database, enabled=True).propose(visit_id)
    assert proposal.decision == DoctorDecision.PENDING
    assert proposal.confidence <= 0.95
    assert "Bác sĩ" in proposal.vietnamese_summary
    assert "chưa được bác sĩ duyệt" in proposal.vietnamese_summary.lower()
    assert "Bắt buộc bác sĩ" in proposal.vietnamese_summary
    assert any("TCMChat" in trace for trace in proposal.provider_trace)


def test_ai_cannot_emit_prescription_or_dose():
    with pytest.raises(ValueError):
        AIProposal(1, "x", metadata={"dosage": "10 g"})
