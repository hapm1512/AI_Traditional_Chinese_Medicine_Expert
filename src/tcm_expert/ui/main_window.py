from datetime import datetime

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from tcm_expert import __display_version__
from tcm_expert.database import FollowupAppointmentRepository, SettingsRepository
from tcm_expert.database.manager import DatabaseManager
from tcm_expert.ui.audio_page import AudioPage
from tcm_expert.ui.appointment_page import AppointmentPage
from tcm_expert.ui.clinical_support_page import ClinicalSupportPage
from tcm_expert.ui.diagnosis_page import DiagnosisPage
from tcm_expert.ui.dashboard_page import DashboardPage
from tcm_expert.ui.formula_page import FormulaPage
from tcm_expert.ui.followup_page import FollowupPage
from tcm_expert.ui.materia_medica_page import MateriaMedicaPage
from tcm_expert.ui.outcome_report_page import OutcomeReportPage
from tcm_expert.ui.patient_page import PatientPage
from tcm_expert.ui.prescription_page import PrescriptionPage
from tcm_expert.ui.settings_page import SettingsPage
from tcm_expert.ui.tongue_page import TonguePage
from tcm_expert.database.user_repository import UserRepository
from tcm_expert.security import UserSession, set_current_user
from tcm_expert.ui.login_dialog import ChangePasswordDialog, LoginDialog
from tcm_expert.ui.user_management_page import UserManagementPage
from tcm_expert.ui.audit_log_page import AuditLogPage
from tcm_expert.ui.backup_page import BackupPage


class AppointmentAlertDialog(QDialog):
    dismissed = Signal(list)

    def __init__(self, alerts: list[dict], parent=None):
        super().__init__(parent)
        self.alert_ids = [int(row["alert_id"]) for row in alerts]
        self.setWindowTitle("Cảnh báo lịch tái khám")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        self.heading = QLabel("🔔 ĐẾN GIỜ HẸN TÁI KHÁM")
        self.heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heading.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: #ffffff; "
            "background: #c62828; padding: 12px; border-radius: 6px;"
        )
        layout.addWidget(self.heading)
        lines = []
        for row in alerts:
            try:
                scheduled = datetime.fromisoformat(row["scheduled_at"]).strftime(
                    "%d/%m/%Y %H:%M"
                )
            except ValueError:
                scheduled = row["scheduled_at"]
            lines.append(
                f"{scheduled} — {row['patient_code']} — {row['full_name']}"
            )
        details = QLabel("\n".join(lines))
        details.setWordWrap(True)
        layout.addWidget(details)
        self.close_button = QPushButton("Đã xem — Tắt cảnh báo")
        self.close_button.clicked.connect(self.dismiss_alert)
        layout.addWidget(self.close_button)
        self.was_dismissed = False
        self.blink_on = True
        self.blink_timer = QTimer(self)
        self.blink_timer.setInterval(500)
        self.blink_timer.timeout.connect(self.toggle_blink)
        self.blink_timer.start()
        QApplication.beep()

    def dismiss_alert(self) -> None:
        if self.was_dismissed:
            return
        self.was_dismissed = True
        self.blink_timer.stop()
        alert_ids = list(self.alert_ids)
        self.hide()
        QTimer.singleShot(0, lambda: self.dismissed.emit(alert_ids))
        self.done(QDialog.DialogCode.Accepted)

    def closeEvent(self, event) -> None:
        if not self.was_dismissed:
            self.was_dismissed = True
            self.blink_timer.stop()
            alert_ids = list(self.alert_ids)
            QTimer.singleShot(0, lambda: self.dismissed.emit(alert_ids))
        super().closeEvent(event)

    def toggle_blink(self) -> None:
        self.blink_on = not self.blink_on
        color = "#c62828" if self.blink_on else "#ef6c00"
        self.heading.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: #ffffff; "
            f"background: {color}; padding: 12px; border-radius: 6px;"
        )


