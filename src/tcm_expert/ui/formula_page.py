from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database import (
    ConsultationRepository,
    FormulaRepository,
    PatientRepository,
    SettingsRepository,
)
from tcm_expert.database.manager import DatabaseManager
from tcm_expert.services.classic_formula_sync import ClassicFormulaSync
from tcm_expert.services.formula_recommender import FormulaRecommender
from tcm_expert.services.ollama_formula_translator import OllamaFormulaTranslator


class FormulaTranslationWorker(QThread):
    progress = Signal(int, int, str)
    batch_finished = Signal(int, int, int, bool)

    def __init__(self, translator: OllamaFormulaTranslator):
        super().__init__()
        self.translator = translator
        self.cancel_requested = False

    def request_cancel(self) -> None:
        self.cancel_requested = True

    def run(self) -> None:
        formula_ids = self.translator.pending_formula_ids()
        total = len(formula_ids)
        completed = errors = 0
        for position, formula_id in enumerate(formula_ids, 1):
            if self.cancel_requested:
                break
            try:
                result = self.translator.translate(formula_id)
                completed += 1
                message = result["name"]
            except Exception as error:
                errors += 1
                message = f"Lỗi bài #{formula_id}: {error}"
            self.progress.emit(position, total, message)
        self.batch_finished.emit(completed, errors, total, self.cancel_requested)


class FormulaPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.formulas = FormulaRepository(database)
        self.patients = PatientRepository(database)
        self.consultations = ConsultationRepository(database)
        self.recommender = FormulaRecommender(database)
        self.classic_formula_sync = ClassicFormulaSync(database)
        self.ollama_translator = OllamaFormulaTranslator(database)
        self.settings = SettingsRepository(database)
        self.current_formula_id: int | None = None
        self.translation_worker: FormulaTranslationWorker | None = None
        self.translation_progress: QProgressDialog | None = None
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

        self.tabs = QTabWidget()
        self.tabs.addTab(self._catalogue_tab(), "Tra cứu bài thuốc")
        self.tabs.addTab(self._doctor_formula_tab(), "Soạn thảo bài thuốc")
        self.tabs.addTab(self._recommendation_tab(), "Gắn vào hồ sơ khám")
        self.tabs.addTab(self._ai_tab(), "Gợi ý thông minh")
        layout.addWidget(self.tabs, 1)
        self.refresh_catalogue()
        self.refresh_patients()

    def has_active_background_task(self) -> bool:
        return self.translation_worker is not None and self.translation_worker.isRunning()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self.refresh_catalogue()
        self.refresh_patients()

    def _editor_with_pen(self, editor: QTextEdit, title: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        button = QPushButton("✎")
        button.setToolTip(f"Mở trình soạn thảo {title.lower()}")
        button.setFixedWidth(42)
        button.clicked.connect(lambda: self._open_editor(editor, title))
        layout.addWidget(editor, 1)
        layout.addWidget(button)
        return container

    def _open_editor(self, editor: QTextEdit, title: str) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Soạn thảo — {title}")
        dialog.resize(680, 420)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setPlainText(editor.toPlainText())
        layout.addWidget(text)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec():
            editor.setPlainText(text.toPlainText())

    def _catalogue_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        filters = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Tên bài thuốc, chỉ định hoặc dược liệu...")
        self.category = QComboBox()
        self.category.addItem("Tất cả nhóm", "")
        for name in self.formulas.categories():
            self.category.addItem(name, name)
        search = QPushButton("Tìm kiếm")
        search.clicked.connect(self.refresh_catalogue)
        edit = QPushButton("Chỉnh sửa bài thuốc")
        edit.clicked.connect(self.edit_selected_formula)
        sync = QPushButton("Cập nhật cổ phương")
        sync.setToolTip("Tải danh mục cổ phương mở để tra cứu và kiểm thử")
        sync.clicked.connect(self.sync_classic_formulas)
        translate = QPushButton("Dịch thử bằng Qwen")
        translate.setToolTip("Dịch bài thuốc đang chọn bằng Ollama cục bộ")
        translate.clicked.connect(self.translate_selected_formula)
        translate_all = QPushButton("Dịch toàn bộ qua đêm")
        translate_all.setToolTip("Dịch và lưu tuần tự các cổ phương chưa có bản Việt")
        translate_all.clicked.connect(self.translate_all_formulas)
        self.query.returnPressed.connect(self.refresh_catalogue)
        filters.addWidget(self.query, 1)
        filters.addWidget(self.category)
        filters.addWidget(search)
        filters.addWidget(edit)
        filters.addWidget(sync)
        filters.addWidget(translate)
        filters.addWidget(translate_all)
        layout.addLayout(filters)
        splitter = QSplitter()
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(("Nhóm", "Tên bài thuốc", "Mã", "Nguồn", "Vị"))
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

    def sync_classic_formulas(self) -> None:
        answer = QMessageBox.question(
            self,
            "Cập nhật cổ phương",
            "Tải dữ liệu cổ phương từ nguồn mở? Dữ liệu chỉ dùng tham khảo và kiểm thử.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self.classic_formula_sync.sync()
        except Exception as error:
            QMessageBox.warning(self, "Không thể cập nhật", str(error))
            return
        self.refresh_catalogue()
        QMessageBox.information(
            self,
            "Đã cập nhật",
            f"Nhận {result.received} bài; thêm {result.inserted}; "
            f"cập nhật {result.updated}; bỏ qua {result.skipped}.",
        )

    def translate_selected_formula(self) -> None:
        if self.current_formula_id is None:
            QMessageBox.warning(self, "Chưa chọn", "Hãy chọn một cổ phương cần dịch thử.")
            return
        try:
            self.ollama_translator.translate(self.current_formula_id)
        except Exception as error:
            QMessageBox.warning(
                self,
                "Không thể dịch",
                f"Kiểm tra Ollama và mô hình qwen2.5:7b.\n\n{error}",
            )
            return
        self.show_selected()
        QMessageBox.information(
            self,
            "Đã dịch thử",
            "Bản dịch được lưu ở trạng thái nháp. Dữ liệu Trung văn vẫn được giữ nguyên.",
        )

    def translate_all_formulas(self) -> None:
        if self.translation_worker is not None and self.translation_worker.isRunning():
            QMessageBox.information(self, "Đang dịch", "Tiến trình dịch toàn bộ đang chạy.")
            return
        pending = self.ollama_translator.pending_formula_ids()
        translated, total = self.ollama_translator.translation_counts()
        if not pending:
            QMessageBox.information(
                self, "Đã hoàn tất", f"Đã có bản dịch cho {translated}/{total} cổ phương."
            )
            return
        answer = QMessageBox.question(
            self,
            "Dịch toàn bộ qua đêm",
            f"Còn {len(pending)} cổ phương chưa dịch. Bắt đầu dịch và lưu từng bài?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.translation_progress = QProgressDialog(
            "Đang khởi động Qwen...", "Dừng sau bài hiện tại", 0, len(pending), self
        )
        self.translation_progress.setWindowTitle("Dịch cổ phương bằng Ollama/Qwen")
        self.translation_progress.setMinimumDuration(0)
        self.translation_progress.setAutoClose(False)
        self.translation_progress.setAutoReset(False)
        self.translation_worker = FormulaTranslationWorker(self.ollama_translator)
        self.translation_progress.canceled.connect(self.translation_worker.request_cancel)
        self.translation_worker.progress.connect(self._translation_progressed)
        self.translation_worker.batch_finished.connect(self._translation_batch_finished)
        self.translation_worker.start()

    def _translation_progressed(self, current: int, total: int, message: str) -> None:
        if self.translation_progress is None:
            return
        self.translation_progress.setMaximum(total)
        self.translation_progress.setValue(current)
        self.translation_progress.setLabelText(
            f"Đã xử lý {current}/{total}\n{message[:180]}"
        )

    def _translation_batch_finished(
        self, completed: int, errors: int, total: int, cancelled: bool
    ) -> None:
        if self.translation_progress is not None:
            self.translation_progress.close()
        self.refresh_catalogue()
        status = "Đã dừng" if cancelled else "Đã hoàn tất"
        QMessageBox.information(
            self,
            status,
            f"Tổng cần dịch: {total}\nĐã lưu: {completed}\nLỗi: {errors}\n"
            "Lần chạy sau sẽ tự bỏ qua các bài đã lưu.",
        )
        if self.translation_worker is not None:
            self.translation_worker.deleteLater()
        self.translation_worker = None
        self.translation_progress = None

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
        self.df_doctor.setReadOnly(True)
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
        form.addRow("Bác sĩ duyệt *", self.df_doctor)
        form.addRow("Pháp trị", self.df_principle)
        form.addRow("Chủ trị kinh nghiệm", self._editor_with_pen(self.df_indications, "Chủ trị"))
        form.addRow("Thành phần *", self._editor_with_pen(self.df_ingredients, "Thành phần"))
        form.addRow("Cách dùng", self._editor_with_pen(self.df_directions, "Cách dùng"))
        form.addRow("Gia giảm", self._editor_with_pen(self.df_modifications, "Gia giảm"))
        form.addRow(
            "Chống chỉ định", self._editor_with_pen(self.df_contraindications, "Chống chỉ định")
        )
        form.addRow("Tương tác/lưu ý", self._editor_with_pen(self.df_interactions, "Lưu ý"))
        form.addRow("Nguồn kinh nghiệm", self.df_source)
        form.addRow("Phê duyệt", self.df_approved)
        actions = QHBoxLayout()
        new_button = QPushButton("Nhập mới")
        new_button.clicked.connect(self.clear_doctor_formula)
        save_button = QPushButton("Lưu bài thuốc")
        save_button.clicked.connect(self.save_doctor_formula)
        actions.addWidget(new_button)
        actions.addWidget(save_button)
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
        self.chosen_formula = QComboBox()
        self.chosen_formula.currentIndexChanged.connect(self.load_chosen_formula)
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
        form.addRow("Lưu ý", self.safety_notes)
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
            ("Bài thuốc", "Cách dùng", "Gia giảm", "Lưu ý", "Phê duyệt")
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
        self.ai_visit.currentIndexChanged.connect(self.show_ai_context)
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
            category = row.get("translated_category") or row["category"]
            name = row.get("translated_name") or row["name"]
            values = (category, name, row["code"], source, count)
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, row["id"])
                self.table.setItem(row_index, column, item)
        if rows:
            self.table.selectRow(0)
        else:
            self.detail.clear()
        self.refresh_doctor_formulas()
        self.refresh_formula_choices()

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
        linked_herbs = "\n".join(
            f"• {x['code']} — {x['translated_name'] or x['name_vi']} {x['name_cn']}"
            for x in formula.get("linked_herbs", [])
        ) or "Chưa có dược liệu đã duyệt liên kết."
        safety = "\n".join(
            f"• {x['herb_name']} ↔ {x['interacts_with']}: {x['effect']}" for x in alerts
        )
        translation = formula.get("translation")
        translated = ""
        if translation:
            translated = (
                "BẢN DỊCH TIẾNG VIỆT — CHƯA DUYỆT\n"
                f"{translation['name']}\n\n"
                f"• Nhóm: {translation['category']}\n"
                f"• Pháp trị: {translation['treatment_principle']}\n"
                f"• Chỉ định: {translation['indications']}\n"
                f"• Cách dùng: {translation['directions']}\n\n"
                f"THÀNH PHẦN\n{translation['ingredients_text']}\n\n"
                f"⚠ CHỐNG CHỈ ĐỊNH\n{translation['contraindications']}\n\n"
                f"⚠ LƯU Ý\n{translation['interactions']}\n\n"
                f"• Mô hình: {translation['model']}\n"
                "• Trạng thái: Bản nháp, cần bác sĩ kiểm tra\n\n"
                "NGUYÊN BẢN TIẾNG TRUNG\n"
            )
        self.detail.setPlainText(
            f"{translated}{formula['name']}  {formula['name_cn']}\n\n"
            f"• Pháp trị: {formula['treatment_principle']}\n"
            f"• Chỉ định: {formula['indications']}\n"
            f"• Dạng: {formula['dosage_form']}\n"
            f"• Cách dùng: {formula['directions']}\n"
            f"• Gia giảm: {formula['modifications']}\n\n"
            f"THÀNH PHẦN\n{ingredients}\n\n"
            f"DƯỢC LIỆU ĐÃ DUYỆT LIÊN KẾT\n{linked_herbs}\n\n"
            f"⚠ CHỐNG CHỈ ĐỊNH\n{formula['contraindications']}\n\n"
            f"⚠ TƯƠNG TÁC / LƯU Ý\n{formula['interactions']}\n"
            f"{safety or '• Chưa ghi nhận dữ liệu tương tác.'}\n\n"
            f"• Nguồn: {formula['reference_source']}\n\n{formula['disclaimer']}"
        )
        index = self.chosen_formula.findData(formula["id"])
        if index >= 0:
            self.chosen_formula.setCurrentIndex(index)

    def refresh_formula_choices(self) -> None:
        if not hasattr(self, "chosen_formula"):
            return
        selected = self.chosen_formula.currentData()
        self.chosen_formula.clear()
        self.chosen_formula.addItem("Chọn bài thuốc", None)
        for row in self.formulas.search():
            if row["source_type"] == "system" or row["doctor_approved"]:
                self.chosen_formula.addItem(f"{row['code']} — {row['name']}", row["id"])
        index = self.chosen_formula.findData(selected)
        if index >= 0:
            self.chosen_formula.setCurrentIndex(index)

    def refresh_doctor_formulas(self) -> None:
        if not hasattr(self, "doctor_table"):
            return
        rows = self.formulas.search()
        self.doctor_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            values = (
                row["code"],
                row["name"],
                row["created_by"] or "Hệ thống",
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
        self._load_formula_into_editor(int(items[0].data(Qt.ItemDataRole.UserRole)))

    def edit_selected_formula(self) -> None:
        if self.current_formula_id is None:
            QMessageBox.warning(self, "Chưa chọn", "Hãy chọn bài thuốc cần chỉnh sửa.")
            return
        self._load_formula_into_editor(self.current_formula_id)
        self.tabs.setCurrentIndex(1)

    def _load_formula_into_editor(self, formula_id: int) -> None:
        self.doctor_formula_id = formula_id
        row = self.formulas.detail(formula_id)
        self.df_code.setText(row["code"])
        self.df_name.setText(row["name"])
        self.df_category.setText(row["category"])
        self.df_doctor.setText(row["created_by"])
        self.df_principle.setText(row["treatment_principle"])
        self.df_indications.setPlainText(row["indications"])
        ingredients = row["ingredients_text"].strip() or "\n".join(
            f"{item['herb_name']} — {item['dosage']:g} {item['unit']} — {item['role']}"
            for item in row["ingredients"]
        )
        self.df_ingredients.setPlainText(ingredients)
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
            self.df_doctor.setText(self.settings.doctor_name(required=True))
            if self.doctor_formula_id is None:
                self.formulas.create_doctor_formula(self.doctor_formula_values())
            else:
                self.formulas.update_formula(self.doctor_formula_id, self.doctor_formula_values())
        except Exception as error:
            QMessageBox.warning(self, "Chưa thể lưu", str(error))
            return
        self.doctor_formula_id = -1
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
        dirty = any(
            widget.text().strip()
            for widget in (self.df_code, self.df_name, self.df_category, self.df_principle)
        ) or any(
            widget.toPlainText().strip()
            for widget in (self.df_indications, self.df_ingredients, self.df_directions)
        )
        if dirty and self.doctor_formula_id is None:
            answer = QMessageBox.question(
                self,
                "Dữ liệu chưa lưu",
                "Thông tin hiện tại chưa được lưu. Tiếp tục nhập mới?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.doctor_formula_id = None
        for widget in (
            self.df_code,
            self.df_name,
            self.df_category,
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
        self.df_doctor.setText(self.settings.doctor_name())

    def refresh_patients(self) -> None:
        selected_patient = self.patient.currentData()
        selected_ai_patient = self.ai_patient.currentData()
        self.patient.blockSignals(True)
        self.patient.clear()
        self.ai_patient.blockSignals(True)
        self.ai_patient.clear()
        self.patient.addItem("Chọn bệnh nhân", None)
        self.ai_patient.addItem("Chọn bệnh nhân", None)
        for row in self.patients.list():
            self.patient.addItem(f"{row['code']} — {row['full_name']}", row["id"])
            self.ai_patient.addItem(f"{row['code']} — {row['full_name']}", row["id"])
        patient_index = self.patient.findData(selected_patient)
        ai_patient_index = self.ai_patient.findData(selected_ai_patient)
        if self.patient.count() > 1:
            self.patient.setCurrentIndex(patient_index if patient_index >= 1 else 1)
        if self.ai_patient.count() > 1:
            self.ai_patient.setCurrentIndex(ai_patient_index if ai_patient_index >= 1 else 1)
        self.patient.blockSignals(False)
        self.ai_patient.blockSignals(False)
        self.refresh_visits()
        self.refresh_ai_visits()

    def refresh_ai_visits(self) -> None:
        selected_visit = self.ai_visit.currentData()
        self.ai_visit.blockSignals(True)
        self.ai_visit.clear()
        self.ai_visit.addItem("Chọn lần khám", None)
        patient_id = self.ai_patient.currentData()
        if patient_id is not None:
            rows = self.consultations.list_for_patient(int(patient_id))
            for number, row in enumerate(reversed(rows), 1):
                self.ai_visit.addItem(
                    f"Lần khám {number} — {row['visit_code']} — {row['created_at']}", row["id"]
                )
            if rows:
                index = self.ai_visit.findData(selected_visit)
                self.ai_visit.setCurrentIndex(index if index >= 1 else 1)
            else:
                self.ai_visit.addItem("Chưa có lần khám", None)
        else:
            self.ai_visit.addItem("Chọn bệnh nhân trước", None)
        self.ai_visit.blockSignals(False)
        self.show_ai_context()

    def show_ai_context(self) -> None:
        consultation_id = self.ai_visit.currentData()
        if consultation_id is None:
            self.ai_result.clear()
            return
        visit = self.consultations.get(int(consultation_id))
        entries = self.consultations.diagnostic_entries(int(consultation_id))
        lines = [
            f"MÃ LẦN KHÁM: {visit['visit_code']}",
            f"LÝ DO KHÁM: {visit.get('chief_complaint') or 'Chưa nhập'}",
            f"TRIỆU CHỨNG: {visit.get('symptoms') or 'Chưa nhập'}",
            f"TIỀN SỬ: {visit.get('western_history') or 'Chưa nhập'}",
            f"NHẬN ĐỊNH: {visit.get('assessment') or 'Chưa nhập'}",
            "",
            "TỨ CHẨN:",
            *(
                [f"• {row['category']}: {row['finding']}" for row in entries]
                or ["• Chưa có dữ liệu"]
            ),
        ]
        self.ai_result.setPlainText("\n".join(lines))

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
        selected_visit = self.visit.currentData()
        self.visit.blockSignals(True)
        self.visit.clear()
        self.visit.addItem("Chọn lần khám", None)
        patient_id = self.patient.currentData()
        if patient_id is not None:
            rows = self.consultations.list_for_patient(int(patient_id))
            for number, row in enumerate(reversed(rows), 1):
                self.visit.addItem(
                    f"Lần khám {number} — {row['visit_code']} — {row['created_at']}", row["id"]
                )
            if rows:
                index = self.visit.findData(selected_visit)
                self.visit.setCurrentIndex(index if index >= 1 else 1)
            else:
                self.visit.addItem("Chưa có lần khám", None)
        else:
            self.visit.addItem("Chọn bệnh nhân trước", None)
        self.visit.blockSignals(False)
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

    def load_chosen_formula(self) -> None:
        formula_id = self.chosen_formula.currentData()
        if formula_id is None:
            return
        formula = self.formulas.detail(int(formula_id))
        self.directions.setText(formula.get("directions") or "")
        self.modifications.setPlainText(formula.get("modifications") or "")
        notes = "\n".join(
            value
            for value in (formula.get("contraindications"), formula.get("interactions"))
            if value
        )
        self.safety_notes.setPlainText(notes)

    def save(self) -> None:
        formula_id = self.chosen_formula.currentData()
        if self.visit.currentData() is None or formula_id is None:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Chọn lần khám và bài thuốc.")
            return
        try:
            self.formulas.save_recommendation(
                int(self.visit.currentData()),
                int(formula_id),
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
