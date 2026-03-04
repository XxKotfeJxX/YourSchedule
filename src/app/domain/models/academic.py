from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(48), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    specialties: Mapped[list["Specialty"]] = relationship(
        "Specialty",
        back_populates="department",
        cascade="all, delete-orphan",
    )
    home_rooms: Mapped[list["RoomProfile"]] = relationship(
        "RoomProfile",
        back_populates="home_department",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_department_company_name"),
        UniqueConstraint("company_id", "short_name", name="uq_department_company_short_name"),
    )


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    degree_level: Mapped[str] = mapped_column(String(32), nullable=False, default="BACHELOR")
    duration_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    department: Mapped[Department] = relationship("Department", back_populates="specialties")
    streams: Mapped[list["Stream"]] = relationship(
        "Stream",
        back_populates="specialty",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "department_id", "name", name="uq_specialty_company_department_name"),
        UniqueConstraint("company_id", "code", name="uq_specialty_company_code"),
        CheckConstraint(
            "duration_years IS NULL OR duration_years > 0",
            name="ck_specialty_duration_years_positive",
        ),
    )


class Stream(Base):
    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    specialty_id: Mapped[int] = mapped_column(
        ForeignKey("specialties.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    admission_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    study_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    specialty: Mapped[Specialty] = relationship("Specialty", back_populates="streams")
    groups: Mapped[list["Resource"]] = relationship("Resource", back_populates="stream")

    __table_args__ = (
        UniqueConstraint("company_id", "specialty_id", "name", name="uq_stream_company_specialty_name"),
        CheckConstraint(
            "study_year IS NULL OR study_year > 0",
            name="ck_stream_study_year_positive",
        ),
    )

