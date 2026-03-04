from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.base import Base
from app.domain.enums import ResourceType


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
    )
    parent_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=True,
    )
    stream_id: Mapped[int | None] = mapped_column(
        ForeignKey("streams.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType, name="resource_type_enum"),
        nullable=False,
    )
    requirement_resources: Mapped[list["RequirementResource"]] = relationship(
        "RequirementResource",
        back_populates="resource",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="resource",
        foreign_keys="User.resource_id",
    )
    subgroup_users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="subgroup",
        foreign_keys="User.subgroup_id",
    )
    parent_group: Mapped["Resource | None"] = relationship(
        "Resource",
        remote_side=[id],
        back_populates="subgroups",
        foreign_keys=[parent_group_id],
    )
    subgroups: Mapped[list["Resource"]] = relationship(
        "Resource",
        back_populates="parent_group",
        foreign_keys=[parent_group_id],
    )
    stream: Mapped["Stream | None"] = relationship("Stream", back_populates="groups")

    __table_args__ = (
        UniqueConstraint("company_id", "name", "type", name="uq_resource_company_name_type"),
    )
