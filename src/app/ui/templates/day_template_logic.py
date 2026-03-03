from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from app.domain.enums import MarkKind
from app.services.template_models import MarkTypeOverview


@dataclass(frozen=True)
class TimelineRow:
    order_index: int
    start_time: str
    end_time: str
    mark_type_id: int
    mark_name: str
    kind: MarkKind
    duration_minutes: int


@dataclass(frozen=True)
class TimelineSummary:
    total_blocks: int
    teaching_blocks: int
    break_blocks: int
    total_minutes: int
    estimated_end_time: str


def build_timeline_rows(
    *,
    mark_type_ids: list[int],
    mark_by_id: dict[int, MarkTypeOverview],
    start_time: time = time(hour=8, minute=30),
) -> list[TimelineRow]:
    rows: list[TimelineRow] = []
    cursor = datetime.combine(datetime.today(), start_time)
    for index, mark_type_id in enumerate(mark_type_ids, start=1):
        mark_type = mark_by_id.get(mark_type_id)
        if mark_type is None:
            continue
        row_start = cursor
        row_end = row_start + timedelta(minutes=mark_type.duration_minutes)
        rows.append(
            TimelineRow(
                order_index=index,
                start_time=row_start.strftime("%H:%M"),
                end_time=row_end.strftime("%H:%M"),
                mark_type_id=mark_type.id,
                mark_name=mark_type.name,
                kind=mark_type.kind,
                duration_minutes=mark_type.duration_minutes,
            )
        )
        cursor = row_end
    return rows


def summarize_timeline(rows: list[TimelineRow]) -> TimelineSummary:
    teaching = sum(1 for row in rows if row.kind == MarkKind.TEACHING)
    breaks = sum(1 for row in rows if row.kind == MarkKind.BREAK)
    total_minutes = sum(row.duration_minutes for row in rows)
    end_time = rows[-1].end_time if rows else "08:30"
    return TimelineSummary(
        total_blocks=len(rows),
        teaching_blocks=teaching,
        break_blocks=breaks,
        total_minutes=total_minutes,
        estimated_end_time=end_time,
    )


def choose_default_break_mark(mark_types: list[MarkTypeOverview]) -> int | None:
    break_marks = [item for item in mark_types if item.kind == MarkKind.BREAK]
    if not break_marks:
        return None
    break_marks.sort(key=lambda item: (abs(item.duration_minutes - 10), item.duration_minutes, item.id))
    return break_marks[0].id


def insert_break_between_teaching(
    *,
    mark_type_ids: list[int],
    mark_by_id: dict[int, MarkTypeOverview],
    break_mark_id: int,
) -> list[int]:
    result: list[int] = []
    previous_kind: MarkKind | None = None
    for mark_id in mark_type_ids:
        current = mark_by_id.get(mark_id)
        current_kind = current.kind if current is not None else None
        if previous_kind == MarkKind.TEACHING and current_kind == MarkKind.TEACHING:
            result.append(break_mark_id)
        result.append(mark_id)
        previous_kind = current_kind
    return result


def build_preset_45_10(mark_types: list[MarkTypeOverview]) -> list[int]:
    teaching_45 = next(
        (item for item in mark_types if item.kind == MarkKind.TEACHING and item.duration_minutes == 45),
        None,
    )
    break_10 = next(
        (item for item in mark_types if item.kind == MarkKind.BREAK and item.duration_minutes == 10),
        None,
    )
    if teaching_45 is None:
        teaching_45 = next((item for item in mark_types if item.kind == MarkKind.TEACHING), None)
    if break_10 is None:
        break_10 = next((item for item in mark_types if item.kind == MarkKind.BREAK), None)

    if teaching_45 is None:
        raise ValueError("Немає жодного блоку навчання для пресету.")
    if break_10 is None:
        raise ValueError("Немає жодного блоку перерви для пресету.")
    return [teaching_45.id, break_10.id, teaching_45.id, teaching_45.id]
