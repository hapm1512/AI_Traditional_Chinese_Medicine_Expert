import json
from pathlib import Path

from tcm_expert.database import DatabaseManager, FormulaRepository
from tcm_expert.services.classic_formula_sync import ClassicFormulaSync
from tcm_expert.services.ollama_formula_translator import (
    OllamaFormulaTranslator,
    OllamaLocalChat,
)


def test_qwen_translation_is_saved_separately(tmp_path: Path):
    database = DatabaseManager(tmp_path / "epic30.db")
    database.initialize()
    source = [{
        "id": "gui_zhi_tang",
        "name": "桂枝汤",
        "category": "解表剂",
        "components": [{"name": "桂枝", "dosage": "三两"}],
        "indication": "太阳中风。",
    }]
    ClassicFormulaSync(database, loader=lambda _url, _timeout: source).sync()
    formula = FormulaRepository(database).search("桂枝汤")[0]
    translated = {
        "name": "Quế chi thang",
        "category": "Giải biểu",
        "treatment_principle": "Điều hòa dinh vệ",
        "indications": "Thái dương trúng phong",
        "directions": "Giữ nguyên liều nguồn",
        "contraindications": "Cần bác sĩ kiểm tra",
        "interactions": "Chưa đủ dữ liệu",
        "ingredients_text": "Quế chi (桂枝) — ba lạng",
    }

    def transport(_url, _payload, _timeout):
        return {"message": {"content": json.dumps(translated)}}

    chat = OllamaLocalChat(model="qwen-test", transport=transport)
    translator = OllamaFormulaTranslator(database, chat=chat, model="qwen-test")
    assert translator.pending_formula_ids() == [formula["id"]]
    translator.translate(formula["id"])
    assert translator.pending_formula_ids() == []
    assert translator.translation_counts() == (1, 1)
    detail = FormulaRepository(database).detail(formula["id"])
    assert detail["name_cn"] == "桂枝汤"
    assert detail["translation"]["name"] == "Quế chi thang"
    assert detail["translation"]["status"] == "draft"
