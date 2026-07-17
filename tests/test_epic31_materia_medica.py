import json
from pathlib import Path

from tcm_expert.database import DatabaseManager, MateriaMedicaRepository
from tcm_expert.services.materia_medica_sync import MateriaMedicaSync
from tcm_expert.services.ollama_formula_translator import OllamaLocalChat
from tcm_expert.services.ollama_herb_translator import OllamaHerbTranslator
from tcm_expert.security import UserSession, set_current_user


def test_sync_updates_without_deleting_and_links_formulas(tmp_path: Path):
    database = DatabaseManager(tmp_path / "epic31.db")
    database.initialize()
    source = [{
        "id": "gui_zhi", "name": "桂枝", "latin_name": "Cinnamomi Ramulus",
        "nature": "温", "flavor": "辛甘", "meridian": "心肺膀胱",
        "effects": "发汗解肌", "processing": "切片",
    }]
    sync = MateriaMedicaSync(database, loader=lambda _url, _timeout: source)
    first = sync.sync()
    assert first.inserted == 1
    with database.transaction() as connection:
        connection.execute(
            """INSERT INTO formulas(code,name,name_cn,ingredients_text)
               VALUES('CF-TEST','桂枝汤','桂枝汤','桂枝 — 三两')"""
        )
    second = sync.sync()
    assert second.updated == 1
    assert second.linked == 1
    assert len(MateriaMedicaRepository(database).search("桂枝")) == 1


def test_qwen_herb_translation_is_draft_and_resumable(tmp_path: Path):
    database = DatabaseManager(tmp_path / "epic31-translate.db")
    database.initialize()
    source = [{"id": "gui_zhi", "name": "桂枝", "effects": "发汗解肌"}]
    MateriaMedicaSync(database, loader=lambda _url, _timeout: source).sync()
    herb_id = MateriaMedicaRepository(database).search("桂枝")[0]["id"]
    translated = {field: "" for field in (
        "name_vi", "nature", "flavor", "meridians", "functions", "modern_effects",
        "combinations", "processing", "toxicity", "contraindications", "cautions",
    )}
    translated.update({"name_vi": "Quế chi", "functions": "Phát hãn giải cơ"})

    def transport(_url, _payload, _timeout):
        return {"message": {"content": json.dumps(translated)}}

    chat = OllamaLocalChat(model="qwen-test", transport=transport)
    translator = OllamaHerbTranslator(database, chat=chat, model="qwen-test")
    assert herb_id in translator.pending_herb_ids()
    translator.translate(herb_id)
    assert herb_id not in translator.pending_herb_ids()
    detail = MateriaMedicaRepository(database).detail(herb_id)
    assert detail["name_cn"] == "桂枝"
    assert detail["translation"]["name_vi"] == "Quế chi"
    assert detail["translation"]["status"] == "draft"


def test_doctor_can_edit_all_catalogue_columns(tmp_path: Path):
    database = DatabaseManager(tmp_path / "epic31-edit.db")
    database.initialize()
    set_current_user(UserSession(2, "doctor", "Bác sĩ", "doctor", 1))
    repository = MateriaMedicaRepository(database)
    herb_id = repository.search("Nhân sâm")[0]["id"]
    repository.save_review(
        herb_id,
        {
            "code": "DL-NHANSAM",
            "name_vi": "Nhân sâm Việt",
            "name_cn": "人參",
            "pharmaceutical_name": "Ginseng Radix et Rhizoma",
            "category_name": "Bổ khí nâng cao",
            "nature": "Ôn",
            "flavor": "Cam",
            "meridians": "Tỳ, Phế",
            "functions": "Bổ khí",
            "reference_source": "Bác sĩ hiệu chỉnh",
        },
        approved=True,
    )
    detail = repository.detail(herb_id)
    assert detail["code"] == "DL-NHANSAM"
    assert detail["name_cn"] == "人參"
    assert detail["category_name"] == "Bổ khí nâng cao"
    assert detail["translation"]["name_vi"] == "Nhân sâm Việt"
    assert detail["translation"]["status"] == "approved"
    set_current_user(None)


def test_epic32_review_queue_and_permissions(tmp_path: Path):
    database = DatabaseManager(tmp_path / "epic32-review.db")
    database.initialize()
    repository = MateriaMedicaRepository(database)
    rows = repository.search()
    first_id = int(rows[0]["id"])
    second_id = int(rows[1]["id"])

    set_current_user(UserSession(1, "admin", "Quản trị", "admin", 1))
    values = dict(repository.detail(first_id))
    values["name_vi"] = values["name_vi"] or "Dược liệu"
    repository.save_review(first_id, values, approved=False)
    try:
        repository.save_review(first_id, values, approved=True)
        assert False, "Quản trị viên không được phê duyệt"
    except PermissionError:
        pass

    set_current_user(UserSession(2, "doctor", "Bác sĩ", "doctor", 2))
    repository.save_review(first_id, values, approved=True)
    counts = repository.review_counts()
    assert counts["approved"] >= 1
    assert repository.next_review_id(first_id) != first_id
    assert repository.next_review_id(second_id) is not None
    set_current_user(None)


def test_epic32_doctor_or_admin_can_add_manual_herb(tmp_path: Path):
    database = DatabaseManager(tmp_path / "epic32-add-herb.db")
    database.initialize()
    repository = MateriaMedicaRepository(database)
    set_current_user(UserSession(1, "admin", "Quản trị", "admin", 1))
    herb_id = repository.create_manual({
        "code": "DL-TEST-001",
        "name_vi": "Dược liệu kiểm thử",
        "name_cn": "測試藥",
        "pharmaceutical_name": "Herba Test",
        "category_name": "Nhóm kiểm thử",
        "nature": "Bình",
        "flavor": "Cam",
        "functions": "Dữ liệu kiểm thử",
    })
    detail = repository.detail(herb_id)
    assert detail["code"] == "DL-TEST-001"
    assert detail["translation"]["status"] == "draft"
    assert detail["reference_source"] == "Sưu tầm"
    assert detail["translation"]["model"] == "collected"
    set_current_user(None)
