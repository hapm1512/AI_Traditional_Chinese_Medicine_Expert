from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import optional_text


class FormulaRepository:
    """Read formula references and record doctor-reviewed suggestions."""

    def __init__(self, database: DatabaseManager):
        self.database = database

    def search(self, query: str = "", category: str = "") -> list[dict[str, Any]]:
        term = f"%{query.strip()}%"
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT f.*, COUNT(fi.id) AS ingredient_count
                   FROM formulas f
                   LEFT JOIN formula_ingredients fi ON fi.formula_id=f.id
                   WHERE f.active=1
                     AND (?='' OR f.category=?)
                     AND (?='%%' OR f.name LIKE ? OR f.name_cn LIKE ? OR f.code LIKE ?
                          OR f.indications LIKE ? OR f.treatment_principle LIKE ?)
                   GROUP BY f.id ORDER BY f.name""",
                (category, category, term, term, term, term, term, term),
            ).fetchall()
        return [dict(row) for row in rows]

    def categories(self) -> list[str]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT DISTINCT category FROM formulas
                   WHERE active=1 AND category<>'' ORDER BY category"""
            ).fetchall()
        return [row[0] for row in rows]

    def detail(self, formula_id: int) -> dict[str, Any]:
        with self.database.transaction() as connection:
            formula = connection.execute(
                "SELECT * FROM formulas WHERE id=? AND active=1", (formula_id,)
            ).fetchone()
            if formula is None:
                raise ValueError("Không tìm thấy bài thuốc.")
            ingredients = connection.execute(
                """SELECT fi.*, h.name_vi AS herb_name, h.name_cn AS herb_name_cn,
                          h.nature, h.flavor, h.toxicity
                   FROM formula_ingredients fi
                   JOIN materia_medica h ON h.id=fi.herb_id
                   WHERE fi.formula_id=? ORDER BY fi.id""",
                (formula_id,),
            ).fetchall()
        result = dict(formula)
        result["ingredients"] = [dict(row) for row in ingredients]
        return result

    def safety_alerts(self, formula_id: int) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT h.name_vi AS herb_name, hi.severity, hi.effect,
                          hi.recommendation, hi.reference_source,
                          COALESCE(other.name_vi, hi.interacting_drug) AS interacts_with
                   FROM formula_ingredients fi
                   JOIN materia_medica h ON h.id=fi.herb_id
                   JOIN herb_interactions hi ON hi.herb_id=h.id
                   LEFT JOIN materia_medica other ON other.id=hi.interacting_herb_id
                   WHERE fi.formula_id=?
                   ORDER BY CASE hi.severity WHEN 'contraindicated' THEN 0
                            WHEN 'high' THEN 1 WHEN 'moderate' THEN 2 ELSE 3 END""",
                (formula_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_recommendations(self, consultation_id: int) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT fr.*, f.code, f.name, f.name_cn, f.disclaimer
                   FROM formula_recommendations fr
                   JOIN formulas f ON f.id=fr.formula_id
                   WHERE fr.consultation_id=? ORDER BY fr.created_at DESC, fr.id DESC""",
                (consultation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_recommendation(
        self, consultation_id: int, formula_id: int, values: Mapping[str, Any]
    ) -> int:
        directions = optional_text(values.get("custom_directions"), 1000)
        modifications = optional_text(values.get("modifications"), 2000)
        safety_notes = optional_text(values.get("safety_notes"), 2000)
        approved = int(bool(values.get("doctor_approved", False)))
        if approved and not safety_notes:
            raise ValueError("Cần ghi chú an toàn trước khi bác sĩ phê duyệt.")
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """INSERT INTO formula_recommendations
                   (consultation_id,formula_id,custom_directions,modifications,
                    safety_notes,doctor_approved) VALUES(?,?,?,?,?,?)""",
                (consultation_id, formula_id, directions, modifications, safety_notes, approved),
            )
            recommendation_id = int(cursor.lastrowid)
            self.database.audit(connection, "create", "formula_recommendation", recommendation_id)
        return recommendation_id

    def delete_recommendation(self, recommendation_id: int) -> None:
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM formula_recommendations WHERE id=?", (recommendation_id,)
            )
            self.database.audit(connection, "delete", "formula_recommendation", recommendation_id)
