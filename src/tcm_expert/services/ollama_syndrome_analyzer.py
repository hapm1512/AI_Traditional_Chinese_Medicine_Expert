from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from tcm_expert.services.ollama_formula_translator import (
    DEFAULT_QWEN_MODEL,
    OllamaLocalChat,
)
from tcm_expert.services.syndrome_reasoner import ORGAN_BY_CODE, suggest


@dataclass(frozen=True)
class SyndromeAnalysisOutcome:
    results: list[dict[str, Any]]
    source: str
    model: str
    fallback_reason: str = ""


class OllamaSyndromeAnalyzer:
    """Local Qwen analysis constrained to the approved syndrome catalogue."""

    def __init__(
        self,
        chat: OllamaLocalChat | None = None,
        model: str = DEFAULT_QWEN_MODEL,
    ):
        self.model = model
        self.chat = chat or OllamaLocalChat(model=model, timeout=120)

    def analyze(
        self, clinical_text: str, syndromes: list[dict[str, Any]]
    ) -> SyndromeAnalysisOutcome:
        text = str(clinical_text or "").strip()
        if not text:
            return SyndromeAnalysisOutcome([], "rules", self.model, "Hồ sơ Tứ chẩn trống")
        try:
            raw = self.chat._chat(self._prompt(text, syndromes))
            results = self._parse(raw, text, syndromes)
            if not results:
                raise RuntimeError("Qwen chưa đưa ra gợi ý có căn cứ hợp lệ")
            return SyndromeAnalysisOutcome(results, "ollama", self.model)
        except Exception as error:
            return SyndromeAnalysisOutcome(
                suggest(text, syndromes), "rules", self.model, str(error)
            )

    def _prompt(self, clinical_text: str, syndromes: list[dict[str, Any]]) -> str:
        catalogue = [
            {
                "code": item["code"],
                "name": item["name"],
                "eight_principles": item.get("eight_principles", ""),
                "pathogenesis": item.get("pathogenesis", ""),
                "treatment_principle": item.get("treatment_principle", ""),
            }
            for item in syndromes
        ]
        return (
            "Bạn là trợ lý phân tích Đông y cho bác sĩ. Chỉ phân tích dữ liệu Tứ chẩn "
            "được cung cấp, không chẩn đoán xác định, không kê đơn, không tạo liều dùng. "
            "Chỉ được chọn code trong DANH_MUC. Mỗi evidence phải là cụm từ xuất hiện "
            "nguyên văn trong HO_SO. Không suy đoán dữ liệu còn thiếu. Trả duy nhất JSON "
            "object dạng {\"suggestions\":[{\"code\":\"...\",\"confidence\":0.0," 
            "\"evidence\":[\"...\"]}]}; tối đa 5 gợi ý, confidence từ 0 đến 1.\n"
            f"DANH_MUC={json.dumps(catalogue, ensure_ascii=False)}\n"
            f"HO_SO={json.dumps(clinical_text, ensure_ascii=False)}"
        )

    @classmethod
    def _parse(
        cls, raw: str, clinical_text: str, syndromes: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError("Qwen không trả JSON phân tích hợp lệ") from error
        suggestions = payload.get("suggestions", []) if isinstance(payload, dict) else []
        if not isinstance(suggestions, list):
            raise RuntimeError("Qwen trả danh sách phân tích không hợp lệ")
        by_code = {str(item["code"]): item for item in syndromes}
        normalised_source = cls._normalise(clinical_text)
        results: list[dict[str, Any]] = []
        used: set[str] = set()
        for suggestion in suggestions[:5]:
            if not isinstance(suggestion, dict):
                continue
            code = str(suggestion.get("code", "")).strip()
            if code not in by_code or code in used:
                continue
            evidence_values = suggestion.get("evidence", [])
            if not isinstance(evidence_values, list):
                continue
            evidence = []
            for value in evidence_values:
                item = str(value).strip()
                if item and cls._normalise(item) in normalised_source:
                    evidence.append(item)
            if not evidence:
                continue
            try:
                confidence = float(suggestion.get("confidence", 0))
            except (TypeError, ValueError):
                confidence = 0
            confidence = max(0.0, min(0.95, confidence))
            syndrome = by_code[code]
            results.append(
                {
                    **syndrome,
                    "confidence": confidence,
                    "matched": evidence,
                    "evidence_count": len(evidence),
                    "evidence_total": len(evidence),
                    "organ_systems": ORGAN_BY_CODE.get(code, "Chưa xác định"),
                    "review_required": True,
                    "analysis_source": "ollama",
                }
            )
            used.add(code)
        return sorted(results, key=lambda item: (-item["confidence"], item["name"]))

    @staticmethod
    def _normalise(value: str) -> str:
        value = unicodedata.normalize("NFC", value).casefold()
        return re.sub(r"\s+", " ", value).strip()
