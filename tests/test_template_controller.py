from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.auth_controller import AuthController
from app.controllers.template_controller import TemplateController
from app.domain.base import Base
from app.domain.enums import MarkKind
from app.domain.models import CalendarPeriod, DayPattern


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


def _create_company(session: Session) -> int:
    user = AuthController(session=session).bootstrap_company_account(
        company_name="Template Org",
        username="template_admin",
        password="admin_pass",
    )
    session.flush()
    return user.company_id


def test_load_templates_overview_returns_all_levels(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)

    teach = controller.create_mark_type(
        company_id=company_id,
        name="Пара 45",
        kind=MarkKind.TEACHING,
        duration_minutes=45,
    )
    brk = controller.create_mark_type(
        company_id=company_id,
        name="Перерва 10",
        kind=MarkKind.BREAK,
        duration_minutes=10,
    )
    day = controller.create_day_template(
        company_id=company_id,
        name="Базовий день",
        mark_type_ids=[teach.id, brk.id, teach.id],
    )
    week = controller.create_week_template(
        company_id=company_id,
        name="Базовий тиждень",
        weekday_to_day_template_id={i: day.id for i in range(7)},
    )
    session.commit()

    overview = controller.load_templates_overview(company_id)

    assert len(overview.mark_types) == 2
    assert len(overview.day_templates) == 1
    assert len(overview.week_templates) == 1
    assert overview.day_templates[0].preview.total_blocks == 3
    assert overview.week_templates[0].id == week.id


def test_delete_mark_type_archives_instead_of_hard_delete(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)

    teach = controller.create_mark_type(
        company_id=company_id,
        name="Пара 50",
        kind=MarkKind.TEACHING,
        duration_minutes=50,
    )
    day = controller.create_day_template(
        company_id=company_id,
        name="День із використанням",
        mark_type_ids=[teach.id],
    )
    session.flush()

    archived = controller.delete_mark_type(company_id=company_id, mark_type_id=teach.id)
    session.commit()

    assert archived.is_archived is True
    assert session.get(DayPattern, day.id) is not None


def test_duplicate_day_template_creates_independent_copy(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)

    teach = controller.create_mark_type(
        company_id=company_id,
        name="Пара 45",
        kind=MarkKind.TEACHING,
        duration_minutes=45,
    )
    brk = controller.create_mark_type(
        company_id=company_id,
        name="Перерва 15",
        kind=MarkKind.BREAK,
        duration_minutes=15,
    )
    day = controller.create_day_template(
        company_id=company_id,
        name="Початковий день",
        mark_type_ids=[teach.id, brk.id],
    )
    duplicate = controller.duplicate_day_template(
        company_id=company_id,
        day_template_id=day.id,
    )
    session.flush()

    controller.update_day_template(
        company_id=company_id,
        day_template_id=day.id,
        mark_type_ids=[teach.id, teach.id, brk.id],
    )
    session.commit()

    refreshed_overview = controller.load_templates_overview(company_id)
    day_by_id = {item.id: item for item in refreshed_overview.day_templates}
    assert day_by_id[duplicate.id].mark_type_ids == (teach.id, brk.id)
    assert day_by_id[day.id].mark_type_ids == (teach.id, teach.id, brk.id)


def test_week_template_requires_full_week_mapping(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)
    mark = controller.create_mark_type(
        company_id=company_id,
        name="Пара 40",
        kind=MarkKind.TEACHING,
        duration_minutes=40,
    )
    day = controller.create_day_template(
        company_id=company_id,
        name="Короткий день",
        mark_type_ids=[mark.id],
    )

    with pytest.raises(ValueError):
        controller.create_week_template(
            company_id=company_id,
            name="Неповний тиждень",
            weekday_to_day_template_id={0: day.id, 1: day.id},
        )


def test_delete_mark_type_permanently_when_unused(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)
    mark = controller.create_mark_type(
        company_id=company_id,
        name="Одноразовий блок",
        kind=MarkKind.BREAK,
        duration_minutes=12,
    )
    session.flush()

    controller.delete_mark_type_permanently(
        company_id=company_id,
        mark_type_id=mark.id,
    )
    session.commit()

    overview = controller.load_templates_overview(company_id)
    ids = {item.id for item in overview.mark_types}
    assert mark.id not in ids


