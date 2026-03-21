from sqlalchemy.orm import Session

from datetime import datetime

from app.domain.enums import ResourceType
from app.domain.models import Resource, ResourceBlackout
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

    def create_blackout(
        self,
        resource_id: int,
        *,
        starts_at: datetime,
        ends_at: datetime,
        title: str | None = None,
    ) -> ResourceBlackout:
        return self.repository.create_blackout(
            resource_id=resource_id,
            starts_at=starts_at,
            ends_at=ends_at,
            title=title,
        )

    def create_blackouts_batch(
        self,
        resource_id: int,
        *,
        intervals: list[tuple[datetime, datetime, str | None]],
    ) -> list[ResourceBlackout]:
        return self.repository.create_blackouts_batch(
            resource_id=resource_id,
            intervals=intervals,
        )

    def get_blackout(self, blackout_id: int) -> ResourceBlackout | None:
        return self.repository.get_blackout(blackout_id=blackout_id)

    def list_blackouts(
        self,
        *,
        resource_id: int | None = None,
        company_id: int | None = None,
    ) -> list[ResourceBlackout]:
        return self.repository.list_blackouts(resource_id=resource_id, company_id=company_id)

    def update_blackout(
        self,
        blackout_id: int,
        *,
        starts_at: datetime | object = _UNSET,
        ends_at: datetime | object = _UNSET,
        title: str | None | object = _UNSET,
    ) -> ResourceBlackout:
        kwargs: dict[str, object] = {"blackout_id": blackout_id}
        if starts_at is not _UNSET:
            kwargs["starts_at"] = starts_at
        if ends_at is not _UNSET:
            kwargs["ends_at"] = ends_at
        if title is not _UNSET:
            kwargs["title"] = title
        return self.repository.update_blackout(**kwargs)

    def delete_blackout(self, blackout_id: int) -> bool:
        return self.repository.delete_blackout(blackout_id=blackout_id)
