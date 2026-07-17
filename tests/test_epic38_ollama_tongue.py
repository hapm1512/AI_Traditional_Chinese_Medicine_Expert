import json
from pathlib import Path

from PIL import Image, ImageDraw

from tcm_expert.services.ollama_tongue_analyzer import OllamaTongueAnalyzer


def sample_image(path: Path) -> Path:
    image = Image.new("RGB", (640, 640), (45, 45, 45))
    draw = ImageDraw.Draw(image)
    draw.ellipse((170, 115, 470, 585), fill=(205, 88, 105))
    image.save(path)
    return path


def test_ollama_vision_result_is_constrained(tmp_path):
    def transport(_url, payload, _timeout):
        assert payload["messages"][0]["images"]
        return {"message": {"content": json.dumps({
            "tongue_color": "Đỏ",
            "coating_color": "Trắng",
            "coating_thickness": "Mỏng",
            "teeth_marks": True,
            "cracks": False,
            "confidence": 0.82,
            "observation": "Lưỡi đỏ, rêu trắng mỏng.",
        }, ensure_ascii=False)}}

    outcome = OllamaTongueAnalyzer(transport=transport).analyze(
        sample_image(tmp_path / "tongue.png")
    )
    assert outcome.source == "ollama"
    assert outcome.result.tongue_color == "Đỏ"
    assert outcome.result.metrics["analysis_source"] == "ollama_vision"
    assert outcome.result.ai_confidence <= 0.82


def test_ollama_failure_uses_offline_fallback(tmp_path):
    def transport(_url, _payload, _timeout):
        raise RuntimeError("Ollama chưa chạy")

    outcome = OllamaTongueAnalyzer(transport=transport).analyze(
        sample_image(tmp_path / "tongue.png")
    )
    assert outcome.source == "offline"
    assert outcome.fallback_reason == "Ollama chưa chạy"
    assert outcome.result.metrics["analysis_source"] == "offline"
