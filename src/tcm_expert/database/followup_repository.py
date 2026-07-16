from __future__ import annotations

from datetime import date

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import ValidationError


class TreatmentFollowupRepository:
    STATUSES = {"improved", "stable", "worsened", "monitoring", "completed"}
    EFFECTIVENESS = {"good", "partial", "none", "not_assessed"}

    def __init__(self, database: DatabaseManager):
        self.database = database

    def create(
        self,
        consultation_id: int,
        *,
        followup_date: str | None = None,
        treatment_status: str = "monitoring",
        symptom_score_before: int = 0,
        symptom_score_after: int = 0,
        effectiveness: str = "not_assessed",
        adverse_reactions: str = "",
        adherence: str = "",
        doctor_note: str = "",
        reviewed_by: str,
    ) -> int:
        reviewer = reviewed_by.strip()
        if not reviewer:
            raise ValidationError("Bắt buộc bác sĩ ghi nhận theo dõi")
        if treatment_status not in self.STATUSES:
            raise ValidationError("Trạng thái điều trị không hợp lệ")
        if effectiveness not in self.EFFECTIVENESS:
            raise ValidationError("Đánh giá hiệu quả không hợp lệ")
        if not 0 <= symptom_score_before <= 10 or not 0 <= symptom_score_after <= 10:
            raise ValidationError("Điểm triệu chứng phải từ 0 đến 10")
        recorded_date = (followup_date or date.today().isoformat()).strip()
        try:
            date.fromisoformat(recorded_date)
        except ValueError as error:
            raise ValidationError("Ngày theo dõi không hợp lệ") from error
        with self.database.transaction() as connection:
            exists = connection.execute(
                "SELECT 1 FROM consultations WHERE id=?", (consultation_id,)
            ).fetchone()
            if exists is None:
                raise ValidationError("Hồ sơ khám không tồn tại")
            cursor = connection.execute(
                """
                INSERT INTO treatment_followups(
                    consultation_id,followup_date,treatment_status,
                    symptom_score_before,symptom_score_after,effectiveness,
                    adverse_reactions,adherence,doctor_note,reviewed_by
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    consultation_id,
                    recorded_date,
                    treatment_status,
                    symptom_score_before,
                    symptom_score_after,
                    effectiveness,
                    adverse_reactions.strip(),
                    adherence.strip(),
                    doctor_note.strip(),
                    reviewer,
                ),
            )
            followup_id = int(cursor.lastrowid)
            connection.execute(
                "UPDATE consultations SET patient_status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (
                    "completed" if treatment_status == "completed" else "monitoring",
                    consultation_id,
                ),
            )
            self.database.audit(
                connection,
                "create_followup",
                "treatment_followup",
                followup_id,
                f"Bác sĩ {reviewer}; trạng thái {treatment_status}",
            )
            return followup_id

    def list_for_consultation(self, consultation_id: int) -> list[dict]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT * FROM treatment_followups
                WHERE consultation_id=?
                ORDER BY followup_date DESC,id DESC
                """,
                (consultation_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get(self, followup_id: int) -> dict | None:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM treatment_followups WHERE id=?", (followup_id,)
            ).fetchone()
            return dict(row) if row else None

    def outcome_summary(self, consultation_id: int) -> dict[str, int | str]:
        rows = self.list_for_consultation(consultation_id)
        if not rows:
            return {"count": 0, "trend": "not_assessed", "change": 0}
        latest = rows[0]
        change = int(latest["symptom_score_before"]) - int(latest["symptom_score_after"])
        trend = "improved" if change > 0 else "worsened" if change < 0 else "stable"
        return {"count": len(rows), "trend": trend, "change": change}
