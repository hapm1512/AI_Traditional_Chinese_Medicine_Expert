import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class AppSettings:
    language: str = "vi_VN"
    theme: str = "dark"
    clinic_name: str = "Phòng khám Đông y"
    # Tạm tắt trong giai đoạn build/test. Bật lại trước bản vận hành chính thức.
    require_doctor_approval: bool = False

    @classmethod
    def load(cls, path: Path) -> "AppSettings":
        if not path.exists():
            settings = cls()
            settings.save(path)
            return settings
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(values, dict):
                raise ValueError("Cấu hình phải là một đối tượng JSON")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            invalid_path = path.with_name(f"settings.invalid_{stamp}.json")
            try:
                path.replace(invalid_path)
            except OSError:
                logging.exception("Không thể lưu cấu hình lỗi")
            logging.warning("Đã khôi phục cấu hình mặc định: %s", error)
            settings = cls()
            settings.save(path)
            return settings
        allowed = cls.__dataclass_fields__.keys()
        settings = cls(**{key: value for key, value in values.items() if key in allowed})
        settings.validate()
        return settings

    def validate(self) -> None:
        self.language = str(self.language).strip() or "vi_VN"
        self.theme = self.theme if self.theme in {"dark"} else "dark"
        self.clinic_name = str(self.clinic_name).strip()[:120] or "Phòng khám Đông y"
        self.require_doctor_approval = bool(self.require_doctor_approval)

    def save(self, path: Path) -> None:
        self.validate()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
