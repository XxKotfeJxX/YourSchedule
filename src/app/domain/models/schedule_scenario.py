from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base


class ScheduleScenario(Base):
    __tablename__ = "schedule_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    calendar_period_id: Mapped[int] = mapped_column(
        ForeignKey("calendar_periods.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    entries: Mapped[list["ScheduleScenarioEntry"]] = relationship(
        "ScheduleScenarioEntry",
        back_populates="scenario",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "calendar_period_id",
            "name",
            name="uq_schedule_scenario_period_name",
        ),
    )


class ScheduleScenarioEntry(Base):
    __tablename__ = "schedule_scenario_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_scenarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_block_id: Mapped[int] = mapped_column(
        ForeignKey("time_blocks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    blocks_count: Mapped[int] = mapped_column(Integer, nullable=False)
    room_resource_id: Mapped[int | None] = mapped_column(
        ForeignKey("resources.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    scenario: Mapped[ScheduleScenario] = relationship("ScheduleScenario", back_populates="entries")
    requirement: Mapped["Requirement"] = relationship("Requirement")
    start_block: Mapped["TimeBlock"] = relationship("TimeBlock")
    room_resource: Mapped["Resource | None"] = relationship("Resource", foreign_keys=[room_resource_id])

    __table_args__ = (
        UniqueConstraint(
            "scenario_id",
            "requirement_id",
            "start_block_id",
            name="uq_schedule_scenario_entry_requirement_start_block",
        ),
        CheckConstraint("blocks_count > 0", name="ck_schedule_scenario_entry_blocks_count_positive"),
    )
