from tcm_expert.core.config import AppSettings


def test_settings_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    expected = AppSettings(clinic_name="Phòng khám thử nghiệm")
    expected.save(path)
    assert AppSettings.load(path) == expected


def test_invalid_settings_are_quarantined(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{invalid", encoding="utf-8")
    settings = AppSettings.load(path)
    assert settings == AppSettings()
    assert list(tmp_path.glob("settings.invalid_*.json"))


def test_doctor_approval_cannot_be_disabled(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"clinic_name":"  ","require_doctor_approval":false}', encoding="utf-8")
    settings = AppSettings.load(path)
    assert settings.clinic_name == "Phòng khám Đông y"
    assert settings.require_doctor_approval is True