class MainWindow(QMainWindow):
    def __init__(
        self,
        clinic_name: str,
        database: DatabaseManager,
        database_counts: dict[str, int] | None = None,
        session: UserSession | None = None,
    ):
        super().__init__()
        self.setWindowTitle("AI Traditional Chinese Medicine Expert")
        self.resize(1180, 720)
        self.setMinimumSize(960, 600)
        if session is None:
            raise ValueError("Phiên đăng nhập không hợp lệ.")
        self.database = database
        self.session = session
        self.users = UserRepository(database)
        self.last_activity = datetime.now()
        self.appointment_repository = FollowupAppointmentRepository(database)
        self.settings_repository = SettingsRepository(database)
        self.appointment_alert_dialog: AppointmentAlertDialog | None = None

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.pages = QStackedWidget()
        self.dashboard_page = DashboardPage(clinic_name, database)
        self.dashboard_page.navigate.connect(self.open_page)
        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(PatientPage(database))
        self.pages.addWidget(DiagnosisPage(database))
        self.pages.addWidget(TonguePage(database))
        self.pages.addWidget(AudioPage(database))
        self.pages.addWidget(MateriaMedicaPage(database))
        self.pages.addWidget(FormulaPage(database))
        self.pages.addWidget(PrescriptionPage(database))
        self.pages.addWidget(ClinicalSupportPage(database))
        self.pages.addWidget(FollowupPage(database))
        self.pages.addWidget(AppointmentPage(database))
        self.pages.addWidget(OutcomeReportPage(database))
        self.pages.addWidget(SettingsPage(database))
        self.pages.addWidget(UserManagementPage(database))
        self.pages.addWidget(AuditLogPage(database))
        self.backup_page = BackupPage(database)
        self.backup_page.restored.connect(self.close)
        self.pages.addWidget(self.backup_page)
        layout.addWidget(self._sidebar())
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        self.appointment_alert_timer = QTimer(self)
        self.appointment_alert_timer.setInterval(30_000)
        self.appointment_alert_timer.timeout.connect(self.check_appointment_alerts)
        self.appointment_alert_timer.start()
        QTimer.singleShot(1_500, self.check_appointment_alerts)
        self.session_timer = QTimer(self)
        self.session_timer.setInterval(30_000)
        self.session_timer.timeout.connect(self.check_session_timeout)
        self.session_timer.start()
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() in {
            QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress,
            QEvent.Type.Wheel, QEvent.Type.TouchBegin,
        }:
            self.last_activity = datetime.now()
        return super().eventFilter(watched, event)

    def check_session_timeout(self) -> None:
        # Tác vụ dịch nền hợp lệ giữ phiên hoạt động xuyên đêm.
        for index in range(self.pages.count()):
            page = self.pages.widget(index)
            checker = getattr(page, "has_active_background_task", None)
            if callable(checker) and checker():
                self.last_activity = datetime.now()
                return
        if (datetime.now() - self.last_activity).total_seconds() >= 15 * 60:
            self.lock_session()

    def lock_session(self) -> None:
        self.session_timer.stop()
        self.users.logout(self.session, "inactive_lock")
        self.hide()
        login = LoginDialog(self.users, parent=self)
        if login.exec() != QDialog.DialogCode.Accepted or login.session is None:
            self.close()
            return
        self.session = login.session
        set_current_user(self.session)
        self.last_activity = datetime.now()
        self.apply_permissions()
        self.show()
        self.session_timer.start()

    def check_appointment_alerts(self) -> None:
        self.appointment_repository.expire_after_90_days()
        if self.appointment_alert_dialog and self.appointment_alert_dialog.isVisible():
            return
        alerts = self.appointment_repository.pending_due_alerts()
        if not alerts:
            return
        dialog = AppointmentAlertDialog(alerts, self)
        dialog.dismissed.connect(self.acknowledge_appointment_alerts)
        self.appointment_alert_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def acknowledge_appointment_alerts(self, alert_ids: list[int]) -> None:
        try:
            self.appointment_repository.acknowledge_alerts(
                alert_ids,
                acknowledged_by=self.settings_repository.doctor_name(),
            )
        except Exception:
            pass
        finally:
            self.appointment_alert_dialog = None

    def closeEvent(self, event) -> None:
        self.appointment_alert_timer.stop()
        dialog = self.appointment_alert_dialog
        if dialog is not None:
            dialog.was_dismissed = True
            dialog.blink_timer.stop()
            dialog.close()
            self.appointment_alert_dialog = None
        self.session_timer.stop()
        self.users.logout(self.session, "application_closed")
        set_current_user(None)
        super().closeEvent(event)

    def _sidebar(self) -> QWidget:
        side = QWidget(objectName="sidebar")
        side.setFixedWidth(240)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(18, 24, 18, 24)
        logo = QLabel("ĐÔNG Y AI")
        logo.setObjectName("title")
        layout.addWidget(logo)
        layout.addSpacing(24)
        self.menu_group = QButtonGroup(self)
        self.menu_group.setExclusive(True)
        for index, text in enumerate(
            (
                "Tổng quan",
                "Quản lý bệnh nhân",
                "Hỗ trợ chẩn đoán",
                "AI phân tích lưỡi",
                "AI phân tích âm thanh",
                "Tra cứu dược",
                "Bài thuốc tham khảo",
                "Đơn thuốc bác sĩ",
                "Hỗ trợ quyết định",
                "Theo dõi điều trị",
                "Lịch hẹn tái khám",
                "Báo cáo kết quả",
                "Cài đặt",
                "Quản lý người dùng",
                "Nhật ký hệ thống",
                "Sao lưu và phục hồi",
            )
        ):
            button = QPushButton(text)
            page_index = index
            button.setCheckable(True)
            self.menu_group.addButton(button, index)
            button.clicked.connect(
                lambda _checked=False, page=page_index: self.open_page(page)
            )
            if index == 0:
                button.setChecked(True)
            layout.addWidget(button)
        layout.addStretch()
        user_label = QLabel(f"{self.session.full_name}\n{self.role_label(self.session.role)}")
        user_label.setWordWrap(True)
        layout.addWidget(user_label)
        change_password = QPushButton("Đổi mật khẩu")
        change_password.clicked.connect(self.change_password)
        layout.addWidget(change_password)
        lock = QPushButton("Khóa phiên")
        lock.clicked.connect(self.lock_session)
        layout.addWidget(lock)
        layout.addWidget(QLabel(f"Phiên bản {__display_version__}"))
        QTimer.singleShot(0, self.apply_permissions)
        return side

    @staticmethod
    def role_label(role: str) -> str:
        return {"admin": "Quản trị", "doctor": "Bác sĩ", "nurse": "Y tá"}.get(role, role)

    def change_password(self) -> None:
        ChangePasswordDialog(self.users, self.session.user_id, parent=self).exec()

    def apply_permissions(self) -> None:
        allowed = {
            "admin": set(range(16)),
            "doctor": set(range(13)),
            "nurse": {0, 1, 2, 3, 4, 9, 10},
        }[self.session.role]
        for index in range(self.pages.count()):
            button = self.menu_group.button(index)
            if button is not None:
                button.setVisible(index in allowed)
        if self.pages.currentIndex() not in allowed:
            self.open_page(0)

    def open_page(self, page: int) -> None:
        allowed = {
            "admin": set(range(16)),
            "doctor": set(range(13)),
            "nurse": {0, 1, 2, 3, 4, 9, 10},
        }[self.session.role]
        if page not in allowed:
            return
        self.pages.setCurrentIndex(page)
        button = self.menu_group.button(page)
        if button is not None:
            button.setChecked(True)
