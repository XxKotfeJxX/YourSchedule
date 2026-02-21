from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.calendar_controller import CalendarController
from app.controllers.requirement_controller import RequirementController
from app.controllers.resource_controller import ResourceController
from app.controllers.scheduler_controller import SchedulerController
from app.domain.base import Base
from app.domain.enums import MarkKind, ResourceType
from app.domain.models import CalendarPeriod, Company, DayPattern, DayPatternItem, MarkType, ScheduleEntry, WeekPattern
from app.services.time_block_generator import TimeBlockGeneratorService


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


def _create_period_for_company(session: Session, company_id: int) -> CalendarPeriod:
    teach = MarkType(company_id=company_id, name=f"T-{company_id}", kind=MarkKind.TEACHING, duration_minutes=45)
    day = DayPattern(company_id=company_id, name=f"Day-{company_id}")
    day.items = [DayPatternItem(order_index=1, mark_type=teach)]
    week = WeekPattern(
        company_id=company_id,
        monday_pattern=day,
        tuesday_pattern=day,
        wednesday_pattern=day,
        thursday_pattern=day,
        friday_pattern=day,
        saturday_pattern=day,
        sunday_pattern=day,
    )
    period = CalendarPeriod(
        company_id=company_id,
        start_date=date(2026, 4, 6),
        end_date=date(2026, 4, 6),
        week_pattern=week,
    )
    session.add(period)
    session.commit()
    TimeBlockGeneratorService(day_start_time=time(hour=8, minute=30)).generate_for_period(session, period.id)
    session.commit()
    return period


def test_scheduler_uses_only_company_requirements(session: Session) -> None:
    c1 = Company(name="C1")
    c2 = Company(name="C2")
    session.add_all([c1, c2])
    session.flush()

    period = _create_period_for_company(session, c1.id)

    teacher_other = ResourceController(session).create_resource(
        name="Teacher Other",
        resource_type=ResourceType.TEACHER,
        company_id=c2.id,
    )
    req_other = RequirementController(session).create_requirement(
        name="Other Company Subject",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
        company_id=c2.id,
    )
    RequirementController(session).assign_resource(req_other.id, teacher_other.id, "LECTOR")
    session.commit()

    result = SchedulerController(session).build_schedule(calendar_period_id=period.id)
    session.commit()

    assert len(result.created_entries) == 0
    assert session.query(ScheduleEntry).count() == 0

    teacher_own = ResourceController(session).create_resource(
        name="Teacher Own",
        resource_type=ResourceType.TEACHER,
        company_id=c1.id,
    )
    req_own = RequirementController(session).create_requirement(
        name="Own Subject",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
        company_id=c1.id,
    )
    RequirementController(session).assign_resource(req_own.id, teacher_own.id, "LECTOR")
    session.commit()

    result2 = SchedulerController(session).build_schedule(calendar_period_id=period.id)
    session.commit()

    assert len(result2.created_entries) == 1
