from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.auth_controller import AuthController
from app.domain.base import Base
from app.repositories.template_repository import TemplateRepository
from app.services.empty_day_template_service import EmptyDayTemplateService


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return session_factory()


def _create_company(session: Session) -> int:
    user = AuthController(session=session).bootstrap_company_account(
        company_name="Template Org",
        username="template_admin",
        password="admin_pass",
    )
    session.flush()
    return int(user.company_id)


def test_ensure_empty_day_template_reuses_existing_non_archived() -> None:
    session = _build_session()
    try:
        company_id = _create_company(session)
        repository = TemplateRepository(session)
        existing = repository.create_day_pattern(
            company_id=company_id,
            name="Empty Day",
            mark_type_ids=[],
        )
        session.flush()

        resolved_id = EmptyDayTemplateService().ensure_empty_day_template(
            session=session,
            company_id=company_id,
        )

        assert resolved_id == existing.id
    finally:
        session.close()


def test_ensure_empty_day_template_creates_new_if_only_archived_exists() -> None:
    session = _build_session()
    try:
        company_id = _create_company(session)
        repository = TemplateRepository(session)
        archived = repository.create_day_pattern(
            company_id=company_id,
            name="Empty Day",
            mark_type_ids=[],
        )
        repository.archive_day_pattern(day_pattern_id=archived.id)
        session.flush()

        created_id = EmptyDayTemplateService().ensure_empty_day_template(
            session=session,
            company_id=company_id,
        )
        created = repository.get_day_pattern(created_id)

        assert created is not None
        assert created.id != archived.id
        assert created.is_archived is False
        assert len(created.items) == 0
        assert created.name == "Empty Day 2"
    finally:
        session.close()
