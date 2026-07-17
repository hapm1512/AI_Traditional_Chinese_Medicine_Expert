from tcm_expert.database import DatabaseManager
from tcm_expert.database.user_repository import UserRepository


def test_default_admin_is_restored_when_last_admin_was_demoted(tmp_path):
    database = DatabaseManager(tmp_path / "admin_recovery.db")
    database.initialize()
    users = UserRepository(database)
    users.ensure_bootstrap_admin()
    with database.transaction() as connection:
        connection.execute("UPDATE app_users SET role='doctor' WHERE username='admin'")

    users.ensure_bootstrap_admin()
    session = users.authenticate("admin", "Admin@123")

    assert session.role == "admin"


def test_last_admin_cannot_be_demoted(tmp_path):
    database = DatabaseManager(tmp_path / "last_admin.db")
    database.initialize()
    users = UserRepository(database)
    users.ensure_bootstrap_admin()
    admin = users.authenticate("admin", "Admin@123")

    try:
        users.save("admin", "Quản trị", "doctor", "", admin.user_id, ("doctor",))
        raise AssertionError("Last admin demotion must fail")
    except ValueError as error:
        assert "quản trị viên cuối cùng" in str(error)
