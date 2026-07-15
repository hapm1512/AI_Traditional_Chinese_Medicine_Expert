from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tcm_expert import __display_version__
from tcm_expert.database.manager import DatabaseManager


class SettingsPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.database = database
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 30)
        title = QLabel("Cài đặt và bảo trì")
        title.setObjectName("title")
        layout.addWidget(title)

        form = QFormLayout()
        form.addRow("Phiên bản", QLabel(__display_version__))
        path = QLabel(str(database.path))
        path.setWordWrap(True)
        form.addRow("Cơ sở dữ liệu", path)
        self.status = QLabel()
        form.addRow("Tình trạng", self.status)
        layout.addLayout(form)

        check_button = QPushButton("Kiểm tra cơ sở dữ liệu")
        check_button.clicked.connect(self._check_database)
        layout.addWidget(check_button)
        backup_button = QPushButton("Sao lưu cơ sở dữ liệu")
        backup_button.clicked.connect(self._backup_database)
        layout.addWidget(backup_button)
        layout.addStretch()
        self._check_database(show_message=False)

    def _check_database(self, _checked: bool = False, show_message: bool = True) -> None:
        try:
            result = self.database.integrity_check()
            healthy = result.lower() == "ok"
            self.status.setText("An toàn" if healthy else f"Có lỗi: {result}")
            if show_message:
                if healthy:
                    QMessageBox.information(self, "Kiểm tra hoàn tất", "Cơ sở dữ liệu an toàn.")
                else:
                    QMessageBox.warning(self, "Phát hiện lỗi", result)
        except Exception as error:
            self.status.setText("Không thể kiểm tra")
            if show_message:
                QMessageBox.critical(self, "Không thể kiểm tra", str(error))

    def _backup_database(self) -> None:
        try:
            destination = self.database.create_backup()
            QMessageBox.information(self, "Sao lưu hoàn tất", f"Đã lưu tại:\n{destination}")
        except Exception as error:
            QMessageBox.critical(self, "Không thể sao lưu", str(error))
