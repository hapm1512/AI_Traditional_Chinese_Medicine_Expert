from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database import ConsultationRepository, FormulaRepository, PatientRepository
from tcm_expert.database.manager import DatabaseManager


class FormulaPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.formulas = FormulaRepository(database)
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.current_formula_id: int | None = None
        self.recommendation_ids: list[int] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Bài thuốc tham khảo")
        title.setObjectName("title")
        layout.addWidget(title)
        warning = QLabel(
            "⚠ Chỉ hỗ trợ tham khảo. Không tự động kê đơn. Bác sĩ chịu trách nhiệm phê duyệt."
        )
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        tabs = QTabWidget()
        tabs.addTab(self._catalogue_tab(), "Tra cứu bài thuốc")
        tabs.addTab(self._recommendation_tab(), "Gắn vào hồ sơ khám")
        layout.addWidget(tabs, 1)
        self.refresh_catalogue()
        self.refresh_patients()

    def _catalogue_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        filters = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Tên, mã, chỉ định, pháp trị...")
        self.category = QComboBox()
        self.category.addItem("Tất cả nhóm", "")
        for name in self.formulas.categories():
            self.category.addItem(name, name)
        search = QPushButton("Tìm kiếm")
        search.clicked.connect(self.refresh_catalogue)
        self.query.returnPressed.connect(self.refresh_catalogue)
        filters.addWidget(self.query, 1)
        filters.addWidget(self.category)
        filters.addWidget(search)
        layout.addLayout(filters)
        splitter = QSplitter()
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(("Mã", "Tên bài thuốc", "Nhóm", "Vị"))
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.show_selected)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail)
        splitter.setSizes((480, 620))
        layout.addWidget(splitter, 1)
        return page

    def _recommendation_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.patient = QComboBox()
        self.patient.currentIndexChanged.connect(self.refresh_visits)
        self.visit = QComboBox()
        self.visit.currentIndexChanged.connect(self.refresh_recommendations)
        self.chosen_formula = QLabel("Chọn bài thuốc tại tab tra cứu")
        self.directions = QLineEdit()
        self.directions.setPlaceholderText("Bác sĩ quyết định")
        self.modifications = QTextEdit()
        self.modifications.setMaximumHeight(75)
        self.safety_notes = QTextEdit()
        self.safety_notes.setMaximumHeight(75)
        self.approved = QCheckBox("Đã được bác sĩ kiểm tra và phê duyệt")
        form.addRow("Bệnh nhân", self.patient)
        form.addRow("Lần khám", self.visit)
        form.addRow("Bài thuốc", self.chosen_formula)
        form.addRow("Cách dùng", self.directions)
        form.addRow("Gia giảm", self.modifications)
        form.addRow("Ghi chú an toàn", self.safety_notes)
        form.addRow("Phê duyệt", self.approved)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        save = QPushButton("Lưu tham khảo")
        save.clicked.connect(self.save)
        delete = QPushButton("Xóa mục chọn")
        delete.clicked.connect(self.delete)
        buttons.addWidget(save)
        buttons.addWidget(delete)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.recommendations = QTableWidget(0, 5)
        self.recommendations.setHorizontalHeaderLabels(
            ("Bài thuốc", "Cách dùng", "Gia giảm", "An toàn", "Phê duyệt")
        )
        self.recommendations.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recommendations.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recommendations.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.recommendations, 1)
        return page

    def refresh_catalogue(self) -> None:
        rows = self.formulas.search(self.query.text(), str(self.category.currentData() or ""))
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = (row["code"], row["name"], row["category"], row["ingredient_count"])
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, row["id"])
                self.table.setItem(row_index, column, item)
        if rows:
            self.table.selectRow(0)
        else:
            self.detail.clear()

    def show_selected(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        self.current_formula_id = int(items[0].data(Qt.ItemDataRole.UserRole))
        formula = self.formulas.detail(self.current_formula_id)
        ingredients = (
            "\n".join(
                f"• {x['herb_name']} ({x['herb_name_cn']}): "
                f"{x['dosage']:g} {x['unit']} — {x['role']}"
                for x in formula["ingredients"]
            )
            or "Chưa có thành phần."
        )
        alerts = self.formulas.safety_alerts(self.current_formula_id)
        safety = "\n".join(
            f"• {x['herb_name']} ↔ {x['interacts_with']}: {x['effect']}" for x in alerts
        )
        self.detail.setPlainText(
            f"{formula['name']}  {formula['name_cn']}\n\n"
            f"Pháp trị: {formula['treatment_principle']}\n"
            f"Chỉ định tham khảo: {formula['indications']}\nDạng: {formula['dosage_form']}\n"
            f"Cách dùng: {formula['directions']}\nGia giảm: {formula['modifications']}\n\n"
            f"THÀNH PHẦN\n{ingredients}\n\nCHỐNG CHỈ ĐỊNH\n{formula['contraindications']}\n\n"
            f"TƯƠNG TÁC\n{formula['interactions']}\n"
            f"{safety or 'Chưa ghi nhận dữ liệu tương tác.'}\n\n"
            f"Nguồn: {formula['reference_source']}\n\n{formula['disclaimer']}"
        )
        self.chosen_formula.setText(formula["name"])

    def refresh_patients(self) -> None:
        self.patient.blockSignals(True)
        self.patient.clear()
        self.patient.addItem("Chọn bệnh nhân", None)
        for row in self.patients.list():
            self.patient.addItem(f"{row['code']} — {row['full_name']}", row["id"])
        self.patient.blockSignals(False)
        self.refresh_visits()

    def refresh_visits(self) -> None:
        self.visit.clear()
        patient_id = self.patient.currentData()
        if patient_id is not None:
            for row in self.consultations.list_for_patient(int(patient_id)):
                self.visit.addItem(f"{row['visit_code']} — {row['created_at']}", row["id"])
        self.refresh_recommendations()

    def refresh_recommendations(self) -> None:
        consultation_id = self.visit.currentData()
        rows = self.formulas.list_recommendations(int(consultation_id)) if consultation_id else []
        self.recommendation_ids = [int(row["id"]) for row in rows]
        self.recommendations.setRowCount(len(rows))
        for index, row in enumerate(rows):
            values = (
                row["name"],
                row["custom_directions"],
                row["modifications"],
                row["safety_notes"],
                "Có" if row["doctor_approved"] else "Chưa",
            )
            for column, value in enumerate(values):
                self.recommendations.setItem(index, column, QTableWidgetItem(str(value)))

    def save(self) -> None:
        if self.visit.currentData() is None or self.current_formula_id is None:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Chọn lần khám và bài thuốc.")
            return
        try:
            self.formulas.save_recommendation(
                int(self.visit.currentData()),
                self.current_formula_id,
                {
                    "custom_directions": self.directions.text(),
                    "modifications": self.modifications.toPlainText(),
                    "safety_notes": self.safety_notes.toPlainText(),
                    "doctor_approved": self.approved.isChecked(),
                },
            )
        except ValueError as error:
            QMessageBox.warning(self, "Chưa thể lưu", str(error))
            return
        self.refresh_recommendations()
        QMessageBox.information(self, "Đã lưu", "Đã lưu bài thuốc tham khảo.")

    def delete(self) -> None:
        row = self.recommendations.currentRow()
        if row < 0:
            return
        self.formulas.delete_recommendation(self.recommendation_ids[row])
        self.refresh_recommendations()
