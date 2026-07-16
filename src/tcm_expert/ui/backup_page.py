from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.security import require_role


class BackupPage(QWidget):
    restored = Signal()

    def __init__(self, database: DatabaseManager):
        super().__init__()
        require_role("admin")
        self.database = database
        self.backup_dir = database.path.parent / "backups"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        title = QLabel("Sao lưu và phục hồi dữ liệu")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(QLabel("Chỉ quản trị viên được thực hiện. Dữ liệu bệnh nhân luôn được giữ nguyên."))
        actions = QHBoxLayout()
        backup = QPushButton("Tạo bản sao lưu")
        restore = QPushButton("Phục hồi từ tệp")
        refresh = QPushButton("Làm mới danh sách")
        backup.clicked.connect(self.create_backup)
        restore.clicked.connect(self.restore_backup)
        refresh.clicked.connect(self.refresh)
        actions.addWidget(backup)
        actions.addWidget(restore)
        actions.addWidget(refresh)
        actions.addStretch()
        layout.addLayout(actions)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(("Tên bản sao", "Thời gian", "Dung lượng"))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        layout.addWidget(QLabel("Phục hồi sẽ tự tạo bản sao an toàn và yêu cầu khởi động lại."))
        self.refresh()

    def refresh(self) -> None:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(self.backup_dir.glob("*.db"), key=lambda path: path.stat().st_mtime,
                       reverse=True)
        self.table.setRowCount(len(files))
        for row, path in enumerate(files):
            modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
            size = f"{path.stat().st_size / 1024:.1f} KB"
            for column, value in enumerate((path.name, modified, size)):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def create_backup(self) -> None:
        require_role("admin")
        default = self.backup_dir / f"tcm_expert_{datetime.now():%Y%m%d_%H%M%S}.db"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Tạo bản sao lưu", str(default), "SQLite Database (*.db)"
        )
        if not filename:
            return
        try:
            destination = self.database.create_backup(Path(filename))
            with self.database.transaction() as connection:
                self.database.audit(connection, "backup", "database", None,
                                    f"destination={destination.name}")
            self.refresh()
            QMessageBox.information(self, "Sao lưu thành công", f"Đã tạo: {destination.name}")
        except Exception as error:
            QMessageBox.critical(self, "Không thể sao lưu", str(error))

    def restore_backup(self) -> None:
        require_role("admin")
        filename, _ = QFileDialog.getOpenFileName(
            self, "Chọn bản sao phục hồi", str(self.backup_dir), "SQLite Database (*.db)"
        )
        if not filename:
            return
        try:
            metadata = self.database.validate_backup(Path(filename))
        except Exception as error:
            QMessageBox.critical(self, "Bản sao không hợp lệ", str(error))
            return
        answer = QMessageBox.warning(
            self, "Xác nhận phục hồi",
            f"Bản sao có {metadata['patient_count']} bệnh nhân.\n"
            "Dữ liệu hiện tại sẽ được thay thế. Tiếp tục?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            safety, _ = self.database.restore_backup(Path(filename))
            QMessageBox.information(
                self, "Phục hồi thành công",
                f"Đã tạo bản sao an toàn: {safety.name}\nỨng dụng sẽ đóng để khởi động lại.",
            )
            self.restored.emit()
        except Exception as error:
            QMessageBox.critical(self, "Không thể phục hồi", str(error))
