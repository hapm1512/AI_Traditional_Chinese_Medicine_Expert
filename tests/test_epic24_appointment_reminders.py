from tcm_expert.database import (
    ConsultationRepository,
    DatabaseManager,
    FollowupAppointmentRepository,
    PatientRepository,
)


def _repository(tmp_path):
    database = DatabaseManager(tmp_path / "reminders.db")
    database.initialize()
    patient = PatientRepository(database).create({"code": "TH024", "full_name": "Trần Bình"})
    consultation = ConsultationRepository(database).create(patient["id"], "TH024-001")
    return database, FollowupAppointmentRepository(database), consultation["id"]


def test_mark_reminded_records_person_time_and_audit(tmp_path):
    database, repository, consultation_id = _repository(tmp_path)
    appointment_id = repository.create(
        consultation_id,
        scheduled_at="2026-08-02T08:30",
        responsible_by="BS Nguyễn An",
    )
    repository.mark_reminded(
        appointment_id,
        reminded_by="Điều dưỡng Mai",
        reminded_at="2026-08-01T09:15",
    )
    row = repository.list(view="reminded", now="2026-08-01T10:00")[0]
    assert row["reminded_at"] == "2026-08-01T09:15"
    assert row["reminded_by"] == "Điều dưỡng Mai"
    assert row["reminder_count"] == 1
    with database.transaction() as connection:
        action = connection.execute(
            "SELECT action FROM audit_log WHERE entity_id=? ORDER BY id DESC", (appointment_id,)
        ).fetchone()[0]
    assert action == "remind_followup_appointment"


def test_attention_filters_are_deterministic(tmp_path):
    _, repository, consultation_id = _repository(tmp_path)
    overdue = repository.create(
        consultation_id,
        scheduled_at="2026-08-01T08:00",
        responsible_by="BS Nguyễn An",
    )
    today = repository.create(
        consultation_id,
        scheduled_at="2026-08-02T14:00",
        responsible_by="BS Nguyễn An",
    )
    upcoming = repository.create(
        consultation_id,
        scheduled_at="2026-08-05T09:00",
        responsible_by="BS Nguyễn An",
    )
    now = "2026-08-02T10:00"
    assert [row["id"] for row in repository.list(view="today", now=now)] == [today]
    assert [row["id"] for row in repository.list(view="overdue_confirmation", now=now)] == [overdue]
    assert [row["id"] for row in repository.list(view="upcoming", now=now)] == [today, upcoming]
    assert {row["id"] for row in repository.list(view="pending_reminder", now=now)} == {
        overdue,
        today,
        upcoming,
    }


def test_due_alert_is_claimed_only_once(tmp_path):
    database, repository, consultation_id = _repository(tmp_path)
    appointment_id = repository.create(
        consultation_id,
        scheduled_at="2026-08-02T10:00",
        responsible_by="BS Nguyễn An",
    )
    first = repository.claim_due_alerts(shown_at="2026-08-02T10:01")
    second = repository.claim_due_alerts(shown_at="2026-08-02T10:02")
    assert [row["id"] for row in first] == [appointment_id]
    assert second == []
    with database.transaction() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM appointment_alerts WHERE appointment_id=?",
            (appointment_id,),
        ).fetchone()[0]
    assert count == 1


def test_alert_stays_pending_until_doctor_acknowledges(tmp_path):
    _, repository, consultation_id = _repository(tmp_path)
    repository.create(
        consultation_id,
        scheduled_at="2026-08-02T10:00",
        responsible_by="BS Nguyễn An",
    )
    pending = repository.pending_due_alerts(now="2026-08-02T10:01")
    assert len(pending) == 1
    assert repository.pending_due_alerts(now="2026-08-02T10:02")
    repository.acknowledge_alerts(
        [pending[0]["alert_id"]],
        acknowledged_by="BS Nguyễn An",
        acknowledged_at="2026-08-02T10:03",
    )
    assert repository.pending_due_alerts(now="2026-08-02T10:04") == []


def test_30_day_history_and_reopen_flow(tmp_path):
    _, repository, consultation_id = _repository(tmp_path)
    appointment_id = repository.create(
        consultation_id,
        scheduled_at="2026-05-01T08:00",
        responsible_by="BS Nguyễn An",
    )
    repository.review_overdue(
        appointment_id,
        action="history_reference",
        note="Bệnh nhân chưa sắp xếp được thời gian",
        reviewed_by="BS Nguyễn An",
        reviewed_at="2026-06-01T08:01",
    )
    row = repository.list(view="history_reference")[0]
    assert row["overdue_note"]
    repository.review_overdue(
        appointment_id,
        action="reopened",
        note="Bệnh nhân đã đến tái khám",
        reviewed_by="BS Nguyễn An",
        reviewed_at="2026-06-02T08:00",
    )
    row = repository.list(status="confirmed")[0]
    assert row["case_state"] == "reopened"


def test_90_day_expiration_keeps_record(tmp_path):
    _, repository, consultation_id = _repository(tmp_path)
    appointment_id = repository.create(
        consultation_id,
        scheduled_at="2026-05-01T08:00",
        responsible_by="BS Nguyễn An",
    )
    assert repository.expire_after_90_days(now="2026-07-31T08:01") == 1
    row = repository.list(view="cancelled_90")[0]
    assert row["id"] == appointment_id
    assert row["status"] == "cancelled"
