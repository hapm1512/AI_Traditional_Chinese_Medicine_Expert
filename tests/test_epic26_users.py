from pathlib import Path

import pytest

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.user_repository import UserRepository
from tcm_expert.security import set_current_user


@pytest.fixture
def users(tmp_path: Path):
    database = DatabaseManager(tmp_path / "users.db")
    database.initialize()
    repository = UserRepository(database)
    assert repository.ensure_bootstrap_admin()
    return database, repository


def test_bootstrap_login_and_change_password(users):
    _database, repository = users
    session = repository.authenticate("admin", "Admin@123")
    assert session.role == "admin"
    repository.change_password(session.user_id, "Secure123")
    repository.logout(session)
    assert repository.authenticate("admin", "Secure123").username == "admin"


def test_create_roles_and_audit_actor(users):
    database, repository = users
    admin = repository.authenticate("admin", "Admin@123")
    set_current_user(admin)
    try:
        user_id = repository.save("doctor01", "Bác sĩ Một", "doctor", "Doctor123")
        doctor = repository.authenticate("doctor01", "Doctor123")
        assert doctor.role == "doctor"
        with database.transaction() as connection:
            row = connection.execute(
                "SELECT actor_username FROM audit_log WHERE entity_type='app_user' AND entity_id=?",
                (user_id,),
            ).fetchone()
        assert row[0] == "admin"
    finally:
        set_current_user(None)


def test_cannot_disable_last_admin(users):
    _database, repository = users
    admin = repository.authenticate("admin", "Admin@123")
    with pytest.raises(ValueError, match="cuối cùng"):
        repository.set_active(admin.user_id, False)


def test_wrong_password_rejected(users):
    _database, repository = users
    with pytest.raises(ValueError, match="không đúng"):
        repository.authenticate("admin", "wrong")


def test_delete_departed_user_preserves_audit(users):
    database, repository = users
    admin = repository.authenticate("admin", "Admin@123")
    set_current_user(admin)
    try:
        user_id = repository.save("nurse01", "Y tá Một", "nurse", "Nurse123")
        repository.delete(user_id)
        assert all(row["id"] != user_id for row in repository.list_users())
        with database.transaction() as connection:
            row = connection.execute(
                "SELECT detail FROM audit_log WHERE action='delete' AND entity_type='app_user'"
            ).fetchone()
        assert "nurse01" in row[0]
    finally:
        set_current_user(None)
