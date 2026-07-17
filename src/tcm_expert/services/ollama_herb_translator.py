from __future__ import annotations

import json
import re

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.services.ollama_formula_translator import DEFAULT_QWEN_MODEL, OllamaLocalChat

FIELDS = (
    "name_vi", "nature", "flavor", "meridians", "functions", "modern_effects",
    "combinations", "processing", "toxicity", "contraindications", "cautions",
)


class OllamaHerbTranslator:
    def __init__(self, database: DatabaseManager, chat: OllamaLocalChat | None = None,
                 model: str = DEFAULT_QWEN_MODEL):
        self.database = database
        self.model = model
        self.chat = chat or OllamaLocalChat(model=model)

    def translate(self, herb_id: int) -> dict[str, str]:
        source = self._source(herb_id)
        prompt = (
            "你是专业中药中文-越南语翻译员。把 JSON 全部内容准确翻译为带声调的越南语。"
            "name_vi 必须是标准越南药名。不得诊断，不得推测或增加剂量。未知内容留空。"
            "只返回键名完全不变的 JSON object。中文药名由系统另行保留，不要放进 name_vi。\n"
            + json.dumps(source, ensure_ascii=False)
        )
        result = self._parse(self.chat._chat(prompt))
        if not result["name_vi"]:
            raise RuntimeError("Bản dịch thiếu tên dược liệu tiếng Việt")
        if source["name_vi"] and result["name_vi"] == source["name_vi"] and re.search(
            r"[\u3400-\u9fff]", source["name_vi"]
        ):
            raise RuntimeError("Qwen chưa dịch tên dược liệu")
        self._save(herb_id, result)
        return result

    def pending_herb_ids(self) -> list[int]:
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

    def _source(self, herb_id: int) -> dict[str, str]:
        with self.database.transaction() as connection:
            row = connection.execute(
                """SELECT name_cn,name_vi,nature,flavor,meridians,functions,modern_effects,
                          combinations,processing,toxicity,contraindications,cautions,
                          properties,preparation
                   FROM materia_medica WHERE id=?""", (herb_id,)
            ).fetchone()
        if row is None:
            raise ValueError("Không tìm thấy dược liệu cần dịch")
        return {
            "name_vi": str(row["name_vi"] or row["name_cn"] or ""),
            "nature": str(row["nature"] or ""), "flavor": str(row["flavor"] or ""),
            "meridians": str(row["meridians"] or ""),
            "functions": str(row["functions"] or row["properties"] or ""),
            "modern_effects": str(row["modern_effects"] or ""),
            "combinations": str(row["combinations"] or ""),
            "processing": str(row["processing"] or row["preparation"] or ""),
            "toxicity": str(row["toxicity"] or ""),
            "contraindications": str(row["contraindications"] or ""),
            "cautions": str(row["cautions"] or ""),
        }

    @staticmethod
    def _parse(raw: str) -> dict[str, str]:
        text = raw.strip()
        if text.startswith("```"):
            text = "\n".join(text.splitlines()[1:-1]).strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError("Qwen không trả JSON hợp lệ") from error
        if not isinstance(payload, dict):
            raise RuntimeError("Qwen trả bản dịch không hợp lệ")
        return {field: str(payload.get(field, "")).strip() for field in FIELDS}

    def _save(self, herb_id: int, values: dict[str, str]) -> None:
        columns = ",".join(FIELDS)
        placeholders = ",".join("?" for _ in FIELDS)
        updates = ",".join(f"{field}=excluded.{field}" for field in FIELDS)
        with self.database.transaction() as connection:
            connection.execute(
                f"""INSERT INTO materia_medica_translations
                    (herb_id,{columns},model,status) VALUES(?,{placeholders},?,'draft')
                    ON CONFLICT(herb_id) DO UPDATE SET {updates},model=excluded.model,
                    status='draft',updated_at=CURRENT_TIMESTAMP""",
                (herb_id, *(values[field] for field in FIELDS), self.model),
            )
            self.database.audit(connection, "translate", "materia_medica", herb_id,
                                f"model={self.model}, status=draft")
