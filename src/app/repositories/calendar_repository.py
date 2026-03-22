from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.enums import MarkKind
from app.domain.models import (
    CalendarPeriod,
    CalendarPeriodWeekTemplate,
    DayPattern,
    DayPatternItem,
    MarkType,
    WeekPattern,
)


class CalendarRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_mark_type(
        self,
        name: str,
        kind: MarkKind,
        duration_minutes: int,
        company_id: int | None = None,
    ) -> MarkType:
        mark_type = MarkType(
            company_id=company_id,
            name=name,
            kind=kind,
            duration_minutes=duration_minutes,
        )
        self.session.add(mark_type)
        self.session.flush()
        return mark_type

    def create_day_pattern(
        self,
        name: str,
        mark_types: list[MarkType],
        company_id: int | None = None,
    ) -> DayPattern:
        day_pattern = DayPattern(company_id=company_id, name=name)
        day_pattern.items = [
            DayPatternItem(order_index=index + 1, mark_type=mark_type)
            for index, mark_type in enumerate(mark_types)
        ]
        self.session.add(day_pattern)
        self.session.flush()
        return day_pattern

    def create_week_pattern(self, day_pattern: DayPattern, company_id: int | None = None) -> WeekPattern:
        week_pattern = WeekPattern(
            company_id=company_id,
            monday_pattern=day_pattern,
            tuesday_pattern=day_pattern,
            wednesday_pattern=day_pattern,
            thursday_pattern=day_pattern,
            friday_pattern=day_pattern,
            saturday_pattern=day_pattern,
            sunday_pattern=day_pattern,
        )
        self.session.add(week_pattern)
        self.session.flush()
        return week_pattern

    def create_calendar_period(
        self,
        start_date: date,
        end_date: date,
        week_pattern: WeekPattern,
        company_id: int | None = None,
        name: str | None = None,
        week_pattern_by_week_index: dict[int, int] | None = None,
    ) -> CalendarPeriod:
        period = CalendarPeriod(
            company_id=company_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            week_pattern=week_pattern,
        )
        self.session.add(period)
        self.session.flush()
        self.replace_period_week_templates(
            calendar_period_id=period.id,
            default_week_pattern_id=period.week_pattern_id,
            week_pattern_by_week_index=week_pattern_by_week_index or {},
        )
        self.session.flush()
        return period

    def get_week_pattern(self, week_pattern_id: int) -> WeekPattern | None:
        return self.session.get(WeekPattern, week_pattern_id)

    def get_calendar_period(self, period_id: int) -> CalendarPeriod | None:
        return self.session.get(CalendarPeriod, period_id)

    def update_calendar_period(
        self,
        *,
        period_id: int,
        start_date: date,
        end_date: date,
        week_pattern_id: int,
        name: str | None = None,
        week_pattern_by_week_index: dict[int, int] | None = None,
    ) -> CalendarPeriod:
        period = self.get_calendar_period(period_id)
        if period is None:
            raise ValueError(f"CalendarPeriod with id={period_id} was not found")
        period.start_date = start_date
        period.end_date = end_date
        period.week_pattern_id = int(week_pattern_id)
        period.name = name
        self.replace_period_week_templates(
            calendar_period_id=period.id,
            default_week_pattern_id=period.week_pattern_id,
            week_pattern_by_week_index=week_pattern_by_week_index or {},
        )
        self.session.flush()
        return period

    def delete_calendar_period(self, *, period_id: int) -> bool:
        period = self.get_calendar_period(period_id)
        if period is None:
            return False
        self.session.delete(period)
        self.session.flush()
        return True

    def replace_period_week_templates(
        self,
        *,
        calendar_period_id: int,
        default_week_pattern_id: int,
        week_pattern_by_week_index: dict[int, int],
    ) -> None:
        self.session.execute(
            delete(CalendarPeriodWeekTemplate).where(
                CalendarPeriodWeekTemplate.calendar_period_id == calendar_period_id
            )
        )
        normalized: dict[int, int] = {}
        for week_index, week_pattern_id in week_pattern_by_week_index.items():
            idx = int(week_index)
            pattern_id = int(week_pattern_id)
            if idx < 1:
                continue
            if pattern_id == int(default_week_pattern_id):
                continue
            normalized[idx] = pattern_id
        if not normalized:
            self.session.flush()
            return
        for week_index, week_pattern_id in sorted(normalized.items(), key=lambda item: item[0]):
            self.session.add(
                CalendarPeriodWeekTemplate(
                    calendar_period_id=calendar_period_id,
                    week_index=week_index,
                    week_pattern_id=week_pattern_id,
                )
            )
        self.session.flush()

    def list_calendar_periods(self, company_id: int | None = None) -> list[CalendarPeriod]:
        statement = select(CalendarPeriod).order_by(CalendarPeriod.start_date.asc(), CalendarPeriod.id.asc())
        if company_id is not None:
            statement = statement.where(CalendarPeriod.company_id == company_id)
        return list(self.session.scalars(statement).all())
