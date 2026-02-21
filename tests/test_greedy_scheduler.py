from collections import Counter
from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.requirement_controller import RequirementController
from app.controllers.resource_controller import ResourceController
from app.controllers.scheduler_controller import SchedulerController
from app.domain.base import Base
from app.domain.enums import MarkKind, ResourceType
from app.domain.models import (
    CalendarPeriod,
    DayPattern,
    DayPatternItem,
    MarkType,
    ScheduleEntry,
    TimeBlock,
    WeekPattern,
)
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


def _create_calendar_period_with_blocks(
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
                name=f"{kind.value}_{duration}_{index}",
                kind=kind,
                duration_minutes=duration,
            )
        )

    day_pattern = DayPattern(name=f"Pattern_{start_date.isoformat()}_{end_date.isoformat()}")
    day_pattern.items = [
        DayPatternItem(order_index=index + 1, mark_type=mark_type)
        for index, mark_type in enumerate(mark_types)
    ]

    week_pattern = WeekPattern(
        monday_pattern=day_pattern,
        tuesday_pattern=day_pattern,
        wednesday_pattern=day_pattern,
        thursday_pattern=day_pattern,
        friday_pattern=day_pattern,
        saturday_pattern=day_pattern,
        sunday_pattern=day_pattern,
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


def test_scheduler_rejects_non_consecutive_teaching_blocks(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[
            (MarkKind.TEACHING, 45),
            (MarkKind.BREAK, 10),
            (MarkKind.TEACHING, 45),
        ],
    )

    resource_controller = ResourceController(session=session)
    requirement_controller = RequirementController(session=session)
    scheduler_controller = SchedulerController(session=session)

    teacher = resource_controller.create_resource(
        name="Teacher A",
        resource_type=ResourceType.TEACHER,
    )
    requirement = requirement_controller.create_requirement(
        name="Algebra",
        duration_blocks=2,
        sessions_total=1,
        max_per_week=1,
    )
    requirement_controller.assign_resource(requirement.id, teacher.id, "LECTOR")
    session.commit()

    result = scheduler_controller.build_schedule(calendar_period_id=period.id)
    session.commit()

    assert len(result.created_entries) == 0
    assert result.unscheduled_sessions == {requirement.id: 1}
    assert session.query(ScheduleEntry).count() == 0


def test_scheduler_handles_resource_conflicts_and_max_per_week(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 8),
        marks=[
            (MarkKind.TEACHING, 45),
            (MarkKind.TEACHING, 45),
            (MarkKind.TEACHING, 45),
        ],
    )

    resource_controller = ResourceController(session=session)
    requirement_controller = RequirementController(session=session)
    scheduler_controller = SchedulerController(session=session)

    teacher = resource_controller.create_resource(
        name="Teacher B",
        resource_type=ResourceType.TEACHER,
    )

    requirement_a = requirement_controller.create_requirement(
        name="Physics",
        duration_blocks=2,
        sessions_total=3,
        max_per_week=2,
    )
    requirement_controller.assign_resource(requirement_a.id, teacher.id, "LECTOR")

    requirement_b = requirement_controller.create_requirement(
        name="Chemistry",
        duration_blocks=2,
        sessions_total=2,
        max_per_week=2,
    )
    requirement_controller.assign_resource(requirement_b.id, teacher.id, "LECTOR")
    session.commit()

    result = scheduler_controller.build_schedule(calendar_period_id=period.id)
    session.commit()

    all_entries = session.query(ScheduleEntry).order_by(ScheduleEntry.id.asc()).all()
    counts = Counter(entry.requirement_id for entry in all_entries)

    assert counts[requirement_a.id] == 2
    assert counts[requirement_b.id] == 2
    assert result.unscheduled_sessions[requirement_a.id] == 1
    assert requirement_b.id not in result.unscheduled_sessions

    teaching_blocks = (
        session.query(TimeBlock)
        .filter(
            TimeBlock.calendar_period_id == period.id,
            TimeBlock.block_kind == MarkKind.TEACHING,
        )
        .all()
    )
    block_by_key = {(block.date, block.order_in_day): block for block in teaching_blocks}

    occupied_block_ids: list[int] = []
    for entry in all_entries:
        start_block = session.get(TimeBlock, entry.start_block_id)
        assert start_block is not None
        for offset in range(entry.blocks_count):
            block = block_by_key[(start_block.date, start_block.order_in_day + offset)]
            occupied_block_ids.append(block.id)

    assert len(occupied_block_ids) == len(set(occupied_block_ids))


def test_scheduler_regeneration_replaces_existing_entries(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 3),
        marks=[
            (MarkKind.TEACHING, 45),
            (MarkKind.TEACHING, 45),
        ],
    )

    resource_controller = ResourceController(session=session)
    requirement_controller = RequirementController(session=session)
    scheduler_controller = SchedulerController(session=session)

    teacher = resource_controller.create_resource(
        name="Teacher C",
        resource_type=ResourceType.TEACHER,
    )
    requirement = requirement_controller.create_requirement(
        name="History",
        duration_blocks=1,
        sessions_total=2,
        max_per_week=2,
    )
    requirement_controller.assign_resource(requirement.id, teacher.id, "LECTOR")
    session.commit()

    first_run = scheduler_controller.build_schedule(calendar_period_id=period.id, replace_existing=True)
    session.commit()
    assert len(first_run.created_entries) == 2
    assert session.query(ScheduleEntry).count() == 2

    second_run = scheduler_controller.build_schedule(calendar_period_id=period.id, replace_existing=True)
    session.commit()
    assert len(second_run.created_entries) == 2
    assert session.query(ScheduleEntry).count() == 2
