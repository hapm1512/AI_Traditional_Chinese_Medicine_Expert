import sqlite3
from datetime import datetime
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tcm_expert.database.schema import MIGRATIONS
from tcm_expert.database.seed import seed_reference_data


class DatabaseManager:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
            )
            current = connection.execute(
                "SELECT COALESCE(MAX(version), 0) FROM schema_version"
            ).fetchone()[0]
            for version, script in MIGRATIONS:
                if version > current:
                    connection.executescript(script)
                    connection.execute("INSERT INTO schema_version(version) VALUES (?)", (version,))
            seed_reference_data(connection)

    @staticmethod
    def audit(
        connection: sqlite3.Connection,
        action: str,
        entity_type: str,
        entity_id: int | None,
        detail: str = "",
    ) -> None:
        connection.execute(
            "INSERT INTO audit_log(action,entity_type,entity_id,detail) VALUES(?,?,?,?)",
            (action, entity_type, entity_id, detail),
        )

    def reference_counts(self) -> dict[str, int]:
        tables = ("symptoms", "tcm_syndromes", "diseases", "materia_medica", "formulas")
        with self.transaction() as connection:
            return {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in tables
            }

    def health_check(self) -> bool:
        with self.transaction() as connection:
            query_ok = connection.execute("SELECT 1").fetchone()[0] == 1
            return query_ok and self.integrity_check() == "ok"

    def integrity_check(self) -> str:
        with self.transaction() as connection:
            return str(connection.execute("PRAGMA integrity_check").fetchone()[0])

    def create_backup(self, destination: Path | None = None) -> Path:
        if not self.path.exists():
            raise FileNotFoundError("Chưa có cơ sở dữ liệu để sao lưu")
        if destination is None:
            backup_dir = self.path.parent / "backups"
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination = backup_dir / f"tcm_expert_{stamp}.db"
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = self.connect()
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return destination
