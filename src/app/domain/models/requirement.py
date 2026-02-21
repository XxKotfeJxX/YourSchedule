from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base


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

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_requirement_company_name"),
        CheckConstraint("duration_blocks > 0", name="ck_requirement_duration_blocks_positive"),
        CheckConstraint("sessions_total > 0", name="ck_requirement_sessions_total_positive"),
        CheckConstraint("max_per_week > 0", name="ck_requirement_max_per_week_positive"),
        CheckConstraint("max_per_week <= sessions_total", name="ck_requirement_max_per_week_le_sessions_total"),
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
