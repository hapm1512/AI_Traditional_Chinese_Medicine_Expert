from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tcm_expert import __display_version__
from tcm_expert.database import SettingsRepository
from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import ValidationError


class DoctorSetupDialog(QDialog):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.settings = SettingsRepository(database)
        self.setWindowTitle("Thiết lập bác sĩ sử dụng")
        self.setMinimumWidth(520)
        form = QFormLayout(self)
        notice = QLabel("Bắt buộc định danh bác sĩ trước khi sử dụng phần mềm.")
        notice.setWordWrap(True)
        form.addRow(notice)
        self.name = QLineEdit()
        self.license = QLineEdit()
        self.specialty = QLineEdit()
        self.workplace = QLineEdit()
        self.phone = QLineEdit()
        self.phone.setMaxLength(10)
        self.phone.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,10}")))
        form.addRow("Họ tên bác sĩ *", self.name)
        form.addRow("Giấy phép hành nghề *", self.license)
        form.addRow("Chuyên khoa", self.specialty)
        form.addRow("Cơ sở công tác", self.workplace)
        form.addRow("Điện thoại", self.phone)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def save(self) -> None:
        try:
            self.settings.save_doctor(
                {
                    "full_name": self.name.text(),
                    "license_number": self.license.text(),
                    "specialty": self.specialty.text(),
                    "workplace": self.workplace.text(),
                    "phone": self.phone.text(),
                }
            )
        except ValueError as error:
            QMessageBox.warning(self, "Thiếu thông tin", str(error))
            return
        self.accept()


class SettingsPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.database = database
        self.settings = SettingsRepository(database)
        self.group_id: int | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        title = QLabel("Cài đặt và bảo trì")
        title.setObjectName("title")
        layout.addWidget(title)
        test_notice = QLabel(
            "Chế độ build/test: chưa bắt buộc khai báo hoặc xác thực quyền bác sĩ."
        )
        test_notice.setObjectName("warning")
        test_notice.setWordWrap(True)
        layout.addWidget(test_notice)

        columns = QHBoxLayout()
        columns.addWidget(self._doctor_box(), 1)
        columns.addWidget(self._group_box(), 1)
        layout.addLayout(columns, 1)
        layout.addWidget(self._maintenance_box())
        layout.addWidget(self._ai_box())
        self.load_doctor()
        self.refresh_groups()
        self._check_database(show_message=False)

    def _ai_box(self) -> QGroupBox:
        box = QGroupBox("Nền tảng AI tham khảo")
        layout = QVBoxLayout(box)
        current = self.settings.ai_settings()
        self.ai_enabled = QCheckBox("Bật luồng đề xuất tham khảo")
        self.ai_enabled.setChecked(bool(current["enabled"]))
        self.ai_enabled.toggled.connect(self.settings.set_ai_enabled)
        layout.addWidget(self.ai_enabled)
        form = QFormLayout()
        self.ai_mode = QComboBox()
        self.ai_mode.addItem("Offline — Rule Engine", "offline")
        self.ai_mode.addItem("Kết nối mô-đun AI", "connected")
        self.ai_mode.setCurrentIndex(max(0, self.ai_mode.findData(current.get("mode", "offline"))))
        self.chat_base_url = QLineEdit(str(current.get("chat_base_url", "")))
        self.chat_model = QLineEdit(str(current.get("chat_model", "tcmchat")))
        self.opentcm_url = QLineEdit(str(current.get("opentcm_url", "")))
        self.tcmbank_url = QLineEdit(str(current.get("tcmbank_url", "")))
        self.symmap_url = QLineEdit(str(current.get("symmap_url", "")))
        self.ai_timeout = QSpinBox()
        self.ai_timeout.setRange(3, 120)
        self.ai_timeout.setSuffix(" giây")
        self.ai_timeout.setValue(int(current.get("timeout_seconds", 20)))
        form.addRow("Chế độ", self.ai_mode)
        form.addRow("Máy chủ TCMChat", self.chat_base_url)
        form.addRow("Mô hình", self.chat_model)
        form.addRow("OpenTCM GraphRAG", self.opentcm_url)
        form.addRow("TCMBank", self.tcmbank_url)
        form.addRow("SymMap", self.symmap_url)
        form.addRow("Thời gian chờ", self.ai_timeout)
        layout.addLayout(form)
        save = QPushButton("Lưu cấu hình AI")
        save.clicked.connect(self.save_ai_config)
        layout.addWidget(save)
        note = QLabel("Việt–Trung → TCMChat → OpenTCM/TCMBank/SymMap → Rule Engine → bác sĩ duyệt. AI không chẩn đoán, đặt liều, kê đơn hoặc tự phê duyệt. Bắt buộc bác sĩ kiểm tra và phê duyệt trước khi sử dụng.")
        note.setWordWrap(True)
        note.setObjectName("warning")
        layout.addWidget(note)
        return box

    def save_ai_config(self) -> None:
        try:
            self.settings.save_ai_config(
                {
                    "mode": self.ai_mode.currentData(),
                    "chat_base_url": self.chat_base_url.text(),
                    "chat_model": self.chat_model.text(),
                    "opentcm_url": self.opentcm_url.text(),
                    "tcmbank_url": self.tcmbank_url.text(),
                    "symmap_url": self.symmap_url.text(),
                    "timeout_seconds": self.ai_timeout.value(),
                }
            )
        except (ValueError, ValidationError) as error:
            QMessageBox.warning(self, "Cấu hình chưa hợp lệ", str(error))
            return
        QMessageBox.information(self, "Đã lưu", "Đã cập nhật cấu hình mô-đun AI.")

    def _doctor_box(self) -> QGroupBox:
        box = QGroupBox("Hồ sơ bác sĩ sử dụng")
        form = QFormLayout(box)
        self.doctor_name = QLineEdit()
        self.license_number = QLineEdit()
        self.specialty = QLineEdit()
        self.workplace = QLineEdit()
        self.phone = QLineEdit()
        self.phone.setMaxLength(10)
        self.phone.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,10}")))
        form.addRow("Họ tên bác sĩ *", self.doctor_name)
        form.addRow("Giấy phép hành nghề *", self.license_number)
        form.addRow("Chuyên khoa", self.specialty)
        form.addRow("Cơ sở công tác", self.workplace)
        form.addRow("Điện thoại", self.phone)
        save = QPushButton("Lưu hồ sơ bác sĩ")
        save.clicked.connect(self.save_doctor)
        form.addRow(save)
        return box

    def _group_box(self) -> QGroupBox:
        box = QGroupBox("Quy định mã nhóm bệnh")
        layout = QVBoxLayout(box)
        form = QFormLayout()
        self.group_name = QLineEdit()
        self.group_prefix = QLineEdit()
        self.group_prefix.setMaxLength(6)
        self.group_prefix.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"[A-Za-z]{0,6}"))
        )
        form.addRow("Tên nhóm bệnh *", self.group_name)
        form.addRow("Mã cố định *", self.group_prefix)
        layout.addLayout(form)
        actions = QHBoxLayout()
        new = QPushButton("Nhập mới")
        new.clicked.connect(self.clear_group)
        save = QPushButton("Lưu quy định")
        save.clicked.connect(self.save_group)
        actions.addWidget(new)
        actions.addWidget(save)
        layout.addLayout(actions)
        self.group_table = QTableWidget(0, 2)
        self.group_table.setHorizontalHeaderLabels(("Nhóm bệnh", "Mã"))
        self.group_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.group_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.group_table.horizontalHeader().setStretchLastSection(True)
        self.group_table.itemSelectionChanged.connect(self.load_group)
        layout.addWidget(self.group_table)
        return box

    def _maintenance_box(self) -> QGroupBox:
        box = QGroupBox("Bảo trì dữ liệu")
        layout = QHBoxLayout(box)
        layout.addWidget(QLabel(f"Phiên bản {__display_version__}"))
        self.status = QLabel()
        layout.addWidget(self.status, 1)
        check = QPushButton("Kiểm tra cơ sở dữ liệu")
        check.clicked.connect(self._check_database)
        backup = QPushButton("Sao lưu cơ sở dữ liệu")
        backup.clicked.connect(self._backup_database)
        layout.addWidget(check)
        layout.addWidget(backup)
        return box

    def load_doctor(self) -> None:
        row = self.settings.doctor()
        self.doctor_name.setText(str(row.get("full_name", "")))
        self.license_number.setText(str(row.get("license_number", "")))
        self.specialty.setText(str(row.get("specialty", "")))
        self.workplace.setText(str(row.get("workplace", "")))
        self.phone.setText(str(row.get("phone", "")))

    def save_doctor(self) -> None:
        try:
            self.settings.save_doctor(
                {
                    "full_name": self.doctor_name.text(),
                    "license_number": self.license_number.text(),
                    "specialty": self.specialty.text(),
                    "workplace": self.workplace.text(),
                    "phone": self.phone.text(),
                }
            )
        except ValueError as error:
            QMessageBox.warning(self, "Chưa thể lưu", str(error))
            return
        QMessageBox.information(self, "Đã lưu", "Đã cập nhật hồ sơ bác sĩ sử dụng.")

    def refresh_groups(self) -> None:
        rows = self.settings.groups()
        self.group_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, value in enumerate((row["name"], row["prefix"])):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, row["id"])
                self.group_table.setItem(row_index, column, item)

    def load_group(self) -> None:
        items = self.group_table.selectedItems()
        if not items:
            return
        self.group_id = int(items[0].data(Qt.ItemDataRole.UserRole))
        self.group_name.setText(items[0].text())
        self.group_prefix.setText(items[1].text())

    def clear_group(self) -> None:
        self.group_id = None
        self.group_name.clear()
        self.group_prefix.clear()
        self.group_name.setFocus()

    def save_group(self) -> None:
        try:
            self.settings.save_group(
                self.group_name.text(), self.group_prefix.text(), self.group_id
            )
        except ValueError as error:
            QMessageBox.warning(self, "Chưa thể lưu", str(error))
            return
        self.clear_group()
        self.refresh_groups()

    def _check_database(self, _checked: bool = False, show_message: bool = True) -> None:
        try:
            result = self.database.integrity_check()
            healthy = result.lower() == "ok"
            self.status.setText("Cơ sở dữ liệu: An toàn" if healthy else f"Có lỗi: {result}")
            if show_message:
                QMessageBox.information(self, "Kiểm tra hoàn tất", self.status.text())
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
