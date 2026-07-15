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

    def update_diagnostic_entry(
        self,
        entry_id: int,
        method: str,
        category: str,
        finding: str,
        severity: int | None = None,
        note: str = "",
    ) -> None:
        choice(method, "Phương pháp tứ chẩn", {"vong", "van", "van_hoi", "thiet"})
        if severity is not None and not 0 <= int(severity) <= 10:
            raise ValueError("Mức độ phải từ 0 đến 10")
        with self.database.transaction() as connection:
            exists = connection.execute(
                "SELECT 1 FROM diagnostic_entries WHERE id=?", (entry_id,)
            ).fetchone()
            if not exists:
                raise LookupError("Không tìm thấy kết quả tứ chẩn")
            connection.execute(
                """UPDATE diagnostic_entries
                SET method=?, category=?, finding=?, severity=?, note=? WHERE id=?""",
                (
                    method,
                    required_text(category, "Nhóm tứ chẩn", 100),
                    required_text(finding, "Kết quả tứ chẩn", 2000),
                    severity,
                    optional_text(note, 2000),
                    entry_id,
                ),
            )
            self.database.audit(connection, "update", "diagnostic_entry", entry_id)

    def delete_diagnostic_entry(self, entry_id: int) -> None:
        with self.database.transaction() as connection:
            exists = connection.execute(
                "SELECT 1 FROM diagnostic_entries WHERE id=?", (entry_id,)
            ).fetchone()
            if not exists:
                raise LookupError("Không tìm thấy kết quả tứ chẩn")
            connection.execute("DELETE FROM diagnostic_entries WHERE id=?", (entry_id,))
            self.database.audit(connection, "delete", "diagnostic_entry", entry_id)

    def listening_smelling_findings(self, consultation_id: int) -> list[dict[str, Any]]:
        self.get(consultation_id)
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT * FROM listening_smelling_findings
                WHERE consultation_id=? ORDER BY recorded_at DESC, id DESC""",
                (consultation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_listening_smelling_finding(
        self, consultation_id: int, values: Mapping[str, Any]
    ) -> int:
        data = self._validate_listening_smelling(values)
        self.get(consultation_id)
        columns = ", ".join(("consultation_id", *data.keys()))
        placeholders = ", ".join("?" for _ in range(len(data) + 1))
        with self.database.transaction() as connection:
            cursor = connection.execute(
                f"INSERT INTO listening_smelling_findings ({columns}) VALUES ({placeholders})",
                (consultation_id, *data.values()),
            )
            self.database.audit(
                connection, "create", "listening_smelling_finding", cursor.lastrowid
            )
        return int(cursor.lastrowid)

    def delete_listening_smelling_finding(self, finding_id: int) -> None:
        with self.database.transaction() as connection:
            exists = connection.execute(
                "SELECT 1 FROM listening_smelling_findings WHERE id=?", (finding_id,)
            ).fetchone()
            if not exists:
                raise LookupError("Không tìm thấy kết quả Văn chẩn")
            connection.execute("DELETE FROM listening_smelling_findings WHERE id=?", (finding_id,))
            self.database.audit(connection, "delete", "listening_smelling_finding", finding_id)

    def inquiry_finding(self, consultation_id: int) -> dict[str, Any] | None:
        self.get(consultation_id)
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM inquiry_findings WHERE consultation_id=?",
                (consultation_id,),
            ).fetchone()
        return None if row is None else dict(row)

    def save_inquiry_finding(
        self, consultation_id: int, values: Mapping[str, Any]
    ) -> dict[str, Any]:
        data = self._validate_inquiry(values)
        self.get(consultation_id)
        columns = ", ".join(data)
        placeholders = ", ".join("?" for _ in data)
        updates = ", ".join(f"{column}=excluded.{column}" for column in data)
        with self.database.transaction() as connection:
            connection.execute(
                f"""INSERT INTO inquiry_findings
                (consultation_id, {columns}) VALUES (?, {placeholders})
                ON CONFLICT(consultation_id) DO UPDATE SET
                {updates}, updated_at=CURRENT_TIMESTAMP""",
                (consultation_id, *data.values()),
            )
            row = connection.execute(
                "SELECT id FROM inquiry_findings WHERE consultation_id=?",
                (consultation_id,),
            ).fetchone()
            self.database.audit(connection, "save", "inquiry_finding", row["id"])
        return self.inquiry_finding(consultation_id) or {}

    def delete_inquiry_finding(self, consultation_id: int) -> None:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT id FROM inquiry_findings WHERE consultation_id=?",
                (consultation_id,),
            ).fetchone()
            if row is None:
                return
            connection.execute(
                "DELETE FROM inquiry_findings WHERE consultation_id=?", (consultation_id,)
            )
            self.database.audit(connection, "delete", "inquiry_finding", row["id"])

    def pulse_findings(self, consultation_id: int) -> list[dict[str, Any]]:
        self.get(consultation_id)
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT * FROM pulse_findings WHERE consultation_id=?
                ORDER BY side, CASE position WHEN 'cun' THEN 1 WHEN 'guan' THEN 2 ELSE 3 END""",
                (consultation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_pulse_finding(self, consultation_id: int, values: Mapping[str, Any]) -> dict[str, Any]:
        data = self._validate_pulse(values)
        self.get(consultation_id)
        columns = ", ".join(data)
        placeholders = ", ".join("?" for _ in data)
        updates = ", ".join(f"{column}=excluded.{column}" for column in data)
        with self.database.transaction() as connection:
            connection.execute(
                f"""INSERT INTO pulse_findings (consultation_id, {columns})
                VALUES (?, {placeholders}) ON CONFLICT(consultation_id, side, position)
                DO UPDATE SET {updates}, updated_at=CURRENT_TIMESTAMP""",
                (consultation_id, *data.values()),
            )
            row = connection.execute(
                """SELECT id FROM pulse_findings
                WHERE consultation_id=? AND side=? AND position=?""",
                (consultation_id, data["side"], data["position"]),
            ).fetchone()
            self.database.audit(connection, "save", "pulse_finding", row["id"])
        return next(
            row
            for row in self.pulse_findings(consultation_id)
            if row["side"] == data["side"] and row["position"] == data["position"]
        )

    def delete_pulse_findings(self, consultation_id: int) -> None:
        self.get(consultation_id)
        with self.database.transaction() as connection:
            connection.execute(
                "DELETE FROM pulse_findings WHERE consultation_id=?", (consultation_id,)
            )
            self.database.audit(connection, "delete", "pulse_findings", consultation_id)

    def palpation_findings(self, consultation_id: int) -> list[dict[str, Any]]:
        self.get(consultation_id)
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT * FROM palpation_findings WHERE consultation_id=? ORDER BY id DESC",
                (consultation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_palpation_finding(self, consultation_id: int, values: Mapping[str, Any]) -> int:
        data = self._validate_palpation(values)
        self.get(consultation_id)
        columns = ", ".join(("consultation_id", *data.keys()))
        placeholders = ", ".join("?" for _ in range(len(data) + 1))
        with self.database.transaction() as connection:
            cursor = connection.execute(
                f"INSERT INTO palpation_findings ({columns}) VALUES ({placeholders})",
                (consultation_id, *data.values()),
            )
            self.database.audit(connection, "create", "palpation_finding", cursor.lastrowid)
        return int(cursor.lastrowid)

    def delete_palpation_finding(self, finding_id: int) -> None:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT 1 FROM palpation_findings WHERE id=?", (finding_id,)
            ).fetchone()
            if row is None:
                raise LookupError("Không tìm thấy kết quả xúc chẩn")
            connection.execute("DELETE FROM palpation_findings WHERE id=?", (finding_id,))
            self.database.audit(connection, "delete", "palpation_finding", finding_id)

    @staticmethod
    def _validate_listening_smelling(values: Mapping[str, Any]) -> dict[str, Any]:
        finding_types = {
            "voice",
            "breathing",
            "cough",
            "sputum",
            "hiccup",
            "pathological_sound",
            "odor",
            "other",
        }
        severity = int(values.get("severity") or 0)
        if not 0 <= severity <= 10:
            raise ValueError("Mức độ phải từ 0 đến 10")
        return {
            "finding_type": choice(values.get("finding_type"), "Loại Văn chẩn", finding_types),
            "characteristic": required_text(values.get("characteristic"), "Đặc điểm", 500),
            "frequency": optional_text(values.get("frequency"), 100),
            "severity": severity,
            "duration": optional_text(values.get("duration"), 100),
            "odor": optional_text(values.get("odor"), 300),
            "note": optional_text(values.get("note"), 2000),
            "recorded_by": required_text(values.get("recorded_by"), "Người ghi nhận", 150),
        }

    @staticmethod
    def _validate_inquiry(values: Mapping[str, Any]) -> dict[str, Any]:
        fields = (
            "cold_heat",
            "sweating",
            "head_body",
            "chest_abdomen",
            "appetite_taste",
            "thirst_drink",
            "sleep",
            "stool",
            "urination",
            "ears_eyes",
            "gynecology",
            "onset_progress",
            "current_treatment",
            "red_flags",
            "note",
        )
        data = {field: optional_text(values.get(field), 2000) for field in fields}
        data["recorded_by"] = required_text(values.get("recorded_by"), "Người hỏi", 150)
        return data

    @staticmethod
    def _validate_pulse(values: Mapping[str, Any]) -> dict[str, Any]:
        bpm_value = values.get("bpm")
        bpm = None if bpm_value in (None, "", 0) else int(bpm_value)
        if bpm is not None and not 20 <= bpm <= 250:
            raise ValueError("Nhịp mạch phải từ 20 đến 250")
        return {
            "side": choice(values.get("side"), "Bên mạch", {"left", "right"}),
            "position": choice(values.get("position"), "Bộ vị", {"cun", "guan", "chi"}),
            "depth": optional_text(values.get("depth"), 100),
            "rate": optional_text(values.get("rate"), 100),
            "strength": optional_text(values.get("strength"), 100),
            "rhythm": optional_text(values.get("rhythm"), 100),
            "quality": required_text(values.get("quality"), "Mạch tượng", 300),
            "bpm": bpm,
            "note": optional_text(values.get("note"), 1000),
            "recorded_by": required_text(values.get("recorded_by"), "Người bắt mạch", 150),
        }

    @staticmethod
    def _validate_palpation(values: Mapping[str, Any]) -> dict[str, Any]:
        severity = int(values.get("severity") or 0)
        if not 0 <= severity <= 10:
            raise ValueError("Mức độ phải từ 0 đến 10")
        return {
            "body_area": required_text(values.get("body_area"), "Vùng sờ nắn", 200),
            "finding_type": choice(
                values.get("finding_type"),
                "Loại xúc chẩn",
                {"temperature", "tenderness", "mass", "skin", "abdomen", "acupoint", "other"},
            ),
            "characteristic": required_text(values.get("characteristic"), "Đặc điểm", 1000),
            "severity": severity,
            "note": optional_text(values.get("note"), 1000),
            "recorded_by": required_text(values.get("recorded_by"), "Người ghi nhận", 150),
        }

    @classmethod
    def _validate(cls, values: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "visit_code": patient_code(values.get("visit_code")),
            "status": choice(values.get("status", "draft"), "Trạng thái", cls.VALID_STATUS),
            "chief_complaint": optional_text(values.get("chief_complaint"), 2000),
            "symptoms": optional_text(values.get("symptoms"), 5000),
            "western_history": optional_text(values.get("western_history"), 5000),
            "doctor_name": optional_text(values.get("doctor_name"), 150),
            "observation": optional_text(values.get("observation"), 5000),
            "listening_smelling": optional_text(values.get("listening_smelling"), 5000),
            "inquiry": optional_text(values.get("inquiry"), 5000),
            "palpation": optional_text(values.get("palpation"), 5000),
            "assessment": optional_text(values.get("assessment"), 5000),
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
