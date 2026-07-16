from tcm_expert.database import (
    ConsultationRepository,
    DashboardRepository,
    DatabaseManager,
    FollowupAppointmentRepository,
    PatientRepository,
)


def _repositories(tmp_path):
    database = DatabaseManager(tmp_path / "dashboard.db")
    database.initialize()
    patient = PatientRepository(database).create(
        {"code": "TH025", "full_name": "Nguyễn Minh"}
    )
    consultation = ConsultationRepository(database).create(patient["id"], "TH025-01")
    return (
        database,
        DashboardRepository(database),
        FollowupAppointmentRepository(database),
        consultation["id"],
    )


def test_dashboard_summary_counts_operational_work(tmp_path):
    _, dashboard, appointments, consultation_id = _repositories(tmp_path)
    overdue = appointments.create(
        consultation_id,
        scheduled_at="2026-07-16T08:00",
        responsible_by="BS An",
    )
    appointments.create(
        consultation_id,
        scheduled_at="2026-07-16T15:00",
        responsible_by="BS An",
    )
    appointments.create(
        consultation_id,
        scheduled_at="2026-07-19T09:00",
        responsible_by="BS An",
    )
    appointments.mark_reminded(
        overdue,
        reminded_by="Điều dưỡng Mai",
        reminded_at="2026-07-15T09:00",
    )

    summary = dashboard.summary(now="2026-07-16T10:00")
    assert summary == {
        "patients": 1,
        "under_treatment": 1,
        "monitoring": 0,
        "today": 2,
        "overdue": 1,
        "pending_reminder": 2,
    }


def test_dashboard_prioritizes_overdue_before_today(tmp_path):
    _, dashboard, appointments, consultation_id = _repositories(tmp_path)
    appointments.create(
        consultation_id,
        scheduled_at="2026-07-16T14:00",
        reason="Kiểm tra sau điều trị",
        responsible_by="BS An",
    )
    appointments.create(
        consultation_id,
        scheduled_at="2026-07-16T08:00",
        reason="Đã quá giờ",
        responsible_by="BS An",
    )

    rows = dashboard.attention_items(now="2026-07-16T10:00")
    assert [row["priority"] for row in rows] == ["overdue", "today"]
    assert rows[0]["patient_code"] == "TH025"
    assert rows[0]["visit_code"] == "TH025-01"


def test_doctor_can_dismiss_only_after_three_hours(tmp_path):
    database, _, appointments, consultation_id = _repositories(tmp_path)
    appointment_id = appointments.create(
        consultation_id,
        scheduled_at="2026-07-16T08:00",
        responsible_by="BS An",
    )
    try:
        appointments.dismiss_overdue_notification(
            appointment_id, doctor_name="BS An", now="2026-07-16T10:59"
        )
    except Exception as error:
        assert "3 giờ" in str(error)
    else:
        raise AssertionError("Thông báo chưa trễ đủ ba giờ")

    appointments.dismiss_overdue_notification(
        appointment_id, doctor_name="BS An", now="2026-07-16T11:00"
    )
    row = next(row for row in appointments.list() if row["id"] == appointment_id)
    assert row["status"] == "cancelled"
    assert row["reviewed_by"] == "BS An"
    with database.transaction() as connection:
        action = connection.execute(
            "SELECT action FROM audit_log WHERE entity_id=? ORDER BY id DESC",
            (appointment_id,),
        ).fetchone()[0]
    assert action == "dismiss_overdue_appointment_notification"
