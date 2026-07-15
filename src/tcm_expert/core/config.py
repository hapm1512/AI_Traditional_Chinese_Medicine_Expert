from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(slots=True)
class AppSettings:
    language: str = "vi_VN"
    theme: str = "dark"
    clinic_name: str = "Phòng khám Đông y"
    require_doctor_approval: bool = True

    @classmethod
    def load(cls, path: Path) -> "AppSettings":
        if not path.exists():
            settings = cls()
            settings.save(path)
            return settings
        values = json.loads(path.read_text(encoding="utf-8"))
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in values.items() if key in allowed})

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

