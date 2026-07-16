from __future__ import annotations

from datetime import datetime, timedelta

from tcm_expert.database.manager import DatabaseManager


class DashboardRepository:
    """Read-only operational summary for the clinic dashboard."""

    def __init__(self, database: DatabaseManager):
        self.database = database

    def summary(self, *, now: str | None = None) -> dict[str, int]:
        current = datetime.fromisoformat(now) if now else datetime.now()
        current = current.replace(second=0, microsecond=0)
        day_start = current.replace(hour=0, minute=0).isoformat(timespec="minutes")
        day_end = (current.replace(hour=23, minute=59)).isoformat(timespec="minutes")
        seven_days = (current + timedelta(days=7)).isoformat(timespec="minutes")
        with self.database.transaction() as connection:
            row = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM patients WHERE deleted_at IS NULL) AS patients,
                    (SELECT COUNT(*) FROM consultations
                     WHERE patient_status='under_treatment') AS under_treatment,
                    (SELECT COUNT(*) FROM consultations
                     WHERE patient_status='monitoring') AS monitoring,
                    (SELECT COUNT(*) FROM followup_appointments
                     WHERE scheduled_at BETWEEN ? AND ?
                       AND status IN ('scheduled','confirmed')
                       AND case_state IN ('active','reopened')) AS today,
                    (SELECT COUNT(*) FROM followup_appointments
                     WHERE scheduled_at<?
                       AND status IN ('scheduled','confirmed')
                       AND case_state IN ('active','reopened')) AS overdue,
                    (SELECT COUNT(*) FROM followup_appointments a
                     WHERE a.scheduled_at BETWEEN ? AND ?
                       AND a.status IN ('scheduled','confirmed')
                       AND a.case_state IN ('active','reopened')
                       AND NOT EXISTS (
                           SELECT 1 FROM appointment_reminders r
                           WHERE r.appointment_id=a.id
                       )) AS pending_reminder
                """,
                (day_start, day_end, current.isoformat(timespec="minutes"), current.isoformat(timespec="minutes"), seven_days),
            ).fetchone()
        return dict(row)

    def attention_items(self, *, now: str | None = None, limit: int = 20) -> list[dict]:
        current = datetime.fromisoformat(now) if now else datetime.now()
        current = current.replace(second=0, microsecond=0)
        day_end = current.replace(hour=23, minute=59).isoformat(timespec="minutes")
        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT a.id AS appointment_id,a.scheduled_at,a.status,a.reason,
                       c.id AS consultation_id,c.visit_code,
                       p.id AS patient_id,p.code AS patient_code,p.full_name,
                       CASE WHEN a.scheduled_at<? THEN 'overdue' ELSE 'today' END AS priority
                FROM followup_appointments a
                JOIN consultations c ON c.id=a.consultation_id
                JOIN patients p ON p.id=c.patient_id
                WHERE a.scheduled_at<=?
                  AND a.status IN ('scheduled','confirmed')
                  AND a.case_state IN ('active','reopened')
                ORDER BY CASE WHEN a.scheduled_at<? THEN 0 ELSE 1 END,
                         a.scheduled_at ASC,a.id ASC
                LIMIT ?
                """,
                (current.isoformat(timespec="minutes"), day_end, current.isoformat(timespec="minutes"), min(max(limit, 1), 100)),
            ).fetchall()
        return [dict(row) for row in rows]
