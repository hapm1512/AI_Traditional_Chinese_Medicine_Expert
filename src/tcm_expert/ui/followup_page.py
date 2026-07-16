from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database import (
    ConsultationRepository,
    PatientRepository,
    SettingsRepository,
    TreatmentFollowupRepository,
    ValidationError,
)
from tcm_expert.database.manager import DatabaseManager


class FollowupPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.followups = TreatmentFollowupRepository(database)
        self.settings = SettingsRepository(database)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Theo dõi điều trị và tái khám")
        title.setObjectName("title")
        layout.addWidget(title)
        warning = QLabel("⚠ Chỉ bác sĩ ghi nhận kết quả thực tế. AI không đánh giá điều trị.")
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        selectors = QHBoxLayout()
        self.patient = QComboBox()
        self.patient.currentIndexChanged.connect(self.refresh_visits)
        self.visit = QComboBox()
        self.visit.currentIndexChanged.connect(self.refresh_followups)
        selectors.addWidget(QLabel("Bệnh nhân"))
        selectors.addWidget(self.patient, 1)
        selectors.addWidget(QLabel("Lần khám"))
        selectors.addWidget(self.visit, 1)
        layout.addLayout(selectors)

        form = QFormLayout()
        self.followup_date = QDateEdit(QDate.currentDate())
        self.followup_date.setCalendarPopup(True)
        self.followup_date.setDisplayFormat("dd/MM/yyyy")
        self.status = QComboBox()
        for text, value in (
            ("Đang theo dõi", "monitoring"),
            ("Cải thiện", "improved"),
            ("Ổn định", "stable"),
            ("Nặng hơn", "worsened"),
            ("Hoàn tất", "completed"),
        ):
            self.status.addItem(text, value)
        self.effectiveness = QComboBox()
        for text, value in (
            ("Chưa đánh giá", "not_assessed"),
            ("Tốt", "good"),
            ("Một phần", "partial"),
            ("Không hiệu quả", "none"),
        ):
            self.effectiveness.addItem(text, value)
        self.before = QSpinBox()
        self.after = QSpinBox()
        for score in (self.before, self.after):
            score.setRange(0, 10)
        self.adherence = QTextEdit()
        self.adherence.setMaximumHeight(58)
        self.adverse = QTextEdit()
        self.adverse.setMaximumHeight(58)
        self.note = QTextEdit()
        self.note.setMaximumHeight(72)
        form.addRow("Ngày tái khám", self.followup_date)
        form.addRow("Trạng thái", self.status)
        form.addRow("Hiệu quả", self.effectiveness)
        scores = QHBoxLayout()
        scores.addWidget(QLabel("Trước"))
        scores.addWidget(self.before)
        scores.addWidget(QLabel("Sau"))
        scores.addWidget(self.after)
        scores.addStretch()
        form.addRow("Điểm triệu chứng", scores)
        form.addRow("Tuân thủ điều trị", self.adherence)
        form.addRow("Phản ứng bất lợi", self.adverse)
        form.addRow("Nhận xét bác sĩ", self.note)
        layout.addLayout(form)
        save = QPushButton("Lưu theo dõi")
        save.clicked.connect(self.save)
        layout.addWidget(save)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ("Ngày", "Trạng thái", "Trước", "Sau", "Thay đổi", "Hiệu quả", "Bác sĩ")
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.refresh_patients()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh_patients()

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
        self.visit.blockSignals(True)
        self.visit.clear()
        self.visit.addItem("Chọn lần khám", None)
        patient_id = self.patient.currentData()
        if patient_id:
            for row in reversed(self.consultations.list_for_patient(int(patient_id))):
                self.visit.addItem(f"{row['visit_code']} — {row['created_at']}", row["id"])
            index = self.visit.findData(selected)
            if self.visit.count() > 1:
                self.visit.setCurrentIndex(index if index >= 1 else 1)
        self.visit.blockSignals(False)
        self.refresh_followups()

    def refresh_followups(self) -> None:
        consultation_id = self.visit.currentData()
        rows = self.followups.list_for_consultation(int(consultation_id)) if consultation_id else []
        status_labels = {
            "monitoring": "Theo dõi", "improved": "Cải thiện", "stable": "Ổn định",
            "worsened": "Nặng hơn", "completed": "Hoàn tất",
        }
        effectiveness_labels = {
            "not_assessed": "Chưa đánh giá", "good": "Tốt", "partial": "Một phần",
            "none": "Không hiệu quả",
        }
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            before, after = int(row["symptom_score_before"]), int(row["symptom_score_after"])
            try:
                shown_date = date.fromisoformat(row["followup_date"]).strftime("%d/%m/%Y")
            except ValueError:
                shown_date = row["followup_date"]
            values = (
                shown_date, status_labels.get(row["treatment_status"], row["treatment_status"]),
                before, after, before - after,
                effectiveness_labels.get(row["effectiveness"], row["effectiveness"]),
                row["reviewed_by"],
            )
            for column, value in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(str(value)))

    def save(self) -> None:
        consultation_id = self.visit.currentData()
        if consultation_id is None:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Hãy chọn lần khám.")
            return
        try:
            self.followups.create(
                int(consultation_id),
                followup_date=self.followup_date.date().toString("yyyy-MM-dd"),
                treatment_status=str(self.status.currentData()),
                symptom_score_before=self.before.value(),
                symptom_score_after=self.after.value(),
                effectiveness=str(self.effectiveness.currentData()),
                adverse_reactions=self.adverse.toPlainText(),
                adherence=self.adherence.toPlainText(),
                doctor_note=self.note.toPlainText(),
                reviewed_by=self.settings.doctor_name(),
            )
        except ValidationError as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))
            return
        self.adherence.clear()
        self.adverse.clear()
        self.note.clear()
        self.refresh_followups()
        QMessageBox.information(self, "Đã lưu", "Đã lưu kết quả theo dõi.")
