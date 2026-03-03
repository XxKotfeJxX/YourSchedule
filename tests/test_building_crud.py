import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.building_controller import BuildingController
from app.domain.base import Base
from app.domain.models import Company


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


def test_building_crud_and_company_filter(session: Session) -> None:
    company_a = Company(name="A")
    company_b = Company(name="B")
    session.add_all([company_a, company_b])
    session.commit()

    controller = BuildingController(session=session)
    created = controller.create_building(
        name="Main Building",
        address="Main st, 1",
        company_id=company_a.id,
    )
    controller.create_building(
        name="Remote Building",
        address=None,
        company_id=company_b.id,
    )
    session.commit()

    listed = controller.list_buildings(company_id=company_a.id)
    assert len(listed) == 1
    assert listed[0].id == created.id
    assert listed[0].name == "Main Building"

    updated = controller.update_building(
        created.id,
        name="Main Building Updated",
        address="Main st, 2",
    )
    session.commit()
    assert updated.name == "Main Building Updated"
    assert updated.address == "Main st, 2"

    controller.archive_building(created.id)
    session.commit()
    assert controller.list_buildings(company_id=company_a.id) == []
    assert len(controller.list_buildings(company_id=company_a.id, include_archived=True)) == 1


def test_building_name_unique_per_company(session: Session) -> None:
    company = Company(name="University")
    session.add(company)
    session.commit()

    controller = BuildingController(session=session)
    controller.create_building(name="A", company_id=company.id)
    session.commit()

    with pytest.raises(IntegrityError):
        controller.create_building(name="A", company_id=company.id)

    session.rollback()
