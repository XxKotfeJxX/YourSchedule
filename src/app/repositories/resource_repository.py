from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ResourceType
from app.domain.models import Resource, ResourceBlackout, Stream

_UNSET = object()


class ResourceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_resource(
        self,
        name: str,
        resource_type: ResourceType,
        company_id: int | None = None,
        parent_group_id: int | None = None,
        stream_id: int | None = None,
    ) -> Resource:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Resource name is required")

        resolved_stream_id = stream_id
        parent_group: Resource | None = None
        resolved_company_id = company_id
        if parent_group_id is not None:
            parent_group = self.get_resource(parent_group_id)
            if parent_group is None:
                raise ValueError(f"Parent group with id={parent_group_id} was not found")
            if parent_group.type != ResourceType.GROUP:
                raise ValueError("Only GROUP resource can be a parent for subgroup")
            resolved_stream_id = parent_group.stream_id
            if resolved_company_id is None:
                resolved_company_id = parent_group.company_id

        if resource_type == ResourceType.GROUP and parent_group_id is not None:
            raise ValueError("Group cannot have parent_group_id")
        if resource_type == ResourceType.SUBGROUP and parent_group_id is None:
            raise ValueError("Subgroup requires parent_group_id")
        if resource_type not in {ResourceType.GROUP, ResourceType.SUBGROUP} and stream_id is not None:
            raise ValueError("stream_id is supported only for GROUP/SUBGROUP resources")

        if parent_group is not None and company_id is not None and parent_group.company_id is not None:
            if parent_group.company_id != company_id:
                raise ValueError("Parent group and subgroup must belong to the same company")
        owner_company_id = resolved_company_id

        if resolved_stream_id is not None:
            stream = self._validate_stream_reference(
                stream_id=resolved_stream_id,
                owner_company_id=owner_company_id,
            )
            resolved_stream_id = stream.id

        resource = Resource(
            company_id=owner_company_id,
            parent_group_id=parent_group_id,
            stream_id=resolved_stream_id,
            name=clean_name,
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
        stream_id: int | None = None,
    ) -> list[Resource]:
        statement = select(Resource).order_by(Resource.name.asc(), Resource.id.asc())
        if resource_type is not None:
            statement = statement.where(Resource.type == resource_type)
        if company_id is not None:
            statement = statement.where(Resource.company_id == company_id)
        if parent_group_id is not None:
            statement = statement.where(Resource.parent_group_id == parent_group_id)
        if stream_id is not None:
            statement = statement.where(Resource.stream_id == stream_id)
        return list(self.session.scalars(statement).all())

    def update_resource(
        self,
        resource_id: int,
        *,
        name: str | None = None,
        resource_type: ResourceType | None = None,
        stream_id: int | None | object = _UNSET,
    ) -> Resource:
        resource = self.get_resource(resource_id)
        if resource is None:
            raise ValueError(f"Resource with id={resource_id} was not found")

        stream_was_updated = False
        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise ValueError("Resource name is required")
            resource.name = clean_name
        if resource_type is not None:
            resource.type = resource_type
        if stream_id is not _UNSET:
            if resource.type not in {ResourceType.GROUP, ResourceType.SUBGROUP}:
                raise ValueError("stream_id is supported only for GROUP/SUBGROUP resources")
            if resource.type == ResourceType.SUBGROUP and stream_id is None and resource.parent_group_id is not None:
                parent_group = self.get_resource(resource.parent_group_id)
                resource.stream_id = parent_group.stream_id if parent_group is not None else None
            else:
                if stream_id is None:
                    resource.stream_id = None
                else:
                    stream = self._validate_stream_reference(
                        stream_id=stream_id,
                        owner_company_id=resource.company_id,
                    )
                    resource.stream_id = stream.id
            stream_was_updated = True

        # Keep subgroup stream links consistent when group stream changes.
        if stream_was_updated and resource.type == ResourceType.GROUP:
            for subgroup in self.list_subgroups(group_id=resource.id):
                subgroup.stream_id = resource.stream_id

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

    def create_blackout(
        self,
        resource_id: int,
        *,
        starts_at: datetime,
        ends_at: datetime,
        title: str | None = None,
    ) -> ResourceBlackout:
        resource = self.get_resource(resource_id)
        if resource is None:
            raise ValueError(f"Resource with id={resource_id} was not found")
        if ends_at <= starts_at:
            raise ValueError("Blackout ends_at must be greater than starts_at")

        blackout = ResourceBlackout(
            resource_id=resource_id,
            starts_at=starts_at,
            ends_at=ends_at,
            title=(title or "").strip() or None,
        )
        self.session.add(blackout)
        self.session.flush()
        return blackout

    def create_blackouts_batch(
        self,
        resource_id: int,
        *,
        intervals: list[tuple[datetime, datetime, str | None]],
    ) -> list[ResourceBlackout]:
        resource = self.get_resource(resource_id)
        if resource is None:
            raise ValueError(f"Resource with id={resource_id} was not found")
        if not intervals:
            return []

        created: list[ResourceBlackout] = []
        for starts_at, ends_at, title in intervals:
            if ends_at <= starts_at:
                raise ValueError("Blackout ends_at must be greater than starts_at")
            blackout = ResourceBlackout(
                resource_id=resource_id,
                starts_at=starts_at,
                ends_at=ends_at,
                title=(title or "").strip() or None,
            )
            self.session.add(blackout)
            created.append(blackout)
        self.session.flush()
        return created

    def get_blackout(self, blackout_id: int) -> ResourceBlackout | None:
        return self.session.get(ResourceBlackout, blackout_id)

    def list_blackouts(
        self,
        *,
        resource_id: int | None = None,
        company_id: int | None = None,
    ) -> list[ResourceBlackout]:
        statement = (
            select(ResourceBlackout)
            .join(Resource, ResourceBlackout.resource_id == Resource.id)
            .order_by(ResourceBlackout.starts_at.asc(), ResourceBlackout.id.asc())
        )
        if resource_id is not None:
            statement = statement.where(ResourceBlackout.resource_id == resource_id)
        if company_id is not None:
            statement = statement.where(Resource.company_id == company_id)
        return list(self.session.scalars(statement).all())

    def update_blackout(
        self,
        blackout_id: int,
        *,
        starts_at: datetime | object = _UNSET,
        ends_at: datetime | object = _UNSET,
        title: str | None | object = _UNSET,
    ) -> ResourceBlackout:
        blackout = self.get_blackout(blackout_id)
        if blackout is None:
            raise ValueError(f"ResourceBlackout with id={blackout_id} was not found")

        new_starts_at = blackout.starts_at if starts_at is _UNSET else starts_at
        new_ends_at = blackout.ends_at if ends_at is _UNSET else ends_at
        if new_starts_at is None or new_ends_at is None:
            raise ValueError("Blackout starts_at and ends_at must be provided")
        if new_ends_at <= new_starts_at:
            raise ValueError("Blackout ends_at must be greater than starts_at")

        blackout.starts_at = new_starts_at
        blackout.ends_at = new_ends_at
        if title is not _UNSET:
            blackout.title = (title or "").strip() or None

        self.session.flush()
        return blackout

    def delete_blackout(self, blackout_id: int) -> bool:
        blackout = self.get_blackout(blackout_id)
        if blackout is None:
            return False
        self.session.delete(blackout)
        self.session.flush()
        return True

    def _validate_stream_reference(self, *, stream_id: int, owner_company_id: int | None) -> Stream:
        stream = self.session.get(Stream, int(stream_id))
        if stream is None:
            raise ValueError(f"Stream with id={stream_id} was not found")
        if owner_company_id is not None and stream.company_id is not None and owner_company_id != stream.company_id:
            raise ValueError("Resource and stream must belong to the same company")
        return stream
