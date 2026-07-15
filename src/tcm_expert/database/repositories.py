from collections.abc import Mapping, Sequence
from typing import Any

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import (
    choice,
    iso_date,
    optional_text,
    patient_code,
    required_text,
)


class PatientRepository:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def create(self, values: Mapping[str, Any]) -> dict[str, Any]:
        data = self._validate(values)
        columns = ", ".join(data)
        placeholders = ", ".join("?" for _ in data)
        with self.database.transaction() as connection:
            cursor = connection.execute(
                f"INSERT INTO patients ({columns}) VALUES ({placeholders})", tuple(data.values())
            )
            self.database.audit(connection, "create", "patient", cursor.lastrowid)
            patient_id = cursor.lastrowid
        return self.get(patient_id)

    def get(self, patient_id: int) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM patients WHERE id = ? AND deleted_at IS NULL", (patient_id,)
            ).fetchone()
        if row is None:
            raise LookupError("Không tìm thấy bệnh nhân")
        return dict(row)

    def list(self, search: str = "", limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        term = f"%{search.strip()}%"
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT * FROM patients WHERE deleted_at IS NULL
                AND (? = '%%' OR full_name LIKE ? OR code LIKE ? OR phone LIKE ?)
                ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
                (term, term, term, term, min(max(limit, 1), 500), max(offset, 0)),
            ).fetchall()
        return [dict(row) for row in rows]

    def update(self, patient_id: int, values: Mapping[str, Any]) -> dict[str, Any]:
        current = self.get(patient_id)
        merged = {**current, **values}
        data = self._validate(merged)
        assignments = ", ".join(f"{column} = ?" for column in data)
        with self.database.transaction() as connection:
            connection.execute(
                f"UPDATE patients SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (*data.values(), patient_id),
            )
            self.database.audit(connection, "update", "patient", patient_id)
        return self.get(patient_id)

    def delete(self, patient_id: int) -> None:
        self.get(patient_id)
        with self.database.transaction() as connection:
            connection.execute(
                "UPDATE patients SET deleted_at=CURRENT_TIMESTAMP WHERE id=?", (patient_id,)
            )
            self.database.audit(connection, "soft_delete", "patient", patient_id)

    @staticmethod
    def _validate(values: Mapping[str, Any]) -> dict[str, Any]:
        sex = str(values.get("sex") or "")
        if sex:
            choice(sex, "Giới tính", {"male", "female", "other", "unknown"})
        return {
            "code": patient_code(values.get("code")),
            "full_name": required_text(values.get("full_name"), "Họ tên", 150),
            "birth_date": iso_date(values.get("birth_date"), "Ngày sinh"),
            "sex": sex,
            "phone": optional_text(values.get("phone"), 30),
            "identity_number": optional_text(values.get("identity_number"), 30),
            "address": optional_text(values.get("address"), 500),
            "emergency_contact": optional_text(values.get("emergency_contact"), 255),
            "allergies": optional_text(values.get("allergies"), 2000),
            "notes": optional_text(values.get("notes"), 5000),
        }


class ConsultationRepository:
    VALID_STATUS = {"draft", "in_review", "approved", "closed"}

    def __init__(self, database: DatabaseManager):
        self.database = database

    def create(self, patient_id: int, visit_code: str, **values: Any) -> dict[str, Any]:
        data = self._validate({"visit_code": visit_code, **values})
        with self.database.transaction() as connection:
            exists = connection.execute(
                "SELECT 1 FROM patients WHERE id=? AND deleted_at IS NULL", (patient_id,)
            ).fetchone()
            if not exists:
                raise LookupError("Không tìm thấy bệnh nhân")
            columns = ", ".join(("patient_id", *data.keys()))
            placeholders = ", ".join("?" for _ in range(len(data) + 1))
            cursor = connection.execute(
                f"INSERT INTO consultations ({columns}) VALUES ({placeholders})",
                (patient_id, *data.values()),
            )
            self.database.audit(connection, "create", "consultation", cursor.lastrowid)
            consultation_id = cursor.lastrowid
        return self.get(consultation_id)

    def get(self, consultation_id: int) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM consultations WHERE id=?", (consultation_id,)
            ).fetchone()
        if row is None:
            raise LookupError("Không tìm thấy hồ sơ khám")
        return dict(row)

    def list_for_patient(self, patient_id: int) -> list[dict[str, Any]]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM consultations WHERE patient_id=? ORDER BY created_at DESC, id DESC",
                (patient_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def update(self, consultation_id: int, values: Mapping[str, Any]) -> dict[str, Any]:
        current = self.get(consultation_id)
        data = self._validate({**current, **values})
        assignments = ", ".join(f"{column} = ?" for column in data)
        with self.database.transaction() as connection:
            connection.execute(
                f"UPDATE consultations SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (*data.values(), consultation_id),
            )
            self.database.audit(connection, "update", "consultation", consultation_id)
        return self.get(consultation_id)

    def delete(self, consultation_id: int) -> None:
        self.get(consultation_id)
        with self.database.transaction() as connection:
            connection.execute("DELETE FROM consultations WHERE id=?", (consultation_id,))
            self.database.audit(connection, "delete", "consultation", consultation_id)

    def diagnostic_entries(self, consultation_id: int) -> list[dict[str, Any]]:
        self.get(consultation_id)
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM diagnostic_entries WHERE consultation_id=? ORDER BY id",
                (consultation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_diagnostic_entry(
        self,
        consultation_id: int,
        method: str,
        category: str,
        finding: str,
        severity: int | None = None,
        note: str = "",
    ) -> int:
        choice(method, "Phương pháp tứ chẩn", {"vong", "van", "van_hoi", "thiet"})
        if severity is not None and not 0 <= int(severity) <= 10:
            raise ValueError("Mức độ phải từ 0 đến 10")
        self.get(consultation_id)
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """INSERT INTO diagnostic_entries
                (consultation_id, method, category, finding, severity, note)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    consultation_id,
                    method,
                    required_text(category, "Nhóm tứ chẩn", 100),
                    required_text(finding, "Kết quả tứ chẩn", 2000),
                    severity,
                    optional_text(note, 2000),
                ),
            )
            self.database.audit(connection, "create", "diagnostic_entry", cursor.lastrowid)
            return int(cursor.lastrowid)

    @classmethod
    def _validate(cls, values: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "visit_code": patient_code(values.get("visit_code")),
            "status": choice(values.get("status", "draft"), "Trạng thái", cls.VALID_STATUS),
            "chief_complaint": optional_text(values.get("chief_complaint"), 2000),
            "symptoms": optional_text(values.get("symptoms"), 5000),
            "western_history": optional_text(values.get("western_history"), 5000),
            "doctor_name": optional_text(values.get("doctor_name"), 150),
        }


class ReferenceRepository:
    ALLOWED_TABLES = {
        "symptoms",
        "organ_systems",
        "meridians",
        "theory_concepts",
        "tcm_syndromes",
        "diseases",
        "herb_categories",
        "materia_medica",
        "formulas",
        "formula_ingredients",
        "herb_interactions",
    }

    def __init__(self, database: DatabaseManager):
        self.database = database

    def list(self, table: str) -> Sequence[dict[str, Any]]:
        if table not in self.ALLOWED_TABLES:
            raise ValueError("Danh mục không được phép")
        with self.database.transaction() as connection:
            rows = connection.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
        return [dict(row) for row in rows]
