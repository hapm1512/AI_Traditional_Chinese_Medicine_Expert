from __future__ import annotations

import hashlib
from typing import Any

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.security import require_role


class MateriaMedicaRepository:
    def __init__(self, database: DatabaseManager):
        self.database = database

    def categories(self) -> list[str]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT name FROM herb_categories ORDER BY name"
            ).fetchall()
        return [str(row[0]) for row in rows]

    def search(self, query: str = "", category: str = "", status: str = "") -> list[dict[str, Any]]:
        term = f"%{query.strip()}%"
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT h.*,hc.name AS category_name,
                          mt.name_vi AS translated_name,mt.status AS translation_status
                   FROM materia_medica h
                   LEFT JOIN herb_categories hc ON hc.id=h.category_id
                   LEFT JOIN materia_medica_translations mt ON mt.herb_id=h.id
                   WHERE (?='%%' OR h.code LIKE ? OR h.name_vi LIKE ? OR h.name_cn LIKE ?
                          OR h.pharmaceutical_name LIKE ? OR h.functions LIKE ?
                          OR h.meridians LIKE ? OR mt.name_vi LIKE ? OR mt.functions LIKE ?)
                     AND (?='' OR hc.name=?)
                     AND (?='' OR COALESCE(mt.status,'pending')=?)
                   ORDER BY COALESCE(NULLIF(mt.name_vi,''),NULLIF(h.name_vi,''),h.name_cn)""",
                (term, term, term, term, term, term, term, term, term,
                 category, category, status, status),
            ).fetchall()
        return [dict(row) for row in rows]

    def detail(self, herb_id: int) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute(
                """SELECT h.*,hc.name AS category_name
                   FROM materia_medica h LEFT JOIN herb_categories hc ON hc.id=h.category_id
                   WHERE h.id=?""", (herb_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Không tìm thấy dược liệu.")
            translation = connection.execute(
                "SELECT * FROM materia_medica_translations WHERE herb_id=?", (herb_id,)
            ).fetchone()
            formulas = connection.execute(
                """SELECT f.code,f.name,f.name_cn FROM formula_herb_links l
                   JOIN formulas f ON f.id=l.formula_id
                   WHERE l.herb_id=? ORDER BY f.name LIMIT 100""", (herb_id,)
            ).fetchall()
        result = dict(row)
        result["translation"] = dict(translation) if translation else None
        result["formulas"] = [dict(item) for item in formulas]
        return result

    def pending_translation_ids(self) -> list[int]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT h.id FROM materia_medica h
                   LEFT JOIN materia_medica_translations mt ON mt.herb_id=h.id
                   WHERE mt.id IS NULL ORDER BY h.id"""
            ).fetchall()
        return [int(row[0]) for row in rows]

    def translation_counts(self) -> tuple[int, int]:
        with self.database.transaction() as connection:
            translated = int(connection.execute(
                "SELECT COUNT(*) FROM materia_medica_translations"
            ).fetchone()[0])
            total = int(connection.execute("SELECT COUNT(*) FROM materia_medica").fetchone()[0])
        return translated, total

    def review_counts(self) -> dict[str, int]:
        with self.database.transaction() as connection:
            row = connection.execute(
                """SELECT COUNT(*) AS total,
                          SUM(CASE WHEN mt.id IS NULL THEN 1 ELSE 0 END) AS pending,
                          SUM(CASE WHEN mt.status='draft' THEN 1 ELSE 0 END) AS draft,
                          SUM(CASE WHEN mt.status='approved' THEN 1 ELSE 0 END) AS approved
                   FROM materia_medica h
                   LEFT JOIN materia_medica_translations mt ON mt.herb_id=h.id"""
            ).fetchone()
        return {
            "total": int(row["total"] or 0),
            "pending": int(row["pending"] or 0),
            "draft": int(row["draft"] or 0),
            "approved": int(row["approved"] or 0),
        }

    def next_review_id(self, herb_id: int) -> int | None:
        with self.database.transaction() as connection:
            row = connection.execute(
                """SELECT h.id FROM materia_medica h
                   LEFT JOIN materia_medica_translations mt ON mt.herb_id=h.id
                   WHERE COALESCE(mt.status,'pending')<>'approved' AND h.id>?
                   ORDER BY CASE COALESCE(mt.status,'pending')
                              WHEN 'draft' THEN 0 ELSE 1 END, h.id LIMIT 1""",
                (herb_id,),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    """SELECT h.id FROM materia_medica h
                       LEFT JOIN materia_medica_translations mt ON mt.herb_id=h.id
                       WHERE COALESCE(mt.status,'pending')<>'approved'
                       ORDER BY CASE COALESCE(mt.status,'pending')
                                  WHEN 'draft' THEN 0 ELSE 1 END, h.id LIMIT 1"""
                ).fetchone()
        return int(row[0]) if row is not None else None

    def create_manual(self, values: dict[str, str]) -> int:
        actor = require_role("doctor", "admin")
        code = str(values.get("code", "")).strip()[:50]
        name_vi = str(values.get("name_vi", "")).strip()[:200]
        name_cn = str(values.get("name_cn", "")).strip()[:200]
        pharmaceutical_name = str(values.get("pharmaceutical_name", "")).strip()[:300]
        category_name = str(values.get("category_name", "")).strip()[:200]
        reference_source = str(values.get("reference_source", "")).strip()[:1000]
        if not code or not name_vi:
            raise ValueError("Mã và tên dược liệu tiếng Việt không được để trống.")
        translation_fields = (
            "nature", "flavor", "meridians", "functions", "modern_effects",
            "combinations", "processing", "toxicity", "contraindications", "cautions",
        )
        cleaned = {
            field: str(values.get(field, "")).strip() for field in translation_fields
        }
        with self.database.transaction() as connection:
            duplicate = connection.execute(
                """SELECT id FROM materia_medica
                   WHERE code=? OR lower(name_vi)=lower(?) LIMIT 1""",
                (code, name_vi),
            ).fetchone()
            if duplicate is not None:
                raise ValueError("Mã hoặc tên dược liệu đã tồn tại.")
            category_id = None
            if category_name:
                category = connection.execute(
                    "SELECT id FROM herb_categories WHERE name=?", (category_name,)
                ).fetchone()
                if category is None:
                    category_code = "HC-MANUAL-" + hashlib.sha1(
                        category_name.encode("utf-8")
                    ).hexdigest()[:10].upper()
                    cursor = connection.execute(
                        "INSERT INTO herb_categories(code,name) VALUES(?,?)",
                        (category_code, category_name),
                    )
                    category_id = int(cursor.lastrowid)
                else:
                    category_id = int(category[0])
            cursor = connection.execute(
                """INSERT INTO materia_medica
                   (source_key,code,name_vi,name_cn,pharmaceutical_name,category_id,
                    nature,flavor,meridians,functions,modern_effects,combinations,
                    processing,toxicity,contraindications,cautions,reference_source,
                    sync_status,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'ready',CURRENT_TIMESTAMP)""",
                (
                    f"manual:{code}", code, name_vi, name_cn, pharmaceutical_name,
                    category_id, cleaned["nature"], cleaned["flavor"],
                    cleaned["meridians"], cleaned["functions"],
                    cleaned["modern_effects"], cleaned["combinations"],
                    cleaned["processing"], cleaned["toxicity"],
                    cleaned["contraindications"], cleaned["cautions"],
                    reference_source or "Sưu tầm",
                ),
            )
            herb_id = int(cursor.lastrowid)
            columns = ",".join(translation_fields)
            placeholders = ",".join("?" for _ in translation_fields)
            connection.execute(
                f"""INSERT INTO materia_medica_translations
                    (herb_id,name_vi,{columns},model,status)
                    VALUES(?,?,{placeholders},'collected','draft')""",
                (herb_id, name_vi, *(cleaned[field] for field in translation_fields)),
            )
            self.database.audit(
                connection, "create", "materia_medica", herb_id,
                f"draft; creator={actor.username}",
            )
        return herb_id

    def save_review(self, herb_id: int, values: dict[str, str], approved: bool) -> None:
        actor = require_role("doctor") if approved else require_role("doctor", "admin")
        fields = (
            "name_vi", "nature", "flavor", "meridians", "functions", "modern_effects",
            "combinations", "processing", "toxicity", "contraindications", "cautions",
        )
        cleaned = {field: str(values.get(field, "")).strip() for field in fields}
        if not cleaned["name_vi"]:
            raise ValueError("Tên dược liệu tiếng Việt không được để trống.")
        code = str(values.get("code", "")).strip()[:50]
        name_cn = str(values.get("name_cn", "")).strip()[:200]
        pharmaceutical_name = str(values.get("pharmaceutical_name", "")).strip()[:300]
        category_name = str(values.get("category_name", "")).strip()[:200]
        reference_source = str(values.get("reference_source", "")).strip()[:1000]
        if not code or not name_cn:
            raise ValueError("Mã và tên Trung không được để trống.")
        columns = ",".join(fields)
        placeholders = ",".join("?" for _ in fields)
        updates = ",".join(f"{field}=excluded.{field}" for field in fields)
        status = "approved" if approved else "draft"
        with self.database.transaction() as connection:
            duplicate = connection.execute(
                "SELECT id FROM materia_medica WHERE code=? AND id<>?", (code, herb_id)
            ).fetchone()
            if duplicate is not None:
                raise ValueError("Mã dược liệu đã tồn tại.")
            category_id = None
            if category_name:
                category = connection.execute(
                    "SELECT id FROM herb_categories WHERE name=?", (category_name,)
                ).fetchone()
                if category is None:
                    category_code = "HC-EDIT-" + hashlib.sha1(
                        category_name.encode("utf-8")
                    ).hexdigest()[:12].upper()
                    cursor = connection.execute(
                        "INSERT INTO herb_categories(code,name) VALUES(?,?)",
                        (category_code, category_name),
                    )
                    category_id = int(cursor.lastrowid)
                else:
                    category_id = int(category[0])
            connection.execute(
                """UPDATE materia_medica SET code=?,name_vi=?,name_cn=?,pharmaceutical_name=?,
                   category_id=?,reference_source=?,updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (code, cleaned["name_vi"], name_cn, pharmaceutical_name,
                 category_id, reference_source, herb_id),
            )
            connection.execute(
                f"""INSERT INTO materia_medica_translations
                    (herb_id,{columns},model,status) VALUES(?,{placeholders},'doctor',?)
                    ON CONFLICT(herb_id) DO UPDATE SET {updates},status=excluded.status,
                    updated_at=CURRENT_TIMESTAMP""",
                (herb_id, *(cleaned[field] for field in fields), status),
            )
            self.database.audit(
                connection, "review", "materia_medica", herb_id,
                f"{status}; reviewer={actor.username}",
            )
