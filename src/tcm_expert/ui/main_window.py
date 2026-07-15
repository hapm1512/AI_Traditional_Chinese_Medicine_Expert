from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.ui.patient_page import PatientPage
from tcm_expert.ui.diagnosis_page import DiagnosisPage


class MainWindow(QMainWindow):
    def __init__(
        self,
        clinic_name: str,
        database: DatabaseManager,
        database_counts: dict[str, int] | None = None,
    ):
        super().__init__()
        self.setWindowTitle("AI Traditional Chinese Medicine Expert")
        self.resize(1180, 720)
        self.setMinimumSize(960, 600)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._dashboard(clinic_name, database_counts or {}))
        self.pages.addWidget(PatientPage(database))
        self.pages.addWidget(DiagnosisPage(database))
        layout.addWidget(self._sidebar())
        layout.addWidget(self.pages, 1)
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
        for index, text in enumerate((
            "Tổng quan",
            "Quản lý bệnh nhân",
            "Hỗ trợ chẩn đoán",
            "Tra cứu dược liệu",
            "Bài thuốc tham khảo",
            "Cài đặt",
        )):
            button = QPushButton(text)
            button.setCheckable(index < 3)
            if index < 3:
                button.clicked.connect(
                    lambda _checked=False, page=index: self.pages.setCurrentIndex(page)
                )
            if index == 0:
                button.setChecked(True)
            layout.addWidget(button)
        layout.addStretch()
        layout.addWidget(QLabel("Phiên bản 0.4.0"))
        return side

    def _dashboard(self, clinic_name: str, database_counts: dict[str, int]) -> QWidget:
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
        warning = QLabel(
            "⚠ Kết quả chỉ tham khảo. Bác sĩ phải phê duyệt điều trị."
        )
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        layout.addSpacing(24)
        layout.addWidget(
            self._card(
                "Nền tảng dữ liệu sẵn sàng",
                "SQLite đã kết nối • Dữ liệu bệnh nhân lưu cục bộ",
            )
        )
        summary = (
            f"{database_counts.get('materia_medica', 0)} dược liệu • "
            f"{database_counts.get('formulas', 0)} phương thuốc • "
            f"{database_counts.get('tcm_syndromes', 0)} hội chứng mẫu"
        )
        layout.addWidget(self._card("Danh mục tham chiếu", summary))
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
