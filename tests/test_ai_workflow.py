import pytest

from tcm_expert.ai import AIInputInsufficient, AIWorkflow, AIWorkflowDisabled, DoctorDecision
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


def test_incomplete_input_is_blocked_and_logged(tmp_path):
    database, visit_id = make_visit(tmp_path)
    with pytest.raises(AIInputInsufficient):
        AIWorkflow(database, enabled=True).propose(visit_id)
    with database.transaction() as connection:
        row = connection.execute(
            "SELECT status FROM ai_operation_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row["status"] == "blocked"


def test_ai_cannot_emit_prescription_or_dose():
    with pytest.raises(ValueError):
        AIProposal(1, "x", metadata={"dosage": "10 g"})

