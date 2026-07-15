from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import optional_text


class PrescriptionRepository:
    """Doctor-controlled prescriptions created from approved references."""

    def __init__(self, database: DatabaseManager):
        self.database = database

    def list_for_consultation(self, consultation_id: int) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT p.*, f.name AS formula_name
                   FROM prescriptions p
                   JOIN formula_recommendations fr ON fr.id=p.recommendation_id
                   JOIN formulas f ON f.id=fr.formula_id
                   WHERE p.consultation_id=? ORDER BY p.id DESC""",
                (consultation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def approved_recommendations(self, consultation_id: int) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT fr.*, f.name AS formula_name, f.treatment_principle
                   FROM formula_recommendations fr
                   JOIN formulas f ON f.id=fr.formula_id
                   WHERE fr.consultation_id=? AND fr.doctor_approved=1
                   ORDER BY fr.id DESC""",
                (consultation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create(self, recommendation_id: int, values: Mapping[str, Any]) -> int:
        diagnosis = optional_text(values.get("diagnosis"), 2000)
        directions = optional_text(values.get("directions"), 2000)
        safety_notes = optional_text(values.get("safety_notes"), 2000)
        doctor_name = optional_text(values.get("doctor_name"), 200)
        if not all((diagnosis, directions, safety_notes, doctor_name)):
            raise ValueError("Cần chẩn đoán, cách dùng, an toàn và tên bác sĩ.")
        with self.database.transaction() as connection:
            recommendation = connection.execute(
                """SELECT fr.*, f.treatment_principle
                   FROM formula_recommendations fr
                   JOIN formulas f ON f.id=fr.formula_id WHERE fr.id=?""",
                (recommendation_id,),
            ).fetchone()
            if recommendation is None or not recommendation["doctor_approved"]:
                raise ValueError(
                    "Chỉ tạo đơn từ bài thuốc đã được bác sĩ phê duyệt."
                )
            consultation_id = int(recommendation["consultation_id"])
            code = f"DT-{datetime.now():%Y%m%d%H%M%S%f}-{recommendation_id:04d}"
            cursor = connection.execute(
                """INSERT INTO prescriptions
                   (consultation_id,recommendation_id,prescription_code,diagnosis,
                    treatment_principle,directions,modifications,safety_notes,doctor_name)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    consultation_id,
                    recommendation_id,
                    code,
                    diagnosis,
                    optional_text(values.get("treatment_principle"), 1000)
                    or recommendation["treatment_principle"],
                    directions,
                    optional_text(values.get("modifications"), 2000),
                    safety_notes,
                    doctor_name,
                ),
            )
            prescription_id = int(cursor.lastrowid)
            connection.execute(
                """INSERT INTO prescription_items
                   (prescription_id,herb_id,role,dosage,unit,preparation,note)
                   SELECT ?,fi.herb_id,fi.role,fi.dosage,fi.unit,fi.preparation,fi.note
                   FROM formula_ingredients fi WHERE fi.formula_id=?""",
                (prescription_id, recommendation["formula_id"]),
            )
            self.database.audit(connection, "create", "prescription", prescription_id)
        return prescription_id

    def approve(self, prescription_id: int) -> None:
        with self.database.transaction() as connection:
            current = connection.execute(
                "SELECT status FROM prescriptions WHERE id=?", (prescription_id,)
            ).fetchone()
            if current is None:
                raise ValueError("Không tìm thấy đơn thuốc.")
            if current["status"] != "draft":
                raise ValueError("Chỉ đơn nháp mới được phê duyệt.")
            connection.execute(
                """UPDATE prescriptions SET status='approved',
                   approved_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (prescription_id,),
            )
            self.database.audit(connection, "approve", "prescription", prescription_id)

    def detail(self, prescription_id: int) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute(
                """SELECT p.*, f.name AS formula_name, pt.full_name, pt.birth_date, pt.sex
                   FROM prescriptions p
                   JOIN consultations c ON c.id=p.consultation_id
                   JOIN patients pt ON pt.id=c.patient_id
                   JOIN formula_recommendations fr ON fr.id=p.recommendation_id
                   JOIN formulas f ON f.id=fr.formula_id WHERE p.id=?""",
                (prescription_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Không tìm thấy đơn thuốc.")
            items = connection.execute(
                """SELECT pi.*, h.name_vi AS herb_name
                   FROM prescription_items pi JOIN materia_medica h ON h.id=pi.herb_id
                   WHERE pi.prescription_id=? ORDER BY pi.id""",
                (prescription_id,),
            ).fetchall()
        result = dict(row)
        result["items"] = [dict(item) for item in items]
        return result
