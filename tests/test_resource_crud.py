import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.resource_controller import ResourceController
from app.domain.base import Base
from app.domain.enums import ResourceType
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


def test_resource_crud_operations(session: Session) -> None:
    controller = ResourceController(session=session)
    company = Company(name="Test Company A")
    session.add(company)
    session.flush()

    teacher = controller.create_resource(
        name="Dr. Kovalenko",
        resource_type=ResourceType.TEACHER,
        company_id=company.id,
    )
    room = controller.create_resource(
        name="Room 101",
        resource_type=ResourceType.ROOM,
        company_id=company.id,
    )
    session.commit()

    resources = controller.list_resources()
    assert [item.id for item in resources] == [teacher.id, room.id]

    only_teachers = controller.list_resources(
        resource_type=ResourceType.TEACHER,
        company_id=company.id,
    )
    assert len(only_teachers) == 1
    assert only_teachers[0].id == teacher.id

    updated = controller.update_resource(
        teacher.id,
        name="Prof. Kovalenko",
        resource_type=ResourceType.TEACHER,
    )
    session.commit()
    assert updated.name == "Prof. Kovalenko"
    assert updated.type == ResourceType.TEACHER

    loaded = controller.get_resource(teacher.id)
    assert loaded is not None
    assert loaded.name == "Prof. Kovalenko"

    deleted = controller.delete_resource(room.id)
    session.commit()
    assert deleted is True
    assert controller.get_resource(room.id) is None

    assert controller.delete_resource(999_999) is False


def test_resource_name_type_unique_constraint(session: Session) -> None:
    controller = ResourceController(session=session)
    company = Company(name="Test Company B")
    session.add(company)
    session.flush()

    controller.create_resource(
        name="Group A",
        resource_type=ResourceType.GROUP,
        company_id=company.id,
    )
    session.commit()

    with pytest.raises(IntegrityError):
        controller.create_resource(
            name="Group A",
            resource_type=ResourceType.GROUP,
            company_id=company.id,
        )


def test_same_name_allowed_for_different_types(session: Session) -> None:
    controller = ResourceController(session=session)
    company = Company(name="Test Company C")
    session.add(company)
    session.flush()

    controller.create_resource(name="A-12", resource_type=ResourceType.ROOM, company_id=company.id)
    controller.create_resource(name="A-12", resource_type=ResourceType.GROUP, company_id=company.id)
    session.commit()

    resources = session.query(Resource).order_by(Resource.id.asc()).all()
    assert len(resources) == 2


def test_subgroup_listing_and_group_delete_with_subgroups(session: Session) -> None:
    controller = ResourceController(session=session)
    company = Company(name="Test Company D")
    session.add(company)
    session.flush()

    group = controller.create_resource(
        name="Group D",
        resource_type=ResourceType.GROUP,
        company_id=company.id,
    )
    subgroup = controller.create_resource(
        name="Group D::Sub 1",
        resource_type=ResourceType.SUBGROUP,
        company_id=company.id,
        parent_group_id=group.id,
    )
    session.commit()

    subgroups = controller.list_subgroups(group_id=group.id, company_id=company.id)
    assert [item.id for item in subgroups] == [subgroup.id]

    deleted = controller.delete_group_with_subgroups(group.id)
    session.commit()
    assert deleted is True
    assert controller.get_resource(group.id) is None
    assert controller.get_resource(subgroup.id) is None
