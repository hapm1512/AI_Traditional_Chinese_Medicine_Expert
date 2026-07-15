import pytest

from tcm_expert.database.validation import ValidationError, bounded_number, choice


def test_bounded_number():
    assert bounded_number("0.5", "Độ tin cậy", 0, 1) == 0.5
    with pytest.raises(ValidationError):
        bounded_number(2, "Độ tin cậy", 0, 1)


def test_choice():
    assert choice("yin", "Âm dương", {"yin", "yang"}) == "yin"
    with pytest.raises(ValidationError):
        choice("invalid", "Âm dương", {"yin", "yang"})
