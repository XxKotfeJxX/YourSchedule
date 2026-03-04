from sqlalchemy.orm import Session

from app.domain.enums import ResourceType
from app.domain.models import Resource
from app.repositories.resource_repository import ResourceRepository

_UNSET = object()


class ResourceController:
    def __init__(self, session: Session) -> None:
        self.repository = ResourceRepository(session=session)

    def create_resource(
        self,
        name: str,
        resource_type: ResourceType,
        company_id: int | None = None,
        parent_group_id: int | None = None,
        stream_id: int | None = None,
    ) -> Resource:
        return self.repository.create_resource(
            name=name,
            resource_type=resource_type,
            company_id=company_id,
            parent_group_id=parent_group_id,
            stream_id=stream_id,
        )

    def get_resource(self, resource_id: int) -> Resource | None:
        return self.repository.get_resource(resource_id=resource_id)

    def list_resources(
        self,
        resource_type: ResourceType | None = None,
        company_id: int | None = None,
        parent_group_id: int | None = None,
        stream_id: int | None = None,
    ) -> list[Resource]:
        return self.repository.list_resources(
            resource_type=resource_type,
            company_id=company_id,
            parent_group_id=parent_group_id,
            stream_id=stream_id,
        )

    def update_resource(
        self,
        resource_id: int,
        *,
        name: str | None = None,
        resource_type: ResourceType | None = None,
        stream_id: int | None | object = _UNSET,
    ) -> Resource:
        kwargs: dict[str, object] = {
            "resource_id": resource_id,
            "name": name,
            "resource_type": resource_type,
        }
        if stream_id is not _UNSET:
            kwargs["stream_id"] = stream_id
        return self.repository.update_resource(**kwargs)

    def delete_resource(self, resource_id: int) -> bool:
        return self.repository.delete_resource(resource_id=resource_id)

    def list_subgroups(self, group_id: int, company_id: int | None = None) -> list[Resource]:
        return self.repository.list_subgroups(group_id=group_id, company_id=company_id)

    def delete_group_with_subgroups(self, group_id: int) -> bool:
        return self.repository.delete_group_with_subgroups(group_id=group_id)
