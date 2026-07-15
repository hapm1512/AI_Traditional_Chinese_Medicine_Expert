from __future__ import annotations

import hashlib
import math
import struct
import wave
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioAnalysisResult:
    audio_sha256: str
    duration_seconds: float
    sample_rate: int
    channels: int
    quality_score: float
    quality_issues: tuple[str, ...]
    rms_level: float
    peak_level: float
    zero_crossing_rate: float
    dominant_frequency: float
    pattern_label: str
    ai_confidence: float
    metrics: dict[str, float]

    def as_dict(self) -> dict:
        return asdict(self)


class AudioAnalyzer:
    """Offline WAV screening. Results describe signals, never diagnose disease."""

    def analyze(self, path: Path, sample_type: str) -> AudioAnalysisResult:
        if sample_type not in {"voice", "cough", "breathing", "other"}:
            raise ValueError("Loại mẫu âm thanh không hợp lệ")
        try:
            with wave.open(str(path), "rb") as source:
                channels = source.getnchannels()
                sample_width = source.getsampwidth()
                sample_rate = source.getframerate()
                frame_count = source.getnframes()
                if sample_width != 2:
                    raise ValueError("Chỉ hỗ trợ WAV PCM 16-bit")
                raw = source.readframes(frame_count)
        except (OSError, EOFError, wave.Error) as error:
            raise ValueError("Tệp WAV không hợp lệ hoặc không thể đọc") from error
        if channels < 1 or channels > 2 or sample_rate <= 0 or frame_count <= 0:
            raise ValueError("Tệp WAV không chứa âm thanh hợp lệ")
        values = struct.unpack(f"<{len(raw) // 2}h", raw)
        mono = values[::channels]
        duration = frame_count / sample_rate
        peak = max(abs(value) for value in mono) / 32768
        rms = math.sqrt(sum(value * value for value in mono) / len(mono)) / 32768
        crossings = sum(
            1 for left, right in zip(mono, mono[1:], strict=False) if (left < 0) != (right < 0)
        )
        zcr = crossings / max(1, len(mono) - 1)
        dominant = self._dominant_frequency(mono, sample_rate)
        issues: list[str] = []
        if duration < 0.5:
            issues.append("Bản ghi quá ngắn")
        if rms < 0.008:
            issues.append("Âm lượng quá nhỏ")
        if peak >= 0.98:
            issues.append("Có nguy cơ vỡ tiếng")
        if sample_rate < 16000:
            issues.append("Tần số lấy mẫu thấp")
        duration_score = min(1.0, duration / 2)
        level_score = min(1.0, rms / 0.06) if rms < 0.06 else max(0.35, 1 - (rms - 0.06) * 2)
        rate_score = min(1.0, sample_rate / 44100)
        quality = max(0.0, min(1.0, duration_score * 0.3 + level_score * 0.4 + rate_score * 0.3))
        if peak >= 0.98:
            quality *= 0.65
        label = self._label(sample_type, rms, zcr, dominant)
        confidence = quality * (0.72 if sample_type != "other" else 0.55)
        return AudioAnalysisResult(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            round(duration, 4),
            sample_rate,
            channels,
            round(quality, 4),
            tuple(issues),
            round(rms, 6),
            round(peak, 6),
            round(zcr, 6),
            round(dominant, 2),
            label,
            round(confidence, 4),
            {"frames": float(frame_count), "sample_width": float(sample_width)},
        )

    @staticmethod
    def _dominant_frequency(samples: tuple[int, ...], sample_rate: int) -> float:
        # Autocorrelation-lite estimate; bounded for responsive offline screening.
        stride = max(1, len(samples) // 12000)
        signal = samples[::stride]
        effective_rate = sample_rate / stride
        if len(signal) < 80:
            return 0.0
        minimum_lag = max(2, int(effective_rate / 1000))
        maximum_lag = min(len(signal) // 3, int(effective_rate / 60))
        best_lag, best_score = 0, 0
        for lag in range(minimum_lag, maximum_lag + 1):
            score = sum(signal[index] * signal[index + lag] for index in range(len(signal) - lag))
            if score > best_score:
                best_lag, best_score = lag, score
        return effective_rate / best_lag if best_lag else 0.0

    @staticmethod
    def _label(sample_type: str, rms: float, zcr: float, frequency: float) -> str:
        if sample_type == "voice":
            if frequency and frequency < 120:
                return "Giọng trầm"
            return "Giọng cao" if frequency > 230 else "Giọng trung bình"
        if sample_type == "cough":
            return "Ho mạnh/khô" if zcr > 0.12 or rms > 0.12 else "Ho nhẹ/đục"
        if sample_type == "breathing":
            return "Hơi thở nhiễu" if zcr > 0.16 else "Hơi thở tương đối đều"
        return "Mẫu âm thanh chưa phân loại"
