import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.building_controller import BuildingController
from app.controllers.room_controller import RoomController
from app.domain.base import Base
from app.domain.enums import RoomType
from app.domain.models import Company, Resource


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_room_crud_filters_and_resource_sync(session: Session) -> None:
    company = Company(name="University")
    session.add(company)
    session.commit()

    building = BuildingController(session=session).create_building(
        name="Main",
        address="Street 1",
        company_id=company.id,
    )
    session.commit()

    controller = RoomController(session=session)
    created = controller.create_room(
        building_id=building.id,
        name="101",
        room_type=RoomType.CLASSROOM,
        capacity=32,
        floor=1,
        company_id=company.id,
    )
    controller.create_room(
        building_id=building.id,
        name="Lab-1",
        room_type=RoomType.LAB,
        capacity=18,
        floor=2,
        company_id=company.id,
    )
    session.commit()

    all_rooms = controller.list_rooms(building_id=building.id)
    assert len(all_rooms) == 2

    by_type = controller.list_rooms(building_id=building.id, room_type=RoomType.CLASSROOM)
    assert len(by_type) == 1
    assert by_type[0].id == created.id

    by_capacity = controller.list_rooms(building_id=building.id, min_capacity=20)
    assert len(by_capacity) == 1
    assert by_capacity[0].id == created.id

    by_search = controller.list_rooms(building_id=building.id, search="lab")
    assert len(by_search) == 1
    assert by_search[0].name == "Lab-1"

    updated = controller.update_room(
        created.id,
        name="101A",
        capacity=None,
        floor=None,
    )
    session.commit()
    assert updated.name == "101A"
    assert updated.capacity is None
    assert updated.floor is None

    resource = session.get(Resource, updated.resource_id)
    assert resource is not None
    assert resource.name == "Main:101A"

    assert controller.delete_room(updated.id) is True
    session.commit()
    assert controller.get_room(updated.id) is None
    assert session.get(Resource, updated.resource_id) is None


def test_bulk_create_rooms_with_duplicate_policies(session: Session) -> None:
    company = Company(name="School")
    session.add(company)
    session.commit()

    building = BuildingController(session=session).create_building(
        name="A",
        address=None,
        company_id=company.id,
    )
    session.commit()

    controller = RoomController(session=session)
    existing = controller.create_room(
        building_id=building.id,
        name="201",
        room_type=RoomType.CLASSROOM,
        company_id=company.id,
    )
    controller.archive_room(existing.id)
    session.commit()

    result_skip = controller.bulk_create_rooms(
        building_id=building.id,
        names=["201", "202", "202", "203"],
        room_type=RoomType.CLASSROOM,
        capacity=24,
        duplicate_policy="skip",
        company_id=company.id,
    )
    session.commit()
    assert result_skip == {"created": 2, "skipped": 1, "updated": 0}

    with pytest.raises(ValueError):
        controller.bulk_create_rooms(
            building_id=building.id,
            names=["201"],
            room_type=RoomType.CLASSROOM,
            duplicate_policy="fail",
            company_id=company.id,
        )

    result_update = controller.bulk_create_rooms(
        building_id=building.id,
        names=["201"],
        room_type=RoomType.LAB,
        capacity=12,
        floor=3,
        duplicate_policy="update",
        company_id=company.id,
    )
    session.commit()
    assert result_update == {"created": 0, "skipped": 0, "updated": 1}

    refreshed = controller.list_rooms(
        building_id=building.id,
        search="201",
        include_archived=True,
    )[0]
    assert refreshed.is_archived is False
    assert refreshed.room_type == RoomType.LAB
    assert refreshed.capacity == 12
    assert refreshed.floor == 3


def test_room_archive_toggle_and_manual_booking(session: Session) -> None:
    company = Company(name="Bookings")
    session.add(company)
    session.commit()

    building = BuildingController(session=session).create_building(
        name="B",
        address=None,
        company_id=company.id,
    )
    session.commit()

    controller = RoomController(session=session)
    room = controller.create_room(
        building_id=building.id,
        name="301",
        room_type=RoomType.CLASSROOM,
        company_id=company.id,
    )
    session.commit()

    controller.archive_room(room.id)
    session.commit()
    archived = controller.get_room(room.id)
    assert archived is not None
    assert archived.is_archived is True

    with pytest.raises(ValueError):
        controller.create_room_booking(
            room_id=room.id,
            starts_at=datetime.utcnow() + timedelta(hours=1),
            ends_at=datetime.utcnow() + timedelta(hours=2),
            title="Cannot book archived",
        )

    controller.unarchive_room(room.id)
    session.commit()
    active = controller.get_room(room.id)
    assert active is not None
    assert active.is_archived is False

    starts_at = datetime.utcnow() + timedelta(hours=1)
    ends_at = starts_at + timedelta(hours=2)
    created_booking = controller.create_room_booking(
        room_id=room.id,
        starts_at=starts_at,
        ends_at=ends_at,
        title="Event",
    )
    session.commit()
    assert created_booking.id is not None

    with pytest.raises(ValueError):
        controller.create_room_booking(
            room_id=room.id,
            starts_at=starts_at + timedelta(minutes=30),
            ends_at=ends_at + timedelta(minutes=30),
            title="Overlap",
        )

    booking_map = controller.upcoming_booking_map([room.id], reference_time=datetime.utcnow())
    assert room.id in booking_map
    assert booking_map[room.id].id == created_booking.id
