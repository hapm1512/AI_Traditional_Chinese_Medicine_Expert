import csv

import pytest

from tcm_expert.database.audit_repository import AuditRepository
from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.user_repository import UserRepository
from tcm_expert.security import UserSession, set_current_user


def test_admin_filters_and_exports_immutable_audit(tmp_path):
    database = DatabaseManager(tmp_path / "audit.db")
    database.initialize()
    users = UserRepository(database)
    users.ensure_bootstrap_admin()
    session = users.authenticate("admin", "Admin@123")
    repository = AuditRepository(database)
    entries = repository.list_entries(actor="admin", action="login")
    assert len(entries) == 1
    assert entries[0]["entity_type"] == "user_session"
    destination = tmp_path / "audit.csv"
    assert repository.export_csv(destination, actor="admin", action="login") == 1
    with destination.open(encoding="utf-8-sig") as stream:
        assert list(csv.reader(stream))[1][1:3] == ["admin", "login"]
    users.logout(session, "test")
    set_current_user(None)


def test_non_admin_cannot_read_or_export_audit(tmp_path):
    database = DatabaseManager(tmp_path / "audit.db")
    database.initialize()
    set_current_user(UserSession(7, "doctor", "Bác sĩ", "doctor", 1))
    repository = AuditRepository(database)
    with pytest.raises(PermissionError):
        repository.list_entries()
    with pytest.raises(PermissionError):
        repository.export_csv(tmp_path / "forbidden.csv")
    set_current_user(None)
