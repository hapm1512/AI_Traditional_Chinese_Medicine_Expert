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
