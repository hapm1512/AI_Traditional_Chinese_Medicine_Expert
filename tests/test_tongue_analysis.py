from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from tcm_expert.database import (
    ConsultationRepository,
    DatabaseManager,
    PatientRepository,
    TongueAnalysisRepository,
)
from tcm_expert.services import TongueAnalyzer


@pytest.fixture
def database(tmp_path):
    manager = DatabaseManager(tmp_path / "test.db")
    manager.initialize()
    return manager


def sample_image(path: Path, color=(205, 88, 105)) -> Path:
    image = Image.new("RGB", (640, 640), (45, 45, 45))
    draw = ImageDraw.Draw(image)
    draw.ellipse((170, 115, 470, 585), fill=color, outline=(120, 30, 45), width=8)
    draw.line((320, 180, 320, 430), fill=(85, 34, 45), width=5)
    image.save(path)
    return path


def consultation(database):
    patient = PatientRepository(database).create({"code": "BN106", "full_name": "Nguyễn An"})
    return ConsultationRepository(database).create(patient["id"], "K-LUOI-01")


def test_offline_analyzer_returns_explainable_result(tmp_path):
    result = TongueAnalyzer().analyze(sample_image(tmp_path / "tongue.png"))
    assert result.image_width == 640
    assert result.tongue_color in {"Hồng", "Đỏ", "Nhạt", "Tím sẫm"}
    assert 0 <= result.quality_score <= 1
    assert 0 <= result.ai_confidence <= 1
    assert len(result.image_sha256) == 64
    assert result.metrics["red"] > result.metrics["green"]


def test_analyzer_rejects_invalid_image(tmp_path):
    invalid = tmp_path / "invalid.jpg"
    invalid.write_text("not an image", encoding="utf-8")
    with pytest.raises(ValueError, match="Ảnh không hợp lệ"):
        TongueAnalyzer().analyze(invalid)


def test_repository_preserves_ai_and_doctor_review(database, tmp_path):
    visit = consultation(database)
    path = sample_image(tmp_path / "tongue.png")
    result = TongueAnalyzer().analyze(path)
    repository = TongueAnalysisRepository(database)
    analysis_id = repository.create(visit["id"], str(path), result.as_dict())
    repository.review(
        analysis_id,
        {
            "tongue_color": "Đỏ",
            "coating_color": "Trắng",
            "coating_thickness": "Mỏng",
            "teeth_marks": True,
            "cracks": False,
            "reviewed_by": "Bác sĩ An",
            "note": "Đã đối chiếu ảnh gốc",
        },
    )
    stored = repository.get(analysis_id)
    assert stored["image_sha256"] == result.image_sha256
    assert stored["doctor_tongue_color"] == "Đỏ"
    assert stored["reviewed_by"] == "Bác sĩ An"
    assert stored["reviewed_at"]
