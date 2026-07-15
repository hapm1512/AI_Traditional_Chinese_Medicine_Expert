from datetime import datetime

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database import ConsultationRepository, PatientRepository
from tcm_expert.database.manager import DatabaseManager


class PatientDialog(QDialog):
    SEXES = (("", "Chưa xác định"), ("male", "Nam"), ("female", "Nữ"), ("other", "Khác"))

    def __init__(self, parent: QWidget, patient: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Thông tin bệnh nhân")
        self.setMinimumWidth(520)
        values = patient or {}
        form = QFormLayout(self)
        self.code = QLineEdit(str(values.get("code", "")))
        self.name = QLineEdit(str(values.get("full_name", "")))
        self.birth = QDateEdit(calendarPopup=True)
        self.birth.setDisplayFormat("yyyy-MM-dd")
        self.birth.setSpecialValueText("Chưa nhập")
        self.birth.setMinimumDate(QDate(1900, 1, 1))
        date = QDate.fromString(str(values.get("birth_date") or ""), "yyyy-MM-dd")
        self.birth.setDate(date if date.isValid() else self.birth.minimumDate())
        self.sex = QComboBox()
        for key, text in self.SEXES:
            self.sex.addItem(text, key)
        self.sex.setCurrentIndex(max(0, self.sex.findData(values.get("sex", ""))))
        self.phone = QLineEdit(str(values.get("phone", "")))
        self.identity = QLineEdit(str(values.get("identity_number", "")))
        self.address = QLineEdit(str(values.get("address", "")))
        self.emergency = QLineEdit(str(values.get("emergency_contact", "")))
        self.allergies = QTextEdit(str(values.get("allergies", "")))
        self.notes = QTextEdit(str(values.get("notes", "")))
        self.allergies.setMaximumHeight(70)
        self.notes.setMaximumHeight(70)
        for label, field in (
            ("Mã bệnh nhân *", self.code),
            ("Họ tên *", self.name),
            ("Ngày sinh", self.birth),
            ("Giới tính", self.sex),
            ("Điện thoại", self.phone),
            ("CCCD", self.identity),
            ("Địa chỉ", self.address),
            ("Liên hệ khẩn cấp", self.emergency),
            ("Dị ứng", self.allergies),
            ("Ghi chú", self.notes),
        ):
            form.addRow(label, field)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> dict[str, str]:
        birth_date = (
            ""
            if self.birth.date() == self.birth.minimumDate()
            else self.birth.date().toString("yyyy-MM-dd")
        )
        return {
            "code": self.code.text(),
            "full_name": self.name.text(),
            "birth_date": birth_date,
            "sex": self.sex.currentData(),
            "phone": self.phone.text(),
            "identity_number": self.identity.text(),
            "address": self.address.text(),
            "emergency_contact": self.emergency.text(),
            "allergies": self.allergies.toPlainText(),
            "notes": self.notes.toPlainText(),
        }


class ConsultationDialog(QDialog):
    def __init__(self, parent: QWidget, consultation: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Hồ sơ khám")
        self.setMinimumWidth(540)
        values = consultation or {}
        form = QFormLayout(self)
        self.code = QLineEdit(str(values.get("visit_code") or self._new_code()))
        self.status = QComboBox()
        for key, text in (
            ("draft", "Bản nháp"),
            ("in_review", "Đang duyệt"),
            ("approved", "Đã duyệt"),
            ("closed", "Đã đóng"),
        ):
            self.status.addItem(text, key)
        self.status.setCurrentIndex(max(0, self.status.findData(values.get("status", "draft"))))
        self.complaint = QTextEdit(str(values.get("chief_complaint", "")))
        self.symptoms = QTextEdit(str(values.get("symptoms", "")))
        self.history = QTextEdit(str(values.get("western_history", "")))
        self.doctor = QLineEdit(str(values.get("doctor_name", "")))
        for edit in (self.complaint, self.symptoms, self.history):
            edit.setMaximumHeight(80)
        for label, field in (
            ("Mã lần khám *", self.code),
            ("Trạng thái", self.status),
            ("Lý do khám", self.complaint),
            ("Triệu chứng", self.symptoms),
            ("Tiền sử Tây y", self.history),
            ("Bác sĩ", self.doctor),
        ):
            form.addRow(label, field)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    @staticmethod
    def _new_code() -> str:
        return datetime.now().strftime("K-%Y%m%d-%H%M%S")

    def values(self) -> dict[str, str]:
        return {
            "visit_code": self.code.text(),
            "status": self.status.currentData(),
            "chief_complaint": self.complaint.toPlainText(),
            "symptoms": self.symptoms.toPlainText(),
            "western_history": self.history.toPlainText(),
            "doctor_name": self.doctor.text(),
        }


class PatientPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.patient_id: int | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        heading = QLabel("Quản lý bệnh nhân")
        heading.setObjectName("title")
        layout.addWidget(heading)
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm mã, họ tên, điện thoại...")
        self.search.textChanged.connect(self.refresh_patients)
        toolbar.addWidget(self.search, 1)
        for text, slot in (
            ("Thêm bệnh nhân", self.add_patient),
            ("Sửa", self.edit_patient),
            ("Xóa", self.delete_patient),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            toolbar.addWidget(button)
        layout.addLayout(toolbar)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.patient_table = QTableWidget(0, 5)
        self.patient_table.setHorizontalHeaderLabels(
            ("Mã", "Họ tên", "Ngày sinh", "Giới tính", "Điện thoại")
        )
        self.patient_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.patient_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.patient_table.setAlternatingRowColors(True)
        self.patient_table.itemSelectionChanged.connect(self.patient_selected)
        self.patient_table.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self.patient_table)
        visits = QGroupBox("Lịch sử khám bệnh")
        visit_layout = QVBoxLayout(visits)
        visit_toolbar = QHBoxLayout()
        self.patient_label = QLabel("Chọn bệnh nhân")
        visit_toolbar.addWidget(self.patient_label, 1)
        for text, slot in (
            ("Thêm lần khám", self.add_consultation),
            ("Sửa hồ sơ", self.edit_consultation),
            ("Xóa hồ sơ", self.delete_consultation),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            visit_toolbar.addWidget(button)
        visit_layout.addLayout(visit_toolbar)
        self.visit_table = QTableWidget(0, 5)
        self.visit_table.setHorizontalHeaderLabels(
            ("Mã khám", "Ngày", "Trạng thái", "Lý do khám", "Bác sĩ")
        )
        self.visit_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.visit_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.visit_table.horizontalHeader().setStretchLastSection(True)
        visit_layout.addWidget(self.visit_table)
        splitter.addWidget(visits)
        layout.addWidget(splitter, 1)
        self.refresh_patients()

    def refresh_patients(self) -> None:
        rows = self.patients.list(self.search.text())
        self.patient_table.setRowCount(len(rows))
        sex = {"male": "Nam", "female": "Nữ", "other": "Khác", "unknown": "Chưa rõ"}
        for row, patient in enumerate(rows):
            values = (
                patient["code"],
                patient["full_name"],
                patient.get("birth_date") or "",
                sex.get(patient.get("sex", ""), ""),
                patient.get("phone") or "",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, patient["id"])
                self.patient_table.setItem(row, column, item)

    def patient_selected(self) -> None:
        selected = self.patient_table.selectedItems()
        self.patient_id = int(selected[0].data(Qt.ItemDataRole.UserRole)) if selected else None
        self.refresh_consultations()

    def refresh_consultations(self) -> None:
        if self.patient_id is None:
            self.patient_label.setText("Chọn bệnh nhân")
            self.visit_table.setRowCount(0)
            return
        patient = self.patients.get(self.patient_id)
        self.patient_label.setText(f"{patient['code']} • {patient['full_name']}")
        rows = self.consultations.list_for_patient(self.patient_id)
        self.visit_table.setRowCount(len(rows))
        status = {
            "draft": "Bản nháp",
            "in_review": "Đang duyệt",
            "approved": "Đã duyệt",
            "closed": "Đã đóng",
        }
        for row, visit in enumerate(rows):
            values = (
                visit["visit_code"],
                visit["created_at"],
                status.get(visit["status"], visit["status"]),
                visit.get("chief_complaint") or "",
                visit.get("doctor_name") or "",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, visit["id"])
                self.visit_table.setItem(row, column, item)

    def _selected_visit_id(self) -> int | None:
        items = self.visit_table.selectedItems()
        return int(items[0].data(Qt.ItemDataRole.UserRole)) if items else None

    def _error(self, error: Exception) -> None:
        QMessageBox.warning(self, "Không thể lưu", str(error))

    def add_patient(self) -> None:
        dialog = PatientDialog(self)
        if dialog.exec():
            try:
                self.patients.create(dialog.values())
                self.refresh_patients()
            except Exception as error:
                self._error(error)

    def edit_patient(self) -> None:
        if self.patient_id is None:
            return
        dialog = PatientDialog(self, self.patients.get(self.patient_id))
        if dialog.exec():
            try:
                self.patients.update(self.patient_id, dialog.values())
                self.refresh_patients()
            except Exception as error:
                self._error(error)

    def delete_patient(self) -> None:
        if self.patient_id is None:
            return
        answer = QMessageBox.question(self, "Xác nhận", "Ẩn bệnh nhân này khỏi danh sách?")
        if answer == QMessageBox.StandardButton.Yes:
            self.patients.delete(self.patient_id)
            self.patient_id = None
            self.refresh_patients()
            self.refresh_consultations()

    def add_consultation(self) -> None:
        if self.patient_id is None:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn bệnh nhân trước.")
            return
        dialog = ConsultationDialog(self)
        if dialog.exec():
            try:
                values = dialog.values()
                code = values.pop("visit_code")
                self.consultations.create(self.patient_id, code, **values)
                self.refresh_consultations()
            except Exception as error:
                self._error(error)

    def edit_consultation(self) -> None:
        visit_id = self._selected_visit_id()
        if visit_id is None:
            return
        dialog = ConsultationDialog(self, self.consultations.get(visit_id))
        if dialog.exec():
            try:
                self.consultations.update(visit_id, dialog.values())
                self.refresh_consultations()
            except Exception as error:
                self._error(error)

    def delete_consultation(self) -> None:
        visit_id = self._selected_visit_id()
        if visit_id is None:
            return
        answer = QMessageBox.question(self, "Xác nhận", "Xóa hồ sơ khám này?")
        if answer == QMessageBox.StandardButton.Yes:
            self.consultations.delete(visit_id)
            self.refresh_consultations()
