from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.models import CalendarPeriod, DayPattern, DayPatternItem, MarkType, WeekPattern


WEEKDAY_INDEXES = (0, 1, 2, 3, 4, 5, 6)


class TemplateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_mark_types(self, *, company_id: int, include_archived: bool = False) -> list[MarkType]:
        statement = (
            select(MarkType)
            .where(MarkType.company_id == company_id)
            .order_by(MarkType.name.asc(), MarkType.id.asc())
        )
        if not include_archived:
            statement = statement.where(MarkType.is_archived.is_(False))
        return list(self.session.scalars(statement).all())

    def get_mark_type(self, mark_type_id: int) -> MarkType | None:
        return self.session.get(MarkType, mark_type_id)

    def get_mark_types_by_ids(self, *, company_id: int, mark_type_ids: Iterable[int]) -> list[MarkType]:
        ids = list(dict.fromkeys(mark_type_ids))
        if not ids:
            return []
        statement = (
            select(MarkType)
            .where(
                MarkType.company_id == company_id,
                MarkType.id.in_(ids),
            )
            .order_by(MarkType.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def create_mark_type(
        self,
        *,
        company_id: int,
        name: str,
        kind,
        duration_minutes: int,
    ) -> MarkType:
        mark_type = MarkType(
            company_id=company_id,
            name=name,
            kind=kind,
            duration_minutes=duration_minutes,
            is_archived=False,
        )
        self.session.add(mark_type)
        self.session.flush()
        return mark_type

    def update_mark_type(
        self,
        *,
        mark_type_id: int,
        name: str | None = None,
        kind=None,
        duration_minutes: int | None = None,
    ) -> MarkType:
        mark_type = self.get_mark_type(mark_type_id)
        if mark_type is None:
            raise ValueError(f"MarkType with id={mark_type_id} was not found")
        if name is not None:
            mark_type.name = name
        if kind is not None:
            mark_type.kind = kind
        if duration_minutes is not None:
            mark_type.duration_minutes = duration_minutes
        self.session.flush()
        return mark_type

    def archive_mark_type(self, *, mark_type_id: int) -> MarkType:
        mark_type = self.get_mark_type(mark_type_id)
        if mark_type is None:
            raise ValueError(f"MarkType with id={mark_type_id} was not found")
        mark_type.is_archived = True
        self.session.flush()
        return mark_type

    def delete_mark_type(self, *, mark_type_id: int) -> bool:
        mark_type = self.get_mark_type(mark_type_id)
        if mark_type is None:
            return False
        self.session.delete(mark_type)
        self.session.flush()
        return True

    def list_day_patterns(self, *, company_id: int, include_archived: bool = False) -> list[DayPattern]:
        statement = (
            select(DayPattern)
            .where(DayPattern.company_id == company_id)
            .order_by(DayPattern.name.asc(), DayPattern.id.asc())
        )
        if not include_archived:
            statement = statement.where(DayPattern.is_archived.is_(False))
        return list(self.session.scalars(statement).all())

    def get_day_pattern(self, day_pattern_id: int) -> DayPattern | None:
        return self.session.get(DayPattern, day_pattern_id)

    def get_day_patterns_by_ids(self, *, company_id: int, day_pattern_ids: Iterable[int]) -> list[DayPattern]:
        ids = list(dict.fromkeys(day_pattern_ids))
        if not ids:
            return []
        statement = (
            select(DayPattern)
            .where(
                DayPattern.company_id == company_id,
                DayPattern.id.in_(ids),
            )
            .order_by(DayPattern.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def create_day_pattern(self, *, company_id: int, name: str, mark_type_ids: list[int]) -> DayPattern:
        day_pattern = DayPattern(
            company_id=company_id,
            name=name,
            is_archived=False,
        )
        day_pattern.items = [
            DayPatternItem(order_index=index + 1, mark_type_id=mark_type_id)
            for index, mark_type_id in enumerate(mark_type_ids)
        ]
        self.session.add(day_pattern)
        self.session.flush()
        return day_pattern

    def update_day_pattern(
        self,
        *,
        day_pattern_id: int,
        name: str | None = None,
        mark_type_ids: list[int] | None = None,
    ) -> DayPattern:
        day_pattern = self.get_day_pattern(day_pattern_id)
        if day_pattern is None:
            raise ValueError(f"DayPattern with id={day_pattern_id} was not found")
        if name is not None:
            day_pattern.name = name
        if mark_type_ids is not None:
            day_pattern.items.clear()
            self.session.flush()
            day_pattern.items = [
                DayPatternItem(order_index=index + 1, mark_type_id=mark_type_id)
                for index, mark_type_id in enumerate(mark_type_ids)
            ]
        self.session.flush()
        return day_pattern

    def archive_day_pattern(self, *, day_pattern_id: int) -> DayPattern:
        day_pattern = self.get_day_pattern(day_pattern_id)
        if day_pattern is None:
            raise ValueError(f"DayPattern with id={day_pattern_id} was not found")
        day_pattern.is_archived = True
        self.session.flush()
        return day_pattern

    def delete_day_pattern(self, *, day_pattern_id: int) -> bool:
        day_pattern = self.get_day_pattern(day_pattern_id)
        if day_pattern is None:
            return False
        self.session.delete(day_pattern)
        self.session.flush()
        return True

    def list_week_patterns(self, *, company_id: int, include_archived: bool = False) -> list[WeekPattern]:
        statement = (
            select(WeekPattern)
            .where(WeekPattern.company_id == company_id)
            .order_by(WeekPattern.id.asc())
        )
        if not include_archived:
            statement = statement.where(WeekPattern.is_archived.is_(False))
        return list(self.session.scalars(statement).all())

    def get_week_pattern(self, week_pattern_id: int) -> WeekPattern | None:
        return self.session.get(WeekPattern, week_pattern_id)

    def create_week_pattern(
        self,
        *,
        company_id: int,
        name: str,
        weekday_to_day_pattern_id: dict[int, int],
    ) -> WeekPattern:
        week_pattern = WeekPattern(
            company_id=company_id,
            name=name,
            is_archived=False,
            monday_pattern_id=weekday_to_day_pattern_id[0],
            tuesday_pattern_id=weekday_to_day_pattern_id[1],
            wednesday_pattern_id=weekday_to_day_pattern_id[2],
            thursday_pattern_id=weekday_to_day_pattern_id[3],
            friday_pattern_id=weekday_to_day_pattern_id[4],
            saturday_pattern_id=weekday_to_day_pattern_id[5],
            sunday_pattern_id=weekday_to_day_pattern_id[6],
        )
        self.session.add(week_pattern)
        self.session.flush()
        return week_pattern

    def update_week_pattern(
        self,
        *,
        week_pattern_id: int,
        name: str | None = None,
        weekday_to_day_pattern_id: dict[int, int] | None = None,
    ) -> WeekPattern:
        week_pattern = self.get_week_pattern(week_pattern_id)
        if week_pattern is None:
            raise ValueError(f"WeekPattern with id={week_pattern_id} was not found")
        if name is not None:
            week_pattern.name = name
        if weekday_to_day_pattern_id is not None:
            week_pattern.monday_pattern_id = weekday_to_day_pattern_id[0]
            week_pattern.tuesday_pattern_id = weekday_to_day_pattern_id[1]
            week_pattern.wednesday_pattern_id = weekday_to_day_pattern_id[2]
            week_pattern.thursday_pattern_id = weekday_to_day_pattern_id[3]
            week_pattern.friday_pattern_id = weekday_to_day_pattern_id[4]
            week_pattern.saturday_pattern_id = weekday_to_day_pattern_id[5]
            week_pattern.sunday_pattern_id = weekday_to_day_pattern_id[6]
        self.session.flush()
        return week_pattern

    def archive_week_pattern(self, *, week_pattern_id: int) -> WeekPattern:
        week_pattern = self.get_week_pattern(week_pattern_id)
        if week_pattern is None:
            raise ValueError(f"WeekPattern with id={week_pattern_id} was not found")
        week_pattern.is_archived = True
        self.session.flush()
        return week_pattern

    def delete_week_pattern(self, *, week_pattern_id: int) -> bool:
        week_pattern = self.get_week_pattern(week_pattern_id)
        if week_pattern is None:
            return False
        self.session.delete(week_pattern)
        self.session.flush()
        return True

    def mark_type_usage_counts(self, *, company_id: int) -> dict[int, int]:
        statement = (
            select(
                DayPatternItem.mark_type_id,
                func.count(func.distinct(DayPatternItem.day_pattern_id)),
            )
            .join(DayPattern, DayPattern.id == DayPatternItem.day_pattern_id)
            .where(DayPattern.company_id == company_id)
            .group_by(DayPatternItem.mark_type_id)
        )
        return {mark_type_id: int(count) for mark_type_id, count in self.session.execute(statement).all()}

    def day_pattern_usage_counts(self, *, company_id: int) -> dict[int, int]:
        counts: dict[int, int] = {}
        for week_pattern in self.list_week_patterns(company_id=company_id, include_archived=True):
            for day_pattern_id in self.weekday_mapping(week_pattern).values():
                counts[day_pattern_id] = counts.get(day_pattern_id, 0) + 1
        return counts

    def week_pattern_usage_counts(self, *, company_id: int) -> dict[int, int]:
        statement = (
            select(CalendarPeriod.week_pattern_id, func.count(CalendarPeriod.id))
            .where(CalendarPeriod.company_id == company_id)
            .group_by(CalendarPeriod.week_pattern_id)
        )
        return {week_pattern_id: int(count) for week_pattern_id, count in self.session.execute(statement).all()}

    @staticmethod
    def weekday_mapping(week_pattern: WeekPattern) -> dict[int, int]:
        return {
            0: week_pattern.monday_pattern_id,
            1: week_pattern.tuesday_pattern_id,
            2: week_pattern.wednesday_pattern_id,
            3: week_pattern.thursday_pattern_id,
            4: week_pattern.friday_pattern_id,
            5: week_pattern.saturday_pattern_id,
            6: week_pattern.sunday_pattern_id,
        }
