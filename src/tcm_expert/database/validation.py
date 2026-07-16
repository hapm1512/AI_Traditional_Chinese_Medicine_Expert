import re
from datetime import date
from typing import Any


class ValidationError(ValueError):
    """Raised when clinical database input is invalid."""


def required_text(value: Any, field: str, maximum: int = 255) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValidationError(f"{field} không được để trống")
    if len(text) > maximum:
        raise ValidationError(f"{field} vượt quá {maximum} ký tự")
    return text


def optional_text(value: Any, maximum: int = 2000) -> str:
    text = str(value or "").strip()
    if len(text) > maximum:
        raise ValidationError(f"Nội dung vượt quá {maximum} ký tự")
    return text


def iso_date(value: Any, field: str = "Ngày") -> str | None:
    if value in (None, ""):
        return None
    try:
        parsed = date.fromisoformat(str(value))
    except ValueError as error:
        raise ValidationError(f"{field} phải theo định dạng YYYY-MM-DD") from error
    if parsed > date.today():
        raise ValidationError(f"{field} không được ở tương lai")
    return parsed.isoformat()


def patient_code(value: Any) -> str:
    code = required_text(value, "Mã bệnh nhân", 32).upper()
    if not re.fullmatch(r"[A-Z0-9_-]+", code):
        raise ValidationError("Mã bệnh nhân chỉ gồm chữ, số, _ hoặc -")
    return code


def exact_digits(value: Any, field: str, length: int, optional: bool = True) -> str:
    text = str(value or "").strip()
    if optional and not text:
        return ""
    if not re.fullmatch(rf"\d{{{length}}}", text):
        raise ValidationError(f"{field} phải đúng {length} chữ số")
    return text


def choice(value: Any, field: str, allowed: set[str]) -> str:
    text = str(value or "")
    if text not in allowed:
        raise ValidationError(f"{field} không hợp lệ")
    return text


def bounded_number(value: Any, field: str, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValidationError(f"{field} phải là số") from error
    if not minimum <= number <= maximum:
        raise ValidationError(f"{field} phải từ {minimum} đến {maximum}")
    return number
