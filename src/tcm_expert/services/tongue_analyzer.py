from __future__ import annotations

import colorsys
import hashlib
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError


@dataclass(frozen=True)
class TongueAnalysisResult:
    image_sha256: str
    image_width: int
    image_height: int
    quality_score: float
    quality_issues: tuple[str, ...]
    segmentation_confidence: float
    tongue_color: str
    coating_color: str
    coating_thickness: str
    teeth_marks: bool
    cracks: bool
    ai_confidence: float
    metrics: dict[str, float]

    def as_dict(self) -> dict:
        return asdict(self)


class TongueAnalyzer:
    """Offline image screening; never returns a diagnosis."""

    def analyze(self, image_path: Path) -> TongueAnalysisResult:
        try:
            image = Image.open(image_path)
            image.verify()
            image = Image.open(image_path).convert("RGB")
        except (OSError, UnidentifiedImageError) as error:
            raise ValueError("Ảnh không hợp lệ hoặc không thể đọc") from error
        width, height = image.size
        quality, issues, sharpness, exposure = self._quality(image)
        pixels = self._tongue_pixels(image)
        minimum = max(200, width * height // 300)
        if len(pixels) < minimum:
            issues.append("Không nhận diện rõ vùng lưỡi")
            segmentation = min(0.25, len(pixels) / max(1, minimum) * 0.25)
        else:
            segmentation = max(0.35, min(0.96, 0.5 + len(pixels) / (width * height) * 2.2))
        metrics = self._metrics(pixels)
        confidence = max(0.0, min(1.0, quality * 0.42 + segmentation * 0.58))
        if issues:
            confidence *= 0.82
        return TongueAnalysisResult(
            hashlib.sha256(image_path.read_bytes()).hexdigest(), width, height,
            round(quality, 4), tuple(issues), round(segmentation, 4),
            self._tongue_color(metrics), self._coating_color(metrics),
            self._coating_thickness(metrics), metrics["edge_irregularity"] >= 0.24,
            metrics["dark_ratio"] >= 0.075 and sharpness >= 18,
            round(confidence, 4), {**metrics, "sharpness": sharpness, "exposure": exposure},
        )

    @staticmethod
    def _quality(image: Image.Image) -> tuple[float, list[str], float, float]:
        issues: list[str] = []
        gray = image.convert("L")
        exposure = ImageStat.Stat(gray).mean[0]
        sharpness = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).stddev[0]
        size_score = min(1.0, min(image.size) / 480)
        exposure_score = max(0.0, 1.0 - abs(exposure - 132) / 132)
        sharpness_score = min(1.0, sharpness / 34)
        if min(image.size) < 480:
            issues.append("Độ phân giải thấp")
        if exposure < 55:
            issues.append("Ảnh quá tối")
        elif exposure > 215:
            issues.append("Ảnh quá sáng")
        if sharpness < 14:
            issues.append("Ảnh mờ")
        score = size_score * 0.35 + exposure_score * 0.30 + sharpness_score * 0.35
        return round(score, 4), issues, round(sharpness, 3), round(exposure, 3)

    @staticmethod
    def _tongue_pixels(image: Image.Image) -> list[tuple[int, int, int]]:
        thumb = image.copy()
        thumb.thumbnail((640, 640))
        width, height = thumb.size
        result = []
        for y in range(height // 6, height * 11 // 12, 2):
            ny = (y - height * 0.55) / (height * 0.42)
            for x in range(width // 8, width * 7 // 8, 2):
                nx = (x - width * 0.5) / (width * 0.40)
                if nx * nx + ny * ny > 1:
                    continue
                rgb = thumb.getpixel((x, y))
                hue, saturation, value = colorsys.rgb_to_hsv(*(item / 255 for item in rgb))
                hue *= 360
                if (hue <= 28 or hue >= 340) and saturation >= 0.12 and value >= 0.18:
                    result.append(rgb)
        return result

    @staticmethod
    def _metrics(pixels: list[tuple[int, int, int]]) -> dict[str, float]:
        if not pixels:
            return dict.fromkeys(("red", "green", "blue", "saturation", "brightness",
                                  "pale_ratio", "dark_ratio", "edge_irregularity"), 0.0)
        count = len(pixels)
        red = sum(p[0] for p in pixels) / count
        green = sum(p[1] for p in pixels) / count
        blue = sum(p[2] for p in pixels) / count
        hsv = [colorsys.rgb_to_hsv(*(item / 255 for item in pixel)) for pixel in pixels]
        pale = sum(1 for r, g, _ in pixels if r > 150 and abs(r - g) < 55) / count
        dark = sum(1 for pixel in pixels if max(pixel) < 95) / count
        variance = math.sqrt(sum((r - red) ** 2 for r, _, _ in pixels) / count) / 255
        return {"red": round(red, 3), "green": round(green, 3), "blue": round(blue, 3),
                "saturation": round(sum(v[1] for v in hsv) / count, 4),
                "brightness": round(sum(v[2] for v in hsv) / count, 4),
                "pale_ratio": round(pale, 4), "dark_ratio": round(dark, 4),
                "edge_irregularity": round(variance, 4)}

    @staticmethod
    def _tongue_color(m: dict[str, float]) -> str:
        if m["brightness"] < 0.39:
            return "Tím sẫm"
        if m["pale_ratio"] > 0.48 or m["saturation"] < 0.22:
            return "Nhạt"
        return "Đỏ" if m["red"] - m["green"] > 72 else "Hồng"

    @staticmethod
    def _coating_color(m: dict[str, float]) -> str:
        if m["green"] > m["blue"] * 1.18 and m["brightness"] > 0.58:
            return "Vàng"
        return "Trắng" if m["brightness"] > 0.62 else "Ít/không rõ"

    @staticmethod
    def _coating_thickness(m: dict[str, float]) -> str:
        if m["pale_ratio"] > 0.55:
            return "Dày"
        return "Mỏng" if m["pale_ratio"] > 0.24 else "Ít/không rõ"
