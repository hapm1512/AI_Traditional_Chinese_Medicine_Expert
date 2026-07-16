from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tcm_expert.database.manager import DatabaseManager


class MateriaMedicaPage(QWidget):
    def __init__(self, database: DatabaseManager):
        super().__init__()
        self.database = database
        self.ids: list[int] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Tra cứu dược")
        title.setObjectName("title")
        layout.addWidget(title)
        warning = QLabel("⚠ Dữ liệu dược liệu chỉ tham khảo. Bác sĩ kiểm tra trước sử dụng.")
        warning.setObjectName("warning")
        layout.addWidget(warning)
        filters = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Tên dược liệu, công dụng, quy kinh...")
        self.category = QComboBox()
        self.category.addItem("Tất cả nhóm", "")
        with database.transaction() as connection:
            rows = connection.execute("SELECT name FROM herb_categories ORDER BY name").fetchall()
        for row in rows:
            self.category.addItem(row["name"], row["name"])
        search = QPushButton("Tìm kiếm")
        search.clicked.connect(self.refresh)
        self.query.returnPressed.connect(self.refresh)
        filters.addWidget(self.query, 1)
        filters.addWidget(self.category)
        filters.addWidget(search)
        layout.addLayout(filters)
        splitter = QSplitter()
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(("Mã", "Tên dược liệu", "Tính vị", "Quy kinh"))
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_selected)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail)
        splitter.setSizes((460, 700))
        layout.addWidget(splitter, 1)
        self.refresh()

    def refresh(self) -> None:
        term = f"%{self.query.text().strip()}%"
        category = str(self.category.currentData() or "")
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT DISTINCT h.* FROM materia_medica h
                   LEFT JOIN herb_categories hc ON hc.id=h.category_id
                   WHERE (?='%%' OR h.name_vi LIKE ? OR h.name_cn LIKE ?
                          OR h.pharmaceutical_name LIKE ? OR h.functions LIKE ?
                          OR h.meridians LIKE ?)
                     AND (?='' OR hc.name=?)
                   ORDER BY h.name_vi""",
                (term, term, term, term, term, term, category, category),
            ).fetchall()
        self.ids = [int(row["id"]) for row in rows]
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            values = (
                row["code"],
                f"{row['name_vi']} {row['name_cn']}",
                f"{row['nature']} • {row['flavor']}",
                row["meridians"],
            )
            for column, value in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(str(value or "")))
        if rows:
            self.table.selectRow(0)
        else:
            self.detail.clear()

    def show_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.ids):
            return
        with self.database.transaction() as connection:
            item = connection.execute(
                "SELECT * FROM materia_medica WHERE id=?", (self.ids[row],)
            ).fetchone()
        if item is None:
            return
        self.detail.setPlainText(
            f"{item['name_vi']}  {item['name_cn']}\n"
            f"{item['pharmaceutical_name']}\n\n"
            f"• Tính vị: {item['nature']}, {item['flavor']}\n"
            f"• Quy kinh: {item['meridians']}\n"
            f"• Công dụng Đông y: {item['functions']}\n"
            f"• Tác dụng tham khảo: {item['modern_effects'] or 'Chưa có dữ liệu'}\n"
            f"• Liều tham khảo: {float(item['dosage_min'] or 0):g}–"
            f"{float(item['dosage_max'] or 0):g} "
            f"{item['dosage_unit']}\n"
            f"• Phối hợp: {item['combinations'] or 'Chưa có dữ liệu'}\n"
            f"• Sơ chế, bào chế: {item['processing'] or item['preparation']}\n"
            f"• Cách sử dụng: {item['preparation']}\n\n"
            f"⚠ CHỐNG CHỈ ĐỊNH\n{item['contraindications'] or 'Chưa có dữ liệu'}\n\n"
            f"⚠ LƯU Ý\n{item['cautions'] or 'Chưa có dữ liệu'}\n\n"
            f"• Nguồn: {item['reference_source']}"
        )
