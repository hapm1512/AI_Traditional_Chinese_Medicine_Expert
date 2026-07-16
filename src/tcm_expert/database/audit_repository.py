import csv
from pathlib import Path

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.security import require_role


class AuditRepository:
    def __init__(self, database: DatabaseManager):
        self.database = database

    @staticmethod
    def _admin() -> None:
        require_role("admin")

    def actors(self) -> list[str]:
        self._admin()
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT DISTINCT actor_username FROM audit_log
                   WHERE actor_username <> '' ORDER BY actor_username"""
            )
            return [str(row[0]) for row in rows]

    def list_entries(
        self,
        actor: str = "",
        action: str = "",
        date_from: str = "",
        date_to: str = "",
        limit: int = 1000,
    ) -> list:
        self._admin()
        clauses, parameters = [], []
        if actor:
            clauses.append("actor_username = ?")
            parameters.append(actor)
        if action:
            clauses.append("action = ?")
            parameters.append(action)
        if date_from:
            clauses.append("date(created_at) >= date(?)")
            parameters.append(date_from)
        if date_to:
            clauses.append("date(created_at) <= date(?)")
            parameters.append(date_to)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(max(1, min(int(limit), 10_000)))
        with self.database.transaction() as connection:
            return list(connection.execute(
                f"""SELECT id,created_at,actor_username,action,entity_type,
                            entity_id,detail
                     FROM audit_log {where}
                     ORDER BY created_at DESC,id DESC LIMIT ?""",
                parameters,
            ))

    def export_csv(self, destination: Path, **filters) -> int:
        rows = self.list_entries(limit=10_000, **filters)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(("Thời gian", "Người dùng", "Thao tác", "Đối tượng", "Mã", "Chi tiết"))
            for row in rows:
                writer.writerow((row["created_at"], row["actor_username"], row["action"],
                                 row["entity_type"], row["entity_id"] or "", row["detail"]))
        return len(rows)
