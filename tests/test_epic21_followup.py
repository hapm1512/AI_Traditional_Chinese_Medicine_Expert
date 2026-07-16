import pytest

from tcm_expert.database import DatabaseManager, TreatmentFollowupRepository, ValidationError


def create_consultation(database: DatabaseManager) -> int:
    with database.transaction() as connection:
        patient_id = connection.execute(
            "INSERT INTO patients(code,full_name) VALUES('TH021','Nguyễn Văn A')"
        ).lastrowid
        return int(
            connection.execute(
                "INSERT INTO consultations(patient_id,visit_code) VALUES(?, 'TH021-01')",
                (patient_id,),
            ).lastrowid
        )


def test_doctor_followup_and_outcome_summary(tmp_path):
    database = DatabaseManager(tmp_path / "epic21.db")
    database.initialize()
    consultation_id = create_consultation(database)
    repository = TreatmentFollowupRepository(database)
    followup_id = repository.create(
        consultation_id,
        followup_date="2026-07-16",
        treatment_status="improved",
        symptom_score_before=8,
        symptom_score_after=3,
        effectiveness="good",
        reviewed_by="BS. Trần Minh",
    )
    assert repository.get(followup_id)["treatment_status"] == "improved"
    assert repository.outcome_summary(consultation_id) == {
        "count": 1,
        "trend": "improved",
        "change": 5,
    }


def test_followup_requires_doctor(tmp_path):
    database = DatabaseManager(tmp_path / "epic21.db")
    database.initialize()
    consultation_id = create_consultation(database)
    with pytest.raises(ValidationError):
        TreatmentFollowupRepository(database).create(consultation_id, reviewed_by="")


def test_followup_rejects_invalid_score(tmp_path):
    database = DatabaseManager(tmp_path / "epic21.db")
    database.initialize()
    consultation_id = create_consultation(database)
    with pytest.raises(ValidationError):
        TreatmentFollowupRepository(database).create(
            consultation_id, symptom_score_after=11, reviewed_by="BS. Trần Minh"
        )
