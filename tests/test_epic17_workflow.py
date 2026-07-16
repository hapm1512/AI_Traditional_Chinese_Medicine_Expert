import pytest

from tcm_expert.database import (
    ConsultationRepository,
    DatabaseManager,
    PatientRepository,
    SettingsRepository,
    ValidationError,
)


@pytest.fixture
def database(tmp_path):
    manager = DatabaseManager(tmp_path / "epic17.db")
    manager.initialize()
    return manager


def test_patient_group_and_visit_codes_are_standardized(database):
    settings = SettingsRepository(database)
    settings.save_group("Hô hấp", "HH")
    patients = PatientRepository(database)
    assert patients.next_number("HH") == "001"
    patient = patients.create({"code": "HH001", "full_name": "Bệnh nhân thử"})
    consultations = ConsultationRepository(database)
    first = consultations.create(patient["id"], "")
    second = consultations.create(patient["id"], "")
    assert first["visit_code"] == "HH001-01"
    assert second["visit_code"] == "HH001-02"


def test_phone_and_identity_lengths_are_enforced(database):
    patients = PatientRepository(database)
    with pytest.raises(ValidationError):
        patients.create({"code": "BN201", "full_name": "Sai", "phone": "0901"})
    patient = patients.create(
        {
            "code": "BN202",
            "full_name": "Đúng",
            "phone": "0901234567",
            "identity_number": "012345678901",
        }
    )
    assert patient["phone"] == "0901234567"


def test_doctor_identity_is_required_for_approval(database):
    settings = SettingsRepository(database)
    with pytest.raises(ValidationError):
        settings.doctor_name(required=True)
    saved = settings.save_doctor(
        {
            "full_name": "Bác sĩ Nguyễn An",
            "license_number": "GPHN-001",
            "specialty": "Y học cổ truyền",
        }
    )
    assert settings.doctor_name(required=True) == saved["full_name"]
