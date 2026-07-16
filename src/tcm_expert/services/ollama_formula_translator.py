from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from tcm_expert.database.manager import DatabaseManager

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_QWEN_MODEL = "qwen2.5:7b"
TRANSLATED_FIELDS = (
    "name",
    "category",
    "treatment_principle",
    "indications",
    "directions",
    "contraindications",
    "interactions",
    "ingredients_text",
)
OllamaTransport = Callable[[str, dict[str, Any], float], dict[str, Any]]


def _ollama_transport(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        # Bỏ qua proxy hệ thống khi gọi máy cục bộ.
        with build_opener(ProxyHandler({})).open(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Không thể kết nối Ollama cục bộ: {error}") from error
    if not isinstance(result, dict):
        raise RuntimeError("Ollama trả dữ liệu không hợp lệ")
    return result


class OllamaLocalChat:
    def __init__(
        self,
        model: str = DEFAULT_QWEN_MODEL,
        timeout: float = 600,
        transport: OllamaTransport = _ollama_transport,
    ):
        self.model = model
        self.timeout = timeout
        self.transport = transport

    def _chat(self, prompt: str) -> str:
        result = self.transport(
            f"{OLLAMA_URL}/api/chat",
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json",
                "keep_alive": "10m",
                "options": {"temperature": 0, "num_predict": 1600},
            },
            self.timeout,
        )
        try:
            content = str(result["message"]["content"]).strip()
        except (KeyError, TypeError) as error:
            raise RuntimeError("Ollama thiếu nội dung dịch thuật") from error
        if not content:
            raise RuntimeError("Ollama trả bản dịch trống")
        return content


class OllamaFormulaTranslator:
    def __init__(
        self,
        database: DatabaseManager,
        chat: OllamaLocalChat | None = None,
        model: str = DEFAULT_QWEN_MODEL,
    ):
        self.database = database
        self.model = model
        self.chat = chat or OllamaLocalChat(model=model)

    def translate(self, formula_id: int) -> dict[str, str]:
        source = self._source(formula_id)
        prompt = (
            "你是专业的中医中文-越南语翻译员。必须把下面 JSON 中每一个中文值翻译成"
            "自然、准确、有越南语声调符号的越南语。严禁原样复制中文句子。"
            "方名、分类、治法、主治、用法、禁忌、注意事项和全部药物组成都必须翻译。"
            "药物的越南语名称后可在括号内保留中文原名。不得诊断，不得改变剂量，"
            "不得增加原文没有的知识。只返回一个 JSON object，键名必须完全不变。\n"
            + json.dumps(source, ensure_ascii=False)
        )
        raw = self.chat._chat(prompt)
        result = self._parse(raw)
        self._validate_translation(source, result)
        self._save(formula_id, result)
        return result

    def pending_formula_ids(self) -> list[int]:
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT f.id FROM formulas f
                   LEFT JOIN formula_translations ft ON ft.formula_id=f.id
                   WHERE f.active=1 AND f.code LIKE 'CF-%'
                     AND (ft.id IS NULL OR TRIM(ft.name)=TRIM(f.name_cn))
                   ORDER BY f.id"""
            ).fetchall()
        return [int(row[0]) for row in rows]

    def translation_counts(self) -> tuple[int, int]:
        with self.database.transaction() as connection:
            total = int(connection.execute(
                "SELECT COUNT(*) FROM formulas WHERE active=1 AND code LIKE 'CF-%'"
            ).fetchone()[0])
            translated = int(connection.execute(
                """SELECT COUNT(*) FROM formula_translations ft
                   JOIN formulas f ON f.id=ft.formula_id
                   WHERE f.active=1 AND f.code LIKE 'CF-%'
                     AND TRIM(ft.name)<>TRIM(f.name_cn)"""
            ).fetchone()[0])
        return translated, total

    def _source(self, formula_id: int) -> dict[str, str]:
        with self.database.transaction() as connection:
            row = connection.execute(
                """SELECT name_cn AS name,category,treatment_principle,indications,
                          directions,contraindications,interactions,ingredients_text
                   FROM formulas WHERE id=? AND active=1""",
                (formula_id,),
            ).fetchone()
        if row is None:
            raise ValueError("Không tìm thấy bài thuốc cần dịch")
        return {field: str(row[field] or "") for field in TRANSLATED_FIELDS}

    @staticmethod
    def _parse(raw: str) -> dict[str, str]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        try:
            payload: Any = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError("Qwen không trả JSON dịch thuật hợp lệ") from error
        if not isinstance(payload, dict):
            raise RuntimeError("Qwen trả dữ liệu dịch thuật không hợp lệ")
        result = {field: str(payload.get(field, "")).strip() for field in TRANSLATED_FIELDS}
        if not result["name"]:
            raise RuntimeError("Bản dịch thiếu tên bài thuốc")
        return result

    @staticmethod
    def _validate_translation(source: dict[str, str], result: dict[str, str]) -> None:
        unchanged = [
            field for field in TRANSLATED_FIELDS
            if source[field] and source[field].strip() == result[field].strip()
            and re.search(r"[\u3400-\u9fff]", source[field])
        ]
        source_han = len(re.findall(r"[\u3400-\u9fff]", " ".join(source.values())))
        result_han = len(re.findall(r"[\u3400-\u9fff]", " ".join(result.values())))
        if "name" in unchanged or len(unchanged) >= 2:
            raise RuntimeError("Qwen đã sao chép tiếng Trung, chưa tạo bản dịch tiếng Việt")
        if source_han >= 20 and result_han >= source_han * 0.75:
            raise RuntimeError("Bản dịch vẫn chứa quá nhiều nội dung tiếng Trung")

    def _save(self, formula_id: int, values: dict[str, str]) -> None:
        columns = ",".join(TRANSLATED_FIELDS)
        placeholders = ",".join("?" for _ in TRANSLATED_FIELDS)
        updates = ",".join(f"{field}=excluded.{field}" for field in TRANSLATED_FIELDS)
        with self.database.transaction() as connection:
            connection.execute(
                f"""INSERT INTO formula_translations
                    (formula_id,{columns},model,status)
                    VALUES(?,{placeholders},?,'draft')
                    ON CONFLICT(formula_id) DO UPDATE SET
                    {updates},model=excluded.model,status='draft',
                    updated_at=CURRENT_TIMESTAMP""",
                (formula_id, *(values[field] for field in TRANSLATED_FIELDS), self.model),
            )
            self.database.audit(
                connection, "translate", "classic_formula", formula_id,
                f"model={self.model}, status=draft",
            )
