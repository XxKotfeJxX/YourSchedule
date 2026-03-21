from datetime import date, datetime, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.base import Base
from app.domain.enums import MarkKind, ResourceType, RoomType
from app.domain.models import (
    Building,
    CalendarPeriod,
    Company,
    DayPattern,
    DayPatternItem,
    MarkType,
    Requirement,
    RequirementResource,
    Resource,
    ResourceBlackout,
    RoomProfile,
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


def test_validation_detects_blackout_conflicts(session: Session) -> None:
    period = _create_period(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[(MarkKind.TEACHING, 45)],
    )

    teacher = Resource(name="Teacher blackout", type=ResourceType.TEACHER)
    requirement = Requirement(name="Math blackout", duration_blocks=1, sessions_total=1, max_per_week=1)
    session.add_all([teacher, requirement])
    session.flush()

    session.add(
        RequirementResource(
            requirement_id=requirement.id,
            resource_id=teacher.id,
            role="LECTOR",
        )
    )

    block = _get_block(session, period.id, date(2026, 3, 2), 1)
    session.add(
        ResourceBlackout(
            resource_id=teacher.id,
            starts_at=block.start_timestamp,
            ends_at=block.end_timestamp,
            title="Unavailable",
        )
    )
    session.add(
        ScheduleEntry(
            requirement_id=requirement.id,
            start_block_id=block.id,
            blocks_count=1,
        )
    )
    session.commit()

    report = ScheduleValidatorService().validate_period(session=session, calendar_period_id=period.id)
    issue_codes = [issue.code for issue in report.issues]
    assert "RESOURCE_BLACKOUT_CONFLICT" in issue_codes


def test_validation_detects_room_constraint_mismatches(session: Session) -> None:
    period = _create_period(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[(MarkKind.TEACHING, 45)],
    )

    company = Company(name="Validation Rooms Company")
    session.add(company)
    session.flush()

    building = Building(company_id=company.id, name="Validation Building")
    session.add(building)
    session.flush()

    teacher = Resource(name="Teacher room", type=ResourceType.TEACHER, company_id=company.id)
    room_resource = Resource(name="Room 12", type=ResourceType.ROOM, company_id=company.id)
    requirement = Requirement(
        company_id=company.id,
        name="Room constrained",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
        room_type=RoomType.COMPUTER_LAB,
        min_capacity=30,
        needs_projector=True,
    )
    session.add_all([teacher, room_resource, requirement])
    session.flush()

    session.add(
        RequirementResource(
            requirement_id=requirement.id,
            resource_id=teacher.id,
            role="LECTOR",
        )
    )

    room_profile = RoomProfile(
        company_id=company.id,
        building_id=building.id,
        resource_id=room_resource.id,
        name="12",
        room_type=RoomType.CLASSROOM,
        capacity=20,
        has_projector=False,
    )
    session.add(room_profile)
    session.flush()

    block = _get_block(session, period.id, date(2026, 3, 2), 1)
    session.add(
        ScheduleEntry(
            company_id=company.id,
            requirement_id=requirement.id,
            start_block_id=block.id,
            blocks_count=1,
            room_resource_id=room_resource.id,
        )
    )
    session.commit()

    report = ScheduleValidatorService().validate_period(session=session, calendar_period_id=period.id)
    issue_codes = [issue.code for issue in report.issues]

    assert "ROOM_TYPE_MISMATCH" in issue_codes
    assert "ROOM_CAPACITY_MISMATCH" in issue_codes
    assert "ROOM_PROJECTOR_REQUIRED" in issue_codes
