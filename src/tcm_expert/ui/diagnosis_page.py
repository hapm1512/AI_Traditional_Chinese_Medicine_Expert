from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database import ConsultationRepository, PatientRepository, SyndromeRepository
from tcm_expert.database.manager import DatabaseManager
from tcm_expert.services.syndrome_reasoner import suggest

METHODS = (
    ("vong", "Vọng chẩn", "Sắc diện, hình thể, lưỡi..."),
    ("van", "Văn chẩn", "Âm thanh, hơi thở, mùi..."),
    ("van_hoi", "Vấn chẩn", "Hàn nhiệt, ăn ngủ, đau, đại tiểu tiện..."),
    ("thiet", "Thiết chẩn", "Mạch, sờ nắn, vị trí đau..."),
)


class DiagnosticEntryDialog(QMessageBox):
    """Kept out intentionally; entries are edited inline for faster clinical input."""


class MethodEditor(QWidget):
    def __init__(self, repository: ConsultationRepository, method: str, hint: str):
        super().__init__()
        self.repository = repository
        self.method = method
        self.consultation_id: int | None = None
        layout = QVBoxLayout(self)
        hint_label = QLabel(hint)
        hint_label.setObjectName("subtitle")
        layout.addWidget(hint_label)
        form = QFormLayout()
        self.category = QLineEdit()
        self.category.setPlaceholderText("Ví dụ: Lưỡi, mạch, giọng nói")
        self.finding = QTextEdit()
        self.finding.setMaximumHeight(76)
        self.severity = QSpinBox()
        self.severity.setRange(0, 10)
        self.note = QLineEdit()
        form.addRow("Nhóm *", self.category)
        form.addRow("Kết quả *", self.finding)
        form.addRow("Mức độ 0–10", self.severity)
        form.addRow("Ghi chú", self.note)
        entry_box = QGroupBox("Nhập thông tin Văn chẩn")
        entry_box.setLayout(form)
        layout.addWidget(entry_box)
        buttons = QHBoxLayout()
        add = QPushButton("Thêm kết quả")
        add.clicked.connect(self.add_entry)
        remove = QPushButton("Xóa mục chọn")
        remove.clicked.connect(self.remove_entry)
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(("Nhóm", "Kết quả", "Mức độ", "Ghi chú"))
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMaximumHeight(190)
        self.empty_table = QLabel("Chưa có dữ liệu Văn chẩn đã lưu.")
        self.empty_table.setObjectName("subtitle")
        layout.addWidget(self.empty_table)
        layout.addWidget(self.table)
        layout.addStretch()

    def set_consultation(self, consultation_id: int | None) -> None:
        self.consultation_id = consultation_id
        self.refresh()

    def refresh(self) -> None:
        rows = (
            []
            if self.consultation_id is None
            else [
                row
                for row in self.repository.diagnostic_entries(self.consultation_id)
                if row["method"] == self.method
            ]
        )
        self.table.setRowCount(len(rows))
        self.table.setVisible(bool(rows))
        self.empty_table.setVisible(not rows)
        for row_index, entry in enumerate(rows):
            values = (entry["category"], entry["finding"], entry.get("severity"), entry["note"])
            for column, value in enumerate(values):
                item = QTableWidgetItem("" if value is None else str(value))
                item.setData(Qt.ItemDataRole.UserRole, entry["id"])
                self.table.setItem(row_index, column, item)

    def add_entry(self) -> None:
        if self.consultation_id is None:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn hồ sơ khám trước.")
            return
        try:
            self.repository.add_diagnostic_entry(
                self.consultation_id,
                self.method,
                self.category.text(),
                self.finding.toPlainText(),
                self.severity.value(),
                self.note.text(),
            )
            self.category.clear()
            self.finding.clear()
            self.severity.setValue(0)
            self.note.clear()
            self.refresh()
        except Exception as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))

    def remove_entry(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        self.repository.delete_diagnostic_entry(int(items[0].data(Qt.ItemDataRole.UserRole)))
        self.refresh()


class ListeningSmellingEditor(QWidget):
    TYPES = (
        ("voice", "Giọng nói"),
        ("breathing", "Hơi thở"),
        ("cough", "Ho"),
        ("sputum", "Đờm"),
        ("hiccup", "Nấc"),
        ("pathological_sound", "Tiếng bệnh lý"),
        ("odor", "Mùi"),
        ("other", "Khác"),
    )
    CHARACTERISTICS = {
        "voice": ("Bình thường", "Yếu", "Khàn", "Nhỏ", "Cao", "Đứt quãng"),
        "breathing": ("Bình thường", "Ngắn", "Gấp", "Yếu", "Khò khè", "Nặng nhọc"),
        "cough": ("Ho khan", "Ho có đờm", "Ho yếu", "Ho dữ dội", "Ho từng cơn"),
        "sputum": ("Trắng", "Vàng", "Trong", "Đặc", "Loãng", "Có mùi"),
        "hiccup": ("Nhẹ", "Mạnh", "Liên tục", "Từng cơn"),
        "pathological_sound": ("Khò khè", "Thở rít", "Rên", "Ợ", "Tiếng khác"),
        "odor": ("Không bất thường", "Hôi", "Chua", "Tanh", "Khét", "Khác"),
        "other": ("Khác",),
    }

    def __init__(self, repository: ConsultationRepository):
        super().__init__()
        self.repository = repository
        self.consultation_id: int | None = None
        layout = QVBoxLayout(self)
        hint = QLabel("Y tá nhập thủ công; chưa sử dụng micro hoặc thiết bị ngoại vi.")
        hint.setObjectName("subtitle")
        layout.addWidget(hint)
        form = QFormLayout()
        self.finding_type = QComboBox()
        for key, label in self.TYPES:
            self.finding_type.addItem(label, key)
        self.finding_type.currentIndexChanged.connect(self._load_characteristics)
        self.characteristic = QComboBox()
        self.characteristic.setEditable(True)
        self.frequency = QComboBox()
        self.frequency.setEditable(True)
        self.frequency.addItems(
            ("", "Một lần", "Thỉnh thoảng", "Từng cơn", "Thường xuyên", "Liên tục")
        )
        self.severity = QSpinBox()
        self.severity.setRange(0, 10)
        self.duration = QLineEdit()
        self.duration.setPlaceholderText("Ví dụ: 3 ngày")
        self.odor = QLineEdit()
        self.odor.setPlaceholderText("Mùi liên quan nếu có")
        self.recorded_by = QLineEdit()
        self.recorded_by.setPlaceholderText("Họ tên y tá/người nhập")
        self.note = QTextEdit()
        self.note.setMaximumHeight(58)
        form.addRow("Loại *", self.finding_type)
        form.addRow("Đặc điểm *", self.characteristic)
        form.addRow("Tần suất", self.frequency)
        form.addRow("Mức độ 0–10", self.severity)
        form.addRow("Thời gian", self.duration)
        form.addRow("Mùi", self.odor)
        form.addRow("Người ghi nhận *", self.recorded_by)
        form.addRow("Ghi chú", self.note)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        add = QPushButton("Lưu Văn chẩn")
        add.clicked.connect(self.add_finding)
        remove = QPushButton("Xóa mục chọn")
        remove.clicked.connect(self.remove_finding)
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ("Loại", "Đặc điểm", "Tần suất", "Mức độ", "Thời gian", "Người nhập", "Thời điểm")
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self._load_characteristics()

    def _load_characteristics(self) -> None:
        current = self.characteristic.currentText() if self.characteristic.count() else ""
        self.characteristic.clear()
        self.characteristic.addItems(self.CHARACTERISTICS[self.finding_type.currentData()])
        if current:
            self.characteristic.setEditText(current)

    def set_consultation(self, consultation_id: int | None) -> None:
        self.consultation_id = consultation_id
        self.refresh()

    def refresh(self) -> None:
        rows = (
            []
            if self.consultation_id is None
            else (self.repository.listening_smelling_findings(self.consultation_id))
        )
        labels = dict(self.TYPES)
        self.table.setRowCount(len(rows))
        for row_index, entry in enumerate(rows):
            values = (
                labels.get(entry["finding_type"], entry["finding_type"]),
                entry["characteristic"],
                entry["frequency"],
                entry["severity"],
                entry["duration"],
                entry["recorded_by"],
                entry["recorded_at"],
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                item.setData(Qt.ItemDataRole.UserRole, entry["id"])
                self.table.setItem(row_index, column, item)

    def add_finding(self) -> None:
        if self.consultation_id is None:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn hồ sơ khám trước.")
            return
        try:
            self.repository.add_listening_smelling_finding(
                self.consultation_id,
                {
                    "finding_type": self.finding_type.currentData(),
                    "characteristic": self.characteristic.currentText(),
                    "frequency": self.frequency.currentText(),
                    "severity": self.severity.value(),
                    "duration": self.duration.text(),
                    "odor": self.odor.text(),
                    "recorded_by": self.recorded_by.text(),
                    "note": self.note.toPlainText(),
                },
            )
            self.severity.setValue(0)
            self.duration.clear()
            self.odor.clear()
            self.note.clear()
            self.refresh()
        except Exception as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))

    def remove_finding(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        self.repository.delete_listening_smelling_finding(
            int(items[0].data(Qt.ItemDataRole.UserRole))
        )
        self.refresh()


class InquiryEditor(QWidget):
    FIELDS = (
        ("cold_heat", "Hàn nhiệt", "Sợ lạnh, phát sốt, nóng trong..."),
        ("sweating", "Mồ hôi", "Có/không, tự hãn, đạo hãn..."),
        ("head_body", "Đầu và thân", "Đau đầu, chóng mặt, đau mỏi..."),
        ("chest_abdomen", "Ngực và bụng", "Tức ngực, hồi hộp, đau bụng..."),
        ("appetite_taste", "Ăn uống, khẩu vị", "Ăn ít, đầy bụng, vị miệng..."),
        ("thirst_drink", "Khát và uống", "Mức khát, thích nóng/lạnh..."),
        ("sleep", "Giấc ngủ", "Khó ngủ, hay tỉnh, nhiều mộng..."),
        ("stool", "Đại tiện", "Tần suất, táo/lỏng, màu sắc..."),
        ("urination", "Tiểu tiện", "Tần suất, lượng, màu, đau buốt..."),
        ("ears_eyes", "Tai và mắt", "Ù tai, nghe kém, hoa mắt..."),
        ("gynecology", "Kinh, đới, thai sản", "Chu kỳ, lượng, màu, đau..."),
        ("onset_progress", "Khởi phát, diễn tiến", "Bắt đầu, yếu tố tăng giảm..."),
        ("current_treatment", "Điều trị hiện tại", "Thuốc đang dùng, đáp ứng..."),
        ("red_flags", "Dấu hiệu cảnh báo", "Đau ngực, khó thở, ngất..."),
        ("note", "Ghi chú khác", "Thông tin Vấn chẩn bổ sung"),
    )

    def __init__(self, repository: ConsultationRepository):
        super().__init__()
        self.repository = repository
        self.consultation_id: int | None = None
        outer = QVBoxLayout(self)
        hint = QLabel("Nhập theo Thập vấn; bác sĩ xác minh trước quyết định điều trị.")
        hint.setObjectName("subtitle")
        outer.addWidget(hint)
        content = QWidget()
        form = QGridLayout(content)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)
        self.inputs: dict[str, QTextEdit] = {}
        for index, (key, label, placeholder) in enumerate(self.FIELDS):
            field = QTextEdit()
            field.setPlaceholderText(placeholder)
            field.setMaximumHeight(54)
            self.inputs[key] = field
            row, pair = divmod(index, 2)
            column = pair * 2
            form.addWidget(QLabel(label), row, column)
            form.addWidget(field, row, column + 1)
        self.recorded_by = QLineEdit()
        self.recorded_by.setPlaceholderText("Họ tên bác sĩ/y tá hỏi bệnh")
        last_row = (len(self.FIELDS) + 1) // 2
        form.addWidget(QLabel("Người hỏi *"), last_row, 0)
        form.addWidget(self.recorded_by, last_row, 1, 1, 3)
        outer.addWidget(content)
        buttons = QHBoxLayout()
        save = QPushButton("Lưu Vấn chẩn")
        save.clicked.connect(self.save)
        clear = QPushButton("Xóa Vấn chẩn")
        clear.clicked.connect(self.remove)
        buttons.addWidget(save)
        buttons.addWidget(clear)
        buttons.addStretch()
        outer.addLayout(buttons)

    def set_consultation(self, consultation_id: int | None) -> None:
        self.consultation_id = consultation_id
        self.refresh()

    def refresh(self) -> None:
        item = (
            None
            if self.consultation_id is None
            else (self.repository.inquiry_finding(self.consultation_id))
        )
        for key, field in self.inputs.items():
            field.setPlainText("" if item is None else item.get(key, ""))
        self.recorded_by.setText("" if item is None else item.get("recorded_by", ""))

    def save(self) -> None:
        if self.consultation_id is None:
            return
        values = {key: field.toPlainText() for key, field in self.inputs.items()}
        values["recorded_by"] = self.recorded_by.text()
        try:
            self.repository.save_inquiry_finding(self.consultation_id, values)
            QMessageBox.information(self, "Đã lưu", "Vấn chẩn đã được cập nhật.")
        except Exception as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))

    def remove(self) -> None:
        if self.consultation_id is None:
            return
        self.repository.delete_inquiry_finding(self.consultation_id)
        self.refresh()


