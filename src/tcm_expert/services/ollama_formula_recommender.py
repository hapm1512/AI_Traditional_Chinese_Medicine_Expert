from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from tcm_expert.database.manager import DatabaseManager
from tcm_expert.services.formula_recommender import FormulaRecommender
from tcm_expert.services.ollama_formula_translator import DEFAULT_QWEN_MODEL, OllamaLocalChat


@dataclass(frozen=True)
class FormulaRecommendationOutcome:
    result: dict[str, Any]
    source: str
    model: str
    fallback_reason: str = ""


class OllamaFormulaRecommender:
    """Qwen reranks approved catalogue formulas; it never creates a prescription."""

    def __init__(
        self,
        database: DatabaseManager,
        chat: OllamaLocalChat | None = None,
        model: str = DEFAULT_QWEN_MODEL,
    ):
        self.database = database
        self.model = model
        self.chat = chat or OllamaLocalChat(model=model, timeout=120)
        self.rules = FormulaRecommender(database)

    def recommend(self, consultation_id: int, limit: int = 3) -> FormulaRecommendationOutcome:
        baseline = self.rules.recommend(consultation_id, limit=20, confirmed_only=True)
        if not baseline["eligible"] or not baseline["recommendations"]:
            return FormulaRecommendationOutcome(baseline, "rules", self.model)
        try:
            raw = self.chat._chat(self._prompt(baseline))
            selected = self._parse(raw, baseline["recommendations"], limit)
            if not selected:
                raise RuntimeError("Qwen chưa chọn bài thuốc hợp lệ trong danh mục")
            result = {**baseline, "recommendations": selected}
            return FormulaRecommendationOutcome(result, "ollama", self.model)
        except Exception as error:
            fallback = {**baseline, "recommendations": baseline["recommendations"][:limit]}
            return FormulaRecommendationOutcome(fallback, "rules", self.model, str(error))

    @staticmethod
    def _prompt(baseline: dict[str, Any]) -> str:
        candidates = [
            {
                "code": item["code"],
                "name": item["name"],
                "treatment_principle": item.get("treatment_principle", ""),
                "indications": item.get("indications", ""),
                "rule_matches": item.get("matched", []),
                "has_safety_alert": bool(item.get("safety")),
            }
            for item in baseline["recommendations"]
        ]
        return (
            "Bạn là trợ lý tra cứu bài thuốc Đông y cho bác sĩ. Chỉ xếp hạng bài thuốc "
            "trong DANH_MUC theo PHAP_TRI đã được bác sĩ xác nhận. Không tạo bài thuốc mới, "
            "không kê đơn, không đưa liều dùng, không gia giảm và không phê duyệt. "
            "Trả duy nhất JSON dạng {\"suggestions\":[{\"code\":\"...\","
            "\"reason\":\"...\"}]}; tối đa 3 mục. reason chỉ giải thích ngắn sự phù hợp.\n"
            f"PHAP_TRI={json.dumps(baseline['principles'], ensure_ascii=False)}\n"
            f"DANH_MUC={json.dumps(candidates, ensure_ascii=False)}"
        )

    @staticmethod
    def _parse(
        raw: str, candidates: list[dict[str, Any]], limit: int
    ) -> list[dict[str, Any]]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]).strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError("Qwen không trả JSON bài thuốc hợp lệ") from error
        suggestions = payload.get("suggestions", []) if isinstance(payload, dict) else []
        if not isinstance(suggestions, list):
            raise RuntimeError("Qwen trả danh sách bài thuốc không hợp lệ")
        by_code = {str(item["code"]): item for item in candidates}
        results: list[dict[str, Any]] = []
        used: set[str] = set()
        for suggestion in suggestions:
            if not isinstance(suggestion, dict):
                continue
            code = str(suggestion.get("code", "")).strip()
            if code not in by_code or code in used:
                continue
            reason = str(suggestion.get("reason", "")).strip()
            item = {**by_code[code], "ai_reason": reason, "review_required": True}
            results.append(item)
            used.add(code)
            if len(results) >= limit:
                break
        return results
