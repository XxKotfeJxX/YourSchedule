from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.base import Base
from app.domain.enums import MarkKind, ResourceType
from app.domain.models import (
    CalendarPeriod,
    DayPattern,
    DayPatternItem,
    MarkType,
    Requirement,
    RequirementResource,
    Resource,
    ScheduleEntry,
    TimeBlock,
    WeekPattern,
)
from app.services.schedule_validator import ScheduleValidatorService
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


def _create_period(
    session: Session,
    *,
    start_date: date,
    end_date: date,
    marks: list[tuple[MarkKind, int]],
) -> CalendarPeriod:
    mark_types: list[MarkType] = []
    for index, (kind, duration) in enumerate(marks, start=1):
        mark_types.append(
            MarkType(
                name=f"{kind.value}_{duration}_{index}_{start_date.isoformat()}",
                kind=kind,
                duration_minutes=duration,
            )
        )

    pattern = DayPattern(name=f"Pattern_{start_date.isoformat()}_{end_date.isoformat()}")
    pattern.items = [
        DayPatternItem(order_index=index + 1, mark_type=mark_type)
        for index, mark_type in enumerate(mark_types)
    ]

    week_pattern = WeekPattern(
        monday_pattern=pattern,
        tuesday_pattern=pattern,
        wednesday_pattern=pattern,
        thursday_pattern=pattern,
        friday_pattern=pattern,
        saturday_pattern=pattern,
        sunday_pattern=pattern,
    )

    period = CalendarPeriod(
        start_date=start_date,
        end_date=end_date,
        week_pattern=week_pattern,
    )
    session.add(period)
    session.commit()

    generator = TimeBlockGeneratorService(day_start_time=time(hour=8, minute=30))
    generator.generate_for_period(session=session, calendar_period_id=period.id)
    session.commit()
    return period


def _get_block(session: Session, period_id: int, day: date, order: int) -> TimeBlock:
    return (
        session.query(TimeBlock)
        .filter(
            TimeBlock.calendar_period_id == period_id,
            TimeBlock.date == day,
            TimeBlock.order_in_day == order,
        )
        .one()
    )


def test_validation_passes_for_valid_schedule(session: Session) -> None:
    period = _create_period(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[(MarkKind.TEACHING, 45), (MarkKind.TEACHING, 45)],
    )

    teacher = Resource(name="Teacher 1", type=ResourceType.TEACHER)
    requirement = Requirement(name="Math", duration_blocks=1, sessions_total=1, max_per_week=1)
    session.add_all([teacher, requirement])
    session.flush()
    session.add(
        RequirementResource(
            requirement_id=requirement.id,
            resource_id=teacher.id,
            role="LECTOR",
        )
    )

    start_block = _get_block(session, period.id, date(2026, 3, 2), 1)
    session.add(
        ScheduleEntry(
            requirement_id=requirement.id,
            start_block_id=start_block.id,
            blocks_count=1,
        )
    )
    session.commit()

    report = ScheduleValidatorService().validate_period(session=session, calendar_period_id=period.id)
    assert report.is_valid is True
    assert report.issues == []


def test_validation_detects_resource_conflict(session: Session) -> None:
    period = _create_period(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[(MarkKind.TEACHING, 45)],
    )

    teacher = Resource(name="Teacher 2", type=ResourceType.TEACHER)
    req_a = Requirement(name="Physics", duration_blocks=1, sessions_total=1, max_per_week=1)
    req_b = Requirement(name="Chemistry", duration_blocks=1, sessions_total=1, max_per_week=1)
    session.add_all([teacher, req_a, req_b])
    session.flush()

    session.add_all(
        [
            RequirementResource(requirement_id=req_a.id, resource_id=teacher.id, role="LECTOR"),
            RequirementResource(requirement_id=req_b.id, resource_id=teacher.id, role="LECTOR"),
        ]
    )

    block = _get_block(session, period.id, date(2026, 3, 2), 1)
    session.add_all(
        [
            ScheduleEntry(requirement_id=req_a.id, start_block_id=block.id, blocks_count=1),
            ScheduleEntry(requirement_id=req_b.id, start_block_id=block.id, blocks_count=1),
        ]
    )
    session.commit()

    report = ScheduleValidatorService().validate_period(session=session, calendar_period_id=period.id)
    issue_codes = [issue.code for issue in report.issues]
    assert "RESOURCE_CONFLICT" in issue_codes


def test_validation_detects_span_and_session_rule_violations(session: Session) -> None:
    period = _create_period(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 3),
        marks=[
            (MarkKind.TEACHING, 45),
            (MarkKind.BREAK, 10),
            (MarkKind.TEACHING, 45),
        ],
    )

    req_bad = Requirement(name="Invalid Span", duration_blocks=2, sessions_total=1, max_per_week=1)
    req_week = Requirement(name="Week Limit", duration_blocks=1, sessions_total=2, max_per_week=1)
    session.add_all([req_bad, req_week])
    session.flush()

    monday_first = _get_block(session, period.id, date(2026, 3, 2), 1)
    monday_third = _get_block(session, period.id, date(2026, 3, 2), 3)
    tuesday_third = _get_block(session, period.id, date(2026, 3, 3), 3)

    session.add_all(
        [
            ScheduleEntry(requirement_id=req_bad.id, start_block_id=monday_first.id, blocks_count=2),
            ScheduleEntry(requirement_id=req_week.id, start_block_id=monday_third.id, blocks_count=1),
            ScheduleEntry(requirement_id=req_week.id, start_block_id=tuesday_third.id, blocks_count=1),
        ]
    )
    session.commit()

    report = ScheduleValidatorService().validate_period(session=session, calendar_period_id=period.id)
    issue_codes = [issue.code for issue in report.issues]

    assert "NON_TEACHING_BLOCK_IN_SPAN" in issue_codes
    assert "SESSION_COUNT_MISMATCH" in issue_codes
    assert "MAX_PER_WEEK_EXCEEDED" in issue_codes
