import time

from tcm_expert import __version__
from tcm_expert.database import DatabaseManager, ReferenceRepository
from tcm_expert.services.syndrome_reasoner import suggest


def test_stable_version():
    assert __version__ == "4.1.0"


def test_reference_initialization_performance(tmp_path):
    database = DatabaseManager(tmp_path / "performance.db")
    started = time.perf_counter()
    database.initialize()
    elapsed = time.perf_counter() - started
    assert database.health_check()
    assert elapsed < 5.0


def test_reasoning_is_transparent_and_bounded(tmp_path):
    database = DatabaseManager(tmp_path / "reasoning.db")
    database.initialize()
    syndromes = ReferenceRepository(database).list("tcm_syndromes")
    results = suggest("Mệt, ăn ít, đại tiện lỏng, lưỡi nhạt", syndromes)
    assert results
    assert results[0]["matched"]
    assert 0.0 < results[0]["confidence"] <= 0.95
    assert results[0]["organ_systems"] == "Tỳ"
    assert results[0]["review_required"] is True


def test_empty_input_never_infers_a_syndrome(tmp_path):
    database = DatabaseManager(tmp_path / "empty.db")
    database.initialize()
    syndromes = ReferenceRepository(database).list("tcm_syndromes")
    assert suggest("", syndromes) == []
