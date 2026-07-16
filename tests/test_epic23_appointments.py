import pytest

from tcm_expert.database import (
    ConsultationRepository,
    DatabaseManager,
    FollowupAppointmentRepository,
    PatientRepository,
    ValidationError,
)


def _appointment_repository(tmp_path):
    database = DatabaseManager(tmp_path / "appointments.db")
    database.initialize()
    patient = PatientRepository(database).create({"code": "TH023", "full_name": "Nguyễn An"})
    consultation = ConsultationRepository(database).create(patient["id"], "TH023-001")
    consultation_id = consultation["id"]
    return database, FollowupAppointmentRepository(database), consultation_id


def test_create_and_update_followup_appointment(tmp_path):
    database, repository, consultation_id = _appointment_repository(tmp_path)
    appointment_id = repository.create(
        consultation_id,
        scheduled_at="2026-08-01T08:30",
        reason="Đánh giá đáp ứng điều trị",
        note="Mang theo đơn thuốc",
        responsible_by="BS Nguyễn An",
    )
    rows = repository.list_for_consultation(consultation_id)
    assert rows[0]["id"] == appointment_id
    assert rows[0]["status"] == "scheduled"

    repository.change_status(appointment_id, "confirmed", "BS Nguyễn An")
    assert repository.list(status="confirmed")[0]["id"] == appointment_id
    with database.transaction() as connection:
        actions = {
            row[0]
            for row in connection.execute(
                "SELECT action FROM audit_log WHERE entity_id=?", (appointment_id,)
            )
        }
    assert "create_followup_appointment" in actions
    assert "update_followup_appointment" in actions


def test_duplicate_active_appointment_is_rejected(tmp_path):
    _, repository, consultation_id = _appointment_repository(tmp_path)
    details = {
        "scheduled_at": "2026-08-01T08:30",
        "responsible_by": "BS Nguyễn An",
    }
    repository.create(consultation_id, **details)
    with pytest.raises(ValidationError, match="đã tồn tại"):
        repository.create(consultation_id, **details)


def test_appointment_requires_responsible_person(tmp_path):
    _, repository, consultation_id = _appointment_repository(tmp_path)
    with pytest.raises(ValidationError, match="người phụ trách"):
        repository.create(
            consultation_id,
            scheduled_at="2026-08-01T08:30",
            responsible_by="",
        )
