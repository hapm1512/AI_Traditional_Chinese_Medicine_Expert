from pathlib import Path

from tcm_expert.database import DatabaseManager, FormulaRepository, MateriaMedicaRepository


def test_epic33_searches_approved_links_both_directions(tmp_path: Path):
    database = DatabaseManager(tmp_path / "epic33-links.db")
    database.initialize()
    with database.transaction() as connection:
        herb_id = int(connection.execute(
            """INSERT INTO materia_medica
               (source_key,code,name_vi,name_cn,reference_source)
               VALUES('epic33-herb','DL-E33','Vị thử Epic 33','三十三藥','Kiểm thử')"""
        ).lastrowid)
        connection.execute(
            """INSERT INTO materia_medica_translations(herb_id,name_vi,status,model)
               VALUES(?, 'Vị đã duyệt Epic 33', 'approved', 'doctor')""",
            (herb_id,),
        )
        formula_id = int(connection.execute(
            """INSERT INTO formulas(code,name,name_cn,ingredients_text)
               VALUES('CF-E33','方三十三','方三十三','三十三藥')"""
        ).lastrowid)
        connection.execute(
            """INSERT INTO formula_translations(formula_id,name,status,model)
               VALUES(?, 'Cổ phương Epic 33', 'approved', 'doctor')""",
            (formula_id,),
        )
        connection.execute(
            "INSERT INTO formula_herb_links(formula_id,herb_id) VALUES(?,?)",
            (formula_id, herb_id),
        )

    herbs = MateriaMedicaRepository(database)
    formulas = FormulaRepository(database)
    assert [row["id"] for row in herbs.search("Cổ phương Epic 33")] == [herb_id]
    assert [row["id"] for row in formulas.search("Vị đã duyệt Epic 33")] == [formula_id]
    assert herbs.detail(herb_id)["formulas"][0]["id"] == formula_id
    assert formulas.detail(formula_id)["linked_herbs"][0]["id"] == herb_id


def test_epic33_hides_draft_links(tmp_path: Path):
    database = DatabaseManager(tmp_path / "epic33-drafts.db")
    database.initialize()
    with database.transaction() as connection:
        herb_id = int(connection.execute(
            """INSERT INTO materia_medica(source_key,code,name_vi,name_cn)
               VALUES('epic33-draft-herb','DL-E33-D','Vị nháp','草稿藥')"""
        ).lastrowid)
        connection.execute(
            "INSERT INTO materia_medica_translations(herb_id,name_vi,status) VALUES(?,?,'draft')",
            (herb_id, "Vị nháp tiếng Việt"),
        )
        formula_id = int(connection.execute(
            """INSERT INTO formulas(code,name,name_cn,ingredients_text)
               VALUES('CF-E33-D','草稿方','草稿方','草稿藥')"""
        ).lastrowid)
        connection.execute(
            "INSERT INTO formula_translations(formula_id,name,status) VALUES(?,?,'draft')",
            (formula_id, "Cổ phương nháp"),
        )
        connection.execute(
            "INSERT INTO formula_herb_links(formula_id,herb_id) VALUES(?,?)",
            (formula_id, herb_id),
        )

    assert MateriaMedicaRepository(database).detail(herb_id)["formulas"] == []
    assert FormulaRepository(database).detail(formula_id)["linked_herbs"] == []
