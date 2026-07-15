from contextlib import contextmanager
from pathlib import Path
import sqlite3
from collections.abc import Iterator

from tcm_expert.database.schema import MIGRATIONS


class DatabaseManager:
    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
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

    def health_check(self) -> bool:
        with self.transaction() as connection:
            return connection.execute("SELECT 1").fetchone()[0] == 1

