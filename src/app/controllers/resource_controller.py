from sqlalchemy.orm import Session

from app.domain.enums import ResourceType
from app.domain.models import Resource
from app.repositories.resource_repository import ResourceRepository


class ResourceController:
    def __init__(self, session: Session) -> None:
        self.repository = ResourceRepository(session=session)

    def create_resource(
        self,
        name: str,
        resource_type: ResourceType,
        company_id: int | None = None,
    ) -> Resource:
        return self.repository.create_resource(
            name=name,
            resource_type=resource_type,
            company_id=company_id,
        )

    def get_resource(self, resource_id: int) -> Resource | None:
        return self.repository.get_resource(resource_id=resource_id)

    def list_resources(
        self,
        resource_type: ResourceType | None = None,
        company_id: int | None = None,
    ) -> list[Resource]:
        return self.repository.list_resources(resource_type=resource_type, company_id=company_id)

    def update_resource(
        self,
        resource_id: int,
        *,
        name: str | None = None,
        resource_type: ResourceType | None = None,
    ) -> Resource:
        return self.repository.update_resource(
            resource_id=resource_id,
            name=name,
            resource_type=resource_type,
        )

    def delete_resource(self, resource_id: int) -> bool:
        return self.repository.delete_resource(resource_id=resource_id)
