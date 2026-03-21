import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.requirement_controller import RequirementController
from app.controllers.resource_controller import ResourceController
from app.domain.base import Base
from app.domain.enums import ResourceType, RoomType
from app.domain.models import Building, Company, RoomProfile


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


def test_requirement_crud_operations(session: Session) -> None:
    controller = RequirementController(session=session)

    requirement = controller.create_requirement(
        name="Physics Lecture",
        duration_blocks=2,
        sessions_total=8,
        max_per_week=2,
    )
    session.commit()

    requirements = controller.list_requirements()
    assert len(requirements) == 1
    assert requirements[0].id == requirement.id

    updated = controller.update_requirement(
        requirement.id,
        name="Advanced Physics Lecture",
        duration_blocks=3,
        sessions_total=9,
        max_per_week=3,
    )
    session.commit()

    assert updated.name == "Advanced Physics Lecture"
    assert updated.duration_blocks == 3
    assert updated.sessions_total == 9
    assert updated.max_per_week == 3

    loaded = controller.get_requirement(requirement.id)
    assert loaded is not None
    assert loaded.name == "Advanced Physics Lecture"

    deleted = controller.delete_requirement(requirement.id)
    session.commit()
    assert deleted is True
    assert controller.get_requirement(requirement.id) is None
    assert controller.delete_requirement(999_999) is False


def test_assign_and_unassign_requirement_resources(session: Session) -> None:
    requirement_controller = RequirementController(session=session)
    resource_controller = ResourceController(session=session)

    teacher = resource_controller.create_resource(
        name="Dr. Shevchenko",
        resource_type=ResourceType.TEACHER,
    )
    room = resource_controller.create_resource(
        name="Auditorium 1",
        resource_type=ResourceType.ROOM,
    )
    requirement = requirement_controller.create_requirement(
        name="Chemistry Lab",
        duration_blocks=2,
        sessions_total=6,
        max_per_week=2,
    )
    session.commit()

    requirement_controller.assign_resource(requirement.id, teacher.id, "LECTOR")
    requirement_controller.assign_resource(requirement.id, room.id, "LOCATION")
    session.commit()

    assigned = requirement_controller.list_requirement_resources(requirement.id)
    assert len(assigned) == 2
    assert {(item.resource_id, item.role) for item in assigned} == {
        (teacher.id, "LECTOR"),
        (room.id, "LOCATION"),
    }

    unassigned = requirement_controller.unassign_resource(requirement.id, teacher.id, "LECTOR")
    session.commit()
    assert unassigned is True

    remaining = requirement_controller.list_requirement_resources(requirement.id)
    assert len(remaining) == 1
    assert remaining[0].resource_id == room.id
    assert remaining[0].role == "LOCATION"

    assert requirement_controller.unassign_resource(requirement.id, teacher.id, "LECTOR") is False


def test_requirement_resource_validation_and_uniqueness(session: Session) -> None:
    requirement_controller = RequirementController(session=session)
    resource_controller = ResourceController(session=session)

    teacher = resource_controller.create_resource(
        name="Dr. Bondar",
        resource_type=ResourceType.TEACHER,
    )
    requirement = requirement_controller.create_requirement(
        name="Math Seminar",
        duration_blocks=1,
        sessions_total=10,
        max_per_week=2,
    )
    session.commit()

    requirement_controller.assign_resource(requirement.id, teacher.id, "LECTOR")
    session.commit()

    with pytest.raises(IntegrityError):
        requirement_controller.assign_resource(requirement.id, teacher.id, "LECTOR")

    session.rollback()

    with pytest.raises(ValueError):
        requirement_controller.assign_resource(999_999, teacher.id, "LECTOR")

    with pytest.raises(ValueError):
        requirement_controller.assign_resource(requirement.id, 999_999, "LECTOR")


def test_requirement_room_constraints_and_fixed_room(session: Session) -> None:
    requirement_controller = RequirementController(session=session)
    resource_controller = ResourceController(session=session)

    company = Company(name="Room Constraints Company")
    session.add(company)
    session.flush()

    building = Building(company_id=company.id, name="Main Building")
    session.add(building)
    session.flush()

    room_resource = resource_controller.create_resource(
        name="Lab 301",
        resource_type=ResourceType.ROOM,
        company_id=company.id,
    )
    session.flush()

    room_profile = RoomProfile(
        company_id=company.id,
        building_id=building.id,
        resource_id=room_resource.id,
        name="301",
        room_type=RoomType.LAB,
        capacity=24,
        has_projector=True,
    )
    session.add(room_profile)
    session.commit()

    requirement = requirement_controller.create_requirement(
        name="Electronics Lab",
        duration_blocks=2,
        sessions_total=6,
        max_per_week=2,
        company_id=company.id,
        room_type=RoomType.LAB,
        min_capacity=20,
        needs_projector=True,
        fixed_room_id=room_profile.id,
    )
    session.commit()

    assert requirement.room_type == RoomType.LAB
    assert requirement.min_capacity == 20
    assert requirement.needs_projector is True
    assert requirement.fixed_room_id == room_profile.id

    updated = requirement_controller.update_requirement(
        requirement.id,
        min_capacity=18,
        needs_projector=False,
        fixed_room_id=None,
    )
    session.commit()

    assert updated.min_capacity == 18
    assert updated.needs_projector is False
    assert updated.fixed_room_id is None


def test_requirement_rejects_incompatible_fixed_room(session: Session) -> None:
    requirement_controller = RequirementController(session=session)
    resource_controller = ResourceController(session=session)

    company = Company(name="Incompatible Room Company")
    session.add(company)
    session.flush()

    building = Building(company_id=company.id, name="Second Building")
    session.add(building)
    session.flush()

    room_resource = resource_controller.create_resource(
        name="Lecture 101",
        resource_type=ResourceType.ROOM,
        company_id=company.id,
    )
    session.flush()

    room_profile = RoomProfile(
        company_id=company.id,
        building_id=building.id,
        resource_id=room_resource.id,
        name="101",
        room_type=RoomType.LECTURE_HALL,
        capacity=120,
        has_projector=False,
    )
    session.add(room_profile)
    session.commit()

    with pytest.raises(ValueError):
        requirement_controller.create_requirement(
            name="Computer Networks",
            duration_blocks=1,
            sessions_total=8,
            max_per_week=2,
            company_id=company.id,
            room_type=RoomType.COMPUTER_LAB,
            needs_projector=True,
            fixed_room_id=room_profile.id,
        )
