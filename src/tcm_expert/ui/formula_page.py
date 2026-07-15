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
from tcm_expert.services.formula_recommender import FormulaRecommender


class FormulaPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.formulas = FormulaRepository(database)
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.recommender = FormulaRecommender(database)
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
        tabs.addTab(self._doctor_formula_tab(), "Bài thuốc kinh nghiệm")
        tabs.addTab(self._recommendation_tab(), "Gắn vào hồ sơ khám")
        tabs.addTab(self._ai_tab(), "Gợi ý thông minh")
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
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(("Mã", "Tên bài thuốc", "Nhóm", "Nguồn", "Vị"))
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

    def _doctor_formula_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        editor = QWidget()
        form = QFormLayout(editor)
        self.doctor_formula_id: int | None = None
        self.df_code = QLineEdit()
        self.df_name = QLineEdit()
        self.df_category = QLineEdit()
        self.df_doctor = QLineEdit()
        self.df_principle = QLineEdit()
        self.df_indications = QTextEdit()
        self.df_ingredients = QTextEdit()
        self.df_directions = QTextEdit()
        self.df_modifications = QTextEdit()
        self.df_contraindications = QTextEdit()
        self.df_interactions = QTextEdit()
        self.df_source = QLineEdit()
        self.df_approved = QCheckBox("Bác sĩ xác nhận cho phép tham khảo")
        for widget in (
            self.df_indications,
            self.df_ingredients,
            self.df_directions,
            self.df_modifications,
            self.df_contraindications,
            self.df_interactions,
        ):
            widget.setMaximumHeight(70)
        self.df_ingredients.setPlaceholderText("Mỗi vị một dòng: tên — lượng — cách chế biến")
        form.addRow("Mã bài thuốc *", self.df_code)
        form.addRow("Tên bài thuốc *", self.df_name)
        form.addRow("Nhóm", self.df_category)
        form.addRow("Bác sĩ tạo *", self.df_doctor)
        form.addRow("Pháp trị", self.df_principle)
        form.addRow("Chủ trị kinh nghiệm", self.df_indications)
        form.addRow("Thành phần *", self.df_ingredients)
        form.addRow("Cách dùng", self.df_directions)
        form.addRow("Gia giảm", self.df_modifications)
        form.addRow("Chống chỉ định", self.df_contraindications)
        form.addRow("Tương tác/lưu ý", self.df_interactions)
        form.addRow("Nguồn kinh nghiệm", self.df_source)
        form.addRow("Phê duyệt", self.df_approved)
        actions = QHBoxLayout()
        new_button = QPushButton("Nhập mới")
        new_button.clicked.connect(self.clear_doctor_formula)
        save_button = QPushButton("Lưu bài thuốc")
        save_button.clicked.connect(self.save_doctor_formula)
        hide_button = QPushButton("Ẩn bài thuốc")
        hide_button.clicked.connect(self.hide_doctor_formula)
        actions.addWidget(new_button)
        actions.addWidget(save_button)
        actions.addWidget(hide_button)
        form.addRow(actions)
        layout.addWidget(editor, 1)
        self.doctor_table = QTableWidget(0, 4)
        self.doctor_table.setHorizontalHeaderLabels(("Mã", "Tên", "Bác sĩ", "Phê duyệt"))
        self.doctor_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.doctor_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.doctor_table.horizontalHeader().setStretchLastSection(True)
        self.doctor_table.itemSelectionChanged.connect(self.load_doctor_formula)
        layout.addWidget(self.doctor_table, 1)
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

    def _ai_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        selector = QHBoxLayout()
        self.ai_patient = QComboBox()
        self.ai_patient.currentIndexChanged.connect(self.refresh_ai_visits)
        self.ai_visit = QComboBox()
        run = QPushButton("Phân tích và xếp hạng")
        run.clicked.connect(self.run_recommendation)
        selector.addWidget(QLabel("Bệnh nhân"))
        selector.addWidget(self.ai_patient, 1)
        selector.addWidget(QLabel("Lần khám"))
        selector.addWidget(self.ai_visit, 1)
        selector.addWidget(run)
        layout.addLayout(selector)
        warning = QLabel("⚠ Không tự động kê toa hoặc đặt liều. Cảnh báo an toàn luôn hiển thị.")
        warning.setObjectName("warning")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        self.ai_result = QTextEdit()
        self.ai_result.setReadOnly(True)
        self.ai_result.setPlaceholderText("Chọn hồ sơ khám, sau đó nhấn phân tích.")
        layout.addWidget(self.ai_result, 1)
        return page

    def refresh_catalogue(self) -> None:
        rows = self.formulas.search(self.query.text(), str(self.category.currentData() or ""))
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            source = "Bác sĩ" if row["source_type"] == "doctor" else "Hệ thống"
            count = row["ingredient_count"] if row["source_type"] == "system" else "Nhập tay"
            values = (row["code"], row["name"], row["category"], source, count)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, row["id"])
                self.table.setItem(row_index, column, item)
        if rows:
            self.table.selectRow(0)
        else:
            self.detail.clear()
        self.refresh_doctor_formulas()

    def show_selected(self) -> None:
        items = self.table.selectedItems()
        if not items:
            return
        self.current_formula_id = int(items[0].data(Qt.ItemDataRole.UserRole))
        formula = self.formulas.detail(self.current_formula_id)
        ingredients = formula.get("ingredients_text", "").strip() or (
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

    def refresh_doctor_formulas(self) -> None:
        if not hasattr(self, "doctor_table"):
            return
        rows = [row for row in self.formulas.search() if row["source_type"] == "doctor"]
        self.doctor_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            values = (
                row["code"],
                row["name"],
                row["created_by"],
                "Có" if row["doctor_approved"] else "Chưa",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, row["id"])
                self.doctor_table.setItem(index, column, item)

    def load_doctor_formula(self) -> None:
        items = self.doctor_table.selectedItems()
        if not items:
            return
        self.doctor_formula_id = int(items[0].data(Qt.ItemDataRole.UserRole))
        row = self.formulas.detail(self.doctor_formula_id)
        self.df_code.setText(row["code"])
        self.df_name.setText(row["name"])
        self.df_category.setText(row["category"])
        self.df_doctor.setText(row["created_by"])
        self.df_principle.setText(row["treatment_principle"])
        self.df_indications.setPlainText(row["indications"])
        self.df_ingredients.setPlainText(row["ingredients_text"])
        self.df_directions.setPlainText(row["directions"])
        self.df_modifications.setPlainText(row["modifications"])
        self.df_contraindications.setPlainText(row["contraindications"])
        self.df_interactions.setPlainText(row["interactions"])
        self.df_source.setText(row["reference_source"])
        self.df_approved.setChecked(bool(row["doctor_approved"]))

    def doctor_formula_values(self) -> dict[str, object]:
        return {
            "code": self.df_code.text(),
            "name": self.df_name.text(),
            "category": self.df_category.text(),
            "created_by": self.df_doctor.text(),
            "treatment_principle": self.df_principle.text(),
            "indications": self.df_indications.toPlainText(),
            "ingredients_text": self.df_ingredients.toPlainText(),
            "directions": self.df_directions.toPlainText(),
            "modifications": self.df_modifications.toPlainText(),
            "contraindications": self.df_contraindications.toPlainText(),
            "interactions": self.df_interactions.toPlainText(),
            "reference_source": self.df_source.text(),
            "doctor_approved": self.df_approved.isChecked(),
        }

    def save_doctor_formula(self) -> None:
        try:
            if self.doctor_formula_id is None:
                self.formulas.create_doctor_formula(self.doctor_formula_values())
            else:
                self.formulas.update_doctor_formula(
                    self.doctor_formula_id, self.doctor_formula_values()
                )
        except Exception as error:
            QMessageBox.warning(self, "Chưa thể lưu", str(error))
            return
        self.clear_doctor_formula()
        self.refresh_catalogue()
        QMessageBox.information(self, "Đã lưu", "Đã lưu bài thuốc kinh nghiệm.")

    def hide_doctor_formula(self) -> None:
        if self.doctor_formula_id is None:
            return
        try:
            self.formulas.hide_doctor_formula(self.doctor_formula_id, self.df_doctor.text())
        except ValueError as error:
            QMessageBox.warning(self, "Chưa thể ẩn", str(error))
            return
        self.clear_doctor_formula()
        self.refresh_catalogue()

    def clear_doctor_formula(self) -> None:
        self.doctor_formula_id = None
        for widget in (
            self.df_code,
            self.df_name,
            self.df_category,
            self.df_doctor,
            self.df_principle,
            self.df_source,
        ):
            widget.clear()
        for widget in (
            self.df_indications,
            self.df_ingredients,
            self.df_directions,
            self.df_modifications,
            self.df_contraindications,
            self.df_interactions,
        ):
            widget.clear()
        self.df_approved.setChecked(False)

    def refresh_patients(self) -> None:
        self.patient.blockSignals(True)
        self.patient.clear()
        self.ai_patient.blockSignals(True)
        self.ai_patient.clear()
        self.patient.addItem("Chọn bệnh nhân", None)
        self.ai_patient.addItem("Chọn bệnh nhân", None)
        for row in self.patients.list():
            self.patient.addItem(f"{row['code']} — {row['full_name']}", row["id"])
            self.ai_patient.addItem(f"{row['code']} — {row['full_name']}", row["id"])
        self.patient.blockSignals(False)
        self.ai_patient.blockSignals(False)
        self.refresh_visits()
        self.refresh_ai_visits()

    def refresh_ai_visits(self) -> None:
        self.ai_visit.clear()
        patient_id = self.ai_patient.currentData()
        if patient_id is not None:
            for row in self.consultations.list_for_patient(int(patient_id)):
                self.ai_visit.addItem(f"{row['visit_code']} — {row['created_at']}", row["id"])

    def run_recommendation(self) -> None:
        consultation_id = self.ai_visit.currentData()
        if consultation_id is None:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Chọn bệnh nhân và lần khám.")
            return
        result = self.recommender.recommend(int(consultation_id))
        lines = ["PHÁP TRỊ", *[f"• {x}" for x in result["principles"]], ""]
        for rank, item in enumerate(result["recommendations"], 1):
            detail = self.formulas.detail(int(item["id"]))
            ingredients = ", ".join(x["herb_name"] for x in detail["ingredients"])
            alerts = item["safety"] or [{"message": "Chưa ghi nhận cảnh báo."}]
            lines.extend(
                (
                    f"#{rank} — {item['name']} — phù hợp {item['score']}%",
                    f"Công năng/pháp trị: {item['treatment_principle']}",
                    f"Chủ trị tham khảo: {item['indications']}",
                    f"Thành phần gốc: {ingredients or 'Chưa có dữ liệu'}",
                    f"Cơ sở xếp hạng: {', '.join(item['matched']) or 'dữ liệu tham chiếu'}",
                    f"Huyệt tham khảo: {', '.join(item['acupoints']) or 'Bác sĩ quyết định'}",
                    "Cảnh báo:",
                    *[f"  • {alert['message']}" for alert in alerts],
                    f"Nguồn: {item['reference_source']}",
                    "",
                )
            )
        lines.append(result["disclaimer"])
        self.ai_result.setPlainText("\n".join(lines))

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
