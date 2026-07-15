from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path
    data: Path
    logs: Path
    database: Path
    settings: Path

    @classmethod
    def discover(cls, root: Path | None = None) -> "AppPaths":
        if root is None:
            base = Path(os.getenv("LOCALAPPDATA", Path.home() / ".local" / "share"))
            root = base / "TCMExpert"
        return cls(
            root=root,
            data=root / "data",
            logs=root / "logs",
            database=root / "data" / "tcm_expert.db",
            settings=root / "settings.json",
        )

    def ensure(self) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)

