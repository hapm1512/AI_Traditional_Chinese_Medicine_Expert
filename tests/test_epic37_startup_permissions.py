from PySide6.QtWidgets import QApplication

from tcm_expert.database import DatabaseManager
from tcm_expert.security import UserSession, set_current_user
from tcm_expert.ui.main_window import MainWindow
from tcm_expert.ui.backup_page import BackupPage


def _app():
    return QApplication.instance() or QApplication([])


def test_doctor_can_start_without_constructing_admin_pages(tmp_path):
    _app()
    database = DatabaseManager(tmp_path / "doctor.db")
    database.initialize()
    session = UserSession(2, "doctor", "Bác sĩ", "doctor", 1)

    window = MainWindow("Phòng khám", database, session=session)

    assert window.session.role == "doctor"
    assert window.pages.count() == 14
    window.session_timer.stop()
    window.appointment_alert_timer.stop()
    set_current_user(None)


def test_admin_keeps_all_admin_pages(tmp_path):
    _app()
    database = DatabaseManager(tmp_path / "admin.db")
    database.initialize()
    session = UserSession(1, "admin", "Quản trị", "admin", 1)

    window = MainWindow("Phòng khám", database, session=session)

    assert isinstance(window.backup_page, BackupPage)
    assert window.pages.count() == 14
    window.session_timer.stop()
    window.appointment_alert_timer.stop()
    set_current_user(None)
