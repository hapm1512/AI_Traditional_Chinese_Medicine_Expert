from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from tcm_expert.database import (
    SettingsRepository, TreatmentOutcomeReportRepository, ValidationError,
)
from tcm_expert.database.manager import DatabaseManager


class OutcomeReportPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.reports = TreatmentOutcomeReportRepository(database)
        self.settings = SettingsRepository(database)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Báo cáo kết quả điều trị")
        title.setObjectName("title")
        layout.addWidget(title)
        warning = QLabel(
            "⚠ Số liệu hỗ trợ tổng hợp. Bác sĩ chịu trách nhiệm kết luận."
        )
        warning.setObjectName("warning")
        layout.addWidget(warning)

        filters = QHBoxLayout()
        self.start = QDateEdit(QDate.currentDate().addMonths(-1))
        self.end = QDateEdit(QDate.currentDate())
        for control in (self.start, self.end):
            control.setCalendarPopup(True)
            control.setDisplayFormat("dd/MM/yyyy")
        refresh = QPushButton("Tổng hợp")
        refresh.clicked.connect(self.refresh)
        filters.addWidget(QLabel("Từ ngày"))
        filters.addWidget(self.start)
        filters.addWidget(QLabel("Đến ngày"))
        filters.addWidget(self.end)
        filters.addWidget(refresh)
        filters.addStretch()
        layout.addLayout(filters)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            (
                "Ngày", "Mã BN", "Bệnh nhân", "Lần khám",
                "Trước", "Sau", "Trạng thái", "Hiệu quả",
            )
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.conclusion = QTextEdit()
        self.conclusion.setPlaceholderText("Kết luận chuyên môn của bác sĩ...")
        self.conclusion.setMaximumHeight(72)
        layout.addWidget(self.conclusion)
        save = QPushButton("Lưu báo cáo đã xác nhận")
        save.clicked.connect(self.save)
        layout.addWidget(save)
        self.refresh()

    def _dates(self) -> tuple[str, str]:
        return self.start.date().toString("yyyy-MM-dd"), self.end.date().toString("yyyy-MM-dd")

    def refresh(self) -> None:
        try:
            summary = self.reports.summary(*self._dates())
        except ValidationError as error:
            QMessageBox.warning(self, "Khoảng thời gian", str(error))
            return
        statuses = summary["status_counts"]
        self.summary_label.setText(
            f"{summary['patient_count']} bệnh nhân • "
            f"{summary['followup_count']} lần theo dõi • "
            f"Điểm giảm trung bình: {summary['average_change']} • "
            f"Cải thiện: {statuses['improved']} • Ổn định: {statuses['stable']} • "
            f"Nặng hơn: {statuses['worsened']} • Phản ứng bất lợi: "
            f"{summary['adverse_reaction_count']}"
        )
        status_labels = {
            "improved": "Cải thiện", "stable": "Ổn định", "worsened": "Nặng hơn",
            "monitoring": "Theo dõi", "completed": "Hoàn tất",
        }
        effect_labels = {
            "good": "Tốt", "partial": "Một phần", "none": "Không hiệu quả",
            "not_assessed": "Chưa đánh giá",
        }
        rows = summary["items"]
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (
                row["followup_date"], row["patient_code"], row["full_name"],
                row["visit_code"], row["symptom_score_before"], row["symptom_score_after"],
                status_labels.get(row["treatment_status"], row["treatment_status"]),
                effect_labels.get(row["effectiveness"], row["effectiveness"]),
            )
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def save(self) -> None:
        try:
            self.reports.create(
                *self._dates(), doctor_conclusion=self.conclusion.toPlainText(),
                reviewed_by=self.settings.doctor_name(),
            )
        except ValidationError as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))
            return
        self.conclusion.clear()
        QMessageBox.information(self, "Đã lưu", "Đã lưu báo cáo kết quả điều trị.")
