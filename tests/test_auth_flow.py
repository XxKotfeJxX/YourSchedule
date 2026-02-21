import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.auth_controller import AuthController
from app.controllers.resource_controller import ResourceController
from app.domain.base import Base
from app.domain.enums import ResourceType, UserRole


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


def test_bootstrap_and_authenticate_company_user(session: Session) -> None:
    controller = AuthController(session=session)

    assert controller.has_company_account() is False

    user = controller.bootstrap_company_account(
        company_name="Acme",
        username="owner",
        password="pass1234",
    )
    session.commit()

    assert user.role == UserRole.COMPANY
    assert controller.has_company_account() is True

    auth_ok = controller.authenticate(username="owner", password="pass1234")
    auth_fail = controller.authenticate(username="owner", password="wrong")
    assert auth_ok is not None
    assert auth_fail is None


def test_create_personal_user_bound_to_group_resource(session: Session) -> None:
    auth = AuthController(session=session)
    company_user = auth.bootstrap_company_account(
        company_name="School",
        username="school_admin",
        password="admin_pass",
    )
    session.flush()

    group = ResourceController(session=session).create_resource(
        name="Group A",
        resource_type=ResourceType.GROUP,
        company_id=company_user.company_id,
    )
    session.flush()

    personal = auth.create_personal_user(
        company_id=company_user.company_id,
        username="student1",
        password="student_pass",
        resource_id=group.id,
    )
    session.commit()

    assert personal.role == UserRole.PERSONAL
    assert personal.resource_id == group.id
    assert personal.company_id == company_user.company_id
