from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.enums import RoomType
from app.domain.models import RoomBooking, RoomProfile
from app.repositories.room_repository import RoomRepository

_UNSET = object()


class RoomController:
    def __init__(self, session: Session) -> None:
        self.repository = RoomRepository(session=session)

    def create_room(
        self,
        *,
        building_id: int,
        name: str,
        room_type: RoomType,
        capacity: int | None = None,
        floor: int | None = None,
        has_projector: bool = False,
        home_department_id: int | None = None,
        company_id: int | None = None,
    ) -> RoomProfile:
        return self.repository.create_room(
            building_id=building_id,
            name=name,
            room_type=room_type,
            capacity=capacity,
            floor=floor,
            has_projector=has_projector,
            home_department_id=home_department_id,
            company_id=company_id,
        )

    def bulk_create_rooms(
        self,
        *,
        building_id: int,
        names: list[str],
        room_type: RoomType,
        capacity: int | None = None,
        floor: int | None = None,
        has_projector: bool = False,
        home_department_id: int | None = None,
        company_id: int | None = None,
        duplicate_policy: str = "skip",
    ) -> dict[str, int]:
        policy = duplicate_policy.strip().lower()
        if policy not in {"skip", "fail", "update"}:
            raise ValueError("Unsupported duplicate policy")

        created = 0
        skipped = 0
        updated = 0

        seen_names: set[str] = set()
        for raw_name in names:
            clean_name = raw_name.strip()
            if not clean_name:
                continue

            normalized = clean_name.casefold()
            if normalized in seen_names:
                continue
            seen_names.add(normalized)

            existing = self.repository.get_room_by_name(
                building_id=building_id,
                name=clean_name,
                include_archived=True,
            )
            if existing is None:
                self.repository.create_room(
                    building_id=building_id,
                    name=clean_name,
                    room_type=room_type,
                    capacity=capacity,
                    floor=floor,
                    has_projector=has_projector,
                    home_department_id=home_department_id,
                    company_id=company_id,
                )
                created += 1
                continue

            if policy == "fail":
                raise ValueError(f"Room '{clean_name}' already exists in this building")
            if policy == "skip":
                skipped += 1
                continue

            self.repository.update_room(
                existing.id,
                name=clean_name,
                room_type=room_type,
                capacity=capacity,
                floor=floor,
                has_projector=has_projector,
                home_department_id=home_department_id,
                is_archived=False,
            )
            updated += 1

        return {"created": created, "skipped": skipped, "updated": updated}

    def get_room(self, room_id: int) -> RoomProfile | None:
        return self.repository.get_room(room_id)

    def list_rooms(
        self,
        *,
        building_id: int | None = None,
        company_id: int | None = None,
        include_archived: bool = False,
        search: str | None = None,
        room_type: RoomType | None = None,
        min_capacity: int | None = None,
        has_projector: bool | None = None,
        home_department_id: int | None = None,
    ) -> list[RoomProfile]:
        return self.repository.list_rooms(
            building_id=building_id,
            company_id=company_id,
            include_archived=include_archived,
            search=search,
            room_type=room_type,
            min_capacity=min_capacity,
            has_projector=has_projector,
            home_department_id=home_department_id,
        )

    def update_room(
        self,
        room_id: int,
        *,
        name: str | object = _UNSET,
        room_type: RoomType | object = _UNSET,
        capacity: int | None | object = _UNSET,
        floor: int | None | object = _UNSET,
        has_projector: bool | object = _UNSET,
        home_department_id: int | None | object = _UNSET,
        is_archived: bool | object = _UNSET,
    ) -> RoomProfile:
        kwargs = {}
        if name is not _UNSET:
            kwargs["name"] = name
        if room_type is not _UNSET:
            kwargs["room_type"] = room_type
        if capacity is not _UNSET:
            kwargs["capacity"] = capacity
        if floor is not _UNSET:
            kwargs["floor"] = floor
        if has_projector is not _UNSET:
            kwargs["has_projector"] = has_projector
        if home_department_id is not _UNSET:
            kwargs["home_department_id"] = home_department_id
        if is_archived is not _UNSET:
            kwargs["is_archived"] = is_archived
        return self.repository.update_room(room_id, **kwargs)

    def archive_room(self, room_id: int) -> RoomProfile:
        return self.repository.archive_room(room_id)

    def unarchive_room(self, room_id: int) -> RoomProfile:
        return self.repository.unarchive_room(room_id)

    def create_room_booking(
        self,
        *,
        room_id: int,
        starts_at: datetime,
        ends_at: datetime,
        title: str | None = None,
    ) -> RoomBooking:
        return self.repository.create_room_booking(
            room_id=room_id,
            starts_at=starts_at,
            ends_at=ends_at,
            title=title,
        )

    def upcoming_booking_map(
        self,
        room_ids: list[int],
        *,
        reference_time: datetime | None = None,
    ) -> dict[int, RoomBooking]:
        return self.repository.upcoming_booking_map(
            room_ids=room_ids,
            reference_time=reference_time,
        )

    def delete_room(self, room_id: int) -> bool:
        return self.repository.delete_room(room_id)
