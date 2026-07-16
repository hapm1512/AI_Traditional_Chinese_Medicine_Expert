from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


MINIMUM_COMPLETENESS = 0.50
FORBIDDEN_OUTPUT_PATTERNS = (
    r"\b\d+(?:[.,]\d+)?\s*(?:g|mg|ml|viên|thang)\b",
    r"(?:kê đơn|toa thuốc|đơn thuốc)\s*:",
    r"(?:chẩn đoán xác định|chẩn đoán cuối cùng)\s*:",
)


class AIValidationError(RuntimeError):
    """Raised when an AI proposal cannot be shown safely."""


@dataclass(frozen=True, slots=True)
class InputQuality:
    score: float
    acceptable: bool
    missing: tuple[str, ...]


def assess_input_quality(report: dict[str, Any]) -> InputQuality:
    score = min(1.0, max(0.0, float(report.get("completeness_score", 0))))
    missing = tuple(str(item).strip() for item in report.get("missing_data", []) if str(item).strip())
    return InputQuality(score, score >= MINIMUM_COMPLETENESS, missing)


def normalize_evidence(rows: list[Any]) -> tuple[str, ...]:
    normalized: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            source = str(row.get("source") or row.get("title") or row.get("id") or "").strip()
        else:
            source = str(row).strip()
        source = " ".join(source.split())[:300]
        if source and source not in normalized:
            normalized.append(source)
    return tuple(normalized)


def validate_ai_output(summary: str, evidence: tuple[str, ...]) -> None:
    text = str(summary).strip()
    if not text:
        raise AIValidationError("Mô-đun AI trả kết quả trống.")
    if not evidence:
        raise AIValidationError("Đề xuất AI thiếu nguồn hoặc căn cứ kiểm chứng.")
    for pattern in FORBIDDEN_OUTPUT_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            raise AIValidationError("Đề xuất AI chứa nội dung chẩn đoán, kê đơn hoặc liều dùng.")
