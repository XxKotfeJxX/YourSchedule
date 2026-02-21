from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.domain.models import CalendarPeriod, DayPatternItem, TimeBlock


class TimeBlockGeneratorService:
    def __init__(self, day_start_time: time = time(hour=8, minute=30)) -> None:
        self.day_start_time = day_start_time

    def generate_for_period(
        self,
        session: Session,
        calendar_period_id: int,
        replace_existing: bool = True,
    ) -> list[TimeBlock]:
        period = session.get(CalendarPeriod, calendar_period_id)
        if period is None:
            raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")

        if replace_existing:
            session.execute(
                delete(TimeBlock).where(TimeBlock.calendar_period_id == calendar_period_id)
            )

        blocks: list[TimeBlock] = []
        current_date = period.start_date
        while current_date <= period.end_date:
            day_pattern = period.week_pattern.get_pattern_for_weekday(current_date.weekday())
            blocks.extend(
                self._build_day_blocks(
                    calendar_period_id=period.id,
                    current_date=current_date,
                    items=day_pattern.items,
                )
            )
            current_date += timedelta(days=1)

        session.add_all(blocks)
        session.flush()
        return blocks

    def _build_day_blocks(
        self,
        calendar_period_id: int,
        current_date: date,
        items: list[DayPatternItem],
    ) -> list[TimeBlock]:
        current_start = datetime.combine(current_date, self.day_start_time)
        day_blocks: list[TimeBlock] = []

        for item in sorted(items, key=lambda block_item: block_item.order_index):
            current_end = current_start + timedelta(minutes=item.mark_type.duration_minutes)
            day_blocks.append(
                TimeBlock(
                    calendar_period_id=calendar_period_id,
                    date=current_date,
                    start_timestamp=current_start,
                    end_timestamp=current_end,
                    block_kind=item.mark_type.kind,
                    order_in_day=item.order_index,
                    day_of_week=current_date.weekday(),
                )
            )
            current_start = current_end

        return day_blocks
