from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database import (
    ClinicalDecisionRepository,
    ConsultationRepository,
    PatientRepository,
    ValidationError,
)
from tcm_expert.database.manager import DatabaseManager
from tcm_expert.services.clinical_decision_support import ClinicalDecisionSupport


class ClinicalSupportPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.reports = ClinicalDecisionRepository(database)
        self.support = ClinicalDecisionSupport(database)
        self.report_ids: list[int] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Hỗ trợ quyết định lâm sàng")
        title.setObjectName("title")
        layout.addWidget(title)
        warning = QLabel("⚠ Không tự chẩn đoán hoặc kê đơn. Bác sĩ phải kiểm tra và phê duyệt.")
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        selectors = QHBoxLayout()
        self.patient = QComboBox()
        self.patient.currentIndexChanged.connect(self.refresh_visits)
        self.visit = QComboBox()
        self.visit.currentIndexChanged.connect(self.refresh_reports)
        generate = QPushButton("Tạo báo cáo hỗ trợ")
        generate.clicked.connect(self.generate)
        for label, widget in (("Bệnh nhân", self.patient), ("Lần khám", self.visit)):
            selectors.addWidget(QLabel(label))
            selectors.addWidget(widget, 1)
        selectors.addWidget(generate)
        layout.addLayout(selectors)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(("Thời gian", "Đầy đủ", "Nguy cơ", "Trạng thái"))
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.show_selected)
        layout.addWidget(self.table, 1)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        layout.addWidget(self.detail, 2)
        approval = QHBoxLayout()
        self.reviewer = QLineEdit()
        self.reviewer.setPlaceholderText("Tên bác sĩ phê duyệt")
        approve = QPushButton("Bác sĩ phê duyệt")
        approve.clicked.connect(self.review)
        approval.addWidget(self.reviewer, 1)
        approval.addWidget(approve)
        layout.addLayout(approval)
        self.refresh_patients()

    def refresh_patients(self) -> None:
        self.patient.clear()
        self.patient.addItem("Chọn bệnh nhân", None)
        for row in self.patients.list():
            self.patient.addItem(f"{row['code']} — {row['full_name']}", row["id"])
        self.refresh_visits()

    def refresh_visits(self) -> None:
        self.visit.clear()
        patient_id = self.patient.currentData()
        if patient_id is not None:
            for row in self.consultations.list_for_patient(int(patient_id)):
                self.visit.addItem(f"{row['visit_code']} — {row['created_at']}", row["id"])
        self.refresh_reports()

    def refresh_reports(self) -> None:
        consultation_id = self.visit.currentData()
        rows = self.reports.list_for_consultation(int(consultation_id)) if consultation_id else []
        self.report_ids = [int(row["id"]) for row in rows]
        self.table.setRowCount(len(rows))
        labels = {"low": "Thấp", "moderate": "Trung bình", "high": "Cao"}
        for index, row in enumerate(rows):
            values = (
                row["created_at"],
                f"{float(row['completeness_score']) * 100:.0f}%",
                labels.get(row["risk_level"], row["risk_level"]),
                "Đã duyệt" if row["status"] == "reviewed" else "Bản nháp",
            )
            for column, value in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(str(value)))
        self.detail.clear()

    def generate(self) -> None:
        consultation_id = self.visit.currentData()
        if consultation_id is None:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Hãy chọn lần khám.")
            return
        self.reports.create(int(consultation_id), self.support.build(int(consultation_id)))
        self.refresh_reports()
        if self.table.rowCount():
            self.table.selectRow(0)

    def show_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.report_ids):
            return
        saved = self.reports.get(self.report_ids[row])
        if saved is None:
            return
        report = saved["report"]
        lines = [
            f"BỆNH NHÂN: {report['patient']}",
            f"ĐỘ ĐẦY ĐỦ TỨ CHẨN: {report['completeness_score'] * 100:.0f}%",
            f"MỨC NGUY CƠ: {report['risk_level'].upper()}",
            "",
            "DỮ LIỆU THIẾU: " + (", ".join(report["missing_data"]) or "Không"),
            "CẢNH BÁO ĐỎ:",
            *([f"• {item}" for item in report["red_flags"]] or ["• Không phát hiện"]),
            "",
            "GỢI Ý CHỨNG:",
            *(
                [
                    f"• {item['name']} — {item['confidence'] * 100:.0f}% — {item['evidence']}"
                    for item in report["syndrome_suggestions"]
                ]
                or ["• Chưa có"]
            ),
            "",
            "GỢI Ý BÀI THUỐC THAM KHẢO:",
            *(
                [
                    f"• {item['name']} — điểm {item['score']}"
                    for item in report["formula_suggestions"]
                ]
                or ["• Chưa có"]
            ),
            "",
            "CẢNH BÁO AN TOÀN:",
            *(
                [f"• [{item['level']}] {item['message']}" for item in report["safety_alerts"]]
                or ["• Chưa ghi nhận"]
            ),
            "",
            report["disclaimer"],
        ]
        self.detail.setPlainText("\n".join(lines))

    def review(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.report_ids):
            QMessageBox.warning(self, "Thiếu dữ liệu", "Hãy chọn báo cáo.")
            return
        try:
            self.reports.review(self.report_ids[row], self.reviewer.text())
        except ValidationError as error:
            QMessageBox.warning(self, "Không thể phê duyệt", str(error))
            return
        self.refresh_reports()
