from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ResourceType, RoomType
from app.domain.models import Requirement, RequirementResource, Resource, RoomProfile

_UNSET = object()

class RequirementRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

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
        self._validate_min_capacity(min_capacity=min_capacity)
        fixed_room = self._resolve_fixed_room(fixed_room_id=fixed_room_id)
        if fixed_room is not None:
            self._validate_fixed_room_constraints(
                requirement_company_id=company_id,
                room=fixed_room,
                room_type=room_type,
                min_capacity=min_capacity,
                needs_projector=needs_projector,
            )

        requirement = Requirement(
            company_id=company_id,
            name=name,
            duration_blocks=duration_blocks,
            sessions_total=sessions_total,
            max_per_week=max_per_week,
            room_type=room_type,
            min_capacity=min_capacity,
            needs_projector=needs_projector,
            fixed_room_id=fixed_room.id if fixed_room is not None else None,
        )
        self.session.add(requirement)
        self.session.flush()
        return requirement

    def get_requirement(self, requirement_id: int) -> Requirement | None:
        return self.session.get(Requirement, requirement_id)

    def list_requirements(self, company_id: int | None = None) -> list[Requirement]:
        statement = select(Requirement).order_by(Requirement.name.asc(), Requirement.id.asc())
        if company_id is not None:
            statement = statement.where(Requirement.company_id == company_id)
        return list(self.session.scalars(statement).all())

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
        requirement = self.get_requirement(requirement_id)
        if requirement is None:
            raise ValueError(f"Requirement with id={requirement_id} was not found")

        if name is not None:
            requirement.name = name
        if duration_blocks is not None:
            requirement.duration_blocks = duration_blocks
        if sessions_total is not None:
            requirement.sessions_total = sessions_total
        if max_per_week is not None:
            requirement.max_per_week = max_per_week
        if room_type is not _UNSET:
            requirement.room_type = room_type
        if min_capacity is not _UNSET:
            self._validate_min_capacity(min_capacity=min_capacity)
            requirement.min_capacity = min_capacity
        if needs_projector is not _UNSET:
            requirement.needs_projector = bool(needs_projector)
        if fixed_room_id is not _UNSET:
            fixed_room = self._resolve_fixed_room(fixed_room_id=fixed_room_id)
            requirement.fixed_room_id = fixed_room.id if fixed_room is not None else None

        if requirement.fixed_room_id is not None:
            fixed_room = self._resolve_fixed_room(fixed_room_id=requirement.fixed_room_id)
            if fixed_room is None:
                raise ValueError(f"Fixed room with id={requirement.fixed_room_id} was not found")
            self._validate_fixed_room_constraints(
                requirement_company_id=requirement.company_id,
                room=fixed_room,
                room_type=requirement.room_type,
                min_capacity=requirement.min_capacity,
                needs_projector=requirement.needs_projector,
            )

        self.session.flush()
        return requirement

    def delete_requirement(self, requirement_id: int) -> bool:
        requirement = self.get_requirement(requirement_id)
        if requirement is None:
            return False
        self.session.delete(requirement)
        self.session.flush()
        return True

    def assign_resource(
        self,
        requirement_id: int,
        resource_id: int,
        role: str,
    ) -> RequirementResource:
        requirement = self.get_requirement(requirement_id)
        if requirement is None:
            raise ValueError(f"Requirement with id={requirement_id} was not found")

        resource = self.session.get(Resource, resource_id)
        if resource is None:
            raise ValueError(f"Resource with id={resource_id} was not found")
        if (
            requirement.company_id is not None
            and resource.company_id is not None
            and requirement.company_id != resource.company_id
        ):
            raise ValueError("Requirement and resource belong to different companies")

        requirement_resource = RequirementResource(
            requirement_id=requirement.id,
            resource_id=resource.id,
            role=role,
        )
        self.session.add(requirement_resource)
        self.session.flush()
        return requirement_resource

    def list_requirement_resources(self, requirement_id: int) -> list[RequirementResource]:
        statement = (
            select(RequirementResource)
            .where(RequirementResource.requirement_id == requirement_id)
            .order_by(RequirementResource.role.asc(), RequirementResource.resource_id.asc())
        )
        return list(self.session.scalars(statement).all())

    def unassign_resource(self, requirement_id: int, resource_id: int, role: str) -> bool:
        requirement_resource = self.session.get(
            RequirementResource,
            (requirement_id, resource_id, role),
        )
        if requirement_resource is None:
            return False
        self.session.delete(requirement_resource)
        self.session.flush()
        return True

    def _resolve_fixed_room(self, fixed_room_id: int | None | object) -> RoomProfile | None:
        if fixed_room_id is None or fixed_room_id is _UNSET:
            return None
        room = self.session.get(RoomProfile, int(fixed_room_id))
        if room is None:
            raise ValueError(f"RoomProfile with id={fixed_room_id} was not found")
        return room

    def _validate_min_capacity(self, min_capacity: int | None | object) -> None:
        if min_capacity is None or min_capacity is _UNSET:
            return
        if int(min_capacity) <= 0:
            raise ValueError("min_capacity must be greater than 0")

    def _validate_fixed_room_constraints(
        self,
        *,
        requirement_company_id: int | None,
        room: RoomProfile,
        room_type: RoomType | None,
        min_capacity: int | None,
        needs_projector: bool,
    ) -> None:
        if room.resource.type != ResourceType.ROOM:
            raise ValueError("fixed_room_id must reference a RoomProfile backed by ROOM resource")

        if (
            requirement_company_id is not None
            and room.company_id is not None
            and requirement_company_id != room.company_id
        ):
            raise ValueError("Requirement and fixed room belong to different companies")

        if room_type is not None and room.room_type != room_type:
            raise ValueError("Fixed room does not match required room_type")

        if min_capacity is not None and (room.capacity or 0) < min_capacity:
            raise ValueError("Fixed room does not satisfy min_capacity")

        if needs_projector and not room.has_projector:
            raise ValueError("Fixed room does not satisfy needs_projector")
