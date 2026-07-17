from __future__ import annotations

import base64
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from tcm_expert.services.ollama_formula_translator import OLLAMA_URL, _ollama_transport
from tcm_expert.services.tongue_analyzer import TongueAnalysisResult, TongueAnalyzer

DEFAULT_VISION_MODEL = "qwen2.5vl:7b"


@dataclass(frozen=True)
class TongueAnalysisOutcome:
    result: TongueAnalysisResult
    source: str
    model: str
    fallback_reason: str = ""


class OllamaTongueAnalyzer:
    """Ollama Vision screening with a deterministic offline fallback."""

    def __init__(self, model: str = DEFAULT_VISION_MODEL, timeout: float = 180, transport=None):
        self.model = model
        self.timeout = timeout
        self.transport = transport or _ollama_transport
        self.offline = TongueAnalyzer()

    def analyze(self, image_path: Path) -> TongueAnalysisOutcome:
        baseline = self.offline.analyze(image_path)
        try:
            payload = self.transport(
                f"{OLLAMA_URL}/api/chat",
                {
                    "model": self.model,
                    "messages": [{
                        "role": "user",
                        "content": self._prompt(),
                        "images": [base64.b64encode(image_path.read_bytes()).decode("ascii")],
                    }],
                    "stream": False,
                    "format": "json",
                    "keep_alive": "10m",
                    "options": {"temperature": 0, "num_predict": 700},
                },
                self.timeout,
            )
            raw = str(payload["message"]["content"])
            values = self._parse(raw)
            confidence = min(baseline.ai_confidence, values["confidence"])
            result = replace(
                baseline,
                tongue_color=values["tongue_color"],
                coating_color=values["coating_color"],
                coating_thickness=values["coating_thickness"],
                teeth_marks=values["teeth_marks"],
                cracks=values["cracks"],
                ai_confidence=round(confidence, 4),
                metrics={
                    **baseline.metrics,
                    "analysis_source": "ollama_vision",
                    "vision_model": self.model,
                    "vision_observation": values["observation"],
                },
            )
            return TongueAnalysisOutcome(result, "ollama", self.model)
        except Exception as error:
            result = replace(
                baseline,
                metrics={
                    **baseline.metrics,
                    "analysis_source": "offline",
                    "vision_model": self.model,
                    "fallback_reason": str(error),
                },
            )
            return TongueAnalysisOutcome(result, "offline", self.model, str(error))

    @staticmethod
    def _prompt() -> str:
        return (
            "Bạn hỗ trợ bác sĩ mô tả ảnh lưỡi Đông y. Chỉ mô tả đặc điểm "
            "nhìn thấy; không chẩn đoán, không suy luận bệnh, không kê đơn. "
            "Nếu ảnh không rõ, giảm "
            "confidence. Trả duy nhất JSON: {\"tongue_color\":\"Hồng|Nhạt|Đỏ|Tím sẫm|"
            "Không rõ\",\"coating_color\":\"Trắng|Vàng|Ít/không rõ|Không rõ\","
            "\"coating_thickness\":\"Mỏng|Dày|Ít/không rõ|Không rõ\","
            "\"teeth_marks\":false,\"cracks\":false,\"confidence\":0.0,"
            "\"observation\":\"mô tả ngắn\"}."
        )

    @staticmethod
    def _parse(raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = "\n".join(text.splitlines()[1:-1]).strip()
        try:
            value = json.loads(text)
        except json.JSONDecodeError as error:
            raise RuntimeError("AI ảnh không trả JSON hợp lệ") from error
        if not isinstance(value, dict):
            raise RuntimeError("AI ảnh trả kết quả không hợp lệ")
        allowed = {
            "tongue_color": {"Hồng", "Nhạt", "Đỏ", "Tím sẫm", "Không rõ"},
            "coating_color": {"Trắng", "Vàng", "Ít/không rõ", "Không rõ"},
            "coating_thickness": {"Mỏng", "Dày", "Ít/không rõ", "Không rõ"},
        }
        result: dict[str, Any] = {}
        for field, choices in allowed.items():
            item = str(value.get(field, "Không rõ")).strip()
            result[field] = item if item in choices else "Không rõ"
        result["teeth_marks"] = value.get("teeth_marks") is True
        result["cracks"] = value.get("cracks") is True
        try:
            result["confidence"] = max(0.0, min(0.95, float(value.get("confidence", 0))))
        except (TypeError, ValueError):
            result["confidence"] = 0.0
        result["observation"] = str(value.get("observation", "")).strip()[:1000]
        return result
