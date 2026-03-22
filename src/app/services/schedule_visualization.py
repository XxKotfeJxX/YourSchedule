from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.domain.enums import MarkKind
from app.domain.models import CalendarPeriod, Requirement, ScheduleEntry, ScheduleScenarioEntry, TimeBlock


WEEKDAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(frozen=True)
class WeeklyGridRow:
    order_in_day: int
    slot_label: str
    cells: dict[int, str]


@dataclass(frozen=True)
class WeeklyScheduleGrid:
    week_start: date
    weekdays: list[date]
    rows: list[WeeklyGridRow]


class ScheduleVisualizationService:
    def build_weekly_grid(
        self,
        session: Session,
        calendar_period_id: int,
        week_start: date | None = None,
        resource_id: int | None = None,
        scenario_id: int | None = None,
    ) -> WeeklyScheduleGrid:
        period = session.get(CalendarPeriod, calendar_period_id)
        if period is None:
            raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")

        normalized_week_start = self._normalize_week_start(
            week_start=week_start,
            period_start=period.start_date,
        )
        week_dates = [normalized_week_start + timedelta(days=offset) for offset in range(7)]
        week_end = week_dates[-1]

        teaching_blocks = self._load_teaching_blocks(
            session=session,
            calendar_period_id=calendar_period_id,
            week_start=normalized_week_start,
            week_end=week_end,
        )

        if not teaching_blocks:
            return WeeklyScheduleGrid(
                week_start=normalized_week_start,
                weekdays=week_dates,
                rows=[],
            )

        block_by_key = {(block.date, block.order_in_day): block for block in teaching_blocks}
        time_label_by_order = self._build_time_label_map(teaching_blocks=teaching_blocks)
        schedule_cells = self._build_schedule_cells(
            session=session,
            calendar_period_id=calendar_period_id,
            week_start=normalized_week_start,
            week_end=week_end,
            block_by_key=block_by_key,
            resource_id=resource_id,
            company_id=period.company_id,
            scenario_id=scenario_id,
        )

        row_orders = sorted({block.order_in_day for block in teaching_blocks})
        rows: list[WeeklyGridRow] = []
        for slot_index, order in enumerate(row_orders, start=1):
            row_cells = {}
            for weekday in range(7):
                values = sorted(set(schedule_cells.get((order, weekday), [])))
                row_cells[weekday] = "\n".join(values)
            rows.append(
                WeeklyGridRow(
                    order_in_day=order,
                    slot_label=f"{slot_index}. {time_label_by_order.get(order, '')}".strip(),
                    cells=row_cells,
                )
            )

        return WeeklyScheduleGrid(
            week_start=normalized_week_start,
            weekdays=week_dates,
            rows=rows,
        )

    def _normalize_week_start(self, week_start: date | None, period_start: date) -> date:
        base = week_start or period_start
        return base - timedelta(days=base.weekday())

    def _load_teaching_blocks(
        self,
        session: Session,
        calendar_period_id: int,
        week_start: date,
        week_end: date,
    ) -> list[TimeBlock]:
        statement = (
            select(TimeBlock)
            .where(
                and_(
                    TimeBlock.calendar_period_id == calendar_period_id,
                    TimeBlock.block_kind == MarkKind.TEACHING,
                    TimeBlock.date >= week_start,
                    TimeBlock.date <= week_end,
                )
            )
            .order_by(TimeBlock.date.asc(), TimeBlock.order_in_day.asc())
        )
        return list(session.scalars(statement).all())

    def _build_time_label_map(self, teaching_blocks: list[TimeBlock]) -> dict[int, str]:
        labels: dict[int, str] = {}
        for block in teaching_blocks:
            if block.order_in_day in labels:
                continue
            labels[block.order_in_day] = (
                f"{block.start_timestamp.strftime('%H:%M')}"
                f"-{block.end_timestamp.strftime('%H:%M')}"
            )
        return labels

    def _build_schedule_cells(
        self,
        session: Session,
        calendar_period_id: int,
        week_start: date,
        week_end: date,
        block_by_key: dict[tuple[date, int], TimeBlock],
        resource_id: int | None,
        company_id: int | None,
        scenario_id: int | None,
    ) -> dict[tuple[int, int], list[str]]:
        cells: dict[tuple[int, int], list[str]] = defaultdict(list)

        if scenario_id is None:
            statement = (
                select(ScheduleEntry, Requirement.name, TimeBlock.date, TimeBlock.order_in_day)
                .join(TimeBlock, ScheduleEntry.start_block_id == TimeBlock.id)
                .join(Requirement, ScheduleEntry.requirement_id == Requirement.id)
                .where(
                    and_(
                        TimeBlock.calendar_period_id == calendar_period_id,
                        TimeBlock.date >= week_start,
                        TimeBlock.date <= week_end,
                    )
                )
                .order_by(TimeBlock.date.asc(), TimeBlock.order_in_day.asc())
            )
        else:
            statement = (
                select(ScheduleScenarioEntry, Requirement.name, TimeBlock.date, TimeBlock.order_in_day)
                .join(TimeBlock, ScheduleScenarioEntry.start_block_id == TimeBlock.id)
                .join(Requirement, ScheduleScenarioEntry.requirement_id == Requirement.id)
                .where(
                    and_(
                        ScheduleScenarioEntry.scenario_id == scenario_id,
                        TimeBlock.calendar_period_id == calendar_period_id,
                        TimeBlock.date >= week_start,
                        TimeBlock.date <= week_end,
                    )
                )
                .order_by(TimeBlock.date.asc(), TimeBlock.order_in_day.asc())
            )
        if company_id is not None:
            statement = statement.where(Requirement.company_id == company_id)
        if resource_id is not None:
            from app.domain.models import RequirementResource

            statement = statement.join(
                RequirementResource,
                RequirementResource.requirement_id == Requirement.id,
            ).where(RequirementResource.resource_id == resource_id)

        for entry, requirement_name, entry_date, start_order in session.execute(statement).all():
            entry_label = requirement_name
            if entry.is_manual:
                entry_label = f"{entry_label} [MAN]"
            elif entry.is_locked:
                entry_label = f"{entry_label} [LOCK]"
            for offset in range(entry.blocks_count):
                key = (entry_date, start_order + offset)
                block = block_by_key.get(key)
                if block is None:
                    continue
                cells[(block.order_in_day, block.date.weekday())].append(entry_label)

        return cells
