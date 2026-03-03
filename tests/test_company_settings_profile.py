import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.auth_controller import AuthController
from app.domain.base import Base
from app.domain.models import CompanyProfile
from app.repositories.auth_repository import AuthRepository


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


def _bootstrap_company(session: Session, *, company_name: str, username: str) -> int:
    controller = AuthController(session=session)
    user = controller.bootstrap_company_account(
        company_name=company_name,
        username=username,
        password="pass1234",
    )
    session.commit()
    return user.company_id


def test_get_company_profile_is_idempotent(session: Session) -> None:
    company_id = _bootstrap_company(session, company_name="Idempotent Org", username="idem_admin")
    controller = AuthController(session=session)

    profile_a = controller.get_company_profile(company_id)
    profile_b = controller.get_company_profile(company_id)
    session.commit()

    count = session.scalar(
        select(func.count())
        .select_from(CompanyProfile)
        .where(CompanyProfile.company_id == company_id)
    )

    assert profile_a.id == profile_b.id
    assert count == 1


@pytest.mark.parametrize(
    ("company_name", "timezone", "expected_message"),
    [
        ("   ", "UTC", "Назва компанії обов'язкова."),
        ("New Name", "   ", "Часовий пояс обов'язковий."),
    ],
)
def test_update_company_profile_validates_required_fields(
    session: Session,
    company_name: str,
    timezone: str,
    expected_message: str,
) -> None:
    company_id = _bootstrap_company(session, company_name="Validation Org", username="validation_admin")
    controller = AuthController(session=session)

    with pytest.raises(ValueError, match=expected_message):
        controller.update_company_profile(
            company_id=company_id,
            company_name=company_name,
            timezone=timezone,
            theme="ocean",
        )


def test_update_company_profile_normalizes_values(session: Session) -> None:
    company_id = _bootstrap_company(session, company_name="Normalize Org", username="normalize_admin")
    controller = AuthController(session=session)

    company, profile = controller.update_company_profile(
        company_id=company_id,
        company_name="  Normalize Org Updated  ",
        timezone="  Europe/Warsaw  ",
        theme="SUNRISE",
    )
    session.commit()

    assert company.name == "Normalize Org Updated"
    assert profile.timezone == "Europe/Warsaw"
    assert profile.theme == "sunrise"


def test_update_company_profile_keeps_language_and_logo_if_not_provided(session: Session) -> None:
    company_id = _bootstrap_company(session, company_name="Keep Fields Org", username="keep_admin")
    repository = AuthRepository(session=session)
    repository.update_company_profile(
        company_id=company_id,
        timezone="UTC",
        theme="ocean",
        language="en",
        update_language=True,
        logo_path="assets/logo.png",
        update_logo_path=True,
    )
    session.commit()

    controller = AuthController(session=session)
    controller.update_company_profile(
        company_id=company_id,
        company_name="Keep Fields Org Updated",
        timezone="Europe/Kyiv",
        theme="graphite",
    )
    session.commit()

    profile = controller.get_company_profile(company_id)
    assert profile.language == "en"
    assert profile.logo_path == "assets/logo.png"
    assert profile.theme == "graphite"
    assert profile.timezone == "Europe/Kyiv"


def test_update_company_profile_updates_language(session: Session) -> None:
    company_id = _bootstrap_company(session, company_name="Language Org", username="lang_admin")
    controller = AuthController(session=session)

    _, profile = controller.update_company_profile(
        company_id=company_id,
        company_name="Language Org",
        timezone="UTC",
        theme="ocean",
        language="de",
    )
    session.commit()

    assert profile.language == "de"


def test_update_company_profile_can_clear_logo(session: Session) -> None:
    company_id = _bootstrap_company(session, company_name="Logo Org", username="logo_admin")
    repository = AuthRepository(session=session)
    repository.update_company_profile(
        company_id=company_id,
        timezone="UTC",
        theme="ocean",
        logo_path="storage/avatars/company_1/test.webp",
        update_logo_path=True,
    )
    session.commit()

    controller = AuthController(session=session)
    controller.update_company_profile(
        company_id=company_id,
        company_name="Logo Org",
        timezone="UTC",
        theme="ocean",
        update_logo_path=True,
        logo_path=None,
    )
    session.commit()

    profile = controller.get_company_profile(company_id)
    assert profile.logo_path is None
