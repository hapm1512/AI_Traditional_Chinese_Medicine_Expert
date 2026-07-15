from tcm_expert.database.manager import DatabaseManager


def test_database_initialization_is_idempotent(tmp_path):
    database = DatabaseManager(tmp_path / "test.db")
    database.initialize()
    database.initialize()
    assert database.health_check()
    with database.transaction() as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"patients", "consultations", "materia_medica", "formula_references", "audit_log"} <= tables

