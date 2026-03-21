from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base
from app.domain.enums import RoomType


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    duration_blocks: Mapped[int] = mapped_column(Integer, nullable=False)
    sessions_total: Mapped[int] = mapped_column(Integer, nullable=False)
    max_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    room_type: Mapped[RoomType | None] = mapped_column(
        SQLEnum(RoomType, name="room_type_enum"),
        nullable=True,
    )
    min_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    needs_projector: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fixed_room_id: Mapped[int | None] = mapped_column(
        ForeignKey("room_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    requirement_resources: Mapped[list["RequirementResource"]] = relationship(
        "RequirementResource",
        back_populates="requirement",
        cascade="all, delete-orphan",
    )
    schedule_entries: Mapped[list["ScheduleEntry"]] = relationship(
        "ScheduleEntry",
        back_populates="requirement",
        cascade="all, delete-orphan",
    )
    fixed_room: Mapped["RoomProfile | None"] = relationship("RoomProfile")

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_requirement_company_name"),
        CheckConstraint("duration_blocks > 0", name="ck_requirement_duration_blocks_positive"),
        CheckConstraint("sessions_total > 0", name="ck_requirement_sessions_total_positive"),
        CheckConstraint("max_per_week > 0", name="ck_requirement_max_per_week_positive"),
        CheckConstraint("max_per_week <= sessions_total", name="ck_requirement_max_per_week_le_sessions_total"),
        CheckConstraint("min_capacity IS NULL OR min_capacity > 0", name="ck_requirement_min_capacity_positive"),
    )


class RequirementResource(Base):
    __tablename__ = "requirement_resources"

    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"),
        primary_key=True,
    )
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("resources.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(80), primary_key=True)

    requirement: Mapped[Requirement] = relationship("Requirement", back_populates="requirement_resources")
    resource: Mapped["Resource"] = relationship("Resource", back_populates="requirement_resources")
