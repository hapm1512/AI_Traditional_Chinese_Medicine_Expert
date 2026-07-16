from pathlib import Path

from tcm_expert.database import DatabaseManager, FormulaRepository


def test_doctor_formula_crud_and_approval_gate(tmp_path: Path) -> None:
    database = DatabaseManager(tmp_path / "doctor-formula.db")
    database.initialize()
    formulas = FormulaRepository(database)
    formula_id = formulas.create_doctor_formula(
        {
            "code": "KN001",
            "name": "Bài thuốc kinh nghiệm",
            "created_by": "BS Nguyễn",
            "ingredients_text": "Cam thảo — 4 g",
            "indications": "Mệt mỏi",
            "doctor_approved": False,
        }
    )
    detail = formulas.detail(formula_id)
    assert detail["source_type"] == "doctor"
    assert detail["ingredients_text"] == "Cam thảo — 4 g"
    assert detail["doctor_approved"] == 0

    formulas.update_doctor_formula(
        formula_id,
        {
            "code": "KN001",
            "name": "Bài thuốc kinh nghiệm",
            "created_by": "BS Nguyễn",
            "ingredients_text": "Cam thảo — 6 g",
            "indications": "Mệt mỏi",
            "doctor_approved": True,
        },
    )
    assert formulas.detail(formula_id)["doctor_approved"] == 1
    formulas.hide_doctor_formula(formula_id, "BS Nguyễn")
    assert all(row["id"] != formula_id for row in formulas.search())


def test_system_formula_can_be_updated_by_identified_doctor(tmp_path: Path) -> None:
    database = DatabaseManager(tmp_path / "system-formula.db")
    database.initialize()
    formulas = FormulaRepository(database)
    current = formulas.search()[0]
    detail = formulas.detail(current["id"])
    formulas.update_formula(
        current["id"],
        {
            "code": detail["code"],
            "name": detail["name"],
            "category": detail["category"],
            "created_by": "BS Nguyễn",
            "treatment_principle": detail["treatment_principle"],
            "indications": detail["indications"] + " — đã rà soát",
            "ingredients_text": "Thành phần đã được bác sĩ rà soát",
            "directions": detail["directions"],
            "doctor_approved": True,
        },
    )
    updated = formulas.detail(current["id"])
    assert updated["source_type"] == "system"
    assert updated["created_by"] == "BS Nguyễn"
    assert "đã rà soát" in updated["indications"]
