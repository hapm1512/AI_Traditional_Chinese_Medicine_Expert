from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database.dashboard_repository import DashboardRepository
from tcm_expert.database.manager import DatabaseManager


class DashboardPage(QWidget):
    navigate = Signal(int)

    def __init__(self, clinic_name: str, database: DatabaseManager):
        super().__init__()
        self.repository = DashboardRepository(database)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        title = QLabel(clinic_name)
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Bảng điều hành phòng khám hôm nay")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        self.cards = QGridLayout()
        self.card_values: dict[str, QLabel] = {}
        definitions = (
            ("today", "Lịch hẹn hôm nay"),
            ("overdue", "Lịch đã quá giờ"),
            ("pending_reminder", "Chưa nhắc trong 7 ngày"),
            ("under_treatment", "Hồ sơ đang điều trị"),
            ("monitoring", "Hồ sơ đang theo dõi"),
            ("patients", "Tổng bệnh nhân"),
        )
        for index, (key, text) in enumerate(definitions):
            self.cards.addWidget(self._summary_card(key, text), index // 3, index % 3)
        layout.addLayout(self.cards)

        actions = QHBoxLayout()
        heading = QLabel("Việc cần xử lý")
        heading.setStyleSheet("font-size: 18px; font-weight: 600; color: #e4c982;")
        actions.addWidget(heading)
        actions.addStretch()
        refresh = QPushButton("Làm mới")
        refresh.clicked.connect(self.refresh)
        appointments = QPushButton("Mở lịch tái khám")
        appointments.clicked.connect(lambda: self.navigate.emit(10))
        patients = QPushButton("Mở bệnh nhân")
        patients.clicked.connect(lambda: self.navigate.emit(1))
        actions.addWidget(refresh)
        actions.addWidget(appointments)
        actions.addWidget(patients)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ("Mức độ", "Ngày giờ", "Mã BN", "Bệnh nhân", "Lần khám", "Lý do")
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.navigate.emit(10))
        layout.addWidget(self.table, 1)
        warning = QLabel("⚠ Dashboard hỗ trợ vận hành, không thay thế quyết định bác sĩ.")
        warning.setObjectName("warning")
        layout.addWidget(warning)
        self.refresh()

    def _summary_card(self, key: str, title: str) -> QFrame:
        card = QFrame(objectName="card")
        card.setMinimumHeight(86)
        layout = QVBoxLayout(card)
        label = QLabel(title)
        label.setObjectName("subtitle")
        value = QLabel("0")
        value.setStyleSheet("font-size: 26px; font-weight: 700; color: #e4c982;")
        self.card_values[key] = value
        layout.addWidget(label)
        layout.addWidget(value)
        return card

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        summary = self.repository.summary()
        for key, label in self.card_values.items():
            label.setText(str(summary.get(key, 0)))
        rows = self.repository.attention_items()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            try:
                scheduled = datetime.fromisoformat(row["scheduled_at"]).strftime("%d/%m/%Y %H:%M")
            except ValueError:
                scheduled = row["scheduled_at"]
            values = (
                "Quá giờ" if row["priority"] == "overdue" else "Hôm nay",
                scheduled,
                row["patient_code"],
                row["full_name"],
                row["visit_code"],
                row["reason"],
            )
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(str(value)))
