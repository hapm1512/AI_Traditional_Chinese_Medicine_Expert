from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem

from tcm_expert.ai.health import test_ai_connections


def install_ai_safety_ui() -> None:
    from tcm_expert.ui.settings_page import SettingsPage

    if getattr(SettingsPage, "_epic20_installed", False):
        return
    original = SettingsPage._ai_box

    def ai_box(self):
        box = original(self)
        button = QPushButton("Kiểm tra các mô-đun AI")
        button.clicked.connect(self.test_ai_modules)
        self.ai_status = QTableWidget(0, 4)
        self.ai_status.setHorizontalHeaderLabels(
            ("Mô-đun", "Trạng thái", "Phản hồi", "Chi tiết")
        )
        self.ai_status.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ai_status.horizontalHeader().setStretchLastSection(True)
        self.ai_status.setMaximumHeight(170)
        box.layout().addWidget(button)
        box.layout().addWidget(self.ai_status)
        return box

    def test_modules(self):
        try:
            self.save_ai_config()
            rows = test_ai_connections(self.database)
        except Exception as error:
            QMessageBox.warning(self, "Không thể kiểm tra", str(error))
            return
        self.ai_status.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (row["name"], row["status"], f"{row['latency_ms']} ms", row["detail"])
            for column, value in enumerate(values):
                self.ai_status.setItem(row_index, column, QTableWidgetItem(str(value)))

    SettingsPage._ai_box = ai_box
    SettingsPage.test_ai_modules = test_modules
    SettingsPage._epic20_installed = True
