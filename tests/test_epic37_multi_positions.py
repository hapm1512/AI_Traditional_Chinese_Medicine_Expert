from tcm_expert.database import DatabaseManager
from tcm_expert.database.user_repository import UserRepository
from tcm_expert.security import UserSession, require_role, set_current_user


def test_admin_can_be_assigned_doctor_position(tmp_path):
    database = DatabaseManager(tmp_path / "positions.db")
    database.initialize()
    users = UserRepository(database)
    users.ensure_bootstrap_admin()
    admin = users.authenticate("admin", "Admin@123")
    users.save("admin", "Quản trị", "admin", "", admin.user_id, ("doctor",))

    refreshed = users.authenticate("admin", "Admin@123")

    assert refreshed.role == "admin"
    assert refreshed.positions == ("doctor",)


def test_active_position_controls_professional_approval():
    admin_mode = UserSession(1, "admin", "Quản trị", "admin", 1, ("doctor",), "admin")
    set_current_user(admin_mode)
    try:
        try:
            require_role("doctor")
            raise AssertionError("Admin mode must not approve professionally")
        except PermissionError:
            pass

        doctor_mode = UserSession(1, "admin", "Quản trị", "admin", 1, ("doctor",), "doctor")
        set_current_user(doctor_mode)
        assert require_role("doctor").username == "admin"
        assert require_role("admin").username == "admin"
    finally:
        set_current_user(None)
