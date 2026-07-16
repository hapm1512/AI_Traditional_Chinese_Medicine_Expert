from __future__ import annotations

import json
from datetime import date

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import ValidationError


class TreatmentOutcomeReportRepository:
    def __init__(self, database: DatabaseManager):
        self.database = database

    @staticmethod
    def _period(start_date: str, end_date: str) -> tuple[str, str]:
        try:
            start = date.fromisoformat(start_date.strip())
            end = date.fromisoformat(end_date.strip())
        except ValueError as error:
            raise ValidationError("Khoảng thời gian không hợp lệ") from error
        if start > end:
            raise ValidationError("Ngày bắt đầu phải trước ngày kết thúc")
        return start.isoformat(), end.isoformat()

    def summary(self, start_date: str, end_date: str) -> dict:
        start, end = self._period(start_date, end_date)
        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT f.*, c.visit_code, p.code AS patient_code, p.full_name
                FROM treatment_followups f
                JOIN consultations c ON c.id=f.consultation_id
                JOIN patients p ON p.id=c.patient_id
                WHERE f.followup_date BETWEEN ? AND ?
                ORDER BY f.followup_date DESC,f.id DESC
                """,
                (start, end),
            ).fetchall()
        items = [dict(row) for row in rows]
        status_counts = {
            key: sum(item["treatment_status"] == key for item in items)
            for key in ("improved", "stable", "worsened", "monitoring", "completed")
        }
        effectiveness_counts = {
            key: sum(item["effectiveness"] == key for item in items)
            for key in ("good", "partial", "none", "not_assessed")
        }
        changes = [
            int(item["symptom_score_before"]) - int(item["symptom_score_after"])
            for item in items
        ]
        return {
            "period_start": start,
            "period_end": end,
            "followup_count": len(items),
            "patient_count": len({item["patient_code"] for item in items}),
            "average_change": round(sum(changes) / len(changes), 2) if changes else 0.0,
            "adverse_reaction_count": sum(
                bool(item["adverse_reactions"].strip()) for item in items
            ),
            "status_counts": status_counts,
            "effectiveness_counts": effectiveness_counts,
            "items": items,
        }

    def create(
        self,
        start_date: str,
        end_date: str,
        *,
        doctor_conclusion: str,
        reviewed_by: str,
    ) -> int:
        reviewer = reviewed_by.strip()
        conclusion = doctor_conclusion.strip()
        if not reviewer:
            raise ValidationError("Bắt buộc bác sĩ xác nhận báo cáo")
        if not conclusion:
            raise ValidationError("Bắt buộc nhập kết luận bác sĩ")
        report = self.summary(start_date, end_date)
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO treatment_outcome_reports(
                    period_start,period_end,report_json,doctor_conclusion,reviewed_by
                ) VALUES(?,?,?,?,?)
                """,
                (
                    report["period_start"], report["period_end"],
                    json.dumps(report, ensure_ascii=False), conclusion, reviewer,
                ),
            )
            report_id = int(cursor.lastrowid)
            self.database.audit(
                connection, "create_outcome_report", "treatment_outcome_report",
                report_id, f"Bác sĩ {reviewer}; {start_date} đến {end_date}",
            )
            return report_id

    def get(self, report_id: int) -> dict | None:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM treatment_outcome_reports WHERE id=?", (report_id,)
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["report"] = json.loads(result.pop("report_json"))
        return result

    def list(self) -> list[dict]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT id,period_start,period_end,doctor_conclusion,reviewed_by,created_at
                FROM treatment_outcome_reports ORDER BY id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]
