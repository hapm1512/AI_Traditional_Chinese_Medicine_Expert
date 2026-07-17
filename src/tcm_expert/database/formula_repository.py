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
                """SELECT f.*,ft.name AS translated_name,
                          ft.category AS translated_category,ft.status AS translation_status,
                          COUNT(fi.id) AS ingredient_count
                   FROM formulas f
                   LEFT JOIN formula_ingredients fi ON fi.formula_id=f.id
                   LEFT JOIN formula_translations ft ON ft.formula_id=f.id
                   WHERE f.active=1
                     AND (?='' OR f.category=?)
                     AND (?='%%' OR f.name LIKE ? OR f.name_cn LIKE ? OR f.code LIKE ?
                          OR f.indications LIKE ? OR f.treatment_principle LIKE ?
                          OR ft.name LIKE ? OR ft.indications LIKE ?
                          OR EXISTS (
                              SELECT 1 FROM formula_herb_links l
                              JOIN materia_medica h ON h.id=l.herb_id
                              JOIN materia_medica_translations mt ON mt.herb_id=h.id
                              WHERE l.formula_id=f.id AND mt.status='approved'
                                AND (h.code LIKE ? OR h.name_vi LIKE ? OR h.name_cn LIKE ?
                                     OR mt.name_vi LIKE ?)
                          ))
                   GROUP BY f.id ORDER BY f.name""",
                (category, category, term, term, term, term, term, term, term, term,
                 term, term, term, term),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_doctor_formula(self, values: Mapping[str, Any]) -> int:
        data = self._doctor_values(values)
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """INSERT INTO formulas
                   (code,name,category,treatment_principle,indications,dosage_form,
                    directions,modifications,contraindications,interactions,
                    reference_source,disclaimer,source_type,created_by,
                    doctor_approved,ingredients_text)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?, 'doctor',?,?,?)""",
                data,
            )
            formula_id = int(cursor.lastrowid)
            self.database.audit(connection, "create", "doctor_formula", formula_id, data[-3])
            return formula_id

    def update_doctor_formula(self, formula_id: int, values: Mapping[str, Any]) -> None:
        self.update_formula(formula_id, values)

    def update_formula(self, formula_id: int, values: Mapping[str, Any]) -> None:
        data = self._doctor_values(values)
        with self.database.transaction() as connection:
            current = connection.execute(
                "SELECT source_type,disclaimer FROM formulas WHERE id=? AND active=1",
                (formula_id,),
            ).fetchone()
            if current is None:
                raise ValueError("Không tìm thấy bài thuốc.")
            disclaimer = current["disclaimer"] if current["source_type"] == "system" else data[11]
            cursor = connection.execute(
                """UPDATE formulas SET code=?,name=?,category=?,treatment_principle=?,
                   indications=?,dosage_form=?,directions=?,modifications=?,
                   contraindications=?,interactions=?,reference_source=?,disclaimer=?,
                   created_by=?,doctor_approved=?,ingredients_text=?
                   WHERE id=? AND active=1""",
                (*data[:11], disclaimer, *data[12:], formula_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Không tìm thấy bài thuốc.")
            self.database.audit(connection, "update", "formula", formula_id, data[-3])

    def hide_doctor_formula(self, formula_id: int, doctor_name: str) -> None:
        doctor_name = optional_text(doctor_name, 200)
        if not doctor_name:
            raise ValueError("Cần nhập tên bác sĩ.")
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """UPDATE formulas SET active=0 WHERE id=? AND source_type='doctor'""",
                (formula_id,),
            )
            if cursor.rowcount != 1:
                raise ValueError("Chỉ được ẩn bài thuốc do bác sĩ nhập.")
            self.database.audit(connection, "hide", "doctor_formula", formula_id, doctor_name)

    @staticmethod
    def _doctor_values(values: Mapping[str, Any]) -> tuple[Any, ...]:
        code = optional_text(values.get("code"), 50)
        name = optional_text(values.get("name"), 200)
        doctor = optional_text(values.get("created_by"), 200)
        ingredients = optional_text(values.get("ingredients_text"), 5000)
        if not all((code, name, doctor, ingredients)):
            raise ValueError("Cần nhập mã, tên, bác sĩ và thành phần.")
        return (
            code,
            name,
            optional_text(values.get("category"), 200),
            optional_text(values.get("treatment_principle"), 2000),
            optional_text(values.get("indications"), 3000),
            optional_text(values.get("dosage_form"), 200),
            optional_text(values.get("directions"), 2000),
            optional_text(values.get("modifications"), 3000),
            optional_text(values.get("contraindications"), 3000),
            optional_text(values.get("interactions"), 3000),
            optional_text(values.get("reference_source"), 1000),
            "Bài thuốc kinh nghiệm chỉ dùng khi bác sĩ chịu trách nhiệm phê duyệt.",
            doctor,
            int(bool(values.get("doctor_approved", False))),
            ingredients,
        )

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
            linked_herbs = connection.execute(
                """SELECT h.id,h.code,h.name_vi,h.name_cn,mt.name_vi AS translated_name
                   FROM formula_herb_links l
                   JOIN materia_medica h ON h.id=l.herb_id
                   JOIN materia_medica_translations mt ON mt.herb_id=h.id
                   WHERE l.formula_id=? AND mt.status='approved'
                   ORDER BY COALESCE(NULLIF(mt.name_vi,''),h.name_vi,h.name_cn)""",
                (formula_id,),
            ).fetchall()
        result = dict(formula)
        result["ingredients"] = [dict(row) for row in ingredients]
        result["linked_herbs"] = [dict(row) for row in linked_herbs]
        with self.database.transaction() as connection:
            translation = connection.execute(
                "SELECT * FROM formula_translations WHERE formula_id=?", (formula_id,)
            ).fetchone()
        result["translation"] = dict(translation) if translation else None
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
        if approved:
            from tcm_expert.security import current_user, require_role

            if current_user() is not None:
                require_role("doctor")
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