class PalpationEditor(QWidget):
    SIDES = (("left", "Trái"), ("right", "Phải"))
    POSITIONS = (("cun", "Thốn"), ("guan", "Quan"), ("chi", "Xích"))
    TYPES = (
        ("temperature", "Nhiệt độ"),
        ("tenderness", "Đau khi ấn"),
        ("mass", "Khối"),
        ("skin", "Da/cơ"),
        ("abdomen", "Bụng"),
        ("acupoint", "Du huyệt"),
        ("other", "Khác"),
    )

    def __init__(self, repository: ConsultationRepository):
        super().__init__()
        self.repository = repository
        self.consultation_id: int | None = None
        outer = QVBoxLayout(self)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        hint = QLabel("Nhập mạch và xúc chẩn thủ công; chưa kết nối thiết bị ngoại vi.")
        hint.setObjectName("subtitle")
        content_layout.addWidget(hint)
        pulse_box = QGroupBox("Mạch chẩn — Thốn, Quan, Xích")
        pulse_form = QFormLayout(pulse_box)
        row = QHBoxLayout()
        self.side = QComboBox()
        self.position = QComboBox()
        for key, label in self.SIDES:
            self.side.addItem(label, key)
        for key, label in self.POSITIONS:
            self.position.addItem(label, key)
        row.addWidget(self.side)
        row.addWidget(self.position)
        pulse_form.addRow("Bộ vị *", row)
        self.depth = QComboBox()
        self.depth.setEditable(True)
        self.depth.addItems(("", "Phù", "Trung", "Trầm"))
        self.rate = QComboBox()
        self.rate.setEditable(True)
        self.rate.addItems(("", "Trì", "Bình", "Sác"))
        self.strength = QComboBox()
        self.strength.setEditable(True)
        self.strength.addItems(("", "Hữu lực", "Vô lực"))
        self.rhythm = QComboBox()
        self.rhythm.setEditable(True)
        self.rhythm.addItems(("", "Đều", "Xúc", "Kết", "Đại"))
        self.quality = QLineEdit()
        self.quality.setPlaceholderText("Ví dụ: Huyền, Hoạt, Sáp, Tế...")
        self.bpm = QSpinBox()
        self.bpm.setRange(0, 250)
        self.bpm.setSpecialValueText("Chưa đo")
        self.pulse_note = QLineEdit()
        self.pulse_recorder = QLineEdit()
        self.pulse_recorder.setPlaceholderText("Họ tên bác sĩ/người bắt mạch")
        pulse_form.addRow("Độ sâu", self.depth)
        pulse_form.addRow("Tốc độ", self.rate)
        pulse_form.addRow("Lực mạch", self.strength)
        pulse_form.addRow("Nhịp", self.rhythm)
        pulse_form.addRow("Mạch tượng *", self.quality)
        pulse_form.addRow("Nhịp/phút", self.bpm)
        pulse_form.addRow("Ghi chú", self.pulse_note)
        pulse_form.addRow("Người bắt mạch *", self.pulse_recorder)
        pulse_buttons = QHBoxLayout()
        save_pulse = QPushButton("Lưu bộ vị")
        save_pulse.clicked.connect(self.save_pulse)
        clear_pulse = QPushButton("Xóa toàn bộ mạch")
        clear_pulse.clicked.connect(self.clear_pulses)
        pulse_buttons.addWidget(save_pulse)
        pulse_buttons.addWidget(clear_pulse)
        pulse_buttons.addStretch()
        pulse_form.addRow(pulse_buttons)
        self.pulse_table = QTableWidget(0, 8)
        self.pulse_table.setHorizontalHeaderLabels(
            ("Bên", "Bộ vị", "Độ sâu", "Tốc độ", "Lực", "Nhịp", "Mạch tượng", "Nhịp/phút")
        )
        self.pulse_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pulse_table.horizontalHeader().setStretchLastSection(True)
        self.pulse_table.setMaximumHeight(170)
        pulse_form.addRow(self.pulse_table)
        content_layout.addWidget(pulse_box)

        touch_box = QGroupBox("Xúc chẩn — sờ nắn")
        touch_form = QFormLayout(touch_box)
        self.body_area = QLineEdit()
        self.body_area.setPlaceholderText("Ví dụ: Hạ sườn phải")
        self.touch_type = QComboBox()
        for key, label in self.TYPES:
            self.touch_type.addItem(label, key)
        self.characteristic = QLineEdit()
        self.characteristic.setPlaceholderText("Nóng/lạnh, mềm/cứng, đau, kích thước...")
        self.touch_severity = QSpinBox()
        self.touch_severity.setRange(0, 10)
        self.touch_note = QLineEdit()
        self.touch_recorder = QLineEdit()
        self.touch_recorder.setPlaceholderText("Họ tên người ghi nhận")
        touch_form.addRow("Vùng sờ nắn *", self.body_area)
        touch_form.addRow("Loại *", self.touch_type)
        touch_form.addRow("Đặc điểm *", self.characteristic)
        touch_form.addRow("Mức độ 0–10", self.touch_severity)
        touch_form.addRow("Ghi chú", self.touch_note)
        touch_form.addRow("Người ghi nhận *", self.touch_recorder)
        buttons = QHBoxLayout()
        add = QPushButton("Thêm xúc chẩn")
        add.clicked.connect(self.add_palpation)
        remove = QPushButton("Xóa mục chọn")
        remove.clicked.connect(self.remove_palpation)
        buttons.addWidget(add)
        buttons.addWidget(remove)
        buttons.addStretch()
        touch_form.addRow(buttons)
        self.touch_table = QTableWidget(0, 5)
        self.touch_table.setHorizontalHeaderLabels(
            ("Vùng", "Loại", "Đặc điểm", "Mức độ", "Người nhập")
        )
        self.touch_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.touch_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.touch_table.horizontalHeader().setStretchLastSection(True)
        self.touch_table.setMaximumHeight(170)
        touch_form.addRow(self.touch_table)
        content_layout.addWidget(touch_box)
        content_layout.addStretch()
        outer.addWidget(content)

    def set_consultation(self, consultation_id: int | None) -> None:
        self.consultation_id = consultation_id
        self.refresh()

    def refresh(self) -> None:
        pulses = (
            []
            if self.consultation_id is None
            else self.repository.pulse_findings(self.consultation_id)
        )
        sides, positions = dict(self.SIDES), dict(self.POSITIONS)
        self.pulse_table.setRowCount(len(pulses))
        for row_index, entry in enumerate(pulses):
            values = (
                sides[entry["side"]],
                positions[entry["position"]],
                entry["depth"],
                entry["rate"],
                entry["strength"],
                entry["rhythm"],
                entry["quality"],
                entry["bpm"],
            )
            for column, value in enumerate(values):
                self.pulse_table.setItem(row_index, column, QTableWidgetItem(str(value or "")))
        touches = (
            []
            if self.consultation_id is None
            else self.repository.palpation_findings(self.consultation_id)
        )
        labels = dict(self.TYPES)
        self.touch_table.setRowCount(len(touches))
        for row_index, entry in enumerate(touches):
            values = (
                entry["body_area"],
                labels.get(entry["finding_type"], entry["finding_type"]),
                entry["characteristic"],
                entry["severity"],
                entry["recorded_by"],
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                item.setData(Qt.ItemDataRole.UserRole, entry["id"])
                self.touch_table.setItem(row_index, column, item)

    def save_pulse(self) -> None:
        if self.consultation_id is None:
            return
        try:
            self.repository.save_pulse_finding(
                self.consultation_id,
                {
                    "side": self.side.currentData(),
                    "position": self.position.currentData(),
                    "depth": self.depth.currentText(),
                    "rate": self.rate.currentText(),
                    "strength": self.strength.currentText(),
                    "rhythm": self.rhythm.currentText(),
                    "quality": self.quality.text(),
                    "bpm": self.bpm.value(),
                    "note": self.pulse_note.text(),
                    "recorded_by": self.pulse_recorder.text(),
                },
            )
            self.quality.clear()
            self.pulse_note.clear()
            self.refresh()
        except Exception as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))

    def clear_pulses(self) -> None:
        if self.consultation_id is not None:
            self.repository.delete_pulse_findings(self.consultation_id)
            self.refresh()

    def add_palpation(self) -> None:
        if self.consultation_id is None:
            return
        try:
            self.repository.add_palpation_finding(
                self.consultation_id,
                {
                    "body_area": self.body_area.text(),
                    "finding_type": self.touch_type.currentData(),
                    "characteristic": self.characteristic.text(),
                    "severity": self.touch_severity.value(),
                    "note": self.touch_note.text(),
                    "recorded_by": self.touch_recorder.text(),
                },
            )
            self.body_area.clear()
            self.characteristic.clear()
            self.touch_note.clear()
            self.refresh()
        except Exception as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))

    def remove_palpation(self) -> None:
        items = self.touch_table.selectedItems()
        if items:
            self.repository.delete_palpation_finding(int(items[0].data(Qt.ItemDataRole.UserRole)))
            self.refresh()


