from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
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

    requirement: Mapped["Requirement"] = relationship("Requirement", back_populates="schedule_entries")
    start_block: Mapped["TimeBlock"] = relationship("TimeBlock", back_populates="schedule_entries")

    __table_args__ = (
        UniqueConstraint(
            "requirement_id",
            "start_block_id",
            name="uq_schedule_entry_requirement_start_block",
        ),
        CheckConstraint("blocks_count > 0", name="ck_schedule_entry_blocks_count_positive"),
    )
