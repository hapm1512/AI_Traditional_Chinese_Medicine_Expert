from __future__ import annotations

from datetime import datetime, timedelta

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import ValidationError


class FollowupAppointmentRepository:
    STATUSES = {"scheduled", "confirmed", "completed", "cancelled", "no_show"}
    ACTIVE_STATUSES = {"scheduled", "confirmed"}
    VIEWS = {
        "today",
        "upcoming",
        "overdue_confirmation",
        "pending_reminder",
        "reminded",
        "history_reference",
        "cancelled_90",
    }
    CASE_ACTIONS = {"history_reference", "reopened", "medical_record"}

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

    def dismiss_overdue_notification(
        self,
        appointment_id: int,
        *,
        doctor_name: str,
        now: str | None = None,
    ) -> None:
        """Close an overdue notification while preserving its audit history."""
        doctor = doctor_name.strip()
        if not doctor:
            raise ValidationError("Bắt buộc có bác sĩ thực hiện")
        current = datetime.fromisoformat(now) if now else datetime.now()
        current = current.replace(second=0, microsecond=0)
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT scheduled_at,status FROM followup_appointments WHERE id=?",
                (appointment_id,),
            ).fetchone()
            if row is None:
                raise ValidationError("Lịch hẹn không tồn tại")
            if row["status"] not in self.ACTIVE_STATUSES:
                raise ValidationError("Thông báo này không còn hoạt động")
            scheduled = datetime.fromisoformat(row["scheduled_at"])
            if current - scheduled < timedelta(hours=3):
                raise ValidationError("Chỉ được xóa thông báo trễ quá 3 giờ")
            connection.execute(
                """
                UPDATE followup_appointments
                SET status='cancelled',overdue_note=?,reviewed_by=?,reviewed_at=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    "Bác sĩ đã xóa thông báo trễ quá 3 giờ",
                    doctor,
                    current.isoformat(timespec="minutes"),
                    appointment_id,
                ),
            )
            self.database.audit(
                connection,
                "dismiss_overdue_appointment_notification",
                "followup_appointment",
                appointment_id,
                f"Bác sĩ {doctor}; trễ quá 3 giờ; giữ lịch sử",
            )

    def mark_reminded(
        self,
        appointment_id: int,
        *,
        reminded_by: str,
        note: str = "",
        reminded_at: str | None = None,
    ) -> int:
        responsible = reminded_by.strip()
        if not responsible:
            raise ValidationError("Bắt buộc nhập người thực hiện nhắc lịch")
        reminder_time = self._validate_datetime(reminded_at or datetime.now().isoformat())
        with self.database.transaction() as connection:
            appointment = connection.execute(
                "SELECT status FROM followup_appointments WHERE id=?", (appointment_id,)
            ).fetchone()
            if appointment is None:
                raise ValidationError("Lịch hẹn không tồn tại")
            if appointment["status"] not in self.ACTIVE_STATUSES:
                raise ValidationError("Chỉ nhắc lịch đang hoạt động")
            cursor = connection.execute(
                """
                INSERT INTO appointment_reminders(
                    appointment_id,reminded_at,reminded_by,note
                ) VALUES(?,?,?,?)
                """,
                (appointment_id, reminder_time, responsible, note.strip()),
            )
            reminder_id = int(cursor.lastrowid)
            self.database.audit(
                connection,
                "remind_followup_appointment",
                "followup_appointment",
                appointment_id,
                f"Đã nhắc {reminder_time}; người nhắc {responsible}",
            )
            return reminder_id

    def claim_due_alerts(self, *, shown_at: str | None = None) -> list[dict]:
        alert_time = self._validate_datetime(shown_at or datetime.now().isoformat())
        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT a.id,a.scheduled_at,a.reason,c.visit_code,
                    p.code AS patient_code,p.full_name
                FROM followup_appointments a
                JOIN consultations c ON c.id=a.consultation_id
                JOIN patients p ON p.id=c.patient_id
                LEFT JOIN appointment_alerts n ON n.appointment_id=a.id
                WHERE a.status IN ('scheduled','confirmed')
                  AND a.case_state IN ('active','reopened')
                  AND a.scheduled_at<=? AND n.id IS NULL
                ORDER BY a.scheduled_at ASC,a.id ASC
                LIMIT 20
                """,
                (alert_time,),
            ).fetchall()
            result = [dict(row) for row in rows]
            for row in result:
                connection.execute(
                    "INSERT INTO appointment_alerts(appointment_id,shown_at) VALUES(?,?)",
                    (row["id"], alert_time),
                )
                self.database.audit(
                    connection,
                    "show_followup_appointment_alert",
                    "followup_appointment",
                    int(row["id"]),
                    f"Đã hiển thị cảnh báo lúc {alert_time}",
                )
            return result

    def pending_due_alerts(self, *, now: str | None = None) -> list[dict]:
        alert_time = self._validate_datetime(now or datetime.now().isoformat())
        with self.database.transaction() as connection:
            due_rows = connection.execute(
                """
                SELECT a.id
                FROM followup_appointments a
                WHERE a.status IN ('scheduled','confirmed')
                  AND a.case_state IN ('active','reopened')
                  AND a.scheduled_at<=?
                ORDER BY a.scheduled_at ASC,a.id ASC
                LIMIT 20
                """,
                (alert_time,),
            ).fetchall()
            for row in due_rows:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO appointment_alerts(appointment_id,shown_at)
                    VALUES(?,?)
                    """,
                    (row["id"], alert_time),
                )
            rows = connection.execute(
                """
                SELECT n.id AS alert_id,a.id,a.scheduled_at,a.reason,c.visit_code,
                    p.code AS patient_code,p.full_name
                FROM appointment_alerts n
                JOIN followup_appointments a ON a.id=n.appointment_id
                JOIN consultations c ON c.id=a.consultation_id
                JOIN patients p ON p.id=c.patient_id
                WHERE n.acknowledged_at IS NULL
                  AND a.status IN ('scheduled','confirmed')
                  AND a.case_state IN ('active','reopened')
                ORDER BY a.scheduled_at ASC,a.id ASC
                LIMIT 20
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def acknowledge_alerts(
        self,
        alert_ids: list[int],
        *,
        acknowledged_by: str,
        acknowledged_at: str | None = None,
    ) -> None:
        if not alert_ids:
            return
        reviewer = acknowledged_by.strip()
        if not reviewer:
            raise ValidationError("Bắt buộc có người xác nhận đã xem cảnh báo")
        seen_at = self._validate_datetime(acknowledged_at or datetime.now().isoformat())
        with self.database.transaction() as connection:
            for alert_id in alert_ids:
                row = connection.execute(
                    "SELECT appointment_id FROM appointment_alerts WHERE id=?",
                    (alert_id,),
                ).fetchone()
                if row is None:
                    continue
                connection.execute(
                    """
                    UPDATE appointment_alerts
                    SET acknowledged_at=?,acknowledged_by=?
                    WHERE id=? AND acknowledged_at IS NULL
                    """,
                    (seen_at, reviewer, alert_id),
                )
                self.database.audit(
                    connection,
                    "acknowledge_followup_appointment_alert",
                    "followup_appointment",
                    int(row["appointment_id"]),
                    f"Đã xem cảnh báo lúc {seen_at}; người xem {reviewer}",
                )

    def review_overdue(
        self,
        appointment_id: int,
        *,
        action: str,
        note: str,
        reviewed_by: str,
        reviewed_at: str | None = None,
    ) -> None:
        if action not in self.CASE_ACTIONS:
            raise ValidationError("Cách xử lý hồ sơ không hợp lệ")
        doctor_note = note.strip()
        reviewer = reviewed_by.strip()
        if not doctor_note:
            raise ValidationError("Bắt buộc ghi chú lý do xử lý")
        if not reviewer:
            raise ValidationError("Bắt buộc có bác sĩ xử lý")
        review_time = self._validate_datetime(reviewed_at or datetime.now().isoformat())
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT scheduled_at,status,case_state FROM followup_appointments WHERE id=?",
                (appointment_id,),
            ).fetchone()
            if row is None:
                raise ValidationError("Lịch hẹn không tồn tại")
            age = datetime.fromisoformat(review_time) - datetime.fromisoformat(row["scheduled_at"])
            if action == "history_reference" and age < timedelta(days=30):
                raise ValidationError("Chỉ lưu theo dõi khi lịch đã quá 30 ngày")
            if action == "reopened":
                if age >= timedelta(days=90) or row["case_state"] == "cancelled_90":
                    raise ValidationError(
                        "Hồ sơ quá 90 ngày; phải tạo hồ sơ khám mới"
                    )
                status = "confirmed"
            elif action == "medical_record":
                status = "completed"
            else:
                status = row["status"]
            connection.execute(
                """
                UPDATE followup_appointments
                SET status=?,case_state=?,overdue_note=?,reviewed_by=?,reviewed_at=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (status, action, doctor_note, reviewer, review_time, appointment_id),
            )
            self.database.audit(
                connection,
                "review_overdue_appointment",
                "followup_appointment",
                appointment_id,
                f"Xử lý {action}; bác sĩ {reviewer}; {doctor_note}",
            )

    def expire_after_90_days(self, *, now: str | None = None) -> int:
        current = datetime.fromisoformat(now) if now else datetime.now()
        cutoff = (current - timedelta(days=90)).replace(second=0, microsecond=0).isoformat(
            timespec="minutes"
        )
        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT id FROM followup_appointments
                WHERE scheduled_at<=?
                  AND case_state IN ('active','history_reference')
                  AND status IN ('scheduled','confirmed','no_show')
                """,
                (cutoff,),
            ).fetchall()
            for row in rows:
                appointment_id = int(row["id"])
                connection.execute(
                    """
                    UPDATE followup_appointments
                    SET status='cancelled',case_state='cancelled_90',
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (appointment_id,),
                )
                self.database.audit(
                    connection,
                    "cancel_appointment_after_90_days",
                    "followup_appointment",
                    appointment_id,
                    (
                        "Bệnh nhân không tái khám sau 90 ngày; "
                        "hồ sơ được đóng, không xóa dữ liệu"
                    ),
                )
            return len(rows)

    def due_summary(self, *, now: str | None = None) -> dict[str, int]:
        current = datetime.fromisoformat(now) if now else datetime.now()
        rows = self.list()
        summary = {"due": 0, "history_30": 0, "cancelled_90": 0}
        for row in rows:
            age = current - datetime.fromisoformat(row["scheduled_at"])
            if row["case_state"] == "cancelled_90":
                summary["cancelled_90"] += 1
            elif (
                row["status"] in self.ACTIVE_STATUSES
                and row["case_state"] in {"active", "reopened"}
                and age >= timedelta(days=30)
            ):
                summary["history_30"] += 1
            elif (
                row["status"] in self.ACTIVE_STATUSES
                and row["case_state"] in {"active", "reopened"}
                and age >= timedelta(0)
            ):
                summary["due"] += 1
        return summary

    def list(
        self,
        *,
        status: str | None = None,
        view: str | None = None,
        now: str | None = None,
    ) -> list[dict]:
        if status is not None and status not in self.STATUSES:
            raise ValidationError("Trạng thái lịch hẹn không hợp lệ")
        if view is not None and view not in self.VIEWS:
            raise ValidationError("Bộ lọc nhắc lịch không hợp lệ")
        where = "WHERE a.status=?" if status else ""
        parameters = (status,) if status else ()
        with self.database.transaction() as connection:
            rows = connection.execute(
                f"""
                SELECT a.*,c.visit_code,p.code AS patient_code,p.full_name,
                    (SELECT ar.reminded_at FROM appointment_reminders ar
                     WHERE ar.appointment_id=a.id
                     ORDER BY ar.reminded_at DESC,ar.id DESC LIMIT 1) AS reminded_at,
                    (SELECT ar.reminded_by FROM appointment_reminders ar
                     WHERE ar.appointment_id=a.id
                     ORDER BY ar.reminded_at DESC,ar.id DESC LIMIT 1) AS reminded_by,
                    (SELECT COUNT(*) FROM appointment_reminders ar
                     WHERE ar.appointment_id=a.id) AS reminder_count
                FROM followup_appointments a
                JOIN consultations c ON c.id=a.consultation_id
                JOIN patients p ON p.id=c.patient_id
                {where}
                ORDER BY a.scheduled_at ASC,a.id ASC
                """,
                parameters,
            ).fetchall()
            result = [dict(row) for row in rows]
        if view is None:
            return result
        current = datetime.fromisoformat(now) if now else datetime.now()
        current = current.replace(second=0, microsecond=0)
        upcoming_end = current + timedelta(days=7)

        def matches(row: dict) -> bool:
            scheduled = datetime.fromisoformat(row["scheduled_at"])
            active = row["status"] in self.ACTIVE_STATUSES
            reminded = bool(row["reminder_count"])
            if view == "today":
                return scheduled.date() == current.date()
            if view == "upcoming":
                return active and current <= scheduled <= upcoming_end
            if view == "overdue_confirmation":
                return row["status"] == "scheduled" and scheduled < current
            if view == "pending_reminder":
                return active and scheduled <= upcoming_end and not reminded
            if view == "reminded":
                return reminded
            return row["case_state"] == view

        return [row for row in result if matches(row)]

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
