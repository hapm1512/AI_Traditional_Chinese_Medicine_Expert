from datetime import datetime

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QFrame,
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
from tcm_expert.ui.formula_page import FormulaPage
from tcm_expert.ui.followup_page import FollowupPage
from tcm_expert.ui.materia_medica_page import MateriaMedicaPage
from tcm_expert.ui.outcome_report_page import OutcomeReportPage
from tcm_expert.ui.patient_page import PatientPage
from tcm_expert.ui.prescription_page import PrescriptionPage
from tcm_expert.ui.settings_page import SettingsPage
from tcm_expert.ui.tongue_page import TonguePage


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
    ):
        super().__init__()
        self.setWindowTitle("AI Traditional Chinese Medicine Expert")
        self.resize(1180, 720)
        self.setMinimumSize(960, 600)
        self.appointment_repository = FollowupAppointmentRepository(database)
        self.settings_repository = SettingsRepository(database)
        self.appointment_alert_dialog: AppointmentAlertDialog | None = None

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._dashboard(clinic_name, database_counts or {}))
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
        layout.addWidget(self._sidebar())
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        self.appointment_alert_timer = QTimer(self)
        self.appointment_alert_timer.setInterval(30_000)
        self.appointment_alert_timer.timeout.connect(self.check_appointment_alerts)
        self.appointment_alert_timer.start()
        QTimer.singleShot(1_500, self.check_appointment_alerts)

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
            )
        ):
            button = QPushButton(text)
            page_index = index
            button.setCheckable(True)
            self.menu_group.addButton(button, index)
            button.clicked.connect(
                lambda _checked=False, page=page_index: self.pages.setCurrentIndex(page)
            )
            if index == 0:
                button.setChecked(True)
            layout.addWidget(button)
        layout.addStretch()
        layout.addWidget(QLabel(f"Phiên bản {__display_version__}"))
        return side

    def _dashboard(self, clinic_name: str, database_counts: dict[str, int]) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 30, 36, 30)
        title = QLabel(clinic_name)
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Hệ thống hỗ trợ chuyên môn Y học cổ truyền")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(24)
        warning = QLabel("⚠ Kết quả chỉ tham khảo. Bác sĩ phải phê duyệt điều trị.")
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        layout.addSpacing(24)
        layout.addWidget(
            self._card(
                "Nền tảng dữ liệu sẵn sàng",
                "SQLite đã kết nối • Dữ liệu bệnh nhân lưu cục bộ",
            )
        )
        summary = (
            f"{database_counts.get('materia_medica', 0)} dược liệu • "
            f"{database_counts.get('formulas', 0)} phương thuốc • "
            f"{database_counts.get('tcm_syndromes', 0)} hội chứng mẫu"
        )
        layout.addWidget(self._card("Danh mục tham chiếu", summary))
        layout.addStretch()
        footer = QLabel("Copyright Hai Pham • Clinical Decision Support")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer.setObjectName("subtitle")
        layout.addWidget(footer)
        return content

    @staticmethod
    def _card(title: str, body: str) -> QFrame:
        card = QFrame(objectName="card")
        card.setMinimumHeight(110)
        layout = QVBoxLayout(card)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 18px; font-weight: 600; color: #e4c982;")
        layout.addWidget(heading)
        layout.addWidget(QLabel(body))
        return card
