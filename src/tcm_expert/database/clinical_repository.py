from __future__ import annotations

import json
from typing import Any

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import ValidationError


class ClinicalDecisionRepository:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def create(
        self,
        consultation_id: int,
        report: dict[str, Any],
        *,
        report_type: str = "rule",
        ai_confidence: float = 0.0,
    ) -> int:
        if report_type not in {"rule", "ai"}:
            raise ValidationError("Loại báo cáo không hợp lệ.")
        ai_confidence = min(1.0, max(0.0, float(ai_confidence)))
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """INSERT INTO clinical_decision_reports
                   (consultation_id,completeness_score,risk_level,report_json,
                    report_type,ai_confidence)
                   VALUES(?,?,?,?,?,?)""",
                (
                    consultation_id,
                    report["completeness_score"],
                    report["risk_level"],
                    json.dumps(report, ensure_ascii=False),
                    report_type,
                    ai_confidence,
                ),
            )
            report_id = int(cursor.lastrowid)
            self.database.audit(connection, "create", "clinical_decision_report", report_id)
            return report_id

    def create_ai(self, consultation_id: int, report: dict[str, Any]) -> int:
        proposal = report.get("ai_proposal", {})
        return self.create(
            consultation_id,
            report,
            report_type="ai",
            ai_confidence=float(proposal.get("confidence", 0.0)),
        )

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
        self.decide(report_id, reviewer, "accepted")

    def decide(
        self,
        report_id: int,
        reviewer: str,
        decision: str,
        reason: str = "",
    ) -> None:
        reviewer = reviewer.strip()
        if not reviewer:
            raise ValidationError("Cần nhập tên bác sĩ phê duyệt.")
        if decision not in {"accepted", "rejected", "edited"}:
            raise ValidationError("Quyết định của bác sĩ không hợp lệ.")
        reason = reason.strip()[:1000]
        if decision == "rejected" and not reason:
            raise ValidationError("Cần nhập lý do từ chối đề xuất AI.")
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """UPDATE clinical_decision_reports
                   SET status='reviewed',reviewed_by=?,reviewed_at=CURRENT_TIMESTAMP,
                       doctor_decision=?,decision_reason=?
                   WHERE id=? AND status='draft'""",
                (reviewer, decision, reason, report_id),
            )
            if cursor.rowcount != 1:
                raise ValidationError("Báo cáo không tồn tại hoặc đã duyệt.")
            self.database.audit(
                connection, "doctor_decision", "clinical_decision_report", report_id,
                f"{reviewer}: {decision}; {reason}"
            )