def test_delete_mark_type_permanently_rejects_used_block(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)
    mark = controller.create_mark_type(
        company_id=company_id,
        name="Використаний блок",
        kind=MarkKind.TEACHING,
        duration_minutes=45,
    )
    controller.create_day_template(
        company_id=company_id,
        name="День",
        mark_type_ids=[mark.id],
    )
    session.flush()

    with pytest.raises(ValueError):
        controller.delete_mark_type_permanently(
            company_id=company_id,
            mark_type_id=mark.id,
        )


def test_delete_day_template_permanently_when_unused(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)
    mark = controller.create_mark_type(
        company_id=company_id,
        name="Block",
        kind=MarkKind.TEACHING,
        duration_minutes=45,
    )
    day = controller.create_day_template(
        company_id=company_id,
        name="Unused day",
        mark_type_ids=[mark.id],
    )
    session.flush()

    controller.delete_day_template_permanently(
        company_id=company_id,
        day_template_id=day.id,
    )
    session.commit()

    overview = controller.load_templates_overview(company_id)
    day_ids = {item.id for item in overview.day_templates}
    assert day.id not in day_ids


def test_delete_day_template_permanently_rejects_used_template(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)
    mark = controller.create_mark_type(
        company_id=company_id,
        name="Block",
        kind=MarkKind.TEACHING,
        duration_minutes=45,
    )
    day = controller.create_day_template(
        company_id=company_id,
        name="Used day",
        mark_type_ids=[mark.id],
    )
    controller.create_week_template(
        company_id=company_id,
        name="Week",
        weekday_to_day_template_id={weekday: day.id for weekday in range(7)},
    )
    session.flush()

    with pytest.raises(ValueError):
        controller.delete_day_template_permanently(
            company_id=company_id,
            day_template_id=day.id,
        )


def test_delete_week_template_permanently_when_unused(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)
    mark = controller.create_mark_type(
        company_id=company_id,
        name="Block",
        kind=MarkKind.TEACHING,
        duration_minutes=45,
    )
    day = controller.create_day_template(
        company_id=company_id,
        name="Day",
        mark_type_ids=[mark.id],
    )
    week = controller.create_week_template(
        company_id=company_id,
        name="Unused week",
        weekday_to_day_template_id={weekday: day.id for weekday in range(7)},
    )
    session.flush()

    controller.delete_week_template_permanently(
        company_id=company_id,
        week_template_id=week.id,
    )
    session.commit()

    overview = controller.load_templates_overview(company_id)
    week_ids = {item.id for item in overview.week_templates}
    assert week.id not in week_ids


def test_delete_week_template_permanently_rejects_used_template(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)
    mark = controller.create_mark_type(
        company_id=company_id,
        name="Block",
        kind=MarkKind.TEACHING,
        duration_minutes=45,
    )
    day = controller.create_day_template(
        company_id=company_id,
        name="Day",
        mark_type_ids=[mark.id],
    )
    week = controller.create_week_template(
        company_id=company_id,
        name="Used week",
        weekday_to_day_template_id={weekday: day.id for weekday in range(7)},
    )
    session.add(
        CalendarPeriod(
            company_id=company_id,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            week_pattern_id=week.id,
        )
    )
    session.flush()

    with pytest.raises(ValueError):
        controller.delete_week_template_permanently(
            company_id=company_id,
            week_template_id=week.id,
        )


def test_day_template_crud_create_update_archive(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)
    teach = controller.create_mark_type(
        company_id=company_id,
        name="Teach 40",
        kind=MarkKind.TEACHING,
        duration_minutes=40,
    )
    brk = controller.create_mark_type(
        company_id=company_id,
        name="Break 10",
        kind=MarkKind.BREAK,
        duration_minutes=10,
    )

    created = controller.create_day_template(
        company_id=company_id,
        name="Day A",
        mark_type_ids=[teach.id, brk.id],
    )
    updated = controller.update_day_template(
        company_id=company_id,
        day_template_id=created.id,
        name="Day A+",
        mark_type_ids=[teach.id, teach.id, brk.id],
    )
    archived = controller.delete_day_template(
        company_id=company_id,
        day_template_id=created.id,
    )
    session.commit()

    assert created.id == updated.id == archived.id
    assert updated.name == "Day A+"
    assert updated.mark_type_ids == (teach.id, teach.id, brk.id)
    assert archived.is_archived is True


