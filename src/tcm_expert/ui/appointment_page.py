from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database import (
    ConsultationRepository,
    FollowupAppointmentRepository,
    PatientRepository,
    SettingsRepository,
    ValidationError,
)
from tcm_expert.database.manager import DatabaseManager


class AppointmentPage(QWidget):
    STATUS_ITEMS = (
        ("Đã lên lịch", "scheduled"),
        ("Đã xác nhận", "confirmed"),
        ("Đã tái khám", "completed"),
        ("Đã hủy", "cancelled"),
        ("Không đến", "no_show"),
    )
    VIEW_ITEMS = (
        ("Tất cả lịch", None),
        ("Lịch hôm nay", "today"),
        ("Sắp đến trong 7 ngày", "upcoming"),
        ("Trễ xác nhận", "overdue_confirmation"),
        ("Chưa nhắc", "pending_reminder"),
        ("Đã nhắc", "reminded"),
        ("Lưu lịch sử 30 ngày", "history_reference"),
        ("Hủy sau 90 ngày", "cancelled_90"),
    )

    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.appointments = FollowupAppointmentRepository(database)
        self.settings = SettingsRepository(database)
        self.row_ids: list[int] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Lịch hẹn tái khám")
        title.setObjectName("title")
        layout.addWidget(title)
        warning = QLabel(
            "⚠ Lịch hẹn hỗ trợ vận hành, không thay thế chỉ định bác sĩ."
        )
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        selectors = QHBoxLayout()
        self.patient = QComboBox()
        self.patient.currentIndexChanged.connect(self.refresh_visits)
        self.visit = QComboBox()
        selectors.addWidget(QLabel("Bệnh nhân"))
        selectors.addWidget(self.patient, 1)
        selectors.addWidget(QLabel("Lần khám"))
        selectors.addWidget(self.visit, 1)
        layout.addLayout(selectors)

        form = QFormLayout()
        appointment_time = QHBoxLayout()
        self.appointment_date = QDateEdit(QDate.currentDate().addDays(7))
        self.appointment_date.setCalendarPopup(True)
        self.appointment_date.setDisplayFormat("dd/MM/yyyy")
        self.appointment_hour = QComboBox()
        self.appointment_hour.addItem("Giờ", None)
        for hour in range(24):
            value = f"{hour:02d}"
            self.appointment_hour.addItem(value, value)
        self.appointment_minute = QComboBox()
        self.appointment_minute.addItem("Phút", None)
        for minute in range(60):
            value = f"{minute:02d}"
            self.appointment_minute.addItem(value, value)
        self.appointment_hour.setMaximumWidth(80)
        self.appointment_minute.setMaximumWidth(80)
        appointment_time.addWidget(self.appointment_date, 1)
        appointment_time.addWidget(QLabel("Giờ hẹn"))
        appointment_time.addWidget(self.appointment_hour)
        appointment_time.addWidget(QLabel(":"))
        appointment_time.addWidget(self.appointment_minute)
        self.reason = QTextEdit()
        self.reason.setMaximumHeight(52)
        self.note = QTextEdit()
        self.note.setMaximumHeight(52)
        form.addRow("Ngày hẹn", appointment_time)
        form.addRow("Lý do tái khám", self.reason)
        form.addRow("Ghi chú chuẩn bị", self.note)
        self.overdue_note = QTextEdit()
        self.overdue_note.setMaximumHeight(52)
        form.addRow("Ghi chú xử lý quá hạn", self.overdue_note)
        layout.addLayout(form)

        actions = QHBoxLayout()
        create = QPushButton("Tạo lịch hẹn")
        create.clicked.connect(self.create_appointment)
        self.status = QComboBox()
        for text, value in self.STATUS_ITEMS:
            self.status.addItem(text, value)
        update = QPushButton("Cập nhật trạng thái")
        update.clicked.connect(self.update_status)
        remind = QPushButton("Đánh dấu đã nhắc")
        remind.clicked.connect(self.mark_reminded)
        dismiss_overdue = QPushButton("Xóa thông báo trễ")
        dismiss_overdue.clicked.connect(self.dismiss_overdue_notification)
        self.filter = QComboBox()
        self.filter.addItem("Tất cả trạng thái", None)
        for text, value in self.STATUS_ITEMS:
            self.filter.addItem(text, value)
        self.filter.currentIndexChanged.connect(self.refresh_table)
        self.view_filter = QComboBox()
        for text, value in self.VIEW_ITEMS:
            self.view_filter.addItem(text, value)
        self.view_filter.currentIndexChanged.connect(self.refresh_table)
        actions.addWidget(create)
        actions.addWidget(remind)
        actions.addWidget(dismiss_overdue)
        actions.addStretch()
        actions.addWidget(QLabel("Trạng thái"))
        actions.addWidget(self.status)
        actions.addWidget(update)
        actions.addWidget(QLabel("Lọc"))
        actions.addWidget(self.filter)
        actions.addWidget(QLabel("Nhắc lịch"))
        actions.addWidget(self.view_filter)
        layout.addLayout(actions)

        case_actions = QHBoxLayout()
        save_history = QPushButton("Lưu theo dõi 30 ngày")
        save_history.clicked.connect(
            lambda: self.review_case("history_reference")
        )
        reopen = QPushButton("Mở lại lịch tái khám")
        reopen.clicked.connect(lambda: self.review_case("reopened"))
        save_record = QPushButton("Lưu thành bệnh án")
        save_record.clicked.connect(lambda: self.review_case("medical_record"))
        case_actions.addWidget(save_history)
        case_actions.addWidget(reopen)
        case_actions.addWidget(save_record)
        case_actions.addStretch()
        layout.addLayout(case_actions)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            (
                "Ngày giờ",
                "Mã BN",
                "Bệnh nhân",
                "Lần khám",
                "Lý do",
                "Trạng thái",
                "Phụ trách",
                "Nhắc lịch",
                "Người nhắc",
                "Xử lý hồ sơ",
                "Ghi chú bác sĩ",
            )
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.setColumnWidth(0, 165)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.refresh_patients()
        self.refresh_table()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh_patients()
        self.refresh_table()

    def refresh_patients(self) -> None:
        selected = self.patient.currentData()
        self.patient.blockSignals(True)
        self.patient.clear()
        self.patient.addItem("Chọn bệnh nhân", None)
        for row in self.patients.list():
            self.patient.addItem(f"{row['code']} — {row['full_name']}", row["id"])
        index = self.patient.findData(selected)
        if self.patient.count() > 1:
            self.patient.setCurrentIndex(index if index >= 1 else 1)
        self.patient.blockSignals(False)
        self.refresh_visits()

    def refresh_visits(self) -> None:
        selected = self.visit.currentData()
        self.visit.clear()
        self.visit.addItem("Chọn lần khám", None)
        patient_id = self.patient.currentData()
        if patient_id:
            for row in reversed(self.consultations.list_for_patient(int(patient_id))):
                self.visit.addItem(f"{row['visit_code']} — {row['created_at']}", row["id"])
            index = self.visit.findData(selected)
            if self.visit.count() > 1:
                self.visit.setCurrentIndex(index if index >= 1 else 1)

    def create_appointment(self) -> None:
        consultation_id = self.visit.currentData()
        if consultation_id is None:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Hãy chọn lần khám.")
            return
        hour = self.appointment_hour.currentData()
        minute = self.appointment_minute.currentData()
        if hour is None or minute is None:
            QMessageBox.warning(
                self, "Thiếu giờ hẹn", "Hãy chọn đầy đủ giờ và phút."
            )
            self.appointment_hour.setFocus()
            return
        time_text = f"{hour}:{minute}"
        try:
            self.appointments.create(
                int(consultation_id),
                scheduled_at=(
                    f"{self.appointment_date.date().toString('yyyy-MM-dd')}T"
                    f"{time_text}"
                ),
                reason=self.reason.toPlainText(),
                note=self.note.toPlainText(),
                responsible_by=self.settings.doctor_name(),
            )
        except ValidationError as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))
            return
        self.reason.clear()
        self.note.clear()
        self.refresh_table()
        QMessageBox.information(self, "Đã lưu", "Đã tạo lịch hẹn tái khám.")

    def update_status(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.row_ids):
            QMessageBox.warning(self, "Chưa chọn", "Hãy chọn một lịch hẹn.")
            return
        try:
            self.appointments.change_status(
                self.row_ids[row],
                str(self.status.currentData()),
                self.settings.doctor_name(),
            )
        except ValidationError as error:
            QMessageBox.warning(self, "Không thể cập nhật", str(error))
            return
        self.refresh_table()
        QMessageBox.information(
            self, "Đã cập nhật", "Đã cập nhật trạng thái lịch hẹn."
        )

    def mark_reminded(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.row_ids):
            QMessageBox.warning(self, "Chưa chọn", "Hãy chọn một lịch hẹn.")
            return
        try:
            self.appointments.mark_reminded(
                self.row_ids[row], reminded_by=self.settings.doctor_name()
            )
        except ValidationError as error:
            QMessageBox.warning(self, "Không thể cập nhật", str(error))
            return
        self.refresh_table()
        QMessageBox.information(self, "Đã cập nhật", "Đã ghi nhận nhắc lịch.")

    def dismiss_overdue_notification(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.row_ids):
            QMessageBox.warning(self, "Chưa chọn", "Hãy chọn một thông báo trễ.")
            return
        answer = QMessageBox.question(
            self,
            "Xác nhận xóa",
            (
                "Chỉ xóa thông báo trễ quá 3 giờ.\n"
                "Lịch sử vẫn được giữ trong hệ thống.\n\n"
                "Bác sĩ xác nhận xóa thông báo này?"
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.appointments.dismiss_overdue_notification(
                self.row_ids[row],
                doctor_name=self.settings.doctor_name(required=True),
            )
        except ValidationError as error:
            QMessageBox.warning(self, "Không thể xóa", str(error))
            return
        self.refresh_table()
        QMessageBox.information(self, "Đã xóa", "Đã đóng thông báo trễ.")

    def review_case(self, action: str) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.row_ids):
            QMessageBox.warning(self, "Chưa chọn", "Hãy chọn một lịch hẹn.")
            return
        try:
            self.appointments.review_overdue(
                self.row_ids[row],
                action=action,
                note=self.overdue_note.toPlainText(),
                reviewed_by=self.settings.doctor_name(),
            )
        except ValidationError as error:
            QMessageBox.warning(self, "Không thể xử lý", str(error))
            return
        self.overdue_note.clear()
        self.refresh_table()
        QMessageBox.information(self, "Đã lưu", "Đã lưu xử lý hồ sơ tái khám.")

    def refresh_table(self) -> None:
        rows = self.appointments.list(
            status=self.filter.currentData(), view=self.view_filter.currentData()
        )
        labels = {value: text for text, value in self.STATUS_ITEMS}
        self.row_ids = [int(row["id"]) for row in rows]
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            try:
                shown_time = datetime.fromisoformat(row["scheduled_at"]).strftime("%d/%m/%Y %H:%M")
            except ValueError:
                shown_time = row["scheduled_at"]
            reminded_at = "Chưa nhắc"
            if row["reminded_at"]:
                try:
                    reminded_at = datetime.fromisoformat(row["reminded_at"]).strftime(
                        "%d/%m/%Y %H:%M"
                    )
                except ValueError:
                    reminded_at = row["reminded_at"]
            values = (
                shown_time,
                row["patient_code"],
                row["full_name"],
                row["visit_code"],
                row["reason"],
                labels.get(row["status"], row["status"]),
                row["responsible_by"],
                reminded_at,
                row["reminded_by"] or "",
                row["case_state"],
                row["overdue_note"],
            )
            for column, value in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(str(value)))
