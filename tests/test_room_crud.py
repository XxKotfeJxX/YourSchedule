import pytest
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
