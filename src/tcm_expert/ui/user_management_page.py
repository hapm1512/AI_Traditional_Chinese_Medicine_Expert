from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from tcm_expert.database.user_repository import UserRepository


class UserManagementPage(QWidget):
    def __init__(self, database):
        super().__init__()
        self.users = UserRepository(database)
        self.user_id: int | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        title = QLabel("Quản lý người dùng")
        title.setObjectName("title")
        layout.addWidget(title)
        form = QFormLayout()
        self.username, self.full_name, self.password = QLineEdit(), QLineEdit(), QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.role = QComboBox()
        self.role.addItem("Quản trị", "admin")
        self.role.addItem("Bác sĩ", "doctor")
        self.role.addItem("Y tá", "nurse")
        form.addRow("Tên đăng nhập", self.username)
        form.addRow("Họ tên", self.full_name)
        form.addRow("Vai trò", self.role)
        form.addRow("Mật khẩu mới", self.password)
        layout.addLayout(form)
        actions = QHBoxLayout()
        new = QPushButton("Nhập mới")
        save = QPushButton("Lưu tài khoản")
        toggle = QPushButton("Khóa / Mở khóa")
        delete = QPushButton("Xóa tài khoản")
        new.clicked.connect(self.clear)
        save.clicked.connect(self.save)
        toggle.clicked.connect(self.toggle_active)
        delete.clicked.connect(self.delete_user)
        actions.addWidget(new); actions.addWidget(save); actions.addWidget(toggle)
        actions.addWidget(delete)
        layout.addLayout(actions)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(("Tên đăng nhập", "Họ tên", "Vai trò", "Trạng thái", "Đăng nhập cuối"))
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.load)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        rows = self.users.list_users()
        self.table.setRowCount(len(rows))
        roles = {"admin": "Quản trị", "doctor": "Bác sĩ", "nurse": "Y tá"}
        for i, row in enumerate(rows):
            values = (row["username"], row["full_name"], roles[row["role"]], "Hoạt động" if row["active"] else "Đã khóa", row["last_login_at"] or "")
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value)); item.setData(Qt.ItemDataRole.UserRole, (row["id"], row["role"], bool(row["active"])))
                self.table.setItem(i, col, item)

    def load(self):
        items = self.table.selectedItems()
        if not items: return
        self.user_id, role, _active = items[0].data(Qt.ItemDataRole.UserRole)
        self.username.setText(items[0].text()); self.full_name.setText(items[1].text())
        self.role.setCurrentIndex(max(0, self.role.findData(role))); self.password.clear()

    def clear(self):
        self.user_id = None; self.username.clear(); self.full_name.clear(); self.password.clear(); self.role.setCurrentIndex(2)

    def save(self):
        try:
            self.users.save(self.username.text(), self.full_name.text(), self.role.currentData(), self.password.text(), self.user_id)
        except Exception as error:
            QMessageBox.warning(self, "Chưa thể lưu", str(error)); return
        self.clear(); self.refresh(); QMessageBox.information(self, "Đã lưu", "Đã cập nhật tài khoản.")

    def toggle_active(self):
        items = self.table.selectedItems()
        if not items: return
        user_id, _role, active = items[0].data(Qt.ItemDataRole.UserRole)
        try: self.users.set_active(int(user_id), not active)
        except ValueError as error: QMessageBox.warning(self, "Chưa thể thay đổi", str(error)); return
        self.refresh()

    def delete_user(self):
        items = self.table.selectedItems()
        if not items:
            QMessageBox.warning(self, "Chưa chọn tài khoản", "Hãy chọn tài khoản cần xóa.")
            return
        user_id, _role, _active = items[0].data(Qt.ItemDataRole.UserRole)
        username = items[0].text()
        full_name = items[1].text()
        answer = QMessageBox.question(
            self,
            "Xác nhận xóa tài khoản",
            f"Xóa vĩnh viễn tài khoản {username} — {full_name}?\n"
            "Nhật ký thao tác trước đây vẫn được giữ.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.users.delete(int(user_id))
        except ValueError as error:
            QMessageBox.warning(self, "Không thể xóa", str(error))
            return
        self.clear()
        self.refresh()
        QMessageBox.information(self, "Đã xóa", "Tài khoản đã được xóa khỏi hệ thống.")
