from __future__ import annotations

import json
import re
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tcm_expert.database.manager import DatabaseManager

DEFAULT_HERB_URL = (
    "https://raw.githubusercontent.com/jangviktor-web/nihaixia-app/"
    "refs/heads/master/assets/data/herbs.json"
)
SOURCE_LABEL = "nihaixia-app herbs.json (MIT)"
JsonLoader = Callable[[str, float], Any]


@dataclass(frozen=True, slots=True)
class HerbSyncResult:
    received: int
    inserted: int
    updated: int
    skipped: int
    linked: int


def _download_json(url: str, timeout: float) -> Any:
    request = Request(url, headers={"User-Agent": "TCMExpert/3.7 herb-sync"})
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            if response.status != 200:
                raise RuntimeError(f"Nguồn dữ liệu trả mã {response.status}")
            raw = response.read(5_000_001)
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise RuntimeError(f"Không thể tải danh mục dược liệu: {error}") from error
    if len(raw) > 5_000_000:
        raise RuntimeError("Dữ liệu dược liệu vượt giới hạn an toàn")
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Nguồn dược liệu không phải JSON hợp lệ") from error


class MateriaMedicaSync:
    def __init__(self, database: DatabaseManager, loader: JsonLoader = _download_json):
        self.database = database
        self.loader = loader

    def sync(self, url: str = DEFAULT_HERB_URL, timeout: float = 30) -> HerbSyncResult:
        if not url.startswith("https://"):
            raise ValueError("Nguồn dược liệu bắt buộc dùng HTTPS")
        payload = self.loader(url, timeout)
        rows = payload.get("herbs") if isinstance(payload, dict) else payload
        if not isinstance(rows, list) or not 1 <= len(rows) <= 3000:
            raise RuntimeError("Nguồn dược liệu thiếu danh sách hợp lệ")
        inserted = updated = skipped = 0
        with self.database.transaction() as connection:
            for raw in rows:
                item = self._normalize(raw)
                if item is None:
                    skipped += 1
                    continue
                category_name = item[-1]
                category_id = None
                if category_name:
                    category_code = "HC-" + hashlib.sha1(
                        category_name.encode("utf-8")
                    ).hexdigest()[:12].upper()
                    connection.execute(
                        "INSERT OR IGNORE INTO herb_categories(code,name) VALUES(?,?)",
                        (category_code, category_name),
                    )
                    category_id = connection.execute(
                        "SELECT id FROM herb_categories WHERE name=?", (category_name,)
                    ).fetchone()[0]
                values = item[:-1]
                existing = connection.execute(
                    """SELECT id FROM materia_medica
                       WHERE source_key=? OR (name_cn<>'' AND name_cn=?)
                          OR (code<>'' AND code=?) LIMIT 1""",
                    (values[0], values[3], values[1]),
                ).fetchone()
                if existing is None:
                    connection.execute(
                        """INSERT INTO materia_medica
                           (source_key,code,name_vi,name_cn,pharmaceutical_name,nature,
                            flavor,properties,meridians,functions,preparation,toxicity,
                           contraindications,reference_source,source_payload,sync_status,category_id)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (*values, category_id)
                    )
                    inserted += 1
                else:
                    connection.execute(
                        """UPDATE materia_medica SET source_key=?,code=?,
                           name_vi=CASE WHEN name_vi='' THEN ? ELSE name_vi END,
                           name_cn=?,pharmaceutical_name=?,nature=?,flavor=?,properties=?,
                           meridians=?,functions=?,preparation=?,toxicity=?,
                           contraindications=?,reference_source=?,source_payload=?,
                           sync_status=?,category_id=COALESCE(?,category_id),
                           updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                        (*values, category_id, int(existing[0])),
                    )
                    updated += 1
            linked = self._link_formulas(connection)
            self.database.audit(
                connection, "sync", "materia_medica_catalog", None,
                f"received={len(rows)}, inserted={inserted}, updated={updated}, "
                f"skipped={skipped}, linked={linked}",
            )
        return HerbSyncResult(len(rows), inserted, updated, skipped, linked)

    @staticmethod
    def _normalize(raw: Any) -> tuple[str, ...] | None:
        if not isinstance(raw, dict):
            return None
        name_cn = str(raw.get("name_cn") or raw.get("name") or raw.get("chinese_name") or "").strip()
        source_key = str(raw.get("id") or raw.get("code") or name_cn).strip()
        if not name_cn:
            return None
        safe_key = re.sub(r"[^A-Za-z0-9_-]", "-", source_key).strip("-")
        if not safe_key:
            safe_key = hashlib.sha1(source_key.encode("utf-8")).hexdigest()[:12].upper()
        code = f"HM-{safe_key}"[:50]
        def value(*keys: str, limit: int = 3000) -> str:
            result = next((raw.get(key) for key in keys if raw.get(key) not in (None, "")), "")
            if isinstance(result, list):
                result = "、".join(str(item).strip() for item in result if str(item).strip())
            return str(result).strip()[:limit]
        name_vi = value("name_vi", "vietnamese_name", limit=200) or name_cn[:200]
        latin = value("pharmaceutical_name", "latin_name", "latin", limit=300)
        nature = value("nature", "property", limit=200)
        flavor = value("flavor", "taste", limit=200)
        properties = value("properties", "description", "original", "rongchuan", "niNote")
        meridians = value("meridians", "meridian")
        functions = value("functions", "effects", "efficacy", "action")
        preparation = value("preparation", "processing", "usage")
        toxicity = value("toxicity", limit=1000)
        contraindications = value("contraindications", "contraindication")
        incomplete = "ready" if functions and (nature or flavor or meridians) else "incomplete"
        return (
            source_key[:200], code, name_vi, name_cn[:200], latin, nature, flavor,
            properties, meridians, functions, preparation, toxicity,
            contraindications, SOURCE_LABEL, json.dumps(raw, ensure_ascii=False)[:20000], incomplete,
            value("category", limit=200),
        )

    @staticmethod
    def _link_formulas(connection: Any) -> int:
        connection.execute("DELETE FROM formula_herb_links")
        herbs = connection.execute(
            "SELECT id,name_cn,name_vi FROM materia_medica WHERE name_cn<>'' OR name_vi<>''"
        ).fetchall()
        formulas = connection.execute(
            "SELECT id,ingredients_text FROM formulas WHERE active=1 AND ingredients_text<>''"
        ).fetchall()
        linked = 0
        for formula in formulas:
            text = str(formula["ingredients_text"])
            for herb in herbs:
                names = (str(herb["name_cn"] or ""), str(herb["name_vi"] or ""))
                matched = next((name for name in names if name and name in text), "")
                if matched:
                    connection.execute(
                        "INSERT OR IGNORE INTO formula_herb_links(formula_id,herb_id,source_name) VALUES(?,?,?)",
                        (formula["id"], herb["id"], matched),
                    )
                    linked += 1
        return linked
