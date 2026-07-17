import logging
import sys
from dataclasses import replace

from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QMessageBox

from tcm_expert.core.config import AppSettings
from tcm_expert.core.logging_config import configure_logging
from tcm_expert.core.paths import AppPaths
from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.settings_repository import SettingsRepository
from tcm_expert.ui.main_window import MainWindow
from tcm_expert.ui.settings_page import DoctorSetupDialog
from tcm_expert.ui.theme import DARK_THEME
from tcm_expert.database.user_repository import UserRepository
from tcm_expert.security import set_current_user
from tcm_expert.ui.login_dialog import ChangePasswordDialog, LoginDialog


def choose_work_position(session, parent=None):
    choices: list[tuple[str, str]] = []
    if session.role == "admin":
        choices.append(("Quản trị hệ thống", "admin"))
    labels = {"doctor": "Bác sĩ", "nurse": "Y tá"}
    choices.extend((labels[item], item) for item in session.positions if item in labels)
    if not choices:
        return session
    if len(choices) == 1:
        return replace(session, active_position=choices[0][1])
    names = [item[0] for item in choices]
    selected, accepted = QInputDialog.getItem(
        parent, "Chọn cương vị làm việc", "Đăng nhập với cương vị:", names, 0, False
    )
    if not accepted:
        return None
    return replace(session, active_position=choices[names.index(selected)][1])


def main() -> int:
    paths = AppPaths.discover()
    paths.ensure()
    configure_logging(paths.logs)
    app = QApplication(sys.argv)
    app.setApplicationName("AI Traditional Chinese Medicine Expert")
    app.setOrganizationName("Hai Pham")
    try:
        settings = AppSettings.load(paths.settings)
        database = DatabaseManager(paths.database)
        database.initialize()
        if not database.health_check():
            raise RuntimeError("Không thể kết nối cơ sở dữ liệu")
        app.setStyleSheet(DARK_THEME)
        users = UserRepository(database)
        bootstrap_created = users.ensure_bootstrap_admin()
        login = LoginDialog(users, bootstrap_created)
        if login.exec() != LoginDialog.DialogCode.Accepted or login.session is None:
            return 0
        session = choose_work_position(login.session)
        if session is None:
            users.logout(login.session, "position_selection_cancelled")
            return 0
        set_current_user(session)
        with database.transaction() as connection:
            must_change = bool(connection.execute(
                "SELECT must_change_password FROM app_users WHERE id=?", (session.user_id,)
            ).fetchone()[0])
        if must_change and ChangePasswordDialog(users, session.user_id, True).exec() != QDialog.DialogCode.Accepted:
            users.logout(session, "password_change_cancelled")
            return 0
        doctor = SettingsRepository(database).doctor()
        if settings.require_doctor_approval and (
            not doctor.get("full_name") or not doctor.get("license_number")
        ):
            if DoctorSetupDialog(database).exec() != DoctorSetupDialog.DialogCode.Accepted:
                return 0
        window = MainWindow(settings.clinic_name, database, database.reference_counts(), session)
        window.show()
        return app.exec()
    except Exception as error:  # GUI boundary logs unexpected failures.
        logging.exception("Application startup failed")
        QMessageBox.critical(None, "Lỗi khởi động", str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
