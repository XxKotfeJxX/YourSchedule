from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Requirement, RequirementResource, Resource


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
    ) -> Requirement:
        requirement = Requirement(
            company_id=company_id,
            name=name,
            duration_blocks=duration_blocks,
            sessions_total=sessions_total,
            max_per_week=max_per_week,
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
