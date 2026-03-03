from app.ui.profile_data import LANGUAGE_OPTIONS, all_timezones


def test_language_options_have_broad_coverage() -> None:
    assert len(LANGUAGE_OPTIONS) >= 30
    codes = {code for code, _label in LANGUAGE_OPTIONS}
    assert "uk" in codes
    assert "en" in codes


def test_all_timezones_returns_non_empty_list() -> None:
    values = all_timezones()
    assert values
    assert "UTC" in values or "Etc/UTC" in values
