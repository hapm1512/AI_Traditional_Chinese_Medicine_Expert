from collections.abc import Mapping
from typing import Any

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import optional_text


class SyndromeRepository:
    """Persists differential-diagnosis results for one consultation."""

    def __init__(self, database: DatabaseManager):
        self.database = database

    def catalogue(self) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute("SELECT * FROM tcm_syndromes ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def selected(self, consultation_id: int) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT cs.*, s.code, s.name, s.eight_principles, s.pathogenesis,
                          s.treatment_principle, s.description
                   FROM consultation_syndromes cs
                   JOIN tcm_syndromes s ON s.id=cs.syndrome_id
                   WHERE cs.consultation_id=?
                   ORDER BY cs.is_primary DESC, cs.confidence DESC, s.name""",
                (consultation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save(self, consultation_id: int, syndrome_id: int, values: Mapping[str, Any]) -> None:
        confidence = float(values.get("confidence") or 0)
        if not 0 <= confidence <= 1:
            raise ValueError("Độ phù hợp phải từ 0 đến 100%")
        is_primary = int(bool(values.get("is_primary")))
        confirmed = int(bool(values.get("doctor_confirmed")))
        if confirmed:
            from tcm_expert.security import current_user, require_role

            if current_user() is not None:
                require_role("doctor")
        evidence = optional_text(values.get("evidence"), 5000)
        with self.database.transaction() as connection:
            if is_primary:
                connection.execute(
                    "UPDATE consultation_syndromes SET is_primary=0 WHERE consultation_id=?",
                    (consultation_id,),
                )
            connection.execute(
                """INSERT INTO consultation_syndromes
                   (consultation_id,syndrome_id,confidence,evidence,is_primary,doctor_confirmed)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(consultation_id,syndrome_id) DO UPDATE SET
                   confidence=excluded.confidence,evidence=excluded.evidence,
                   is_primary=excluded.is_primary,doctor_confirmed=excluded.doctor_confirmed""",
                (consultation_id, syndrome_id, confidence, evidence, is_primary, confirmed),
            )
            self.database.audit(connection, "save", "consultation_syndrome", syndrome_id)

    def delete(self, consultation_id: int, syndrome_id: int) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM consultation_syndromes WHERE consultation_id=? AND syndrome_id=?",
                (consultation_id, syndrome_id),
            )
            self.database.audit(connection, "delete", "consultation_syndrome", syndrome_id)

    def clinical_text(self, consultation_id: int) -> str:
        with self.database.transaction() as connection:
            consultation = connection.execute(
                """SELECT chief_complaint,symptoms,observation,listening_smelling,
                          inquiry,palpation,assessment
                   FROM consultations WHERE id=?""",
                (consultation_id,),
            ).fetchone()
            diagnostics = connection.execute(
                "SELECT category,finding,note FROM diagnostic_entries WHERE consultation_id=?",
                (consultation_id,),
            ).fetchall()
            inquiry = connection.execute(
                "SELECT * FROM inquiry_findings WHERE consultation_id=?",
                (consultation_id,),
            ).fetchone()
            pulses = connection.execute(
                "SELECT depth,rate,strength,rhythm,quality,note "
                "FROM pulse_findings WHERE consultation_id=?",
                (consultation_id,),
            ).fetchall()
            touches = connection.execute(
                "SELECT body_area,characteristic,note "
                "FROM palpation_findings WHERE consultation_id=?",
                (consultation_id,),
            ).fetchall()
            tongue = connection.execute(
                """SELECT tongue_color,coating_color,coating_thickness,teeth_marks,cracks,
                          doctor_tongue_color,doctor_coating_color,
                          doctor_coating_thickness,doctor_teeth_marks,doctor_cracks,doctor_note
                   FROM tongue_analyses WHERE consultation_id=?
                   ORDER BY reviewed_at IS NOT NULL DESC,id DESC LIMIT 1""",
                (consultation_id,),
            ).fetchone()
            audio = connection.execute(
                """SELECT sample_type,manual_characteristic,pattern_label,
                          doctor_pattern_label,doctor_note
                   FROM audio_analyses WHERE consultation_id=?
                   ORDER BY reviewed_at IS NOT NULL DESC,id DESC LIMIT 5""",
                (consultation_id,),
            ).fetchall()
        parts: list[str] = []
        for row in (consultation, inquiry, tongue):
            if row:
                parts.extend(str(value) for value in row if value)
        for rows in (diagnostics, pulses, touches, audio):
            for row in rows:
                parts.extend(str(value) for value in row if value)
        return " | ".join(parts)
