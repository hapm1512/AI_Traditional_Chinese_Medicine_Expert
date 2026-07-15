from __future__ import annotations

import json
from typing import Any

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import ValidationError


class ClinicalDecisionRepository:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def create(self, consultation_id: int, report: dict[str, Any]) -> int:
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """INSERT INTO clinical_decision_reports
                   (consultation_id,completeness_score,risk_level,report_json)
                   VALUES(?,?,?,?)""",
                (
                    consultation_id,
                    report["completeness_score"],
                    report["risk_level"],
                    json.dumps(report, ensure_ascii=False),
                ),
            )
            report_id = int(cursor.lastrowid)
            self.database.audit(connection, "create", "clinical_decision_report", report_id)
            return report_id

    def list_for_consultation(self, consultation_id: int) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT * FROM clinical_decision_reports
                   WHERE consultation_id=? ORDER BY created_at DESC,id DESC""",
                (consultation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, report_id: int) -> dict[str, Any] | None:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM clinical_decision_reports WHERE id=?", (report_id,)
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["report"] = json.loads(result["report_json"])
        return result

    def review(self, report_id: int, reviewer: str) -> None:
        reviewer = reviewer.strip()
        if not reviewer:
            raise ValidationError("Cần nhập tên bác sĩ phê duyệt.")
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """UPDATE clinical_decision_reports
                   SET status='reviewed',reviewed_by=?,reviewed_at=CURRENT_TIMESTAMP
                   WHERE id=? AND status='draft'""",
                (reviewer, report_id),
            )
            if cursor.rowcount != 1:
                raise ValidationError("Báo cáo không tồn tại hoặc đã duyệt.")
            self.database.audit(connection, "review", "clinical_decision_report", report_id, reviewer)
