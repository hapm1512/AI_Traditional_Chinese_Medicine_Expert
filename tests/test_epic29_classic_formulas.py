from pathlib import Path

import pytest

from tcm_expert.database import DatabaseManager, FormulaRepository
from tcm_expert.services.classic_formula_sync import ClassicFormulaSync


@pytest.fixture
def database(tmp_path: Path) -> DatabaseManager:
    manager = DatabaseManager(tmp_path / "epic29.db")
    manager.initialize()
    return manager


def sample_loader(_url: str, _timeout: float):
    return [{
        "id": "gui_zhi_tang", "name": "桂枝汤", "alias": "", "meridian": "太阳",
        "category": "解表剂",
        "components": [
            {"name": "桂枝", "dosage": "三两", "role": "解肌"},
            {"name": "芍药", "dosage": "三两"},
        ],
        "indication": "太阳中风。", "contraindication": "表实无汗者慎用。",
        "dosage": "水煎服。",
        "explanation": "调和营卫。",
        "keywords": ["恶风", "汗出"],
    }]


def test_sync_imports_and_updates_without_duplicates(database: DatabaseManager):
    sync = ClassicFormulaSync(database, loader=sample_loader)
    first = sync.sync()
    second = sync.sync()
    assert (first.inserted, first.updated, first.skipped) == (1, 0, 0)
    assert (second.inserted, second.updated, second.skipped) == (0, 1, 0)
    rows = FormulaRepository(database).search("桂枝汤")
    assert len(rows) == 1
    detail = FormulaRepository(database).detail(rows[0]["id"])
    assert detail["code"] == "CF-gui_zhi_tang"
    assert "桂枝 — 三两 — 解肌" in detail["ingredients_text"]
    assert "MIT" in detail["reference_source"]


def test_sync_rejects_non_https(database: DatabaseManager):
    with pytest.raises(ValueError, match="HTTPS"):
        ClassicFormulaSync(database, loader=sample_loader).sync(
            "http://example.test/formulas.json"
        )
