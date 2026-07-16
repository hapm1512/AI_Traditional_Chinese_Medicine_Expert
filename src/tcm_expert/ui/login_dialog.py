from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QMessageBox,
)

from tcm_expert.database.user_repository import UserRepository
from tcm_expert.security import UserSession


class LoginDialog(QDialog):
    def __init__(self, users: UserRepository, bootstrap_created: bool = False, parent=None):
        super().__init__(parent)
        self.users = users
        self.session: UserSession | None = None
        self.setWindowTitle("Đăng nhập hệ thống")
        self.setMinimumWidth(420)
        form = QFormLayout(self)
        title = QLabel("AI Traditional Chinese Medicine Expert")
        title.setObjectName("title")
        form.addRow(title)
        if bootstrap_created:
            notice = QLabel("Lần đầu: admin / Admin@123\nHệ thống yêu cầu đổi mật khẩu.")
            notice.setObjectName("warning")
            form.addRow(notice)
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.username.returnPressed.connect(self.password.setFocus)
        self.password.returnPressed.connect(self.login)
        form.addRow("Tên đăng nhập", self.username)
        form.addRow("Mật khẩu", self.password)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Đăng nhập")
        buttons.accepted.connect(self.login)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.username.setFocus()

    def login(self) -> None:
        try:
            self.session = self.users.authenticate(self.username.text(), self.password.text())
        except ValueError as error:
            self.password.clear()
            QMessageBox.warning(self, "Đăng nhập thất bại", str(error))
            return
        self.accept()


class ChangePasswordDialog(QDialog):
    def __init__(self, users: UserRepository, user_id: int, required: bool = False, parent=None):
        super().__init__(parent)
        self.users, self.user_id, self.required = users, user_id, required
        self.setWindowTitle("Đổi mật khẩu")
        form = QFormLayout(self)
        if required:
            form.addRow(QLabel("Bắt buộc đổi mật khẩu trước khi sử dụng."))
        self.password = QLineEdit()
        self.confirm = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Mật khẩu mới", self.password)
        form.addRow("Nhập lại", self.confirm)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def reject(self) -> None:
        if self.required:
            return
        super().reject()

    def save(self) -> None:
        if self.password.text() != self.confirm.text():
            QMessageBox.warning(self, "Chưa thể lưu", "Mật khẩu nhập lại không khớp.")
            return
        try:
            self.users.change_password(self.user_id, self.password.text())
        except ValueError as error:
            QMessageBox.warning(self, "Chưa thể lưu", str(error))
            return
        self.accept()
