from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
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
    SettingsRepository,
    ValidationError,
)
from tcm_expert.database.manager import DatabaseManager
from tcm_expert.services.clinical_decision_support import ClinicalDecisionSupport
from tcm_expert.services.ollama_formula_recommender import (
    FormulaRecommendationOutcome,
    OllamaFormulaRecommender,
)
from tcm_expert.ai import AIWorkflowDisabled, create_ai_workflow


class FormulaRecommendationWorker(QThread):
    completed = Signal(object)

    def __init__(self, database: DatabaseManager, consultation_id: int):
        super().__init__()
        self.database = database
        self.consultation_id = consultation_id

    def run(self) -> None:
        outcome = OllamaFormulaRecommender(self.database).recommend(self.consultation_id)
        self.completed.emit(outcome)


class ClinicalSupportPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.reports = ClinicalDecisionRepository(database)
        self.support = ClinicalDecisionSupport(database)
        self.database = database
        self._formula_worker: FormulaRecommendationWorker | None = None
        self.settings = SettingsRepository(database)
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
        self.formula_generate = QPushButton("Qwen gợi ý bài thuốc")
        self.formula_generate.clicked.connect(self.generate_formula_ai)
        ai_generate = QPushButton("Đề xuất tham khảo")
        ai_generate.clicked.connect(self.generate_ai)
        for label, widget in (("Bệnh nhân", self.patient), ("Lần khám", self.visit)):
            selectors.addWidget(QLabel(label))
            selectors.addWidget(widget, 1)
        selectors.addWidget(generate)
        selectors.addWidget(self.formula_generate)
        selectors.addWidget(ai_generate)
        layout.addLayout(selectors)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ("Thời gian", "Nguồn", "Đầy đủ", "Tin cậy", "Nguy cơ", "Quyết định")
        )
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
        self.reviewer.setReadOnly(True)
        self.reviewer.setText(self.settings.doctor_name())
        approve = QPushButton("Bác sĩ phê duyệt")
        approve.clicked.connect(self.review)
        reject = QPushButton("Bác sĩ từ chối")
        reject.clicked.connect(self.reject)
        approval.addWidget(self.reviewer, 1)
        approval.addWidget(approve)
        approval.addWidget(reject)
        layout.addLayout(approval)
        self.refresh_patients()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh_patients()
        self.reviewer.setText(self.settings.doctor_name())

    def refresh_patients(self) -> None:
        selected_patient = self.patient.currentData()
        self.patient.blockSignals(True)
        self.patient.clear()
        self.patient.addItem("Chọn bệnh nhân", None)
        for row in self.patients.list():
            self.patient.addItem(f"{row['code']} — {row['full_name']}", row["id"])
        index = self.patient.findData(selected_patient)
        if self.patient.count() > 1:
            self.patient.setCurrentIndex(index if index >= 1 else 1)
        self.patient.blockSignals(False)
        self.refresh_visits()

    def refresh_visits(self) -> None:
        selected_visit = self.visit.currentData()
        self.visit.blockSignals(True)
        self.visit.clear()
        self.visit.addItem("Chọn lần khám", None)
        patient_id = self.patient.currentData()
        if patient_id is not None:
            rows = self.consultations.list_for_patient(int(patient_id))
            for number, row in enumerate(reversed(rows), 1):
                self.visit.addItem(
                    f"Lần khám {number} — {row['visit_code']} — {row['created_at']}", row["id"]
                )
            if not rows:
                self.visit.addItem("Chưa có hồ sơ khám", None)
            else:
                index = self.visit.findData(selected_visit)
                self.visit.setCurrentIndex(index if index >= 1 else 1)
        self.visit.blockSignals(False)
        self.refresh_reports()

    def refresh_reports(self) -> None:
        consultation_id = self.visit.currentData()
        rows = self.reports.list_for_consultation(int(consultation_id)) if consultation_id else []
        self.report_ids = [int(row["id"]) for row in rows]
        self.table.setRowCount(len(rows))
        labels = {"low": "Thấp", "moderate": "Trung bình", "high": "Cao"}
        decisions = {
            "pending": "Chờ bác sĩ",
            "accepted": "Đã được duyệt",
            "rejected": "Đã từ chối",
            "edited": "Đã chỉnh sửa",
        }
        for index, row in enumerate(rows):
            values = (
                row["created_at"],
                "AI tham khảo" if row["report_type"] == "ai" else "Rule Engine",
                f"{float(row['completeness_score']) * 100:.0f}%",
                f"{float(row['ai_confidence']) * 100:.0f}%"
                if row["report_type"] == "ai"
                else "—",
                labels.get(row["risk_level"], row["risk_level"]),
                decisions.get(row["doctor_decision"], row["doctor_decision"]),
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

    def generate_formula_ai(self) -> None:
        consultation_id = self.visit.currentData()
        if consultation_id is None:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Hãy chọn lần khám.")
            return
        if self._formula_worker is not None and self._formula_worker.isRunning():
            return
        self.formula_generate.setEnabled(False)
        self.formula_generate.setText("Qwen đang phân tích...")
        self._formula_worker = FormulaRecommendationWorker(self.database, int(consultation_id))
        self._formula_worker.completed.connect(self._save_formula_ai_report)
        self._formula_worker.finished.connect(self._formula_worker.deleteLater)
        self._formula_worker.start()

    def _save_formula_ai_report(self, outcome: FormulaRecommendationOutcome) -> None:
        consultation_id = self.visit.currentData()
        self.formula_generate.setEnabled(True)
        self.formula_generate.setText("Qwen gợi ý bài thuốc")
        self._formula_worker = None
        if consultation_id is None:
            return
        report = self.support.build(int(consultation_id), formula_outcome=outcome)
        self.reports.create(int(consultation_id), report)
        self.refresh_reports()
        if self.table.rowCount():
            self.table.selectRow(0)
        if not report["formula_eligible"]:
            QMessageBox.information(self, "Chưa đủ điều kiện", report["formula_blocked_reason"])
        elif outcome.source == "rules":
            QMessageBox.information(
                self,
                "Đã dùng luật nội bộ",
                "Ollama không hoạt động; kết quả vẫn chờ bác sĩ kiểm tra.\n"
                + outcome.fallback_reason,
            )

    def generate_ai(self) -> None:
        consultation_id = self.visit.currentData()
        if consultation_id is None:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Hãy chọn lần khám.")
            return
        workflow = create_ai_workflow(self.reports.database)
        try:
            proposal = workflow.propose(int(consultation_id))
        except AIWorkflowDisabled as error:
            QMessageBox.information(self, "AI đang tắt", str(error))
            return
        report = self.support.build(int(consultation_id))
        report["ai_proposal"] = {
            "summary": proposal.vietnamese_summary,
            "evidence": list(proposal.evidence),
            "warnings": list(proposal.warnings),
            "provider_trace": list(proposal.provider_trace),
            "confidence": proposal.confidence,
            "status": proposal.decision.value,
        }
        self.reports.create_ai(int(consultation_id), report)
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
        proposal = report.get("ai_proposal")
        if proposal:
            status = (
                "ĐÃ ĐƯỢC BÁC SĨ DUYỆT"
                if saved["status"] == "reviewed"
                else "CHƯA ĐƯỢC BÁC SĨ DUYỆT"
            )
            lines = [
                f"ĐỀ XUẤT THAM KHẢO — {status}",
                f"ĐỘ TIN CẬY: {float(proposal.get('confidence', 0)) * 100:.0f}%",
                f"QUYẾT ĐỊNH: {saved.get('doctor_decision', 'pending').upper()}",
                *([f"LÝ DO: {saved['decision_reason']}"] if saved.get("decision_reason") else []),
                "",
                proposal["summary"],
                "",
                "CĂN CỨ:",
                *([f"• {item}" for item in proposal["evidence"]] or ["• Chưa có"]),
                "",
                "TRẠNG THÁI MÔ-ĐUN:",
                *[f"• {item}" for item in proposal["provider_trace"]],
                "",
                "CẢNH BÁO:",
                *([f"• {item}" for item in proposal.get("warnings", [])] or ["• Chưa có"]),
            ]
            self.detail.setPlainText("\n".join(lines))
            return
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
            (
                f"Nguồn: Ollama/{report.get('formula_model')}"
                if report.get("formula_source") == "ollama"
                else "Nguồn: Luật nội bộ"
            ),
            *(
                [f"• {report['formula_blocked_reason']}"]
                if not report.get("formula_eligible", True)
                else []
            ),
            *(
                [
                    f"• {item['name']} — điểm {item['score']}"
                    + (f" — {item['reason']}" if item.get("reason") else "")
                    for item in report["formula_suggestions"]
                ]
                or (["• Chưa có"] if report.get("formula_eligible", True) else [])
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
        from tcm_expert.security import require_role

        try:
            require_role("doctor")
        except PermissionError as error:
            QMessageBox.warning(self, "Không đủ quyền chuyên môn", str(error))
            return
        row = self.table.currentRow()
        if row < 0 or row >= len(self.report_ids):
            QMessageBox.warning(self, "Thiếu dữ liệu", "Hãy chọn báo cáo.")
            return
        report_id = self.report_ids[row]
        try:
            doctor = self.settings.doctor_name(required=True)
            self.reviewer.setText(doctor)
            self.reports.review(report_id, doctor)
        except ValidationError as error:
            QMessageBox.warning(self, "Không thể phê duyệt", str(error))
            return
        self.refresh_reports()
        if report_id in self.report_ids:
            self.table.selectRow(self.report_ids.index(report_id))
        QMessageBox.information(self, "Đã phê duyệt", "Bác sĩ đã phê duyệt báo cáo.")

    def reject(self) -> None:
        from tcm_expert.security import require_role

        try:
            require_role("doctor")
        except PermissionError as error:
            QMessageBox.warning(self, "Không đủ quyền chuyên môn", str(error))
            return
        row = self.table.currentRow()
        if row < 0 or row >= len(self.report_ids):
            QMessageBox.warning(self, "Thiếu dữ liệu", "Hãy chọn báo cáo.")
            return
        reason, accepted = QInputDialog.getMultiLineText(
            self, "Lý do từ chối", "Nhận xét bắt buộc của bác sĩ:"
        )
        if not accepted:
            return
        report_id = self.report_ids[row]
        try:
            doctor = self.settings.doctor_name(required=True)
            self.reviewer.setText(doctor)
            self.reports.decide(report_id, doctor, "rejected", reason)
        except ValidationError as error:
            QMessageBox.warning(self, "Không thể từ chối", str(error))
            return
        self.refresh_reports()
        if report_id in self.report_ids:
            self.table.selectRow(self.report_ids.index(report_id))
        QMessageBox.information(self, "Đã ghi nhận", "Bác sĩ đã từ chối đề xuất.")
