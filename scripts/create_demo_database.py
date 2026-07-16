from pathlib import Path

from tcm_expert.database import ConsultationRepository, DatabaseManager, PatientRepository


def main() -> None:
    destination = Path("sample") / "tcm_expert_demo.db"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    database = DatabaseManager(destination)
    database.initialize()
    patient = PatientRepository(database).create(
        {
            "code": "BN999",
            "full_name": "Bệnh nhân minh họa",
            "birth_date": "1985-01-01",
            "sex": "other",
        }
    )
    consultation = ConsultationRepository(database).create(
        patient["id"], "DEMO-KHAM-001", chief_complaint="Hồ sơ dùng thử"
    )
    ConsultationRepository(database).add_diagnostic_entry(
        consultation["id"], "vong", "inspection", "Dữ liệu minh họa", 1
    )
    assert database.health_check()
    print(destination.resolve())


if __name__ == "__main__":
    main()
