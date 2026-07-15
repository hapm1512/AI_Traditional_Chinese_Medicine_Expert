import sqlite3

import pytest

from tcm_expert.database import (
    ConsultationRepository,
    DatabaseManager,
    PatientRepository,
    ReferenceRepository,
    ValidationError,
)
from tcm_expert.database.schema import MIGRATIONS

EXPECTED_TABLES = {
    "patients",
    "consultations",
    "diagnostic_entries",
    "symptoms",
    "consultation_symptoms",
    "organ_systems",
    "meridians",
    "theory_concepts",
    "tcm_syndromes",
    "consultation_syndromes",
    "diseases",
    "disease_relations",
    "consultation_diseases",
    "materia_medica",
    "herb_categories",
    "formulas",
    "formula_ingredients",
    "herb_interactions",
    "formula_recommendations",
    "audit_log",
    "listening_smelling_findings",
    "inquiry_findings",
    "pulse_findings",
    "palpation_findings",
}


@pytest.fixture
def database(tmp_path):
    manager = DatabaseManager(tmp_path / "test.db")
    manager.initialize()
    return manager


def test_database_initialization_is_idempotent(database):
    database.initialize()
    assert database.health_check()
    with database.transaction() as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        versions = [row[0] for row in connection.execute("SELECT version FROM schema_version")]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    assert EXPECTED_TABLES <= tables
    assert versions == [1, 2, 3, 4, 5]
    assert integrity == "ok"


def test_migrates_epic_one_database(tmp_path):
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.executescript(MIGRATIONS[0][1])
    connection.execute("CREATE TABLE schema_version(version INTEGER PRIMARY KEY)")
    connection.execute("INSERT INTO schema_version VALUES(1)")
    connection.commit()
    connection.close()

    DatabaseManager(path).initialize()
    with sqlite3.connect(path) as migrated:
        assert migrated.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 5
        columns = {row[1] for row in migrated.execute("PRAGMA table_info(patients)")}
    assert {"allergies", "deleted_at", "identity_number"} <= columns


def test_patient_crud_and_audit(database):
    repository = PatientRepository(database)
    patient = repository.create(
        {
            "code": "bn-001",
            "full_name": "Nguyễn Văn An",
            "birth_date": "1988-05-20",
            "sex": "male",
        }
    )
    assert patient["code"] == "BN-001"
    updated = repository.update(patient["id"], {"phone": "0900000000"})
    assert updated["phone"] == "0900000000"
    assert repository.list("Văn An")[0]["id"] == patient["id"]
    repository.delete(patient["id"])
    assert repository.list() == []
    with database.transaction() as connection:
        assert connection.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 3


def test_patient_validation(database):
    repository = PatientRepository(database)
    with pytest.raises(ValidationError):
        repository.create({"code": "BN 01", "full_name": ""})
    with pytest.raises(ValidationError):
        repository.create(
            {"code": "BN01", "full_name": "An", "birth_date": "2999-01-01"}
        )


def test_consultation_and_four_diagnostics(database):
    patient = PatientRepository(database).create(
        {"code": "BN002", "full_name": "Trần Thị Bình"}
    )
    consultations = ConsultationRepository(database)
    visit = consultations.create(patient["id"], "K-2026-001", chief_complaint="Mệt mỏi")
    for method in ("vong", "van", "van_hoi", "thiet"):
        consultations.add_diagnostic_entry(visit["id"], method, "mẫu", "Kết quả mẫu", 2)
    assert consultations.list_for_patient(patient["id"])[0]["visit_code"] == "K-2026-001"
    with database.transaction() as connection:
        methods = {
            row[0]
            for row in connection.execute(
                "SELECT method FROM diagnostic_entries WHERE consultation_id=?", (visit["id"],)
            )
        }
    assert methods == {"vong", "van", "van_hoi", "thiet"}


def test_consultation_update_delete_and_diagnostic_listing(database):
    patient = PatientRepository(database).create(
        {"code": "BN003", "full_name": "Lê Văn Cường"}
    )
    repository = ConsultationRepository(database)
    visit = repository.create(patient["id"], "K-2026-002")
    repository.add_diagnostic_entry(visit["id"], "vong", "Lưỡi", "Lưỡi nhạt")
    assert repository.diagnostic_entries(visit["id"])[0]["finding"] == "Lưỡi nhạt"
    updated = repository.update(visit["id"], {"status": "in_review"})
    assert updated["status"] == "in_review"
    repository.delete(visit["id"])
    assert repository.list_for_patient(patient["id"]) == []


def test_diagnostic_update_delete_and_assessment(database):
    patient = PatientRepository(database).create(
        {"code": "BN004", "full_name": "Phạm Thị Dung"}
    )
    repository = ConsultationRepository(database)
    visit = repository.create(patient["id"], "K-2026-004")
    entry_id = repository.add_diagnostic_entry(
        visit["id"], "thiet", "Mạch", "Mạch trầm", 4
    )
    repository.update_diagnostic_entry(
        entry_id, "thiet", "Mạch", "Mạch trầm tế", 6, "Tay trái"
    )
    assert repository.diagnostic_entries(visit["id"])[0]["severity"] == 6
    updated = repository.update(visit["id"], {"assessment": "Khí huyết hư"})
    assert updated["assessment"] == "Khí huyết hư"
    repository.delete_diagnostic_entry(entry_id)
    assert repository.diagnostic_entries(visit["id"]) == []