def test_day_template_allows_empty_schedule(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)

    created = controller.create_day_template(
        company_id=company_id,
        name="Вихідний",
        mark_type_ids=[],
    )
    updated = controller.update_day_template(
        company_id=company_id,
        day_template_id=created.id,
        name="Вихідний (оновлений)",
        mark_type_ids=[],
    )
    session.commit()

    assert created.mark_type_ids == ()
    assert updated.mark_type_ids == ()
    assert updated.preview.total_blocks == 0
    assert updated.name == "Вихідний (оновлений)"


def test_day_template_can_be_cleared_to_empty(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)
    teach = controller.create_mark_type(
        company_id=company_id,
        name="Teach 45",
        kind=MarkKind.TEACHING,
        duration_minutes=45,
    )
    day = controller.create_day_template(
        company_id=company_id,
        name="Спочатку непорожній",
        mark_type_ids=[teach.id],
    )

    updated = controller.update_day_template(
        company_id=company_id,
        day_template_id=day.id,
        mark_type_ids=[],
    )
    session.commit()

    assert updated.mark_type_ids == ()
    assert updated.preview.total_blocks == 0


def test_week_template_crud_create_update_archive(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)
    teach = controller.create_mark_type(
        company_id=company_id,
        name="Teach 45",
        kind=MarkKind.TEACHING,
        duration_minutes=45,
    )
    day_a = controller.create_day_template(
        company_id=company_id,
        name="Day A",
        mark_type_ids=[teach.id],
    )
    day_b = controller.create_day_template(
        company_id=company_id,
        name="Day B",
        mark_type_ids=[teach.id, teach.id],
    )

    created = controller.create_week_template(
        company_id=company_id,
        name="Week A",
        weekday_to_day_template_id={weekday: day_a.id for weekday in range(7)},
    )
    updated = controller.update_week_template(
        company_id=company_id,
        week_template_id=created.id,
        name="Week B",
        weekday_to_day_template_id={
            0: day_b.id,
            1: day_b.id,
            2: day_a.id,
            3: day_a.id,
            4: day_a.id,
            5: day_b.id,
            6: day_b.id,
        },
    )
    archived = controller.delete_week_template(
        company_id=company_id,
        week_template_id=created.id,
    )
    session.commit()

    assert created.id == updated.id == archived.id
    assert updated.name == "Week B"
    assert updated.weekday_to_day_template_id[0] == day_b.id
    assert updated.weekday_to_day_template_id[2] == day_a.id
    assert archived.is_archived is True


def test_duplicate_week_template_creates_independent_copy(session: Session) -> None:
    company_id = _create_company(session)
    controller = TemplateController(session=session)
    teach = controller.create_mark_type(
        company_id=company_id,
        name="Teach 35",
        kind=MarkKind.TEACHING,
        duration_minutes=35,
    )
    day_a = controller.create_day_template(
        company_id=company_id,
        name="Day A",
        mark_type_ids=[teach.id],
    )
    day_b = controller.create_day_template(
        company_id=company_id,
        name="Day B",
        mark_type_ids=[teach.id, teach.id],
    )
    week = controller.create_week_template(
        company_id=company_id,
        name="Week Source",
        weekday_to_day_template_id={weekday: day_a.id for weekday in range(7)},
    )
    duplicate = controller.duplicate_week_template(
        company_id=company_id,
        week_template_id=week.id,
    )

    controller.update_week_template(
        company_id=company_id,
        week_template_id=week.id,
        weekday_to_day_template_id={weekday: day_b.id for weekday in range(7)},
    )
    session.commit()

    overview = controller.load_templates_overview(company_id)
    weeks = {item.id: item for item in overview.week_templates}
    assert weeks[duplicate.id].weekday_to_day_template_id[0] == day_a.id
    assert weeks[week.id].weekday_to_day_template_id[0] == day_b.id
