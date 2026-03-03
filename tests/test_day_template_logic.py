from __future__ import annotations

import pytest

from app.domain.enums import MarkKind
from app.services.template_models import MarkTypeOverview
from app.ui.templates.day_template_logic import (
    build_preset_45_10,
    build_timeline_rows,
    choose_default_break_mark,
    insert_break_between_teaching,
    summarize_timeline,
)


def _mark(
    *,
    mark_id: int,
    name: str,
    kind: MarkKind,
    duration: int,
) -> MarkTypeOverview:
    return MarkTypeOverview(
        id=mark_id,
        name=name,
        kind=kind,
        duration_minutes=duration,
        is_archived=False,
        used_in_day_templates=0,
    )


def test_build_timeline_rows_and_summary() -> None:
    teaching = _mark(mark_id=1, name="Pair 45", kind=MarkKind.TEACHING, duration=45)
    brk = _mark(mark_id=2, name="Break 10", kind=MarkKind.BREAK, duration=10)
    rows = build_timeline_rows(
        mark_type_ids=[1, 2, 1],
        mark_by_id={1: teaching, 2: brk},
    )
    summary = summarize_timeline(rows)

    assert len(rows) == 3
    assert rows[0].start_time == "08:30"
    assert rows[0].end_time == "09:15"
    assert rows[1].start_time == "09:15"
    assert rows[2].end_time == "10:10"
    assert summary.total_blocks == 3
    assert summary.teaching_blocks == 2
    assert summary.break_blocks == 1
    assert summary.total_minutes == 100
    assert summary.estimated_end_time == "10:10"


def test_insert_break_between_teaching() -> None:
    teaching = _mark(mark_id=1, name="Pair", kind=MarkKind.TEACHING, duration=45)
    brk = _mark(mark_id=2, name="Break", kind=MarkKind.BREAK, duration=10)
    result = insert_break_between_teaching(
        mark_type_ids=[1, 1, 2, 1, 1],
        mark_by_id={1: teaching, 2: brk},
        break_mark_id=2,
    )
    assert result == [1, 2, 1, 2, 1, 2, 1]


def test_choose_default_break_mark_prefers_10_minutes() -> None:
    break_15 = _mark(mark_id=3, name="Break 15", kind=MarkKind.BREAK, duration=15)
    break_10 = _mark(mark_id=4, name="Break 10", kind=MarkKind.BREAK, duration=10)
    assert choose_default_break_mark([break_15, break_10]) == 4


def test_build_preset_45_10_raises_when_no_break_exists() -> None:
    teaching = _mark(mark_id=1, name="Pair", kind=MarkKind.TEACHING, duration=45)
    with pytest.raises(ValueError):
        build_preset_45_10([teaching])
