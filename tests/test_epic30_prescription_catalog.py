from pathlib import Path

from tcm_expert.database import DatabaseManager, PrescriptionRepository
from tcm_expert.services.classic_formula_sync import ClassicFormulaSync


def test_classic_formulas_are_available_for_prescription(tmp_path: Path):
    database = DatabaseManager(tmp_path / "prescription-catalog.db")
    database.initialize()
    ClassicFormulaSync(
        database,
        loader=lambda _url, _timeout: [{
            "id": "gui_zhi_tang",
            "name": "桂枝汤",
            "category": "解表剂",
            "components": [{"name": "桂枝", "dosage": "三两"}],
            "indication": "太阳中风。",
        }],
    ).sync()
    repository = PrescriptionRepository(database)
    rows = repository.approved_formula_catalog()
    assert any(row["code"] == "CF-gui_zhi_tang" for row in rows)
