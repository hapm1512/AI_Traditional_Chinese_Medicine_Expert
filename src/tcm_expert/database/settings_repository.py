from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.database.validation import ValidationError, optional_text, required_text


class SettingsRepository:
    TEST_DOCTOR_NAME = "Bác sĩ kiểm thử"
    def __init__(self, database: DatabaseManager):
        self.database = database

    def doctor(self) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM doctor_profile WHERE id=1").fetchone()
        return dict(row) if row else {}

    def doctor_name(self, required: bool = False) -> str:
        from tcm_expert.security import current_user

        actor = current_user()
        if required and actor is not None and actor.role != "doctor":
            raise ValidationError("Chỉ tài khoản bác sĩ được phê duyệt.")
        name = str(self.doctor().get("full_name", "")).strip()
        license_number = str(self.doctor().get("license_number", "")).strip()
        if required and (not name or not license_number):
            raise ValidationError("Bắt buộc khai báo bác sĩ và giấy phép hành nghề.")
        return name or self.TEST_DOCTOR_NAME

    def save_doctor(self, values: dict[str, Any]) -> dict[str, Any]:
        data = {
            "full_name": required_text(values.get("full_name"), "Họ tên bác sĩ", 150),
            "license_number": required_text(
                values.get("license_number"), "Số giấy phép hành nghề", 80
            ),
            "specialty": optional_text(values.get("specialty"), 150),
            "workplace": optional_text(values.get("workplace"), 255),
            "phone": self._digits(values.get("phone"), "Điện thoại", 10, optional=True),
        }
        with self.database.transaction() as connection:
            connection.execute(
                """UPDATE doctor_profile SET full_name=?,license_number=?,specialty=?,
                   workplace=?,phone=?,updated_at=CURRENT_TIMESTAMP WHERE id=1""",
                tuple(data.values()),
            )
            self.database.audit(connection, "update", "doctor_profile", 1, data["full_name"])
        return self.doctor()

    def ai_settings(self) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM ai_settings WHERE id=1").fetchone()
        result = dict(row) if row else {"enabled": 0}
        result["enabled"] = bool(result.get("enabled"))
        return result

    def set_ai_enabled(self, enabled: bool) -> None:
        with self.database.transaction() as connection:
            connection.execute("UPDATE ai_settings SET enabled=?,updated_at=CURRENT_TIMESTAMP WHERE id=1", (int(bool(enabled)),))
            self.database.audit(connection, "update", "ai_settings", 1, f"enabled={bool(enabled)}")

    def save_ai_config(self, values: dict[str, Any]) -> dict[str, Any]:
        mode = str(values.get("mode", "offline")).strip().lower()
        if mode not in {"offline", "connected"}:
            raise ValidationError("Chế độ AI không hợp lệ.")
        data = {
            "mode": mode,
            "chat_base_url": self._endpoint(values.get("chat_base_url")),
            "chat_model": optional_text(values.get("chat_model"), 100) or "tcmchat",
            "opentcm_url": self._endpoint(values.get("opentcm_url")),
            "tcmbank_url": self._endpoint(values.get("tcmbank_url")),
            "symmap_url": self._endpoint(values.get("symmap_url")),
            "timeout_seconds": max(3, min(120, int(values.get("timeout_seconds", 20)))),
        }
        if mode == "connected" and not data["chat_base_url"]:
            raise ValidationError("Chế độ kết nối cần địa chỉ TCMChat.")
        with self.database.transaction() as connection:
            connection.execute(
                """UPDATE ai_settings SET mode=?,chat_base_url=?,chat_model=?,
                   opentcm_url=?,tcmbank_url=?,symmap_url=?,timeout_seconds=?,
                   updated_at=CURRENT_TIMESTAMP WHERE id=1""",
                tuple(data.values()),
            )
            self.database.audit(connection, "update", "ai_settings", 1, f"mode={mode}")
        return self.ai_settings()

    @staticmethod
    def _endpoint(value: Any) -> str:
        text = str(value or "").strip().rstrip("/")
        if not text:
            return ""
        parsed = urlparse(text)
        local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
            raise ValidationError("Địa chỉ AI phải dùng HTTPS hoặc máy cục bộ.")
        if not parsed.netloc or parsed.username or parsed.password:
            raise ValidationError("Địa chỉ AI không hợp lệ.")
        return text

    def groups(self, active_only: bool = False) -> list[dict[str, Any]]:
        where = "WHERE active=1" if active_only else ""
        with self.database.transaction() as connection:
            rows = connection.execute(
                f"SELECT * FROM patient_code_groups {where} ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def save_group(self, name: str, prefix: str, group_id: int | None = None) -> int:
        name = required_text(name, "Tên nhóm bệnh", 100)
        prefix = required_text(prefix, "Mã nhóm", 6).upper()
        if not re.fullmatch(r"[A-Z]{1,6}", prefix):
            raise ValidationError("Mã nhóm chỉ gồm 1–6 chữ cái không dấu.")
        try:
            with self.database.transaction() as connection:
                if group_id is None:
                    cursor = connection.execute(
                        "INSERT INTO patient_code_groups(name,prefix) VALUES(?,?)",
                        (name, prefix),
                    )
                    group_id = int(cursor.lastrowid)
                else:
                    connection.execute(
                        "UPDATE patient_code_groups SET name=?,prefix=?,active=1 WHERE id=?",
                        (name, prefix, group_id),
                    )
                self.database.audit(connection, "save", "patient_code_group", group_id, prefix)
        except Exception as error:
            if "UNIQUE" in str(error):
                raise ValidationError("Tên hoặc mã nhóm đã tồn tại.") from error
            raise
        return group_id

    @staticmethod
    def _digits(value: Any, field: str, length: int, optional: bool = False) -> str:
        text = str(value or "").strip()
        if optional and not text:
            return ""
        if not re.fullmatch(rf"\d{{{length}}}", text):
            raise ValidationError(f"{field} phải đúng {length} chữ số.")
        return text
