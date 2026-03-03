from __future__ import annotations

from app.ui.templates.text_utils import truncate_text


def test_truncate_text_keeps_short_value() -> None:
    assert truncate_text("Break", 10) == "Break"


def test_truncate_text_trims_whitespace() -> None:
    assert truncate_text("  Teaching block  ", 20) == "Teaching block"


def test_truncate_text_adds_ellipsis_for_long_value() -> None:
    result = truncate_text("VeryLongTemplateNameForCard", 12)
    assert result == "VeryLongT..."
    assert len(result) == 12


def test_truncate_text_with_small_limit_has_no_ellipsis() -> None:
    assert truncate_text("Template", 3) == "Tem"