class SyndromeEditor(QWidget):
    def __init__(self, repository: SyndromeRepository):
        super().__init__()
        self.repository = repository
        self.consultation_id: int | None = None
        self.syndromes = repository.catalogue()
        layout = QVBoxLayout(self)
        warning = QLabel("Gợi ý biện chứng chỉ hỗ trợ tham khảo; bác sĩ chịu trách nhiệm xác nhận.")
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        form = QFormLayout()
        self.syndrome = QComboBox()
        for item in self.syndromes:
            self.syndrome.addItem(item["name"], item["id"])
        self.syndrome.currentIndexChanged.connect(self.show_reference)
        self.principles = QLabel()
        self.principles.setWordWrap(True)
        self.pathogenesis = QLabel()
        self.pathogenesis.setWordWrap(True)
        self.treatment = QLabel()
        self.treatment.setWordWrap(True)
        self.confidence = QSpinBox()
        self.confidence.setRange(0, 100)
        self.confidence.setSingleStep(5)
        self.confidence.setSuffix(" %")
        self.evidence = QTextEdit()
        self.evidence.setMaximumHeight(72)
        self.evidence.setPlaceholderText("Dấu hiệu Tứ chẩn hỗ trợ nhận định")
        self.primary = QCheckBox("Chứng chính")
        self.confirmed = QCheckBox("Bác sĩ đã xác nhận")
        form.addRow("Hội chứng", self.syndrome)
        form.addRow("Bát cương", self.principles)
        form.addRow("Bệnh cơ", self.pathogenesis)
        form.addRow("Phép trị", self.treatment)
        form.addRow("Độ phù hợp", self.confidence)
        form.addRow("Căn cứ", self.evidence)
        checks = QHBoxLayout()
        checks.addWidget(self.primary)
        checks.addWidget(self.confirmed)
        checks.addStretch()
        form.addRow(checks)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        analyse = QPushButton("Gợi ý từ Tứ chẩn")
        analyse.clicked.connect(self.analyse)
        save = QPushButton("Lưu biện chứng")
        save.clicked.connect(self.save)
        remove = QPushButton("Xóa mục chọn")
        remove.clicked.connect(self.remove)
        buttons.addWidget(analyse)
        buttons.addWidget(save)
        buttons.addWidget(remove)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ("Hội chứng", "Bát cương", "Phép trị", "Phù hợp", "Chứng chính", "Xác nhận")
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.load_selected)
        layout.addWidget(self.table, 1)
        self.show_reference()

    def set_consultation(self, consultation_id: int | None) -> None:
        self.consultation_id = consultation_id
        self.refresh()

    def show_reference(self) -> None:
        index = self.syndrome.currentIndex()
        if index < 0:
            return
        item = self.syndromes[index]
        self.principles.setText(item["eight_principles"] or "—")
        self.pathogenesis.setText(item["pathogenesis"] or "—")
        self.treatment.setText(item["treatment_principle"] or "—")

    def refresh(self) -> None:
        rows = (
            [] if self.consultation_id is None else self.repository.selected(self.consultation_id)
        )
        self.table.setRowCount(len(rows))
        for row_index, entry in enumerate(rows):
            values = (
                entry["name"],
                entry["eight_principles"],
                entry["treatment_principle"],
                f"{round(entry['confidence'] * 100)}%",
                "Có" if entry["is_primary"] else "",
                "Có" if entry["doctor_confirmed"] else "",
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.ItemDataRole.UserRole, entry["syndrome_id"])
                cell.setData(Qt.ItemDataRole.UserRole + 1, entry)
                self.table.setItem(row_index, column, cell)

    def analyse(self) -> None:
        if self.consultation_id is None:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn lần khám trước.")
            return
        results = suggest(self.repository.clinical_text(self.consultation_id), self.syndromes)
        if not results:
            QMessageBox.information(self, "Chưa đủ căn cứ", "Chưa tìm thấy mẫu phù hợp rõ ràng.")
            return
        result = results[0]
        self.syndrome.setCurrentIndex(self.syndrome.findData(result["id"]))
        self.confidence.setValue(round(result["confidence"] * 100))
        self.evidence.setPlainText("; ".join(result["matched"]))
        QMessageBox.information(
            self, "Gợi ý tham khảo", f"Gợi ý cao nhất: {result['name']}. Bác sĩ cần xác nhận."
        )

    def save(self) -> None:
        if self.consultation_id is None:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn lần khám trước.")
            return
        if self.syndrome.currentData() is None:
            return
        try:
            self.repository.save(
                self.consultation_id,
                int(self.syndrome.currentData()),
                {
                    "confidence": self.confidence.value() / 100,
                    "evidence": self.evidence.toPlainText(),
                    "is_primary": self.primary.isChecked(),
                    "doctor_confirmed": self.confirmed.isChecked(),
                },
            )
            self.refresh()
        except Exception as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))

    def load_selected(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        entry = items[0].data(Qt.ItemDataRole.UserRole + 1)
        self.syndrome.setCurrentIndex(self.syndrome.findData(entry["syndrome_id"]))
        self.confidence.setValue(round(entry["confidence"] * 100))
        self.evidence.setPlainText(entry["evidence"])
        self.primary.setChecked(bool(entry["is_primary"]))
        self.confirmed.setChecked(bool(entry["doctor_confirmed"]))

    def remove(self) -> None:
        items = self.table.selectedItems()
        if self.consultation_id is not None and items:
            self.repository.delete(
                self.consultation_id, int(items[0].data(Qt.ItemDataRole.UserRole))
            )
            self.refresh()


class DiagnosisPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.syndromes = SyndromeRepository(database)
        self.editors: list[QWidget] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Hồ sơ khám và Tứ chẩn")
        title.setObjectName("title")
        layout.addWidget(title)
        selectors = QHBoxLayout()
        self.patient = QComboBox()
        self.visit = QComboBox()
        self.patient.currentIndexChanged.connect(self.load_visits)
        self.visit.currentIndexChanged.connect(self.load_consultation)
        selectors.addWidget(QLabel("Bệnh nhân"))
        selectors.addWidget(self.patient, 1)
        selectors.addWidget(QLabel("Lần khám"))
        selectors.addWidget(self.visit, 1)
        layout.addLayout(selectors)
        self.summary = QGroupBox("Thông tin tổng hợp")
        form = QFormLayout(self.summary)
        self.complaint = QTextEdit()
        self.history = QTextEdit()
        self.assessment = QTextEdit()
        for field in (self.complaint, self.history, self.assessment):
            field.setMaximumHeight(64)
        self.doctor = QLineEdit()
        self.status = QComboBox()
        for key, text in (
            ("draft", "Bản nháp"),
            ("in_review", "Đang duyệt"),
            ("approved", "Đã duyệt"),
            ("closed", "Đã đóng"),
        ):
            self.status.addItem(text, key)
        form.addRow("Lý do khám", self.complaint)
        form.addRow("Tiền sử", self.history)
        form.addRow("Nhận định sơ bộ", self.assessment)
        form.addRow("Bác sĩ", self.doctor)
        form.addRow("Trạng thái", self.status)
        save = QPushButton("Lưu hồ sơ")
        save.clicked.connect(self.save_summary)
        form.addRow(save)
        layout.addWidget(self.summary)
        tabs = QTabWidget()
        for method, name, hint in METHODS:
            editor = (
                ListeningSmellingEditor(self.consultations)
                if method == "van"
                else InquiryEditor(self.consultations)
                if method == "van_hoi"
                else PalpationEditor(self.consultations)
                if method == "thiet"
                else MethodEditor(self.consultations, method, hint)
            )
            self.editors.append(editor)
            tabs.addTab(self._scrollable(editor), name)
        syndrome_editor = SyndromeEditor(self.syndromes)
        self.editors.append(syndrome_editor)
        tabs.addTab(self._scrollable(syndrome_editor), "Biện chứng luận trị")
        layout.addWidget(tabs, 1)
        self.reload_patients()

    @staticmethod
    def _scrollable(editor: QWidget) -> QScrollArea:
        editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        if editor.layout() is not None:
            editor.layout().setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(editor)
        return scroll

    def reload_patients(self) -> None:
        self.patient.blockSignals(True)
        self.patient.clear()
        self.patient.addItem("— Chọn bệnh nhân —", None)
        for item in self.patients.list(limit=500):
            self.patient.addItem(f"{item['code']} • {item['full_name']}", item["id"])
        self.patient.blockSignals(False)
        self.load_visits()

    def load_visits(self) -> None:
        patient_id = self.patient.currentData()
        self.visit.blockSignals(True)
        self.visit.clear()
        self.visit.addItem("— Chọn lần khám —", None)
        if patient_id is not None:
            for item in self.consultations.list_for_patient(int(patient_id)):
                self.visit.addItem(f"{item['visit_code']} • {item['created_at']}", item["id"])
        self.visit.blockSignals(False)
        self.load_consultation()

    def load_consultation(self) -> None:
        consultation_id = self.visit.currentData()
        enabled = consultation_id is not None
        self.summary.setEnabled(enabled)
        for editor in self.editors:
            editor.set_consultation(int(consultation_id) if enabled else None)
        if not enabled:
            for field in (self.complaint, self.history, self.assessment, self.doctor):
                field.clear()
            return
        item = self.consultations.get(int(consultation_id))
        self.complaint.setPlainText(item.get("chief_complaint", ""))
        self.history.setPlainText(item.get("western_history", ""))
        self.assessment.setPlainText(item.get("assessment", ""))
        self.doctor.setText(item.get("doctor_name", ""))
        self.status.setCurrentIndex(max(0, self.status.findData(item["status"])))

    def save_summary(self) -> None:
        consultation_id = self.visit.currentData()
        if consultation_id is None:
            return
        try:
            self.consultations.update(
                int(consultation_id),
                {
                    "chief_complaint": self.complaint.toPlainText(),
                    "western_history": self.history.toPlainText(),
                    "assessment": self.assessment.toPlainText(),
                    "doctor_name": self.doctor.text(),
                    "status": self.status.currentData(),
                },
            )
            QMessageBox.information(self, "Đã lưu", "Hồ sơ khám đã được cập nhật.")
        except Exception as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))
