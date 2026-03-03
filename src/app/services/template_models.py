from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import MarkKind


WEEKDAY_LABELS_UA = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Нд",
}


@dataclass(frozen=True)
class DayTemplatePreview:
    total_blocks: int
    teaching_blocks: int
    break_blocks: int
    total_minutes: int
    estimated_end_time: str


@dataclass(frozen=True)
class WeekTemplatePreview:
    assigned_days: int
    unique_day_templates: int
    total_blocks: int
    teaching_blocks: int
    break_blocks: int
    total_minutes: int


@dataclass(frozen=True)
class MarkTypeOverview:
    id: int
    name: str
    kind: MarkKind
    duration_minutes: int
    is_archived: bool
    used_in_day_templates: int


@dataclass(frozen=True)
class DayTemplateOverview:
    id: int
    name: str
    mark_type_ids: tuple[int, ...]
    is_archived: bool
    used_in_week_templates: int
    preview: DayTemplatePreview


@dataclass(frozen=True)
class WeekTemplateOverview:
    id: int
    name: str
    weekday_to_day_template_id: dict[int, int]
    weekday_to_day_template_name: dict[int, str]
    is_archived: bool
    used_in_calendar_periods: int
    preview: WeekTemplatePreview


@dataclass(frozen=True)
class TemplatesOverview:
    mark_types: list[MarkTypeOverview]
    day_templates: list[DayTemplateOverview]
    week_templates: list[WeekTemplateOverview]

