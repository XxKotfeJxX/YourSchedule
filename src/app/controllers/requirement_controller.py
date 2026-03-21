from sqlalchemy.orm import Session

from app.domain.enums import RoomType
from app.domain.models import Requirement, RequirementResource
from app.repositories.requirement_repository import RequirementRepository

_UNSET = object()


class RequirementController:
    def __init__(self, session: Session) -> None:
        self.repository = RequirementRepository(session=session)

    def create_requirement(
        self,
        name: str,
        duration_blocks: int,
        sessions_total: int,
        max_per_week: int,
        company_id: int | None = None,
        room_type: RoomType | None = None,
        min_capacity: int | None = None,
        needs_projector: bool = False,
        fixed_room_id: int | None = None,
    ) -> Requirement:
        return self.repository.create_requirement(
            name=name,
            duration_blocks=duration_blocks,
            sessions_total=sessions_total,
            max_per_week=max_per_week,
            company_id=company_id,
            room_type=room_type,
            min_capacity=min_capacity,
            needs_projector=needs_projector,
            fixed_room_id=fixed_room_id,
        )

    def get_requirement(self, requirement_id: int) -> Requirement | None:
        return self.repository.get_requirement(requirement_id=requirement_id)

    def list_requirements(self, company_id: int | None = None) -> list[Requirement]:
        return self.repository.list_requirements(company_id=company_id)

    def update_requirement(
        self,
        requirement_id: int,
        *,
        name: str | None = None,
        duration_blocks: int | None = None,
        sessions_total: int | None = None,
        max_per_week: int | None = None,
        room_type: RoomType | None | object = _UNSET,
        min_capacity: int | None | object = _UNSET,
        needs_projector: bool | object = _UNSET,
        fixed_room_id: int | None | object = _UNSET,
    ) -> Requirement:
        kwargs: dict[str, object] = {
            "requirement_id": requirement_id,
            "name": name,
            "duration_blocks": duration_blocks,
            "sessions_total": sessions_total,
            "max_per_week": max_per_week,
        }
        if room_type is not _UNSET:
            kwargs["room_type"] = room_type
        if min_capacity is not _UNSET:
            kwargs["min_capacity"] = min_capacity
        if needs_projector is not _UNSET:
            kwargs["needs_projector"] = needs_projector
        if fixed_room_id is not _UNSET:
            kwargs["fixed_room_id"] = fixed_room_id
        return self.repository.update_requirement(**kwargs)

    def delete_requirement(self, requirement_id: int) -> bool:
        return self.repository.delete_requirement(requirement_id=requirement_id)

    def assign_resource(
        self,
        requirement_id: int,
        resource_id: int,
        role: str,
    ) -> RequirementResource:
        return self.repository.assign_resource(
            requirement_id=requirement_id,
            resource_id=resource_id,
            role=role,
        )

    def list_requirement_resources(self, requirement_id: int) -> list[RequirementResource]:
        return self.repository.list_requirement_resources(requirement_id=requirement_id)

    def unassign_resource(self, requirement_id: int, resource_id: int, role: str) -> bool:
        return self.repository.unassign_resource(
            requirement_id=requirement_id,
            resource_id=resource_id,
            role=role,
        )
