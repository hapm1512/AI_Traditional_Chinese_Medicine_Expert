from __future__ import annotations

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
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

from tcm_expert.database import (
    ConsultationRepository,
    PatientRepository,
    PrescriptionRepository,
)
from tcm_expert.database.manager import DatabaseManager


class PrescriptionPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.prescriptions = PrescriptionRepository(database)
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.prescription_ids: list[int] = []
        self.recommendation_rows: dict[int, dict] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Đơn thuốc bác sĩ")
        title.setObjectName("title")
        layout.addWidget(title)
        warning = QLabel(
            "⚠ Chỉ tạo từ bài thuốc đã duyệt. "
            "Bác sĩ chịu trách nhiệm đơn và liều dùng."
        )
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        selectors = QHBoxLayout()
        self.patient = QComboBox()
        self.patient.currentIndexChanged.connect(self.refresh_visits)
        self.visit = QComboBox()
        self.visit.currentIndexChanged.connect(self.refresh_context)
        selectors.addWidget(QLabel("Bệnh nhân"))
        selectors.addWidget(self.patient, 1)
        selectors.addWidget(QLabel("Lần khám"))
        selectors.addWidget(self.visit, 1)
        layout.addLayout(selectors)

        splitter = QSplitter()
        editor = QWidget()
        form = QFormLayout(editor)
        self.recommendation = QComboBox()
        self.recommendation.currentIndexChanged.connect(self.load_recommendation)
        self.diagnosis = QTextEdit()
        self.diagnosis.setMaximumHeight(70)
        self.principle = QLineEdit()
        self.directions = QTextEdit()
        self.directions.setMaximumHeight(70)
        self.modifications = QTextEdit()
        self.modifications.setMaximumHeight(70)
        self.safety = QTextEdit()
        self.safety.setMaximumHeight(70)
        self.doctor = QLineEdit()
        form.addRow("Bài thuốc đã duyệt", self.recommendation)
        form.addRow("Chẩn đoán", self.diagnosis)
        form.addRow("Pháp trị", self.principle)
        form.addRow("Cách dùng", self.directions)
        form.addRow("Gia giảm", self.modifications)
        form.addRow("Ghi chú an toàn", self.safety)
        form.addRow("Bác sĩ", self.doctor)
        buttons = QHBoxLayout()
        create = QPushButton("Tạo đơn nháp")
        create.clicked.connect(self.create_prescription)
        approve = QPushButton("Bác sĩ phê duyệt")
        approve.clicked.connect(self.approve_prescription)
        buttons.addWidget(create)
        buttons.addWidget(approve)
        form.addRow(buttons)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ("Mã đơn", "Bài thuốc", "Bác sĩ", "Trạng thái")
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.show_detail)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        right_layout.addWidget(self.table, 1)
        right_layout.addWidget(self.preview, 1)
        splitter.addWidget(editor)
        splitter.addWidget(right)
        splitter.setSizes((450, 650))
        layout.addWidget(splitter, 1)
        self.refresh_patients()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh_patients(preserve_selection=True)

    def refresh_patients(self, preserve_selection: bool = False) -> None:
        selected_id = self.patient.currentData() if preserve_selection else None
        self.patient.blockSignals(True)
        self.patient.clear()
        self.patient.addItem("Chọn bệnh nhân", None)
        for row in self.patients.list():
            self.patient.addItem(f"{row['code']} — {row['full_name']}", row["id"])
        if selected_id is not None:
            index = self.patient.findData(selected_id)
            self.patient.setCurrentIndex(max(index, 0))
        self.patient.blockSignals(False)
        self.refresh_visits()

    def refresh_visits(self) -> None:
        selected_id = self.visit.currentData()
        self.visit.blockSignals(True)
        self.visit.clear()
        self.visit.addItem("Chọn lần khám", None)
        patient_id = self.patient.currentData()
        rows = []
        if patient_id is not None:
            rows = self.consultations.list_for_patient(int(patient_id))
        for row in rows:
            self.visit.addItem(f"{row['visit_code']} — {row['created_at']}", row["id"])
        if not rows:
            self.visit.addItem("Chưa có lần khám", None)
        elif selected_id is not None:
            index = self.visit.findData(selected_id)
            self.visit.setCurrentIndex(max(index, 0))
        self.visit.blockSignals(False)
        self.refresh_context()

    def refresh_context(self) -> None:
        consultation_id = self.visit.currentData()
        self.recommendation.blockSignals(True)
        self.recommendation.clear()
        self.recommendation.addItem("Chọn bài thuốc đã duyệt", None)
        rows = []
        if consultation_id is not None:
            rows = self.prescriptions.approved_recommendations(int(consultation_id))
        self.recommendation_rows = {int(row["id"]): row for row in rows}
        for row in rows:
            self.recommendation.addItem(row["formula_name"], row["id"])
        if not rows:
            self.recommendation.addItem("Chưa có bài thuốc đã duyệt", None)
        self.recommendation.blockSignals(False)
        self.clear_recommendation_detail()
        self.refresh_prescriptions()

    def load_recommendation(self) -> None:
        recommendation_id = self.recommendation.currentData()
        if recommendation_id is None:
            self.clear_recommendation_detail()
            return
        row = self.recommendation_rows.get(int(recommendation_id))
        if row is None:
            self.clear_recommendation_detail()
            return
        self.directions.setPlainText(row["custom_directions"] or "")
        self.modifications.setPlainText(row["modifications"] or "")
        self.safety.setPlainText(row["safety_notes"] or "")
        self.principle.setText(row["treatment_principle"] or "")

    def clear_recommendation_detail(self) -> None:
        self.directions.clear()
        self.modifications.clear()
        self.safety.clear()
        self.principle.clear()

    def refresh_prescriptions(self) -> None:
        consultation_id = self.visit.currentData()
        rows = (
            self.prescriptions.list_for_consultation(int(consultation_id))
            if consultation_id is not None
            else []
        )
        self.prescription_ids = [int(row["id"]) for row in rows]
        self.table.setRowCount(len(rows))
        labels = {
            "draft": "Nháp",
            "approved": "Đã duyệt",
            "dispensed": "Đã cấp",
            "cancelled": "Đã hủy",
        }
        for index, row in enumerate(rows):
            values = (
                row["prescription_code"],
                row["formula_name"],
                row["doctor_name"],
                labels[row["status"]],
            )
            for column, value in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(str(value)))
        if rows:
            self.table.selectRow(0)
        else:
            self.preview.clear()

    def create_prescription(self) -> None:
        recommendation_id = self.recommendation.currentData()
        if recommendation_id is None:
            QMessageBox.warning(
                self, "Thiếu dữ liệu", "Chưa có bài thuốc được phê duyệt."
            )
            return
        try:
            self.prescriptions.create(
                int(recommendation_id),
                {
                    "diagnosis": self.diagnosis.toPlainText(),
                    "treatment_principle": self.principle.text(),
                    "directions": self.directions.toPlainText(),
                    "modifications": self.modifications.toPlainText(),
                    "safety_notes": self.safety.toPlainText(),
                    "doctor_name": self.doctor.text(),
                },
            )
        except ValueError as error:
            QMessageBox.warning(self, "Chưa thể tạo đơn", str(error))
            return
        self.refresh_prescriptions()
        QMessageBox.information(
            self, "Đã tạo", "Đã tạo đơn nháp để bác sĩ kiểm tra."
        )

    def approve_prescription(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        try:
            self.prescriptions.approve(self.prescription_ids[row])
        except ValueError as error:
            QMessageBox.warning(self, "Chưa thể phê duyệt", str(error))
            return
        self.refresh_prescriptions()

    def show_detail(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        detail = self.prescriptions.detail(self.prescription_ids[row])
        items = "\n".join(
            f"• {item['herb_name']}: {item['dosage']:g} {item['unit']} — {item['role']}"
            for item in detail["items"]
        )
        status = "ĐÃ PHÊ DUYỆT" if detail["status"] == "approved" else "BẢN NHÁP"
        self.preview.setPlainText(
            f"{detail['prescription_code']} — {status}\n"
            f"Bệnh nhân: {detail['full_name']}\nBác sĩ: {detail['doctor_name']}\n\n"
            f"Chẩn đoán: {detail['diagnosis']}\nPháp trị: {detail['treatment_principle']}\n"
            f"Bài thuốc: {detail['formula_name']}\n\nTHÀNH PHẦN\n{items}\n\n"
            f"Cách dùng: {detail['directions']}\nGia giảm: {detail['modifications']}\n"
            f"An toàn: {detail['safety_notes']}\n\n"
            "Đơn chỉ có hiệu lực sau khi bác sĩ phê duyệt."
        )