def test_seed_reference_data_and_formula_disclaimer(database):
    references = ReferenceRepository(database)
    assert len(references.list("materia_medica")) >= 2
    formulas = references.list("formulas")
    assert formulas
    assert "chỉ mang tính tham khảo" in formulas[0]["disclaimer"]
    assert database.reference_counts()["tcm_syndromes"] >= 2


def test_foreign_keys_are_enforced(database):
    with pytest.raises(sqlite3.IntegrityError), database.transaction() as connection:
        connection.execute("INSERT INTO consultations(patient_id) VALUES(99999)")


def test_manual_listening_smelling_workflow(database):
    patient = PatientRepository(database).create(
        {"code": "BN005", "full_name": "Nguyễn Thị Epic Năm"}
    )
    repository = ConsultationRepository(database)
    visit = repository.create(patient["id"], "K-2026-005")
    finding_id = repository.add_listening_smelling_finding(
        visit["id"],
        {
            "finding_type": "cough",
            "characteristic": "Ho khan, tiếng yếu",
            "frequency": "Từng cơn",
            "severity": 4,
            "duration": "3 ngày",
            "recorded_by": "Y tá Lan",
        },
    )
    rows = repository.listening_smelling_findings(visit["id"])
    assert rows[0]["id"] == finding_id
    assert rows[0]["recorded_by"] == "Y tá Lan"
    repository.delete_listening_smelling_finding(finding_id)
    assert repository.listening_smelling_findings(visit["id"]) == []


def test_listening_smelling_validation(database):
    patient = PatientRepository(database).create(
        {"code": "BN006", "full_name": "Nguyễn Văn Kiểm Thử"}
    )
    repository = ConsultationRepository(database)
    visit = repository.create(patient["id"], "K-2026-006")
    with pytest.raises(ValidationError):
        repository.add_listening_smelling_finding(
            visit["id"],
            {"finding_type": "cough", "characteristic": "", "recorded_by": ""},
        )


def test_structured_inquiry_upsert_and_delete(database):
    patient = PatientRepository(database).create(
        {"code": "BN007", "full_name": "Bệnh nhân Vấn chẩn"}
    )
    repository = ConsultationRepository(database)
    visit = repository.create(patient["id"], "K-2026-007")
    saved = repository.save_inquiry_finding(
        visit["id"],
        {
            "cold_heat": "Sợ lạnh, không sốt",
            "sleep": "Khó vào giấc",
            "stool": "Đại tiện lỏng",
            "recorded_by": "Y tá Lan",
        },
    )
    assert saved["cold_heat"] == "Sợ lạnh, không sốt"
    repository.save_inquiry_finding(
        visit["id"], {"sleep": "Ngủ tốt hơn", "recorded_by": "Bác sĩ An"}
    )
    current = repository.inquiry_finding(visit["id"])
    assert current["sleep"] == "Ngủ tốt hơn"
    assert current["recorded_by"] == "Bác sĩ An"
    repository.delete_inquiry_finding(visit["id"])
    assert repository.inquiry_finding(visit["id"]) is None


def test_inquiry_requires_recorder(database):
    patient = PatientRepository(database).create(
        {"code": "BN008", "full_name": "Kiểm thử Vấn chẩn"}
    )
    repository = ConsultationRepository(database)
    visit = repository.create(patient["id"], "K-2026-008")
    with pytest.raises(ValidationError):
        repository.save_inquiry_finding(visit["id"], {"sleep": "Mất ngủ"})


def test_structured_pulse_and_palpation(database):
    patient = PatientRepository(database).create(
        {"code": "BN009", "full_name": "Bệnh nhân Thiết chẩn"}
    )
    repository = ConsultationRepository(database)
    visit = repository.create(patient["id"], "K-2026-009")
    pulse = repository.save_pulse_finding(visit["id"], {
        "side": "left", "position": "cun", "depth": "Phù", "rate": "Sác",
        "strength": "Hữu lực", "rhythm": "Đều", "quality": "Huyền sác",
        "bpm": 92, "recorded_by": "Bác sĩ An",
    })
    assert pulse["quality"] == "Huyền sác"
    repository.save_pulse_finding(visit["id"], {
        "side": "left", "position": "cun", "quality": "Huyền",
        "recorded_by": "Bác sĩ An",
    })
    assert len(repository.pulse_findings(visit["id"])) == 1
    finding_id = repository.add_palpation_finding(visit["id"], {
        "body_area": "Hạ sườn phải", "finding_type": "tenderness",
        "characteristic": "Ấn đau nhẹ", "severity": 3, "recorded_by": "Y tá Lan",
    })
    assert repository.palpation_findings(visit["id"])[0]["severity"] == 3
    repository.delete_palpation_finding(finding_id)
    assert repository.palpation_findings(visit["id"]) == []
    repository.delete_pulse_findings(visit["id"])
    assert repository.pulse_findings(visit["id"]) == []


def test_pulse_and_palpation_validation(database):
    patient = PatientRepository(database).create(
        {"code": "BN010", "full_name": "Kiểm thử Thiết chẩn"}
    )
    repository = ConsultationRepository(database)
    visit = repository.create(patient["id"], "K-2026-010")
    with pytest.raises((ValidationError, ValueError)):
        repository.save_pulse_finding(visit["id"], {
            "side": "left", "position": "cun", "quality": "", "recorded_by": "",
        })
    with pytest.raises((ValidationError, ValueError)):
        repository.add_palpation_finding(visit["id"], {
            "body_area": "Bụng", "finding_type": "invalid",
            "characteristic": "Đau", "recorded_by": "Bác sĩ An",
        })
