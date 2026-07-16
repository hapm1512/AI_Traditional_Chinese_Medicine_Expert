from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QFormLayout,
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
        self.scheduled_at = QDateTimeEdit(QDateTime.currentDateTime().addDays(7))
        self.scheduled_at.setCalendarPopup(True)
        self.scheduled_at.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.reason = QTextEdit()
        self.reason.setMaximumHeight(52)
        self.note = QTextEdit()
        self.note.setMaximumHeight(52)
        form.addRow("Ngày giờ hẹn", self.scheduled_at)
        form.addRow("Lý do tái khám", self.reason)
        form.addRow("Ghi chú chuẩn bị", self.note)
        layout.addLayout(form)

        actions = QHBoxLayout()
        create = QPushButton("Tạo lịch hẹn")
        create.clicked.connect(self.create_appointment)
        self.status = QComboBox()
        for text, value in self.STATUS_ITEMS:
            self.status.addItem(text, value)
        update = QPushButton("Cập nhật trạng thái")
        update.clicked.connect(self.update_status)
        self.filter = QComboBox()
        self.filter.addItem("Tất cả trạng thái", None)
        for text, value in self.STATUS_ITEMS:
            self.filter.addItem(text, value)
        self.filter.currentIndexChanged.connect(self.refresh_table)
        actions.addWidget(create)
        actions.addStretch()
        actions.addWidget(QLabel("Trạng thái"))
        actions.addWidget(self.status)
        actions.addWidget(update)
        actions.addWidget(QLabel("Lọc"))
        actions.addWidget(self.filter)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            (
                "Ngày giờ",
                "Mã BN",
                "Bệnh nhân",
                "Lần khám",
                "Lý do",
                "Trạng thái",
                "Phụ trách",
            )
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
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
        try:
            self.appointments.create(
                int(consultation_id),
                scheduled_at=self.scheduled_at.dateTime().toString("yyyy-MM-ddTHH:mm"),
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

    def refresh_table(self) -> None:
        rows = self.appointments.list(status=self.filter.currentData())
        labels = {value: text for text, value in self.STATUS_ITEMS}
        self.row_ids = [int(row["id"]) for row in rows]
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            try:
                shown_time = datetime.fromisoformat(row["scheduled_at"]).strftime("%d/%m/%Y %H:%M")
            except ValueError:
                shown_time = row["scheduled_at"]
            values = (
                shown_time,
                row["patient_code"],
                row["full_name"],
                row["visit_code"],
                row["reason"],
                labels.get(row["status"], row["status"]),
                row["responsible_by"],
            )
            for column, value in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(str(value)))
