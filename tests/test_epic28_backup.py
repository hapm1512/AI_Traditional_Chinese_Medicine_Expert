import sqlite3

import pytest

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.security import UserSession, set_current_user


def admin_session():
    return UserSession(1, "admin", "Quản trị", "admin", 1)


def test_backup_and_restore_preserves_patient_data(tmp_path):
    database = DatabaseManager(tmp_path / "data" / "clinic.db")
    database.initialize()
    with database.transaction() as connection:
        connection.execute(
            "INSERT INTO patients(code,full_name,birth_date,sex) VALUES(?,?,?,?)",
            ("BN-001", "Nguyễn Văn An", "1990-01-01", "male"),
        )
    backup = database.create_backup(tmp_path / "saved.db")
    with database.transaction() as connection:
        connection.execute("DELETE FROM patients WHERE code='BN-001'")
    set_current_user(admin_session())
    safety, metadata = database.restore_backup(backup)
    with database.transaction() as connection:
        assert connection.execute("SELECT full_name FROM patients").fetchone()[0] == "Nguyễn Văn An"
        assert connection.execute("SELECT COUNT(*) FROM audit_log WHERE action='restore'").fetchone()[0] == 1
    assert safety.exists()
    assert metadata["patient_count"] == 1
    set_current_user(None)


def test_restore_rejects_non_admin_and_invalid_database(tmp_path):
    database = DatabaseManager(tmp_path / "clinic.db")
    database.initialize()
    source = database.create_backup(tmp_path / "saved.db")
    set_current_user(UserSession(2, "doctor", "Bác sĩ", "doctor", 2))
    with pytest.raises(PermissionError):
        database.restore_backup(source)
    invalid = tmp_path / "invalid.db"
    sqlite3.connect(invalid).close()
    with pytest.raises(RuntimeError):
        database.validate_backup(invalid)
    set_current_user(None)
