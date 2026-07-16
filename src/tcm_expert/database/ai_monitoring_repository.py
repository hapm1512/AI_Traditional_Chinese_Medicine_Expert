from __future__ import annotations

from typing import Any

from tcm_expert.database.manager import DatabaseManager


class AIMonitoringRepository:
    def __init__(self, database: DatabaseManager):
        self.database = database
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.database.transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS ai_operation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consultation_id INTEGER,
                    provider TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL CHECK(status IN ('ok','fallback','blocked','error')),
                    latency_ms INTEGER NOT NULL DEFAULT 0 CHECK(latency_ms >= 0),
                    detail TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(consultation_id) REFERENCES consultations(id) ON DELETE SET NULL
                );
                CREATE INDEX IF NOT EXISTS idx_ai_operation_created
                    ON ai_operation_log(created_at DESC,id DESC);
                """
            )

    def record(self, consultation_id: int | None, provider: str, status: str,
               latency_ms: int, detail: str = "") -> int:
        safe_status = status if status in {"ok", "fallback", "blocked", "error"} else "error"
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """INSERT INTO ai_operation_log
                   (consultation_id,provider,status,latency_ms,detail) VALUES(?,?,?,?,?)""",
                (consultation_id, provider[:100], safe_status, max(0, latency_ms), detail[:1000]),
            )
            log_id = int(cursor.lastrowid)
            self.database.audit(connection, "ai_operation", "ai_operation_log", log_id, safe_status)
            return log_id

    def latest(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM ai_operation_log ORDER BY id DESC LIMIT ?",
                (max(1, min(200, int(limit))),),
            ).fetchall()
        return [dict(row) for row in rows]

