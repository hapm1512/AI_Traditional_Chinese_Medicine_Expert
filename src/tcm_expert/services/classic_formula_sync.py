from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tcm_expert.database.manager import DatabaseManager

DEFAULT_FORMULA_URL = (
    "https://raw.githubusercontent.com/jangviktor-web/nihaixia-app/"
    "refs/heads/master/assets/data/formulas.json"
)
SOURCE_LABEL = "nihaixia-app formulas.json (MIT) — Thương hàn luận/Kim quỹ yếu lược"

JsonLoader = Callable[[str, float], Any]


@dataclass(frozen=True, slots=True)
class SyncResult:
    received: int
    inserted: int
    updated: int
    skipped: int


def _download_json(url: str, timeout: float) -> Any:
    request = Request(url, headers={"User-Agent": "TCMExpert/3.4 formula-sync"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - validated HTTPS
            if response.status != 200:
                raise RuntimeError(f"Nguồn dữ liệu trả mã {response.status}")
            raw = response.read(2_500_001)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise RuntimeError(f"Không thể tải dữ liệu cổ phương: {error}") from error
    if len(raw) > 2_500_000:
        raise RuntimeError("Dữ liệu cổ phương vượt giới hạn an toàn")
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Nguồn cổ phương không phải JSON hợp lệ") from error


class ClassicFormulaSync:
    def __init__(self, database: DatabaseManager, loader: JsonLoader = _download_json):
        self.database = database
        self.loader = loader

    def sync(self, url: str = DEFAULT_FORMULA_URL, timeout: float = 25) -> SyncResult:
        if not url.startswith("https://"):
            raise ValueError("Nguồn cổ phương bắt buộc dùng HTTPS")
        payload = self.loader(url, timeout)
        rows = payload.get("formulas") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise RuntimeError("Nguồn cổ phương thiếu danh sách dữ liệu")
        if not 1 <= len(rows) <= 2000:
            raise RuntimeError("Số lượng cổ phương không hợp lệ")

        inserted = updated = skipped = 0
        with self.database.transaction() as connection:
            name_owners = {
                str(row[0]): str(row[1])
                for row in connection.execute("SELECT name,code FROM formulas")
            }
            for raw in rows:
                normalized = self._normalize(raw)
                if normalized is None:
                    skipped += 1
                    continue
                owner = name_owners.get(normalized[1])
                if owner is not None and owner != normalized[0]:
                    unique_name = f"{normalized[1]} [{normalized[0][3:]}]"[:200]
                    normalized = (normalized[0], unique_name, *normalized[2:])
                existing = connection.execute(
                    "SELECT id FROM formulas WHERE code=?", (normalized[0],)
                ).fetchone()
                if existing is None:
                    connection.execute(
                        """INSERT INTO formulas
                           (code,name,name_cn,category,treatment_principle,indications,
                            dosage_form,directions,modifications,contraindications,
                            interactions,reference_source,disclaimer,source_type,
                            created_by,doctor_approved,ingredients_text,active)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,'system','',1,?,1)""",
                        normalized,
                    )
                    inserted += 1
                else:
                    connection.execute(
                        """UPDATE formulas SET name=?,name_cn=?,category=?,
                           treatment_principle=?,indications=?,dosage_form=?,directions=?,
                           modifications=?,contraindications=?,interactions=?,
                           reference_source=?,disclaimer=?,ingredients_text=?,active=1
                           WHERE code=? AND source_type='system'""",
                        (*normalized[1:13], normalized[13], normalized[0]),
                    )
                    updated += 1
                name_owners[normalized[1]] = normalized[0]
            self.database.audit(
                connection, "sync", "classic_formula_catalog", None,
                f"received={len(rows)}, inserted={inserted}, updated={updated}, skipped={skipped}",
            )
        return SyncResult(len(rows), inserted, updated, skipped)

    @staticmethod
    def _normalize(raw: Any) -> tuple[str, ...] | None:
        if not isinstance(raw, dict):
            return None
        source_id = str(raw.get("id", "")).strip()
        name_cn = str(raw.get("name", "")).strip()
        if not source_id or not name_cn:
            return None
        alias = str(raw.get("alias", "")).strip()
        components = raw.get("components", [])
        if not isinstance(components, list):
            components = []
        ingredient_lines = []
        for item in components:
            if not isinstance(item, dict) or not str(item.get("name", "")).strip():
                continue
            parts = [str(item.get(key, "")).strip() for key in ("name", "dosage", "role")]
            ingredient_lines.append(" — ".join(part for part in parts if part))
        keywords = raw.get("keywords", [])
        keyword_text = (
            "、".join(str(x).strip() for x in keywords if str(x).strip())
            if isinstance(keywords, list) else ""
        )
        explanation = str(raw.get("explanation", "")).strip()
        meridian = str(raw.get("meridian", "")).strip()
        principle = "；".join(x for x in (meridian, explanation) if x)
        disclaimer = (
            "Dữ liệu cổ phương dùng tra cứu và kiểm thử. Không tự động kê đơn "
            "hoặc quy đổi liều. Bác sĩ phải đối chiếu nguyên bản và chịu trách "
            "nhiệm quyết định."
        )
        name = f"{name_cn} ({alias})" if alias and alias != name_cn else name_cn
        return (
            f"CF-{source_id}"[:50], name[:200], name_cn[:200],
            str(raw.get("category", "Cổ phương")).strip()[:200], principle[:2000],
            str(raw.get("indication", "")).strip()[:3000], "Cổ phương",
            str(raw.get("dosage", "")).strip()[:2000], "",
            str(raw.get("contraindication", "")).strip()[:3000],
            f"Từ khóa nguồn: {keyword_text}"[:3000], SOURCE_LABEL, disclaimer,
            "\n".join(ingredient_lines)[:5000],
        )
