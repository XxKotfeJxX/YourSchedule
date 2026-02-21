from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ResourceType
from app.domain.models import Resource


class ResourceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_resource(
        self,
        name: str,
        resource_type: ResourceType,
        company_id: int | None = None,
        parent_group_id: int | None = None,
    ) -> Resource:
        resource = Resource(
            company_id=company_id,
            parent_group_id=parent_group_id,
            name=name,
            type=resource_type,
        )
        self.session.add(resource)
        self.session.flush()
        return resource

    def get_resource(self, resource_id: int) -> Resource | None:
        return self.session.get(Resource, resource_id)

    def list_resources(
        self,
        resource_type: ResourceType | None = None,
        company_id: int | None = None,
        parent_group_id: int | None = None,
    ) -> list[Resource]:
        statement = select(Resource).order_by(Resource.name.asc(), Resource.id.asc())
        if resource_type is not None:
            statement = statement.where(Resource.type == resource_type)
        if company_id is not None:
            statement = statement.where(Resource.company_id == company_id)
        if parent_group_id is not None:
            statement = statement.where(Resource.parent_group_id == parent_group_id)
        return list(self.session.scalars(statement).all())

    def update_resource(
        self,
        resource_id: int,
        *,
        name: str | None = None,
        resource_type: ResourceType | None = None,
    ) -> Resource:
        resource = self.get_resource(resource_id)
        if resource is None:
            raise ValueError(f"Resource with id={resource_id} was not found")

        if name is not None:
            resource.name = name
        if resource_type is not None:
            resource.type = resource_type

        self.session.flush()
        return resource

    def delete_resource(self, resource_id: int) -> bool:
        resource = self.get_resource(resource_id)
        if resource is None:
            return False
        self.session.delete(resource)
        self.session.flush()
        return True

    def list_subgroups(self, group_id: int, company_id: int | None = None) -> list[Resource]:
        statement = (
            select(Resource)
            .where(
                Resource.parent_group_id == group_id,
                Resource.type == ResourceType.SUBGROUP,
            )
            .order_by(Resource.name.asc(), Resource.id.asc())
        )
        if company_id is not None:
            statement = statement.where(Resource.company_id == company_id)
        return list(self.session.scalars(statement).all())

    def delete_group_with_subgroups(self, group_id: int) -> bool:
        group = self.get_resource(group_id)
        if group is None:
            return False

        subgroups = self.list_subgroups(group_id=group_id)
        for subgroup in subgroups:
            self.session.delete(subgroup)

        self.session.delete(group)
        self.session.flush()
        return True
