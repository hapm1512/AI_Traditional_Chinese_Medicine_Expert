from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget
)


class MainWindow(QMainWindow):
    def __init__(self, clinic_name: str):
        super().__init__()
        self.setWindowTitle("AI Traditional Chinese Medicine Expert")
        self.resize(1180, 720)
        self.setMinimumSize(960, 600)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._sidebar())
        layout.addWidget(self._dashboard(clinic_name), 1)
        self.setCentralWidget(root)

    def _sidebar(self) -> QWidget:
        side = QWidget(objectName="sidebar")
        side.setFixedWidth(240)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(18, 24, 18, 24)
        logo = QLabel("ĐÔNG Y AI")
        logo.setObjectName("title")
        layout.addWidget(logo)
        layout.addSpacing(24)
        for text in ("Tổng quan", "Tiếp nhận bệnh nhân", "Hỗ trợ chẩn đoán", "Tra cứu dược liệu", "Bài thuốc tham khảo", "Cài đặt"):
            layout.addWidget(QPushButton(text))
        layout.addStretch()
        layout.addWidget(QLabel("Phiên bản 0.1.0"))
        return side

    def _dashboard(self, clinic_name: str) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(36, 30, 36, 30)
        title = QLabel(clinic_name)
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Hệ thống hỗ trợ chuyên môn Y học cổ truyền")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(24)
        warning = QLabel("⚠ Kết quả và bài thuốc chỉ tham khảo. Bác sĩ phải phê duyệt điều trị.")
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        layout.addSpacing(24)
        layout.addWidget(self._card("Nền tảng sẵn sàng", "SQLite đã kết nối • Dữ liệu được lưu cục bộ"))
        layout.addWidget(self._card("Epic tiếp theo", "Xây dựng dữ liệu nền và quản lý danh mục"))
        layout.addStretch()
        footer = QLabel("Copyright Hai Pham • Clinical Decision Support")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer.setObjectName("subtitle")
        layout.addWidget(footer)
        return content

    @staticmethod
    def _card(title: str, body: str) -> QFrame:
        card = QFrame(objectName="card")
        card.setMinimumHeight(110)
        layout = QVBoxLayout(card)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 18px; font-weight: 600; color: #e4c982;")
        layout.addWidget(heading)
        layout.addWidget(QLabel(body))
        return card

