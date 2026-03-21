from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.domain.enums import ResourceType, RoomType
from app.domain.models import Building, Department, Resource, RoomBooking, RoomProfile

_UNSET = object()


class RoomRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

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
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Room name is required")

        building = self.session.get(Building, building_id)
        if building is None:
            raise ValueError(f"Building with id={building_id} was not found")

        owner_company_id = company_id if company_id is not None else building.company_id
        self._validate_department_reference(
            home_department_id=home_department_id,
            owner_company_id=owner_company_id,
        )
        resource_name = self._build_resource_name(building_name=building.name, room_name=clean_name)

        resource = Resource(
            company_id=owner_company_id,
            name=resource_name,
            type=ResourceType.ROOM,
        )
        self.session.add(resource)
        self.session.flush()

        room = RoomProfile(
            company_id=owner_company_id,
            building_id=building_id,
            home_department_id=home_department_id,
            resource_id=resource.id,
            name=clean_name,
            room_type=room_type,
            capacity=capacity,
            floor=floor,
            has_projector=bool(has_projector),
            is_archived=False,
        )
        self.session.add(room)
        self.session.flush()
        return room

    def get_room(self, room_id: int) -> RoomProfile | None:
        return self.session.get(RoomProfile, room_id)

    def get_room_by_name(
        self,
        *,
        building_id: int,
        name: str,
        include_archived: bool = True,
    ) -> RoomProfile | None:
        statement = select(RoomProfile).where(
            and_(
                RoomProfile.building_id == building_id,
                func.lower(RoomProfile.name) == name.strip().lower(),
            )
        )
        if not include_archived:
            statement = statement.where(RoomProfile.is_archived.is_(False))
        return self.session.scalar(statement)

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
        statement = select(RoomProfile).order_by(RoomProfile.name.asc(), RoomProfile.id.asc())
        if building_id is not None:
            statement = statement.where(RoomProfile.building_id == building_id)
        if company_id is not None:
            statement = statement.where(RoomProfile.company_id == company_id)
        if not include_archived:
            statement = statement.where(RoomProfile.is_archived.is_(False))
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(RoomProfile.name.ilike(pattern))
        if room_type is not None:
            statement = statement.where(RoomProfile.room_type == room_type)
        if min_capacity is not None:
            statement = statement.where(
                and_(
                    RoomProfile.capacity.is_not(None),
                    RoomProfile.capacity >= min_capacity,
                )
            )
        if has_projector is not None:
            statement = statement.where(RoomProfile.has_projector.is_(bool(has_projector)))
        if home_department_id is not None:
            statement = statement.where(RoomProfile.home_department_id == home_department_id)
        return list(self.session.scalars(statement).all())

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
        room = self.get_room(room_id)
        if room is None:
            raise ValueError(f"Room with id={room_id} was not found")

        if name is not _UNSET:
            clean_name = str(name).strip()
            if not clean_name:
                raise ValueError("Room name is required")
            room.name = clean_name
        if room_type is not _UNSET:
            room.room_type = room_type
        if capacity is not _UNSET:
            room.capacity = capacity
        if floor is not _UNSET:
            room.floor = floor
        if has_projector is not _UNSET:
            room.has_projector = bool(has_projector)
        if home_department_id is not _UNSET:
            self._validate_department_reference(
                home_department_id=home_department_id,
                owner_company_id=room.company_id,
            )
            room.home_department_id = home_department_id
        if is_archived is not _UNSET:
            room.is_archived = is_archived

        if name is not _UNSET:
            building = self.session.get(Building, room.building_id)
            if building is not None:
                resource = self.session.get(Resource, room.resource_id)
                if resource is not None:
                    resource.name = self._build_resource_name(building_name=building.name, room_name=room.name)

        self.session.flush()
        return room

    def archive_room(self, room_id: int) -> RoomProfile:
        return self.update_room(room_id, is_archived=True)

    def unarchive_room(self, room_id: int) -> RoomProfile:
        return self.update_room(room_id, is_archived=False)

    def create_room_booking(
        self,
        *,
        room_id: int,
        starts_at: datetime,
        ends_at: datetime,
        title: str | None = None,
    ) -> RoomBooking:
        room = self.get_room(room_id)
        if room is None:
            raise ValueError(f"Room with id={room_id} was not found")
        if room.is_archived:
            raise ValueError("Cannot book an archived room")
        if ends_at <= starts_at:
            raise ValueError("Booking end time must be after start time")

        overlapping = self.session.scalar(
            select(RoomBooking.id).where(
                and_(
                    RoomBooking.room_id == room_id,
                    RoomBooking.is_cancelled.is_(False),
                    RoomBooking.starts_at < ends_at,
                    RoomBooking.ends_at > starts_at,
                )
            )
        )
        if overlapping is not None:
            raise ValueError("Room is already booked for the selected time range")

        booking = RoomBooking(
            room_id=room_id,
            title=(title or "").strip() or None,
            starts_at=starts_at,
            ends_at=ends_at,
            is_cancelled=False,
        )
        self.session.add(booking)
        self.session.flush()
        return booking

    def upcoming_booking_map(
        self,
        room_ids: list[int],
        *,
        reference_time: datetime | None = None,
    ) -> dict[int, RoomBooking]:
        if not room_ids:
            return {}

        now = reference_time or datetime.utcnow()
        bookings = list(
            self.session.scalars(
                select(RoomBooking)
                .where(
                    and_(
                        RoomBooking.room_id.in_(room_ids),
                        RoomBooking.is_cancelled.is_(False),
                        RoomBooking.ends_at >= now,
                    )
                )
                .order_by(RoomBooking.room_id.asc(), RoomBooking.starts_at.asc(), RoomBooking.id.asc())
            ).all()
        )

        result: dict[int, RoomBooking] = {}
        for booking in bookings:
            if booking.room_id not in result:
                result[booking.room_id] = booking
        return result

    def delete_room(self, room_id: int) -> bool:
        room = self.get_room(room_id)
        if room is None:
            return False

        resource = self.session.get(Resource, room.resource_id)
        self.session.delete(room)
        if resource is not None:
            self.session.delete(resource)
        self.session.flush()
        return True

    def _build_resource_name(self, *, building_name: str, room_name: str) -> str:
        clean_building = building_name.strip() or "Building"
        clean_room = room_name.strip() or "Room"
        return f"{clean_building}:{clean_room}"

    def _validate_department_reference(
        self,
        *,
        home_department_id: int | None | object,
        owner_company_id: int | None,
    ) -> None:
        if home_department_id in (_UNSET, None):
            return
        department = self.session.get(Department, int(home_department_id))
        if department is None:
            raise ValueError(f"Department with id={home_department_id} was not found")
        if (
            owner_company_id is not None
            and department.company_id is not None
            and owner_company_id != department.company_id
        ):
            raise ValueError("Room and department belong to different companies")
