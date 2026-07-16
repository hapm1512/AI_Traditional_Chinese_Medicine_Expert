from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database.audio_repository import AudioAnalysisRepository
from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.settings_repository import SettingsRepository
from tcm_expert.services.audio_analyzer import AudioAnalyzer


class AudioPage(QWidget):
    TYPES = (
        ("Giọng nói", "voice"),
        ("Tiếng ho", "cough"),
        ("Tiếng thở", "breathing"),
        ("Khác", "other"),
    )

    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.database = database
        self.repository = AudioAnalysisRepository(database)
        self.settings = SettingsRepository(database)
        self.analyzer = AudioAnalyzer()
        self.source_path: Path | None = None
        self.analysis_id: int | None = None
        self._build_ui()
        self.refresh_consultations()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        title = QLabel("HỖ TRỢ CHẨN ĐOÁN ÂM THANH")
        title.setObjectName("title")
        root.addWidget(title)
        warning = QLabel("Chỉ mô tả tín hiệu. Không tự kết luận bệnh. Bác sĩ phải xác nhận.")
        warning.setObjectName("warning")
        root.addWidget(warning)
        toolbar = QHBoxLayout()
        self.consultation = QComboBox()
        self.consultation.currentIndexChanged.connect(self.refresh_history)
        self.sample_type = QComboBox()
        for label, value in self.TYPES:
            self.sample_type.addItem(label, value)
        choose = QPushButton("Chọn WAV")
        choose.clicked.connect(self.choose_audio)
        analyze = QPushButton("AI đánh giá")
        analyze.clicked.connect(self.analyze_audio)
        toolbar.addWidget(QLabel("Mã BN / lần khám"))
        toolbar.addWidget(self.consultation, 1)
        toolbar.addWidget(self.sample_type)
        toolbar.addWidget(choose)
        toolbar.addWidget(analyze)
        root.addLayout(toolbar)

        body = QHBoxLayout()
        status = QVBoxLayout()
        self.quality = QLabel("Chất lượng: —")
        self.features = QLabel("Đặc trưng: —")
        self.features.setWordWrap(True)
        self.result = QLabel("Mẫu hỗ trợ: —")
        self.result.setWordWrap(True)
        self.issues = QLabel("Lỗi bản ghi: —")
        self.issues.setWordWrap(True)
        for widget in (self.quality, self.features, self.result, self.issues):
            status.addWidget(widget)
        status.addStretch()
        body.addLayout(status, 1)

        form = QFormLayout()
        self.manual = QTextEdit()
        self.manual.setPlaceholderText("Y tá mô tả tiếng ho, nấc, tiếng thở...")
        self.manual.setMaximumHeight(90)
        manual_save = QPushButton("Lưu nhập liệu tay")
        manual_save.clicked.connect(self.save_manual)
        self.doctor_label = QLineEdit()
        self.doctor = QLineEdit()
        self.doctor.setReadOnly(True)
        self.note = QTextEdit()
        self.note.setMaximumHeight(90)
        approve = QPushButton("Bác sĩ xác nhận")
        approve.clicked.connect(self.save_review)
        form.addRow("Mô tả thủ công", self.manual)
        form.addRow(manual_save)
        form.addRow("Kết luận mô tả", self.doctor_label)
        form.addRow("Bác sĩ", self.doctor)
        form.addRow("Ghi chú", self.note)
        form.addRow(approve)
        body.addLayout(form, 1)
        root.addLayout(body)

        self.history = QTableWidget(0, 6)
        self.history.setHorizontalHeaderLabels(
            ("Thời gian", "Loại", "Nguồn", "Mẫu hỗ trợ", "Tin cậy", "Đã duyệt")
        )
        self.history.itemSelectionChanged.connect(self.load_selected)
        root.addWidget(self.history, 1)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh_consultations()

    def refresh_consultations(self) -> None:
        selected = self.consultation.currentData()
        self.consultation.blockSignals(True)
        self.consultation.clear()
        self.consultation.addItem("Chưa có hồ sơ khám", None)
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT c.id,c.visit_code,p.full_name FROM consultations c
                JOIN patients p ON p.id=c.patient_id ORDER BY c.id DESC"""
            ).fetchall()
        for row in rows:
            self.consultation.addItem(f"{row['visit_code']} — {row['full_name']}", row["id"])
        index = self.consultation.findData(selected)
        if self.consultation.count() > 1:
            self.consultation.setCurrentIndex(index if index >= 1 else 1)
        self.consultation.blockSignals(False)
        self.refresh_history()

    def choose_audio(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Chọn âm thanh", "", "WAV PCM (*.wav)")
        if filename:
            self.source_path = Path(filename)

    def analyze_audio(self) -> None:
        consultation_id = self.consultation.currentData()
        if not consultation_id or not self.source_path:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Chọn hồ sơ khám và tệp WAV.")
            return
        try:
            result = self.analyzer.analyze(self.source_path, self.sample_type.currentData())
            audio_dir = self.database.path.parent / "audio_samples"
            audio_dir.mkdir(parents=True, exist_ok=True)
            stored = audio_dir / f"{result.audio_sha256}.wav"
            if not stored.exists():
                shutil.copy2(self.source_path, stored)
            self.analysis_id = self.repository.create(
                consultation_id, self.sample_type.currentData(), str(stored), result.as_dict()
            )
            self._apply_result(result.as_dict())
            self.refresh_history()
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Không thể phân tích", str(error))

    def save_manual(self) -> None:
        try:
            self.analysis_id = self.repository.create_manual(
                self.consultation.currentData(),
                self.sample_type.currentData(),
                self.manual.toPlainText(),
            )
            self.refresh_history()
            QMessageBox.information(self, "Đã lưu", "Đã lưu mô tả âm thanh thủ công.")
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Dữ liệu chưa hợp lệ", str(error))

    def save_review(self) -> None:
        if not self.analysis_id:
            QMessageBox.warning(self, "Chưa chọn", "Chọn một kết quả trước.")
            return
        try:
            doctor = self.settings.doctor_name(required=True)
            self.repository.review(
                self.analysis_id,
                doctor,
                self.doctor_label.text(),
                self.note.toPlainText(),
            )
            self.doctor.setText(doctor)
            self.refresh_history()
            QMessageBox.information(self, "Đã lưu", "Đã lưu xác nhận của bác sĩ.")
        except ValueError as error:
            QMessageBox.warning(self, "Dữ liệu chưa hợp lệ", str(error))

    def refresh_history(self) -> None:
        consultation_id = self.consultation.currentData()
        rows = self.repository.list_for_consultation(consultation_id) if consultation_id else []
        labels = dict((value, label) for label, value in self.TYPES)
        self.history.setRowCount(len(rows))
        for index, row in enumerate(rows):
            values = (
                row["created_at"],
                labels.get(row["sample_type"], row["sample_type"]),
                "Tệp WAV" if row["source_mode"] == "file" else "Nhập tay",
                row["pattern_label"],
                f"{row['ai_confidence'] * 100:.1f}%",
                "Có" if row["reviewed_at"] else "Chưa",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, row["id"])
                self.history.setItem(index, column, item)

    def load_selected(self) -> None:
        items = self.history.selectedItems()
        if not items:
            return
        row = self.repository.get(int(items[0].data(Qt.ItemDataRole.UserRole)))
        if not row:
            return
        self.analysis_id = row["id"]
        self.quality.setText(f"Chất lượng: {row['quality_score'] * 100:.1f}%")
        self.features.setText(
            f"Đặc trưng: RMS {row['rms_level']:.4f} • Peak {row['peak_level']:.4f} • "
            f"ZCR {row['zero_crossing_rate']:.4f} • Tần số {row['dominant_frequency']:.1f} Hz"
        )
        self.result.setText(
            f"Mẫu hỗ trợ: {row['pattern_label']} • Tin cậy {row['ai_confidence'] * 100:.1f}%"
        )
        self.issues.setText(
            "Lỗi bản ghi: " + (row["quality_issues"].replace("\n", "; ") or "Không")
        )
        self.manual.setPlainText(row["manual_characteristic"])
        self.doctor_label.setText(row["doctor_pattern_label"] or row["pattern_label"])
        self.doctor.setText(row["reviewed_by"])
        self.note.setPlainText(row["doctor_note"])

    def _apply_result(self, result: dict) -> None:
        self.quality.setText(f"Chất lượng: {result['quality_score'] * 100:.1f}%")
        self.features.setText(
            f"Đặc trưng: RMS {result['rms_level']:.4f} • Peak {result['peak_level']:.4f} • "
            f"ZCR {result['zero_crossing_rate']:.4f} • Tần số {result['dominant_frequency']:.1f} Hz"
        )
        self.result.setText(
            f"Mẫu hỗ trợ: {result['pattern_label']} • Tin cậy {result['ai_confidence'] * 100:.1f}%"
        )
        self.issues.setText("Lỗi bản ghi: " + ("; ".join(result["quality_issues"]) or "Không"))
        self.doctor_label.setText(result["pattern_label"])
