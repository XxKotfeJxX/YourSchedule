from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.base import Base
from app.domain.enums import TimePreference


class SchedulerPolicy(Base):
    __tablename__ = "scheduler_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    max_sessions_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True, default=4)
    max_consecutive_blocks: Mapped[int | None] = mapped_column(Integer, nullable=True, default=3)
    enforce_no_gaps: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    time_preference: Mapped[TimePreference] = mapped_column(
        SQLEnum(TimePreference, name="time_preference_enum"),
        nullable=False,
        default=TimePreference.BALANCED,
    )
    weight_time_preference: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    weight_compactness: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    weight_building_transition: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("company_id", name="uq_scheduler_policy_company"),
        CheckConstraint(
            "max_sessions_per_day IS NULL OR max_sessions_per_day > 0",
            name="ck_scheduler_policy_max_sessions_per_day_positive",
        ),
        CheckConstraint(
            "max_consecutive_blocks IS NULL OR max_consecutive_blocks > 0",
            name="ck_scheduler_policy_max_consecutive_blocks_positive",
        ),
        CheckConstraint(
            "weight_time_preference >= 0",
            name="ck_scheduler_policy_weight_time_preference_non_negative",
        ),
        CheckConstraint(
            "weight_compactness >= 0",
            name="ck_scheduler_policy_weight_compactness_non_negative",
        ),
        CheckConstraint(
            "weight_building_transition >= 0",
            name="ck_scheduler_policy_weight_building_transition_non_negative",
        ),
    )
