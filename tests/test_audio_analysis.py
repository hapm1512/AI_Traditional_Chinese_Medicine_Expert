import math
import struct
import wave

import pytest

from tcm_expert.database import (
    AudioAnalysisRepository,
    ConsultationRepository,
    DatabaseManager,
    PatientRepository,
)
from tcm_expert.services import AudioAnalyzer


def sample_wav(path, seconds=1.0, frequency=180, amplitude=9000, rate=16000):
    frames = [
        int(amplitude * math.sin(2 * math.pi * frequency * index / rate))
        for index in range(int(rate * seconds))
    ]
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(rate)
        target.writeframes(struct.pack(f"<{len(frames)}h", *frames))
    return path


@pytest.fixture
def database(tmp_path):
    manager = DatabaseManager(tmp_path / "test.db")
    manager.initialize()
    return manager


def consultation(database):
    patient = PatientRepository(database).create({"code": "BN-AUDIO", "full_name": "Nguyễn An"})
    return ConsultationRepository(database).create(patient["id"], "K-AUDIO-01")


def test_audio_analyzer_extracts_features(tmp_path):
    result = AudioAnalyzer().analyze(sample_wav(tmp_path / "voice.wav"), "voice")
    assert result.duration_seconds == 1
    assert result.sample_rate == 16000
    assert result.rms_level > 0
    assert 150 <= result.dominant_frequency <= 210
    assert result.pattern_label == "Giọng trung bình"
    assert 0 <= result.ai_confidence <= 1


def test_audio_analyzer_rejects_invalid_file(tmp_path):
    invalid = tmp_path / "bad.wav"
    invalid.write_text("invalid", encoding="utf-8")
    with pytest.raises(ValueError, match="WAV không hợp lệ"):
        AudioAnalyzer().analyze(invalid, "cough")


def test_repository_keeps_ai_manual_and_review(database, tmp_path):
    visit = consultation(database)
    result = AudioAnalyzer().analyze(sample_wav(tmp_path / "cough.wav"), "cough")
    repository = AudioAnalysisRepository(database)
    analysis_id = repository.create(
        visit["id"], "cough", str(tmp_path / "cough.wav"), result.as_dict()
    )
    manual_id = repository.create_manual(visit["id"], "cough", "Ho khan từng cơn")
    repository.review(analysis_id, "Bác sĩ An", "Ho khô", "Đã nghe lại")
    stored = repository.get(analysis_id)
    assert stored["audio_sha256"] == result.audio_sha256
    assert stored["doctor_pattern_label"] == "Ho khô"
    assert repository.get(manual_id)["manual_characteristic"] == "Ho khan từng cơn"
