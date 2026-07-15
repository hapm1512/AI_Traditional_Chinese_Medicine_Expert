from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.tongue_repository import TongueAnalysisRepository
from tcm_expert.services.tongue_analyzer import TongueAnalyzer


class TonguePage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.database = database
        self.repository = TongueAnalysisRepository(database)
        self.analyzer = TongueAnalyzer()
        self.source_path: Path | None = None
        self.analysis_id: int | None = None
        self._build_ui()
        self.refresh_consultations()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        title = QLabel("AI PHÂN TÍCH LƯỠI")
        title.setObjectName("title")
        root.addWidget(title)
        warning = QLabel("Kết quả mô tả ảnh, không phải chẩn đoán. Bác sĩ phải kiểm tra.")
        warning.setObjectName("warning")
        root.addWidget(warning)
        toolbar = QHBoxLayout()
        self.consultation = QComboBox()
        self.consultation.currentIndexChanged.connect(self.refresh_history)
        choose = QPushButton("Chọn ảnh")
        choose.clicked.connect(self.choose_image)
        analyze = QPushButton("Phân tích offline")
        analyze.clicked.connect(self.analyze_image)
        toolbar.addWidget(QLabel("Hồ sơ khám"))
        toolbar.addWidget(self.consultation, 1)
        toolbar.addWidget(choose)
        toolbar.addWidget(analyze)
        root.addLayout(toolbar)

        body = QHBoxLayout()
        left = QVBoxLayout()
        self.preview = QLabel("Chưa chọn ảnh")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(380, 300)
        self.preview.setStyleSheet("border: 1px solid #4d5a52; background: #101713;")
        left.addWidget(self.preview)
        self.quality = QLabel("Chất lượng: —")
        self.confidence = QLabel("Độ tin cậy AI: —")
        self.issues = QLabel("Lỗi ảnh: —")
        self.issues.setWordWrap(True)
        left.addWidget(self.quality)
        left.addWidget(self.confidence)
        left.addWidget(self.issues)
        body.addLayout(left, 1)

        form = QFormLayout()
        self.tongue_color = QComboBox()
        self.tongue_color.addItems(("Hồng", "Nhạt", "Đỏ", "Tím sẫm", "Không rõ"))
        self.coating_color = QComboBox()
        self.coating_color.addItems(("Trắng", "Vàng", "Ít/không rõ", "Không rõ"))
        self.coating_thickness = QComboBox()
        self.coating_thickness.addItems(("Mỏng", "Dày", "Ít/không rõ", "Không rõ"))
        self.teeth_marks = QCheckBox("Có dấu răng")
        self.cracks = QCheckBox("Có vết nứt")
        self.doctor = QLineEdit()
        self.note = QTextEdit()
        self.note.setMaximumHeight(100)
        form.addRow("Màu chất lưỡi", self.tongue_color)
        form.addRow("Màu rêu", self.coating_color)
        form.addRow("Độ dày rêu", self.coating_thickness)
        form.addRow("Dấu răng", self.teeth_marks)
        form.addRow("Vết nứt", self.cracks)
        form.addRow("Bác sĩ duyệt", self.doctor)
        form.addRow("Ghi chú", self.note)
        approve = QPushButton("Lưu kết quả bác sĩ")
        approve.clicked.connect(self.save_review)
        form.addRow(approve)
        body.addLayout(form, 1)
        root.addLayout(body, 1)

        self.history = QTableWidget(0, 5)
        self.history.setHorizontalHeaderLabels(
            ("Thời gian", "Màu lưỡi", "Rêu", "Tin cậy", "Đã duyệt")
        )
        self.history.itemSelectionChanged.connect(self.load_selected)
        root.addWidget(self.history)

    def refresh_consultations(self) -> None:
        selected = self.consultation.currentData()
        self.consultation.blockSignals(True)
        self.consultation.clear()
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT c.id,c.visit_code,p.full_name FROM consultations c
                   JOIN patients p ON p.id=c.patient_id ORDER BY c.id DESC"""
            ).fetchall()
        for row in rows:
            self.consultation.addItem(f"{row['visit_code']} — {row['full_name']}", row["id"])
        index = self.consultation.findData(selected)
        if index >= 0:
            self.consultation.setCurrentIndex(index)
        self.consultation.blockSignals(False)
        self.refresh_history()

    def choose_image(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh lưỡi", "", "Ảnh (*.jpg *.jpeg *.png *.bmp *.webp)"
        )
        if filename:
            self.source_path = Path(filename)
            self._show_image(self.source_path)

    def analyze_image(self) -> None:
        consultation_id = self.consultation.currentData()
        if not consultation_id or not self.source_path:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Chọn hồ sơ khám và ảnh lưỡi.")
            return
        try:
            result = self.analyzer.analyze(self.source_path)
            image_dir = self.database.path.parent / "tongue_images"
            image_dir.mkdir(parents=True, exist_ok=True)
            stored = image_dir / f"{result.image_sha256}{self.source_path.suffix.lower()}"
            if not stored.exists():
                shutil.copy2(self.source_path, stored)
            self.analysis_id = self.repository.create(
                consultation_id, str(stored), result.as_dict()
            )
            self._apply_result(result.as_dict())
            self.refresh_history()
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Không thể phân tích", str(error))

    def _apply_result(self, result: dict) -> None:
        self._set_combo(self.tongue_color, result["tongue_color"])
        self._set_combo(self.coating_color, result["coating_color"])
        self._set_combo(self.coating_thickness, result["coating_thickness"])
        self.teeth_marks.setChecked(bool(result["teeth_marks"]))
        self.cracks.setChecked(bool(result["cracks"]))
        self.quality.setText(f"Chất lượng: {result['quality_score'] * 100:.1f}%")
        self.confidence.setText(f"Độ tin cậy AI: {result['ai_confidence'] * 100:.1f}%")
        self.issues.setText("Lỗi ảnh: " + ("; ".join(result["quality_issues"]) or "Không"))

    def save_review(self) -> None:
        if not self.analysis_id:
            QMessageBox.warning(self, "Chưa phân tích", "Chọn một kết quả AI trước.")
            return
        try:
            self.repository.review(self.analysis_id, {
                "tongue_color": self.tongue_color.currentText(),
                "coating_color": self.coating_color.currentText(),
                "coating_thickness": self.coating_thickness.currentText(),
                "teeth_marks": self.teeth_marks.isChecked(), "cracks": self.cracks.isChecked(),
                "reviewed_by": self.doctor.text(), "note": self.note.toPlainText(),
            })
            self.refresh_history()
            QMessageBox.information(self, "Đã lưu", "Đã lưu kết quả bác sĩ duyệt.")
        except ValueError as error:
            QMessageBox.warning(self, "Dữ liệu chưa hợp lệ", str(error))

    def refresh_history(self) -> None:
        consultation_id = self.consultation.currentData()
        rows = self.repository.list_for_consultation(consultation_id) if consultation_id else []
        self.history.setRowCount(len(rows))
        for index, row in enumerate(rows):
            values = (row["created_at"], row["tongue_color"],
                      f"{row['coating_color']} / {row['coating_thickness']}",
                      f"{row['ai_confidence'] * 100:.1f}%", "Có" if row["reviewed_at"] else "Chưa")
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
        self._show_image(Path(row["original_image_path"]))
        self._set_combo(self.tongue_color, row["doctor_tongue_color"] or row["tongue_color"])
        self._set_combo(self.coating_color, row["doctor_coating_color"] or row["coating_color"])
        self._set_combo(self.coating_thickness,
                        row["doctor_coating_thickness"] or row["coating_thickness"])
        self.teeth_marks.setChecked(bool(row["doctor_teeth_marks"] if row["doctor_teeth_marks"] is not None else row["teeth_marks"]))
        self.cracks.setChecked(bool(row["doctor_cracks"] if row["doctor_cracks"] is not None else row["cracks"]))
        self.doctor.setText(row["reviewed_by"])
        self.note.setPlainText(row["doctor_note"])
        self.quality.setText(f"Chất lượng: {row['quality_score'] * 100:.1f}%")
        self.confidence.setText(f"Độ tin cậy AI: {row['ai_confidence'] * 100:.1f}%")
        self.issues.setText("Lỗi ảnh: " + (row["quality_issues"].replace("\n", "; ") or "Không"))

    def _show_image(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.preview.setText("Không đọc được ảnh")
        else:
            self.preview.setPixmap(pixmap.scaled(
                self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    @staticmethod
    def _set_combo(combo: QComboBox, value: str) -> None:
        index = combo.findText(value)
        if index < 0:
            combo.addItem(value)
            index = combo.count() - 1
        combo.setCurrentIndex(index)
