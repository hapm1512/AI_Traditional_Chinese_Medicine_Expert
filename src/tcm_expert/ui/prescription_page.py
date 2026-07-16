from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
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
    SettingsRepository,
)
from tcm_expert.database.manager import DatabaseManager


class PrescriptionPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.prescriptions = PrescriptionRepository(database)
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.settings = SettingsRepository(database)
        self.prescription_ids: list[int] = []
        self.recommendation_rows: dict[str, dict] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Đơn thuốc bác sĩ")
        title.setObjectName("title")
        layout.addWidget(title)
        warning = QLabel(
            "⚠ Chỉ tạo từ bài thuốc đã duyệt. Bác sĩ chịu trách nhiệm đơn và liều dùng."
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
        self.doctor.setReadOnly(True)
        form.addRow("Bài thuốc đã duyệt", self.recommendation)
        form.addRow("Chẩn đoán", self._editor_with_pen(self.diagnosis, "Chẩn đoán"))
        form.addRow("Pháp trị", self._editor_with_pen(self.principle, "Pháp trị"))
        form.addRow("Cách dùng", self._editor_with_pen(self.directions, "Cách dùng"))
        form.addRow("Gia giảm", self._editor_with_pen(self.modifications, "Gia giảm"))
        form.addRow("Ghi chú an toàn", self._editor_with_pen(self.safety, "Ghi chú an toàn"))
        form.addRow("Bác sĩ", self.doctor)
        buttons = QHBoxLayout()
        create = QPushButton("Tạo đơn thuốc")
        create.clicked.connect(self.create_prescription)
        approve = QPushButton("Bác sĩ phê duyệt")
        approve.clicked.connect(self.approve_prescription)
        buttons.addWidget(create)
        buttons.addWidget(approve)
        form.addRow(buttons)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(("Mã đơn", "Bài thuốc", "Bác sĩ", "Trạng thái"))
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
        self.doctor.setText(self.settings.doctor_name())

    def _editor_with_pen(self, editor: QWidget, title: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        if isinstance(editor, QTextEdit):
            editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        button = QPushButton("✎")
        button.setFixedWidth(42)
        button.setToolTip(f"Mở bảng soạn thảo {title.lower()}")
        button.clicked.connect(lambda: self._open_editor(editor, title))
        layout.addWidget(editor, 1)
        layout.addWidget(button)
        return container

    def _open_editor(self, editor: QWidget, title: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Soạn thảo — {title}")
        dialog.resize(700, 440)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        current = editor.toPlainText() if isinstance(editor, QTextEdit) else editor.text()
        text.setPlainText(current)
        layout.addWidget(text)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec():
            if isinstance(editor, QTextEdit):
                editor.setPlainText(text.toPlainText())
            else:
                editor.setText(text.toPlainText().replace("\n", " ").strip())

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
        else:
            index = self.visit.findData(selected_id)
            self.visit.setCurrentIndex(index if index >= 1 else 1)
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
        self.recommendation_rows = {f"r:{row['id']}": row for row in rows}
        used_formula_ids = {int(row["formula_id"]) for row in rows}
        for row in rows:
            self.recommendation.addItem(
                f"Đã chọn — {row['formula_name']}", f"r:{row['id']}"
            )
        catalogue = []
        if consultation_id is not None:
            catalogue = [
                row for row in self.prescriptions.approved_formula_catalog()
                if int(row["formula_id"]) not in used_formula_ids
            ]
        for row in catalogue:
            self.recommendation_rows[f"f:{row['formula_id']}"] = row
            self.recommendation.addItem(
                f"{row['code']} — {row['formula_name']}", f"f:{row['formula_id']}"
            )
        if not rows and not catalogue:
            self.recommendation.addItem("Chưa có bài thuốc đã duyệt", None)
        self.recommendation.blockSignals(False)
        self.clear_recommendation_detail()
        self.refresh_prescriptions()

    def load_recommendation(self) -> None:
        selection = self.recommendation.currentData()
        if selection is None:
            self.clear_recommendation_detail()
            return
        row = self.recommendation_rows.get(str(selection))
        if row is None:
            self.clear_recommendation_detail()
            return
        self.directions.setPlainText(
            row.get("custom_directions") or row.get("directions") or ""
        )
        self.modifications.setPlainText(row["modifications"] or "")
        self.safety.setPlainText(
            row.get("safety_notes")
            or "\n".join(
                value for value in (row.get("contraindications"), row.get("interactions"))
                if value
            )
        )
        self.principle.setText(row["treatment_principle"] or "")

    def selected_recommendation_id(self, doctor: str) -> int:
        selection = str(self.recommendation.currentData() or "")
        if selection.startswith("r:"):
            return int(selection[2:])
        if not selection.startswith("f:") or self.visit.currentData() is None:
            raise ValueError("Chưa chọn bài thuốc cho hồ sơ.")
        return self.prescriptions.approve_formula_for_consultation(
            int(self.visit.currentData()),
            int(selection[2:]),
            {
                "directions": self.directions.toPlainText(),
                "modifications": self.modifications.toPlainText(),
                "safety_notes": self.safety.toPlainText(),
                "doctor_name": doctor,
            },
        )

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
        try:
            doctor = self.settings.doctor_name(required=True)
            recommendation_id = self.selected_recommendation_id(doctor)
            self.prescriptions.create(
                recommendation_id,
                {
                    "diagnosis": self.diagnosis.toPlainText(),
                    "treatment_principle": self.principle.text(),
                    "directions": self.directions.toPlainText(),
                    "modifications": self.modifications.toPlainText(),
                    "safety_notes": self.safety.toPlainText(),
                    "doctor_name": doctor,
                },
            )
            self.doctor.setText(doctor)
        except ValueError as error:
            QMessageBox.warning(self, "Chưa thể tạo đơn", str(error))
            return
        self.refresh_prescriptions()
        QMessageBox.information(self, "Đã tạo", "Đã tạo đơn nháp để bác sĩ kiểm tra.")

    def _form_values(self, doctor: str) -> dict[str, str]:
        return {
            "diagnosis": self.diagnosis.toPlainText(),
            "treatment_principle": self.principle.text(),
            "directions": self.directions.toPlainText(),
            "modifications": self.modifications.toPlainText(),
            "safety_notes": self.safety.toPlainText(),
            "doctor_name": doctor,
        }

    def approve_prescription(self) -> None:
        row = self.table.currentRow()
        try:
            doctor = self.settings.doctor_name(required=True)
            prescription_id = None
            if 0 <= row < len(self.prescription_ids):
                selected_id = self.prescription_ids[row]
                if self.prescriptions.detail(selected_id)["status"] == "draft":
                    prescription_id = selected_id
            if prescription_id is None:
                recommendation_id = self.selected_recommendation_id(doctor)
                prescription_id = self.prescriptions.create(
                    recommendation_id, self._form_values(doctor)
                )
            self.prescriptions.approve(prescription_id)
            self.doctor.setText(doctor)
        except ValueError as error:
            QMessageBox.warning(self, "Chưa thể phê duyệt", str(error))
            return
        self.refresh_prescriptions()
        if prescription_id in self.prescription_ids:
            self.table.selectRow(self.prescription_ids.index(prescription_id))
        QMessageBox.information(
            self,
            "Đã lưu và phê duyệt",
            "Đơn thuốc đã được lưu và bác sĩ phê duyệt.",
        )

    def show_detail(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        detail = self.prescriptions.detail(self.prescription_ids[row])
        self.diagnosis.setPlainText(detail["diagnosis"])
        self.principle.setText(detail["treatment_principle"])
        self.directions.setPlainText(detail["directions"])
        self.modifications.setPlainText(detail["modifications"])
        self.safety.setPlainText(detail["safety_notes"])
        self.doctor.setText(detail["doctor_name"])
        recommendation_index = self.recommendation.findData(
            f"r:{detail['recommendation_id']}"
        )
        if recommendation_index >= 0:
            self.recommendation.setCurrentIndex(recommendation_index)
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
