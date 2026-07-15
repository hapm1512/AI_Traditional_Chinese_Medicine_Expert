from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from tcm_expert.database import ConsultationRepository, PatientRepository
from tcm_expert.database.manager import DatabaseManager


METHODS = (
    ("vong", "Vọng chẩn", "Sắc diện, hình thể, lưỡi..."),
    ("van", "Văn chẩn", "Âm thanh, hơi thở, mùi..."),
    ("van_hoi", "Vấn chẩn", "Hàn nhiệt, ăn ngủ, đau, đại tiểu tiện..."),
    ("thiet", "Thiết chẩn", "Mạch, sờ nắn, vị trí đau..."),
)


class DiagnosticEntryDialog(QMessageBox):
    """Kept out intentionally; entries are edited inline for faster clinical input."""


class MethodEditor(QWidget):
    def __init__(self, repository: ConsultationRepository, method: str, hint: str):
        super().__init__()
        self.repository = repository
        self.method = method
        self.consultation_id: int | None = None
        layout = QVBoxLayout(self)
        hint_label = QLabel(hint)
        hint_label.setObjectName("subtitle")
        layout.addWidget(hint_label)
        form = QFormLayout()
        self.category = QLineEdit()
        self.category.setPlaceholderText("Ví dụ: Lưỡi, mạch, giọng nói")
        self.finding = QTextEdit()
        self.finding.setMaximumHeight(76)
        self.severity = QSpinBox()
        self.severity.setRange(0, 10)
        self.note = QLineEdit()
        form.addRow("Nhóm *", self.category)
        form.addRow("Kết quả *", self.finding)
        form.addRow("Mức độ 0–10", self.severity)
        form.addRow("Ghi chú", self.note)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        add = QPushButton("Thêm kết quả")
        add.clicked.connect(self.add_entry)
        remove = QPushButton("Xóa mục chọn")
        remove.clicked.connect(self.remove_entry)
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(("Nhóm", "Kết quả", "Mức độ", "Ghi chú"))
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

    def set_consultation(self, consultation_id: int | None) -> None:
        self.consultation_id = consultation_id
        self.refresh()

    def refresh(self) -> None:
        rows = [] if self.consultation_id is None else [
            row for row in self.repository.diagnostic_entries(self.consultation_id)
            if row["method"] == self.method
        ]
        self.table.setRowCount(len(rows))
        for row_index, entry in enumerate(rows):
            values = (entry["category"], entry["finding"], entry.get("severity"), entry["note"])
            for column, value in enumerate(values):
                item = QTableWidgetItem("" if value is None else str(value))
                item.setData(Qt.ItemDataRole.UserRole, entry["id"])
                self.table.setItem(row_index, column, item)

    def add_entry(self) -> None:
        if self.consultation_id is None:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn hồ sơ khám trước.")
            return
        try:
            self.repository.add_diagnostic_entry(
                self.consultation_id, self.method, self.category.text(),
                self.finding.toPlainText(), self.severity.value(), self.note.text(),
            )
            self.category.clear()
            self.finding.clear()
            self.severity.setValue(0)
            self.note.clear()
            self.refresh()
        except Exception as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))

    def remove_entry(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        self.repository.delete_diagnostic_entry(
            int(items[0].data(Qt.ItemDataRole.UserRole))
        )
        self.refresh()


class DiagnosisPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.editors: list[MethodEditor] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Hồ sơ khám và Tứ chẩn")
        title.setObjectName("title")
        layout.addWidget(title)
        selectors = QHBoxLayout()
        self.patient = QComboBox()
        self.visit = QComboBox()
        self.patient.currentIndexChanged.connect(self.load_visits)
        self.visit.currentIndexChanged.connect(self.load_consultation)
        selectors.addWidget(QLabel("Bệnh nhân"))
        selectors.addWidget(self.patient, 1)
        selectors.addWidget(QLabel("Lần khám"))
        selectors.addWidget(self.visit, 1)
        layout.addLayout(selectors)
        self.summary = QGroupBox("Thông tin tổng hợp")
        form = QFormLayout(self.summary)
        self.complaint = QTextEdit()
        self.history = QTextEdit()
        self.assessment = QTextEdit()
        for field in (self.complaint, self.history, self.assessment):
            field.setMaximumHeight(64)
        self.doctor = QLineEdit()
        self.status = QComboBox()
        for key, text in (("draft", "Bản nháp"), ("in_review", "Đang duyệt"),
                          ("approved", "Đã duyệt"), ("closed", "Đã đóng")):
            self.status.addItem(text, key)
        form.addRow("Lý do khám", self.complaint)
        form.addRow("Tiền sử", self.history)
        form.addRow("Nhận định sơ bộ", self.assessment)
        form.addRow("Bác sĩ", self.doctor)
        form.addRow("Trạng thái", self.status)
        save = QPushButton("Lưu hồ sơ")
        save.clicked.connect(self.save_summary)
        form.addRow(save)
        layout.addWidget(self.summary)
        tabs = QTabWidget()
        for method, name, hint in METHODS:
            editor = MethodEditor(self.consultations, method, hint)
            self.editors.append(editor)
            tabs.addTab(editor, name)
        layout.addWidget(tabs, 1)
        self.reload_patients()

    def reload_patients(self) -> None:
        self.patient.blockSignals(True)
        self.patient.clear()
        self.patient.addItem("— Chọn bệnh nhân —", None)
        for item in self.patients.list(limit=500):
            self.patient.addItem(f"{item['code']} • {item['full_name']}", item["id"])
        self.patient.blockSignals(False)
        self.load_visits()

    def load_visits(self) -> None:
        patient_id = self.patient.currentData()
        self.visit.blockSignals(True)
        self.visit.clear()
        self.visit.addItem("— Chọn lần khám —", None)
        if patient_id is not None:
            for item in self.consultations.list_for_patient(int(patient_id)):
                self.visit.addItem(f"{item['visit_code']} • {item['created_at']}", item["id"])
        self.visit.blockSignals(False)
        self.load_consultation()

    def load_consultation(self) -> None:
        consultation_id = self.visit.currentData()
        enabled = consultation_id is not None
        self.summary.setEnabled(enabled)
        for editor in self.editors:
            editor.set_consultation(int(consultation_id) if enabled else None)
        if not enabled:
            for field in (self.complaint, self.history, self.assessment, self.doctor):
                field.clear()
            return
        item = self.consultations.get(int(consultation_id))
        self.complaint.setPlainText(item.get("chief_complaint", ""))
        self.history.setPlainText(item.get("western_history", ""))
        self.assessment.setPlainText(item.get("assessment", ""))
        self.doctor.setText(item.get("doctor_name", ""))
        self.status.setCurrentIndex(max(0, self.status.findData(item["status"])))

    def save_summary(self) -> None:
        consultation_id = self.visit.currentData()
        if consultation_id is None:
            return
        try:
            self.consultations.update(int(consultation_id), {
                "chief_complaint": self.complaint.toPlainText(),
                "western_history": self.history.toPlainText(),
                "assessment": self.assessment.toPlainText(),
                "doctor_name": self.doctor.text(), "status": self.status.currentData(),
            })
            QMessageBox.information(self, "Đã lưu", "Hồ sơ khám đã được cập nhật.")
        except Exception as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))
