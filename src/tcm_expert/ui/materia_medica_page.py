from __future__ import annotations

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QProgressDialog,
    QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget,
)

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.materia_medica_repository import MateriaMedicaRepository
from tcm_expert.services.materia_medica_sync import MateriaMedicaSync
from tcm_expert.services.ollama_herb_translator import OllamaHerbTranslator


class HerbTranslationWorker(QThread):
    progress = Signal(int, int, str)
    batch_finished = Signal(int, int, int, bool)

    def __init__(self, translator: OllamaHerbTranslator, herb_ids: list[int] | None = None):
        super().__init__()
        self.translator = translator
        self.herb_ids = herb_ids
        self.cancel_requested = False

    def request_cancel(self) -> None:
        self.cancel_requested = True

    def run(self) -> None:
        ids = self.herb_ids if self.herb_ids is not None else self.translator.pending_herb_ids()
        completed = errors = 0
        for position, herb_id in enumerate(ids, 1):
            if self.cancel_requested:
                break
            try:
                result = self.translator.translate(herb_id)
                completed += 1
                message = result["name_vi"]
            except Exception as error:
                errors += 1
                message = f"Lỗi vị #{herb_id}: {error}"
            self.progress.emit(position, len(ids), message)
        self.batch_finished.emit(completed, errors, len(ids), self.cancel_requested)


class MateriaMedicaPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.repository = MateriaMedicaRepository(database)
        self.sync_service = MateriaMedicaSync(database)
        self.translator = OllamaHerbTranslator(database)
        self.ids: list[int] = []
        self.worker: HerbTranslationWorker | None = None
        self.progress_dialog: QProgressDialog | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Tra cứu dược liệu")
        title.setObjectName("title")
        layout.addWidget(title)
        warning = QLabel(
            "⚠ Dữ liệu chỉ tham khảo. Không tự đề xuất liều. Bác sĩ kiểm tra trước sử dụng."
        )
        warning.setObjectName("warning")
        layout.addWidget(warning)

        filters = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Tên dược liệu, công năng hoặc cổ phương...")
        self.category = QComboBox()
        self.category.addItem("Tất cả nhóm", "")
        for name in self.repository.categories():
            self.category.addItem(name, name)
        self.status = QComboBox()
        self.status.addItem("Mọi trạng thái", "")
        self.status.addItem("Chờ dịch", "pending")
        self.status.addItem("Bản dịch nháp", "draft")
        self.status.addItem("Đã duyệt", "approved")
        search = QPushButton("Tìm kiếm")
        search.clicked.connect(self.refresh)
        add_herb = QPushButton("Thêm dược liệu")
        add_herb.clicked.connect(self.add_herb)
        sync = QPushButton("Cập nhật dược liệu")
        sync.clicked.connect(self.sync_catalogue)
        translate = QPushButton("Dịch vị đang chọn")
        translate.clicked.connect(self.translate_selected)
        review = QPushButton("Sửa / duyệt")
        review.clicked.connect(self.review_selected)
        translate_all = QPushButton("Dịch toàn bộ qua đêm")
        translate_all.clicked.connect(self.translate_all)
        self.query.returnPressed.connect(self.refresh)
        for widget in (
            self.query, self.category, self.status, search, add_herb, sync, translate,
            review, translate_all
        ):
            filters.addWidget(widget, 1 if widget is self.query else 0)
        layout.addLayout(filters)

        self.counts = QLabel()
        layout.addWidget(self.counts)
        splitter = QSplitter()
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ("Mã", "Tên Việt", "Tên Trung", "Tên Latin", "Nhóm", "Trạng thái")
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_selected)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail)
        splitter.setSizes((650, 650))
        layout.addWidget(splitter, 1)
        self.refresh()

    def has_active_background_task(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def refresh(self) -> None:
        rows = self.repository.search(
            self.query.text(), str(self.category.currentData() or ""),
            str(self.status.currentData() or ""),
        )
        self.ids = [int(row["id"]) for row in rows]
        self.table.setRowCount(len(rows))
        labels = {None: "Chờ dịch", "draft": "Bản dịch nháp", "approved": "Đã duyệt"}
        for index, row in enumerate(rows):
            name_vi = row["translated_name"] or row["name_vi"]
            values = (row["code"], name_vi, row["name_cn"], row["pharmaceutical_name"],
                      row["category_name"], labels.get(row["translation_status"], "Chờ dịch"))
            for column, value in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(str(value or "")))
        translated, total = self.repository.translation_counts()
        review = self.repository.review_counts()
        self.counts.setText(
            f"Danh mục: {total} vị • Đã dịch: {translated} • Chờ dịch: {review['pending']} "
            f"• Bản nháp: {review['draft']} • Đã duyệt: {review['approved']}"
        )
        if rows:
            self.table.selectRow(0)
        else:
            self.detail.clear()

    def add_herb(self) -> None:
        fields = (
            ("code", "Mã dược liệu"), ("name_vi", "Tên Việt"),
            ("name_cn", "Tên Trung"),
            ("pharmaceutical_name", "Tên Latin / dược điển"),
            ("category_name", "Nhóm dược liệu"), ("nature", "Tính"),
            ("flavor", "Vị"), ("meridians", "Quy kinh"),
            ("functions", "Công năng, chủ trị"),
            ("modern_effects", "Tác dụng hiện đại"),
            ("combinations", "Phối ngũ"), ("processing", "Sơ chế, bào chế"),
            ("toxicity", "Độc tính"),
            ("contraindications", "Chống chỉ định"), ("cautions", "Lưu ý"),
            ("reference_source", "Nguồn dữ liệu"),
        )
        dialog = QDialog(self)
        dialog.setWindowTitle("Thêm dược liệu mới")
        dialog.resize(760, 760)
        layout = QVBoxLayout(dialog)
        note = QLabel("Bác sĩ hoặc Admin nhập dữ liệu. Bản ghi mới được lưu dạng nháp.")
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QFormLayout()
        editors: dict[str, QTextEdit | QLineEdit] = {}
        short_fields = {
            "code", "name_vi", "name_cn", "pharmaceutical_name", "category_name",
            "nature", "flavor", "meridians", "reference_source",
        }
        for key, label in fields:
            if key in short_fields:
                editor: QTextEdit | QLineEdit = QLineEdit()
            else:
                editor = QTextEdit()
                editor.setMaximumHeight(80)
            editors[key] = editor
            form.addRow(label, editor)
        source_editor = editors["reference_source"]
        if isinstance(source_editor, QLineEdit):
            source_editor.setText("Sưu tầm")
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = {
            key: editor.text() if isinstance(editor, QLineEdit) else editor.toPlainText()
            for key, editor in editors.items()
        }
        try:
            herb_id = self.repository.create_manual(values)
        except PermissionError as error:
            QMessageBox.warning(self, "Không có quyền", str(error))
            return
        except Exception as error:
            QMessageBox.warning(self, "Không thể thêm", str(error))
            return
        self.status.setCurrentIndex(0)
        self.query.clear()
        self.refresh()
        if herb_id in self.ids:
            self.table.selectRow(self.ids.index(herb_id))
        QMessageBox.information(
            self, "Đã thêm", "Dược liệu sưu tầm đã được lưu dạng bản nháp."
        )

    def show_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.ids):
            return
        item = self.repository.detail(self.ids[row])
        tr = item.get("translation") or {}
        value = lambda key: tr.get(key) or item.get(key) or "Chưa có dữ liệu"
        formulas = "\n".join(
            f"  - {f['code']} — {f['translated_name'] or f['name']} {f['name_cn']}"
            for f in item["formulas"]
        ) or "  Chưa có cổ phương đã duyệt liên kết"
        self.detail.setPlainText(
            f"{value('name_vi')}  {item['name_cn']}\n{item['pharmaceutical_name']}\n\n"
            f"• Tính vị: {value('nature')}, {value('flavor')}\n"
            f"• Quy kinh: {value('meridians')}\n"
            f"• Công năng, chủ trị: {value('functions')}\n"
            f"• Tác dụng hiện đại: {value('modern_effects')}\n"
            f"• Phối ngũ: {value('combinations')}\n"
            f"• Sơ chế, bào chế: {value('processing')}\n"
            f"• Độc tính: {value('toxicity')}\n\n"
            f"⚠ CHỐNG CHỈ ĐỊNH\n{value('contraindications')}\n\n"
            f"⚠ LƯU Ý\n{value('cautions')}\n\n"
            f"• Cổ phương đã duyệt chứa vị này:\n{formulas}\n\n"
            f"• Nguồn: {item['reference_source']}\n"
            f"• Trạng thái: {tr.get('status', 'chờ dịch')}"
        )

    def sync_catalogue(self) -> None:
        try:
            result = self.sync_service.sync()
        except Exception as error:
            QMessageBox.warning(self, "Không thể cập nhật", str(error))
            return
        self.refresh()
        QMessageBox.information(
            self, "Đã cập nhật",
            f"Nhận {result.received}; thêm {result.inserted}; cập nhật {result.updated}; "
            f"bỏ qua {result.skipped}; liên kết {result.linked}.",
        )

    def translate_selected(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, "Đang dịch", "Một tiến trình dịch đang chạy.")
            return
        row = self.table.currentRow()
        if row < 0 or row >= len(self.ids):
            QMessageBox.warning(self, "Chưa chọn", "Hãy chọn dược liệu cần dịch.")
            return
        self.progress_dialog = QProgressDialog(
            "Đang gửi vị thuốc tới Qwen...", "Dừng sau vị hiện tại", 0, 1, self
        )
        self.progress_dialog.setWindowTitle("Dịch vị thuốc bằng Ollama/Qwen")
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.setValue(0)
        self.worker = HerbTranslationWorker(self.translator, [self.ids[row]])
        self.progress_dialog.canceled.connect(self.worker.request_cancel)
        self.worker.progress.connect(self._progressed)
        self.worker.batch_finished.connect(self._finished)
        self.worker.start()

    def translate_all(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        pending = self.translator.pending_herb_ids()
        if not pending:
            QMessageBox.information(self, "Đã hoàn tất", "Không còn dược liệu chờ dịch.")
            return
        self.progress_dialog = QProgressDialog(
            "Đang khởi động Qwen...", "Dừng sau vị hiện tại", 0, len(pending), self
        )
        self.progress_dialog.setWindowTitle("Dịch dược liệu qua đêm")
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.worker = HerbTranslationWorker(self.translator)
        self.progress_dialog.canceled.connect(self.worker.request_cancel)
        self.worker.progress.connect(self._progressed)
        self.worker.batch_finished.connect(self._finished)
        self.worker.start()

    def review_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.ids):
            QMessageBox.warning(self, "Chưa chọn", "Hãy chọn dược liệu cần kiểm tra.")
            return
        item = self.repository.detail(self.ids[row])
        current = item.get("translation") or {}
        fields = (
            ("code", "Mã dược liệu"), ("name_vi", "Tên Việt"),
            ("name_cn", "Tên Trung"), ("pharmaceutical_name", "Tên Latin / dược điển"),
            ("category_name", "Nhóm dược liệu"), ("nature", "Tính"), ("flavor", "Vị"),
            ("meridians", "Quy kinh"), ("functions", "Công năng, chủ trị"),
            ("modern_effects", "Tác dụng hiện đại"), ("combinations", "Phối ngũ"),
            ("processing", "Sơ chế, bào chế"), ("toxicity", "Độc tính"),
            ("contraindications", "Chống chỉ định"), ("cautions", "Lưu ý"),
            ("reference_source", "Nguồn dữ liệu"),
        )
        dialog = QDialog(self)
        dialog.setWindowTitle("Bác sĩ kiểm tra bản dịch")
        dialog.resize(760, 760)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        editors: dict[str, QTextEdit | QLineEdit] = {}
        for key, label in fields:
            if key in (
                "code", "name_vi", "name_cn", "pharmaceutical_name", "category_name",
                "nature", "flavor", "meridians", "reference_source",
            ):
                editor: QTextEdit | QLineEdit = QLineEdit()
                editor.setText(str(current.get(key) or item.get(key) or ""))
            else:
                editor = QTextEdit()
                editor.setMaximumHeight(80)
                editor.setPlainText(str(current.get(key) or item.get(key) or ""))
            editors[key] = editor
            form.addRow(label, editor)
        layout.addLayout(form)
        approved = QCheckBox("Bác sĩ đã kiểm tra và phê duyệt")
        approved.setChecked(current.get("status") == "approved")
        layout.addWidget(approved)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        save = buttons.addButton("Lưu", QDialogButtonBox.ButtonRole.AcceptRole)
        save_next = buttons.addButton(
            "Lưu và mở vị kế tiếp", QDialogButtonBox.ButtonRole.ActionRole
        )
        action = {"next": False}
        save.clicked.connect(dialog.accept)
        def accept_and_continue() -> None:
            action["next"] = True
            dialog.accept()
        save_next.clicked.connect(accept_and_continue)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = {
            key: editor.text() if isinstance(editor, QLineEdit) else editor.toPlainText()
            for key, editor in editors.items()
        }
        herb_id = self.ids[row]
        try:
            self.repository.save_review(herb_id, values, approved.isChecked())
        except PermissionError as error:
            QMessageBox.warning(self, "Không có quyền", str(error))
            return
        except Exception as error:
            QMessageBox.warning(self, "Không thể lưu", str(error))
            return
        self.refresh()
        if action["next"]:
            next_id = self.repository.next_review_id(herb_id)
            if next_id is None:
                QMessageBox.information(self, "Đã hoàn tất", "Không còn dược liệu chờ kiểm duyệt.")
                return
            try:
                next_row = self.ids.index(next_id)
            except ValueError:
                self.status.setCurrentIndex(0)
                self.refresh()
                next_row = self.ids.index(next_id)
            self.table.selectRow(next_row)
            QTimer.singleShot(0, self.review_selected)

    def _progressed(self, current: int, total: int, message: str) -> None:
        if self.progress_dialog:
            self.progress_dialog.setMaximum(total)
            self.progress_dialog.setValue(current)
            self.progress_dialog.setLabelText(f"{current}/{total}: {message}")

    def _finished(self, completed: int, errors: int, total: int, cancelled: bool) -> None:
        if self.progress_dialog:
            self.progress_dialog.close()
        self.refresh()
        state = "Đã dừng" if cancelled else "Đã hoàn tất"
        QMessageBox.information(
            self, state, f"Đã dịch {completed}/{total}; lỗi {errors}. Lần sau tự tiếp tục phần còn lại."
        )
        self.worker = None
        self.progress_dialog = None
