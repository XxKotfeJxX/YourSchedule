from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base
from app.domain.enums import MarkKind


class MarkType(Base):
    __tablename__ = "mark_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[MarkKind] = mapped_column(
        Enum(MarkKind, name="mark_kind_enum"),
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_mark_type_company_name"),
        CheckConstraint("duration_minutes > 0", name="ck_mark_type_duration_positive"),
    )


class DayPattern(Base):
    __tablename__ = "day_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    items: Mapped[list[DayPatternItem]] = relationship(
        "DayPatternItem",
        back_populates="day_pattern",
        cascade="all, delete-orphan",
        order_by="DayPatternItem.order_index",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_day_pattern_company_name"),
    )


class DayPatternItem(Base):
    __tablename__ = "day_pattern_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_pattern_id: Mapped[int] = mapped_column(
        ForeignKey("day_patterns.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    mark_type_id: Mapped[int] = mapped_column(
        ForeignKey("mark_types.id", ondelete="RESTRICT"),
        nullable=False,
    )

    day_pattern: Mapped[DayPattern] = relationship("DayPattern", back_populates="items")
    mark_type: Mapped[MarkType] = relationship("MarkType")

    __table_args__ = (
        UniqueConstraint(
            "day_pattern_id",
            "order_index",
            name="uq_day_pattern_order_index",
        ),
        CheckConstraint("order_index >= 1", name="ck_day_pattern_order_positive"),
    )


class WeekPattern(Base):
    __tablename__ = "week_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    monday_pattern_id: Mapped[int] = mapped_column(
        ForeignKey("day_patterns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tuesday_pattern_id: Mapped[int] = mapped_column(
        ForeignKey("day_patterns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    wednesday_pattern_id: Mapped[int] = mapped_column(
        ForeignKey("day_patterns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    thursday_pattern_id: Mapped[int] = mapped_column(
        ForeignKey("day_patterns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    friday_pattern_id: Mapped[int] = mapped_column(
        ForeignKey("day_patterns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    saturday_pattern_id: Mapped[int] = mapped_column(
        ForeignKey("day_patterns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sunday_pattern_id: Mapped[int] = mapped_column(
        ForeignKey("day_patterns.id", ondelete="RESTRICT"),
        nullable=False,
    )

    monday_pattern: Mapped[DayPattern] = relationship(foreign_keys=[monday_pattern_id])
    tuesday_pattern: Mapped[DayPattern] = relationship(foreign_keys=[tuesday_pattern_id])
    wednesday_pattern: Mapped[DayPattern] = relationship(foreign_keys=[wednesday_pattern_id])
    thursday_pattern: Mapped[DayPattern] = relationship(foreign_keys=[thursday_pattern_id])
    friday_pattern: Mapped[DayPattern] = relationship(foreign_keys=[friday_pattern_id])
    saturday_pattern: Mapped[DayPattern] = relationship(foreign_keys=[saturday_pattern_id])
    sunday_pattern: Mapped[DayPattern] = relationship(foreign_keys=[sunday_pattern_id])

    def get_pattern_for_weekday(self, weekday: int) -> DayPattern:
        mapping = {
            0: self.monday_pattern,
            1: self.tuesday_pattern,
            2: self.wednesday_pattern,
            3: self.thursday_pattern,
            4: self.friday_pattern,
            5: self.saturday_pattern,
            6: self.sunday_pattern,
        }
        if weekday not in mapping:
            raise ValueError(f"Unsupported weekday index: {weekday}")
        return mapping[weekday]


class CalendarPeriod(Base):
    __tablename__ = "calendar_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    week_pattern_id: Mapped[int] = mapped_column(
        ForeignKey("week_patterns.id", ondelete="RESTRICT"),
        nullable=False,
    )

    week_pattern: Mapped[WeekPattern] = relationship("WeekPattern")
    time_blocks: Mapped[list[TimeBlock]] = relationship(
        "TimeBlock",
        back_populates="calendar_period",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_calendar_period_date_range"),
    )


class TimeBlock(Base):
    __tablename__ = "time_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    calendar_period_id: Mapped[int] = mapped_column(
        ForeignKey("calendar_periods.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    block_kind: Mapped[MarkKind] = mapped_column(
        Enum(MarkKind, name="time_block_kind_enum"),
        nullable=False,
    )
    order_in_day: Mapped[int] = mapped_column(Integer, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)

    calendar_period: Mapped[CalendarPeriod] = relationship("CalendarPeriod", back_populates="time_blocks")
    schedule_entries: Mapped[list["ScheduleEntry"]] = relationship(
        "ScheduleEntry",
        back_populates="start_block",
    )

    __table_args__ = (
        UniqueConstraint(
            "calendar_period_id",
            "date",
            "order_in_day",
            name="uq_time_block_in_day",
        ),
        CheckConstraint("order_in_day >= 1", name="ck_time_block_order_positive"),
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_time_block_day_of_week_range"),
        CheckConstraint("end_timestamp > start_timestamp", name="ck_time_block_positive_duration"),
    )
