import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.requirement_controller import RequirementController
from app.controllers.resource_controller import ResourceController
from app.domain.base import Base
from app.domain.enums import ResourceType


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
