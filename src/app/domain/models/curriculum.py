from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base
from app.domain.enums import PlanComponentType, PlanTargetType


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    components: Mapped[list["PlanComponent"]] = relationship(
        "PlanComponent",
        back_populates="subject",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_subject_company_name"),
        UniqueConstraint("company_id", "code", name="uq_subject_company_code"),
    )


class CurriculumPlan(Base):
    __tablename__ = "curriculum_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    specialty_id: Mapped[int | None] = mapped_column(
        ForeignKey("specialties.id", ondelete="SET NULL"),
        nullable=True,
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    stream_id: Mapped[int | None] = mapped_column(
        ForeignKey("streams.id", ondelete="SET NULL"),
        nullable=True,
    )
    semester: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    components: Mapped[list["PlanComponent"]] = relationship(
        "PlanComponent",
        back_populates="plan",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_curriculum_plan_company_name"),
        CheckConstraint("semester IS NULL OR semester > 0", name="ck_curriculum_plan_semester_positive"),
    )


class PlanComponent(Base):
    __tablename__ = "plan_components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("curriculum_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    component_type: Mapped[PlanComponentType] = mapped_column(
        SQLEnum(PlanComponentType, name="plan_component_type_enum"),
        nullable=False,
    )
    duration_blocks: Mapped[int] = mapped_column(Integer, nullable=False)
    sessions_total: Mapped[int] = mapped_column(Integer, nullable=False)
    max_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    plan: Mapped[CurriculumPlan] = relationship("CurriculumPlan", back_populates="components")
    subject: Mapped[Subject] = relationship("Subject", back_populates="components")
    assignments: Mapped[list["PlanComponentAssignment"]] = relationship(
        "PlanComponentAssignment",
        back_populates="component",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("duration_blocks > 0", name="ck_plan_component_duration_blocks_positive"),
        CheckConstraint("sessions_total > 0", name="ck_plan_component_sessions_total_positive"),
        CheckConstraint("max_per_week > 0", name="ck_plan_component_max_per_week_positive"),
        CheckConstraint(
            "max_per_week <= sessions_total",
            name="ck_plan_component_max_per_week_le_sessions_total",
        ),
    )


class PlanComponentAssignment(Base):
    __tablename__ = "plan_component_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    component_id: Mapped[int] = mapped_column(
        ForeignKey("plan_components.id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_resource_id: Mapped[int] = mapped_column(
        ForeignKey("resources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_type: Mapped[PlanTargetType] = mapped_column(
        SQLEnum(PlanTargetType, name="plan_target_type_enum"),
        nullable=False,
    )
    target_resource_id: Mapped[int | None] = mapped_column(
        ForeignKey("resources.id", ondelete="RESTRICT"),
        nullable=True,
    )
    stream_id: Mapped[int | None] = mapped_column(
        ForeignKey("streams.id", ondelete="SET NULL"),
        nullable=True,
    )
    sessions_total: Mapped[int] = mapped_column(Integer, nullable=False)
    max_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    requirement_id: Mapped[int | None] = mapped_column(
        ForeignKey("requirements.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    component: Mapped[PlanComponent] = relationship("PlanComponent", back_populates="assignments")
    teacher_resource: Mapped["Resource"] = relationship("Resource", foreign_keys=[teacher_resource_id])
    target_resource: Mapped["Resource | None"] = relationship("Resource", foreign_keys=[target_resource_id])

    __table_args__ = (
        CheckConstraint("sessions_total > 0", name="ck_plan_component_assignment_sessions_total_positive"),
        CheckConstraint("max_per_week > 0", name="ck_plan_component_assignment_max_per_week_positive"),
        CheckConstraint(
            "max_per_week <= sessions_total",
            name="ck_plan_component_assignment_max_per_week_le_sessions_total",
        ),
        CheckConstraint(
            "("
            "target_type = 'STREAM' AND stream_id IS NOT NULL AND target_resource_id IS NULL"
            ") OR ("
            "target_type IN ('GROUP', 'SUBGROUP') AND stream_id IS NULL AND target_resource_id IS NOT NULL"
            ")",
            name="ck_plan_component_assignment_target_scope",
        ),
        UniqueConstraint(
            "component_id",
            "teacher_resource_id",
            "target_type",
            "target_resource_id",
            "stream_id",
            name="uq_plan_component_assignment_unique",
        ),
    )
