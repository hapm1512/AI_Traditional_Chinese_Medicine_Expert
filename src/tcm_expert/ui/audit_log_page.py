from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from tcm_expert.database.audit_repository import AuditRepository


class AuditLogPage(QWidget):
    ACTIONS = {
        "": "Tất cả thao tác", "login": "Đăng nhập", "logout": "Đăng xuất",
        "save": "Lưu", "delete": "Xóa", "activate": "Mở khóa",
        "deactivate": "Khóa", "change_password": "Đổi mật khẩu",
    }

    def __init__(self, database):
        super().__init__()
        self.repository = AuditRepository(database)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        title = QLabel("Nhật ký hệ thống")
        title.setObjectName("title")
        layout.addWidget(title)
        note = QLabel("Nhật ký chỉ đọc — không thể sửa hoặc xóa.")
        layout.addWidget(note)
        filters = QHBoxLayout()
        self.actor = QComboBox()
        self.action = QComboBox()
        for value, text in self.ACTIONS.items():
            self.action.addItem(text, value)
        self.date_from, self.date_to = QDateEdit(), QDateEdit()
        for field in (self.date_from, self.date_to):
            field.setCalendarPopup(True)
            field.setDisplayFormat("dd/MM/yyyy")
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        refresh = QPushButton("Lọc nhật ký")
        export = QPushButton("Xuất CSV")
        refresh.clicked.connect(self.refresh)
        export.clicked.connect(self.export_csv)
        for label, widget in (("Người dùng", self.actor), ("Thao tác", self.action),
                              ("Từ ngày", self.date_from), ("Đến ngày", self.date_to)):
            filters.addWidget(QLabel(label)); filters.addWidget(widget)
        filters.addWidget(refresh); filters.addWidget(export)
        layout.addLayout(filters)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(("Thời gian", "Người dùng", "Thao tác", "Đối tượng", "Mã", "Chi tiết"))
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.show_detail)
        layout.addWidget(self.table, 1)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(90)
        self.detail.setPlaceholderText("Chọn một dòng để xem chi tiết.")
        layout.addWidget(self.detail)
        self.load_actors()
        self.refresh()

    def load_actors(self) -> None:
        selected = self.actor.currentData() or ""
        self.actor.clear(); self.actor.addItem("Tất cả người dùng", "")
        for actor in self.repository.actors():
            self.actor.addItem(actor, actor)
        self.actor.setCurrentIndex(max(0, self.actor.findData(selected)))

    def filters(self) -> dict:
        return {"actor": self.actor.currentData() or "", "action": self.action.currentData() or "",
                "date_from": self.date_from.date().toString("yyyy-MM-dd"),
                "date_to": self.date_to.date().toString("yyyy-MM-dd")}

    def refresh(self) -> None:
        rows = self.repository.list_entries(**self.filters())
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (row["created_at"], row["actor_username"], row["action"],
                      row["entity_type"], row["entity_id"] or "", row["detail"])
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value)); item.setData(Qt.ItemDataRole.UserRole, row["detail"])
                self.table.setItem(row_index, column, item)

    def show_detail(self) -> None:
        items = self.table.selectedItems()
        self.detail.setPlainText(str(items[0].data(Qt.ItemDataRole.UserRole))) if items else self.detail.clear()

    def export_csv(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Xuất nhật ký", "nhat_ky_he_thong.csv", "CSV (*.csv)")
        if not filename:
            return
        count = self.repository.export_csv(Path(filename), **self.filters())
        QMessageBox.information(self, "Đã xuất", f"Đã xuất {count} dòng nhật ký.")
