from datetime import date, datetime

from PySide6.QtCore import QDate, QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database import ConsultationRepository, PatientRepository, SettingsRepository
from tcm_expert.database.manager import DatabaseManager


def parse_birth_date(value: str) -> str:
    """Convert the manual Vietnamese date format to SQLite ISO format."""
    text = value.replace("_", "").strip()
    if not text or not text.replace("/", "").strip():
        return ""
    try:
        parsed = datetime.strptime(text, "%d/%m/%Y").date()
    except ValueError as error:
        raise ValueError("Ngày sinh phải đúng định dạng dd/mm/yyyy.") from error
    if parsed > date.today():
        raise ValueError("Ngày sinh không được ở tương lai.")
    if parsed.year < 1900:
        raise ValueError("Năm sinh phải từ 1900 trở đi.")
    return parsed.isoformat()


class PatientDialog(QDialog):
    SEXES = (("", "Chưa xác định"), ("male", "Nam"), ("female", "Nữ"), ("other", "Khác"))

    def __init__(
        self,
        parent: QWidget,
        database: DatabaseManager,
        patient: dict | None = None,
        intake: dict | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Thông tin bệnh nhân")
        self.setMinimumWidth(520)
        values = patient or {}
        intake_values = intake or {}
        root = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        scroll.setWidget(content)
        root.addWidget(scroll)
        self.patients = PatientRepository(database)
        groups = SettingsRepository(database).groups(active_only=True)
        self.group = QComboBox()
        for group in groups:
            self.group.addItem(f"{group['name']} ({group['prefix']})", group["prefix"])
        existing_code = str(values.get("code", ""))
        existing_prefix = next(
            (str(group["prefix"]) for group in groups if existing_code.startswith(group["prefix"])),
            "",
        )
        if existing_prefix:
            self.group.setCurrentIndex(max(0, self.group.findData(existing_prefix)))
        self.number = QLineEdit(existing_code[len(existing_prefix) :] if existing_prefix else "")
        self.number.setMaxLength(3)
        self.number.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,3}")))
        self.group.currentIndexChanged.connect(self._suggest_number)
        if not patient:
            self._suggest_number()
        self.name = QLineEdit(str(values.get("full_name", "")))
        self.birth = QLineEdit()
        self.birth.setInputMask("00/00/0000;_")
        self.birth.setPlaceholderText("dd/mm/yyyy")
        saved_birth = QDate.fromString(str(values.get("birth_date") or ""), "yyyy-MM-dd")
        if saved_birth.isValid():
            self.birth.setText(saved_birth.toString("dd/MM/yyyy"))
        self.sex = QComboBox()
        for key, text in self.SEXES:
            self.sex.addItem(text, key)
        self.sex.setCurrentIndex(max(0, self.sex.findData(values.get("sex", ""))))
        self.phone = QLineEdit(str(values.get("phone", "")))
        self.phone.setMaxLength(10)
        self.phone.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,10}")))
        self.identity = QLineEdit(str(values.get("identity_number", "")))
        self.identity.setMaxLength(12)
        self.identity.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,12}")))
        self.address = QLineEdit(str(values.get("address", "")))
        self.emergency = QLineEdit(str(values.get("emergency_contact", "")))
        self.allergies = QTextEdit(str(values.get("allergies", "")))
        self.notes = QTextEdit(str(values.get("notes", "")))
        self.allergies.setMaximumHeight(70)
        self.notes.setMaximumHeight(70)
        self.complaint = QTextEdit(str(intake_values.get("chief_complaint", "")))
        self.symptoms = QTextEdit(str(intake_values.get("symptoms", "")))
        self.western_history = QTextEdit(str(intake_values.get("western_history", "")))
        for field in (self.complaint, self.symptoms, self.western_history):
            field.setMaximumHeight(70)
        for label, field in (
            ("Nhóm bệnh *", self.group),
            ("Số thứ tự *", self.number),
            ("Họ tên *", self.name),
            ("Ngày sinh", self.birth),
            ("Giới tính", self.sex),
            ("Điện thoại", self.phone),
            ("CCCD", self.identity),
            ("Địa chỉ", self.address),
            ("Liên hệ khẩn cấp", self.emergency),
            ("Dị ứng", self.allergies),
            ("Ghi chú", self.notes),
            ("Lý do đến khám", self.complaint),
            ("Tình trạng BN mô tả", self.symptoms),
            ("Bệnh sử, thuốc đang dùng", self.western_history),
        ):
            form.addRow(label, field)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        form.addRow(buttons)

    def _suggest_number(self) -> None:
        prefix = str(self.group.currentData() or "")
        if prefix:
            self.number.setText(self.patients.next_number(prefix))

    def values(self) -> dict[str, str]:
        birth_date = parse_birth_date(self.birth.text())
        return {
            "code": f"{self.group.currentData() or ''}{self.number.text()}",
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

    def accept(self) -> None:
        try:
            parse_birth_date(self.birth.text())
        except ValueError as error:
            QMessageBox.warning(self, "Ngày sinh không hợp lệ", str(error))
            self.birth.setFocus()
            self.birth.selectAll()
            return
        super().accept()

    def intake_values(self) -> dict[str, str]:
        return {
            "chief_complaint": self.complaint.toPlainText(),
            "symptoms": self.symptoms.toPlainText(),
            "western_history": self.western_history.toPlainText(),
        }


class ConsultationDialog(QDialog):
    def __init__(self, parent: QWidget, visit_code: str, consultation: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Hồ sơ khám")
        self.setMinimumWidth(540)
        values = consultation or {}
        self.workflow_status = str(values.get("status", "draft"))
        form = QFormLayout(self)
        self.code = QLineEdit(str(values.get("visit_code") or visit_code))
        self.code.setReadOnly(True)
        self.patient_status = QComboBox()
        for key, text in (
            ("under_treatment", "Đang điều trị"),
            ("monitoring", "Đang theo dõi"),
            ("completed", "Đã kết thúc điều trị"),
        ):
            self.patient_status.addItem(text, key)
        self.patient_status.setCurrentIndex(
            max(0, self.patient_status.findData(values.get("patient_status", "under_treatment")))
        )
        self.complaint = QTextEdit(str(values.get("chief_complaint", "")))
        self.symptoms = QTextEdit(str(values.get("symptoms", "")))
        self.history = QTextEdit(str(values.get("western_history", "")))
        self.doctor = QLineEdit(str(values.get("doctor_name", "")))
        for edit in (self.complaint, self.symptoms, self.history):
            edit.setMaximumHeight(80)
        for label, field in (
            ("Mã lần khám *", self.code),
            ("Tình trạng bệnh nhân", self.patient_status),
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
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        form.addRow(buttons)

    def values(self) -> dict[str, str]:
        return {
            "visit_code": self.code.text(),
            "status": self.workflow_status,
            "patient_status": self.patient_status.currentData(),
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
            ("Mã BN", "Họ tên", "Ngày sinh", "Giới tính", "Điện thoại")
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
            ("Mã lần khám", "Ngày", "Tình trạng", "Lý do khám", "Bác sĩ")
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
                self._display_date(patient.get("birth_date")),
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
            "under_treatment": "Đang điều trị",
            "monitoring": "Đang theo dõi",
            "completed": "Đã kết thúc điều trị",
        }
        total = len(rows)
        for row, visit in enumerate(rows):
            chronological_number = total - row
            visit_name = (
                "Lần đầu"
                if chronological_number == 1
                else f"Tái khám {chronological_number - 1}"
            )
            values = (
                f"{visit_name} • {visit['visit_code']}",
                visit["created_at"],
                status.get(visit["patient_status"], visit["patient_status"]),
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
        dialog = PatientDialog(self, self.patients.database)
        if dialog.exec():
            try:
                patient = self.patients.create(dialog.values())
                self.consultations.create(patient["id"], "", **dialog.intake_values())
                self.refresh_patients()
            except Exception as error:
                self._error(error)

    def edit_patient(self) -> None:
        if self.patient_id is None:
            return
        visits = self.consultations.list_for_patient(self.patient_id)
        current_visit = visits[0] if visits else None
        dialog = PatientDialog(
            self,
            self.patients.database,
            self.patients.get(self.patient_id),
            current_visit,
        )
        if dialog.exec():
            try:
                self.patients.update(self.patient_id, dialog.values())
                if current_visit:
                    self.consultations.update(current_visit["id"], dialog.intake_values())
                else:
                    self.consultations.create(
                        self.patient_id, "", **dialog.intake_values()
                    )
                self.refresh_patients()
                self.refresh_consultations()
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
        visit_code = self.consultations.next_visit_code(self.patient_id)
        dialog = ConsultationDialog(self, visit_code)
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
        current = self.consultations.get(visit_id)
        dialog = ConsultationDialog(self, current["visit_code"], current)
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

    @staticmethod
    def _display_date(value: str | None) -> str:
        date = QDate.fromString(str(value or ""), "yyyy-MM-dd")
        return date.toString("dd/MM/yyyy") if date.isValid() else ""
