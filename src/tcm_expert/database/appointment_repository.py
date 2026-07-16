from __future__ import annotations

from datetime import datetime

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import ValidationError


class FollowupAppointmentRepository:
    STATUSES = {"scheduled", "confirmed", "completed", "cancelled", "no_show"}
    ACTIVE_STATUSES = {"scheduled", "confirmed"}

    def __init__(self, database: DatabaseManager):
        self.database = database

    @staticmethod
    def _validate_datetime(value: str) -> str:
        try:
            return datetime.fromisoformat(value).replace(second=0, microsecond=0).isoformat(
                timespec="minutes"
            )
        except (TypeError, ValueError) as error:
            raise ValidationError("Ngày giờ hẹn không hợp lệ") from error

    def create(
        self,
        consultation_id: int,
        *,
        scheduled_at: str,
        reason: str = "",
        note: str = "",
        responsible_by: str,
    ) -> int:
        appointment_time = self._validate_datetime(scheduled_at)
        responsible = responsible_by.strip()
        if not responsible:
            raise ValidationError("Bắt buộc nhập người phụ trách lịch hẹn")
        with self.database.transaction() as connection:
            exists = connection.execute(
                "SELECT 1 FROM consultations WHERE id=?", (consultation_id,)
            ).fetchone()
            if exists is None:
                raise ValidationError("Hồ sơ khám không tồn tại")
            duplicate = connection.execute(
                """
                SELECT 1 FROM followup_appointments
                WHERE consultation_id=? AND scheduled_at=?
                  AND status IN ('scheduled','confirmed')
                """,
                (consultation_id, appointment_time),
            ).fetchone()
            if duplicate:
                raise ValidationError("Lịch tái khám này đã tồn tại")
            cursor = connection.execute(
                """
                INSERT INTO followup_appointments(
                    consultation_id,scheduled_at,reason,note,responsible_by
                ) VALUES(?,?,?,?,?)
                """,
                (
                    consultation_id,
                    appointment_time,
                    reason.strip(),
                    note.strip(),
                    responsible,
                ),
            )
            appointment_id = int(cursor.lastrowid)
            self.database.audit(
                connection,
                "create_followup_appointment",
                "followup_appointment",
                appointment_id,
                f"Hẹn {appointment_time}; phụ trách {responsible}",
            )
            return appointment_id

    def change_status(self, appointment_id: int, status: str, responsible_by: str) -> None:
        if status not in self.STATUSES:
            raise ValidationError("Trạng thái lịch hẹn không hợp lệ")
        responsible = responsible_by.strip()
        if not responsible:
            raise ValidationError("Bắt buộc nhập người cập nhật lịch hẹn")
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE followup_appointments
                SET status=?,responsible_by=?,updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (status, responsible, appointment_id),
            )
            if cursor.rowcount != 1:
                raise ValidationError("Lịch hẹn không tồn tại")
            self.database.audit(
                connection,
                "update_followup_appointment",
                "followup_appointment",
                appointment_id,
                f"Trạng thái {status}; người cập nhật {responsible}",
            )

    def list(self, *, status: str | None = None) -> list[dict]:
        if status is not None and status not in self.STATUSES:
            raise ValidationError("Trạng thái lịch hẹn không hợp lệ")
        where = "WHERE a.status=?" if status else ""
        parameters = (status,) if status else ()
        with self.database.transaction() as connection:
            rows = connection.execute(
                f"""
                SELECT a.*,c.visit_code,p.code AS patient_code,p.full_name
                FROM followup_appointments a
                JOIN consultations c ON c.id=a.consultation_id
                JOIN patients p ON p.id=c.patient_id
                {where}
                ORDER BY a.scheduled_at ASC,a.id ASC
                """,
                parameters,
            ).fetchall()
            return [dict(row) for row in rows]

    def list_for_consultation(self, consultation_id: int) -> list[dict]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT * FROM followup_appointments
                WHERE consultation_id=? ORDER BY scheduled_at DESC,id DESC
                """,
                (consultation_id,),
            ).fetchall()
            return [dict(row) for row in rows]
