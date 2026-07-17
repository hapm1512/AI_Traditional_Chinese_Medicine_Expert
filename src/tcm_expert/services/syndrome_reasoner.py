import re
import unicodedata
from typing import Any

RULES = {
    "TYKHIHU": ("mệt", "ăn ít", "đại tiện lỏng", "bụng trướng", "lưỡi nhạt", "mạch hư"),
    "CANUAT": ("căng thẳng", "dễ cáu", "tức ngực", "hạ sườn", "hay thở dài", "mạch huyền"),
    "TAMTYHU": ("hồi hộp", "mất ngủ", "hay quên", "mệt", "ăn kém", "sắc mặt nhợt"),
    "THANAMHU": ("đau lưng", "ù tai", "đạo hãn", "nóng lòng bàn tay", "miệng khô", "mạch tế"),
    "PHẾKHIHU": ("ho yếu", "thở ngắn", "tự hãn", "mệt", "tiếng nói nhỏ", "dễ cảm"),
    "DAMTHAP": ("nặng đầu", "ngực tức", "đờm nhiều", "rêu lưỡi nhớt", "mạch hoạt", "buồn nôn"),
}

ORGAN_BY_CODE = {
    "TYKHIHU": "Tỳ",
    "CANUAT": "Can",
    "TAMTYHU": "Tâm, Tỳ",
    "THANAMHU": "Thận",
    "PHẾKHIHU": "Phế",
    "DAMTHAP": "Tỳ, Phế",
}


def _normalise(value: str) -> str:
    value = unicodedata.normalize("NFC", value).lower()
    return re.sub(r"\s+", " ", value)


def suggest(text: str, syndromes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Returns transparent keyword matches, never a medical diagnosis."""
    source = _normalise(text)
    results = []
    for syndrome in syndromes:
        keywords = RULES.get(syndrome["code"], ())
        matched = [keyword for keyword in keywords if _normalise(keyword) in source]
        if not matched:
            continue
        coverage = len(matched) / max(len(keywords), 1)
        confidence = min(0.95, 0.30 + len(matched) * 0.09 + coverage * 0.20)
        results.append(
            {
                **syndrome,
                "confidence": confidence,
                "matched": matched,
                "evidence_count": len(matched),
                "evidence_total": len(keywords),
                "organ_systems": ORGAN_BY_CODE.get(syndrome["code"], "Chưa xác định"),
                "review_required": True,
            }
        )
    return sorted(results, key=lambda item: (-item["confidence"], item["name"]))
