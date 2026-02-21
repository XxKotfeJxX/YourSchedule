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


def test_register_user_company_or_personal(session: Session) -> None:
    controller = AuthController(session=session)

    company_user = controller.register_user(
        username="org_admin",
        password="org_pass",
        company_name="OrgName",
    )
    personal_user = controller.register_user(
        username="solo_user",
        password="solo_pass",
    )
    session.commit()

    assert company_user.role == UserRole.COMPANY
    assert personal_user.role == UserRole.PERSONAL
    assert personal_user.resource_id is None
    assert personal_user.subgroup_id is None


def test_group_users_include_subgroup_assignments(session: Session) -> None:
    auth = AuthController(session=session)
    company_user = auth.bootstrap_company_account(
        company_name="School X",
        username="school_admin_x",
        password="admin_pass_x",
    )
    session.flush()

    resources = ResourceController(session=session)
    group = resources.create_resource(
        name="Group X",
        resource_type=ResourceType.GROUP,
        company_id=company_user.company_id,
    )
    subgroup = resources.create_resource(
        name="Group X::Sub 1",
        resource_type=ResourceType.SUBGROUP,
        company_id=company_user.company_id,
        parent_group_id=group.id,
    )
    session.flush()

    user_a = auth.create_personal_user(
        company_id=company_user.company_id,
        username="student_x_a",
        password="student_pass",
        resource_id=group.id,
    )
    user_b = auth.create_personal_user(
        company_id=company_user.company_id,
        username="student_x_b",
        password="student_pass",
        resource_id=group.id,
    )
    session.flush()

    auth.update_user_membership(
        user_b.id,
        resource_id=group.id,
        subgroup_id=subgroup.id,
    )
    session.commit()

    users = auth.list_group_users(
        company_id=company_user.company_id,
        group_id=group.id,
        subgroup_ids=[subgroup.id],
    )
    assert {item.id for item in users} == {user_a.id, user_b.id}
    assigned = {item.id: item.subgroup_id for item in users}
    assert assigned[user_a.id] is None
    assert assigned[user_b.id] == subgroup.id


def test_available_personal_users_include_standalone_accounts(session: Session) -> None:
    auth = AuthController(session=session)
    company_user = auth.bootstrap_company_account(
        company_name="Target Org",
        username="target_admin",
        password="target_pass",
    )
    standalone = auth.register_user(
        username="standalone_personal",
        password="standalone_pass",
    )
    other_company_admin = auth.bootstrap_company_account(
        company_name="Other Org",
        username="other_admin",
        password="other_pass",
    )
    other_company_personal = auth.create_personal_user(
        company_id=other_company_admin.company_id,
        username="other_member",
        password="other_member_pass",
    )
    session.commit()

    available = auth.list_available_personal_users_for_company(company_id=company_user.company_id)
    available_ids = {item.id for item in available}
    assert standalone.id in available_ids
    assert other_company_personal.id not in available_ids


def test_reassign_standalone_personal_to_company_and_attach_to_group(session: Session) -> None:
    auth = AuthController(session=session)
    company_user = auth.bootstrap_company_account(
        company_name="School Attach",
        username="attach_admin",
        password="attach_pass",
    )
    group = ResourceController(session=session).create_resource(
        name="Attach Group",
        resource_type=ResourceType.GROUP,
        company_id=company_user.company_id,
    )
    standalone = auth.register_user(
        username="attach_personal",
        password="attach_personal_pass",
    )
    session.flush()

    moved = auth.reassign_personal_user_company(user_id=standalone.id, company_id=company_user.company_id)
    auth.update_user_membership(
        moved.id,
        resource_id=group.id,
        subgroup_id=None,
    )
    session.commit()

    users = auth.list_group_users(
        company_id=company_user.company_id,
        group_id=group.id,
        subgroup_ids=[],
    )
    user_ids = {item.id for item in users}
    assert moved.id in user_ids
