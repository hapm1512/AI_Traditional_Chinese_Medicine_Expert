from tcm_expert.core.config import AppSettings


def test_settings_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    expected = AppSettings(clinic_name="Phòng khám thử nghiệm")
    expected.save(path)
    assert AppSettings.load(path) == expected
