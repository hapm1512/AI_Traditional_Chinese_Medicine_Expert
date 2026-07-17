from datetime import date

import pytest

from tcm_expert.ui.patient_page import parse_birth_date


def test_manual_birth_date_converts_to_iso():
    assert parse_birth_date("20/05/1988") == "1988-05-20"


def test_manual_birth_date_is_optional():
    assert parse_birth_date("__/__/____") == ""


@pytest.mark.parametrize("value", ("31/02/2000", "2000-02-20", "1/1/2000"))
def test_manual_birth_date_rejects_invalid_format(value):
    with pytest.raises(ValueError, match="dd/mm/yyyy"):
        parse_birth_date(value)


def test_manual_birth_date_rejects_future_date():
    future = date.today().replace(year=date.today().year + 1).strftime("%d/%m/%Y")
    with pytest.raises(ValueError, match="tương lai"):
        parse_birth_date(future)
