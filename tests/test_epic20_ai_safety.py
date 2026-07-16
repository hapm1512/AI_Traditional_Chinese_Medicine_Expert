import pytest

from tcm_expert.ai.validation import (
    AIValidationError,
    assess_input_quality,
    normalize_evidence,
    validate_ai_output,
)
from tcm_expert.ai.factory import test_ai_connections as check_ai_connections
from tcm_expert.database import DatabaseManager


def test_input_quality_threshold():
    low = assess_input_quality({"completeness_score": 0.49, "missing_data": ["Thiết chẩn"]})
    assert low.acceptable is False
    assert low.missing == ("Thiết chẩn",)
    assert assess_input_quality({"completeness_score": 0.50}).acceptable is True


def test_sources_are_normalized_and_deduplicated():
    rows = [{"source": "  OpenTCM   A  "}, {"source": "OpenTCM A"}, {"title": "TCMBank"}]
    assert normalize_evidence(rows) == ("OpenTCM A", "TCMBank")


def test_unsafe_dose_is_blocked():
    with pytest.raises(AIValidationError):
        validate_ai_output("Đơn thuốc: dùng 10 g mỗi ngày", ("Nguồn kiểm chứng",))


def test_offline_module_status(tmp_path):
    database = DatabaseManager(tmp_path / "epic20.db")
    database.initialize()
    rows = check_ai_connections(database)
    assert rows[0]["name"] == "Rule Engine"
    assert rows[0]["status"] == "Sẵn sàng"

