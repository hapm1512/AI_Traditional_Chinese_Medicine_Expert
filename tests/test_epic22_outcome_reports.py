import pytest

from tcm_expert.database import (
    DatabaseManager, TreatmentFollowupRepository, TreatmentOutcomeReportRepository,
    ValidationError,
)


def create_consultation(database: DatabaseManager) -> int:
    with database.transaction() as connection:
        patient_id = connection.execute(
            "INSERT INTO patients(code,full_name) VALUES('TH022','Lê Thị B')"
        ).lastrowid
        return int(connection.execute(
            "INSERT INTO consultations(patient_id,visit_code) VALUES(?,'TH022-01')",
            (patient_id,),
        ).lastrowid)


def test_summary_and_doctor_confirmed_snapshot(tmp_path):
    database = DatabaseManager(tmp_path / "epic22.db")
    database.initialize()
    consultation_id = create_consultation(database)
    TreatmentFollowupRepository(database).create(
        consultation_id, followup_date="2026-07-16", treatment_status="improved",
        symptom_score_before=8, symptom_score_after=3, effectiveness="good",
        adverse_reactions="Khô miệng", reviewed_by="BS. Trần Minh",
    )
    repository = TreatmentOutcomeReportRepository(database)
    summary = repository.summary("2026-07-01", "2026-07-31")
    assert summary["patient_count"] == 1
    assert summary["average_change"] == 5.0
    assert summary["adverse_reaction_count"] == 1
    report_id = repository.create(
        "2026-07-01", "2026-07-31", doctor_conclusion="Điều trị đáp ứng tốt.",
        reviewed_by="BS. Trần Minh",
    )
    report = repository.get(report_id)
    assert report["report"]["followup_count"] == 1
    assert report["doctor_conclusion"] == "Điều trị đáp ứng tốt."


def test_report_requires_doctor_conclusion(tmp_path):
    database = DatabaseManager(tmp_path / "epic22.db")
    database.initialize()
    repository = TreatmentOutcomeReportRepository(database)
    with pytest.raises(ValidationError):
        repository.create(
            "2026-07-01", "2026-07-31", doctor_conclusion="", reviewed_by="BS. A"
        )


def test_report_rejects_reversed_period(tmp_path):
    database = DatabaseManager(tmp_path / "epic22.db")
    database.initialize()
    with pytest.raises(ValidationError):
        TreatmentOutcomeReportRepository(database).summary("2026-08-01", "2026-07-01")
