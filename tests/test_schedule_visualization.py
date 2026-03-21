from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.base import Base
from app.domain.enums import MarkKind
from app.domain.models import (
    CalendarPeriod,
    DayPattern,
    DayPatternItem,
    MarkType,
    Requirement,
    ScheduleEntry,
    ScheduleScenario,
    ScheduleScenarioEntry,
    TimeBlock,
    WeekPattern,
)
from app.services.schedule_visualization import ScheduleVisualizationService
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


def _seed_period_with_teaching_blocks(session: Session) -> CalendarPeriod:
    teaching_1 = MarkType(name="Teaching 1", kind=MarkKind.TEACHING, duration_minutes=45)
    teaching_2 = MarkType(name="Teaching 2", kind=MarkKind.TEACHING, duration_minutes=45)
    day_pattern = DayPattern(name="Visualization day")
    day_pattern.items = [
        DayPatternItem(order_index=1, mark_type=teaching_1),
        DayPatternItem(order_index=2, mark_type=teaching_2),
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
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 8),
        week_pattern=week_pattern,
    )
    session.add(period)
    session.commit()

    generator = TimeBlockGeneratorService(day_start_time=time(hour=8, minute=30))
    generator.generate_for_period(session=session, calendar_period_id=period.id)
    session.commit()
    return period


def test_weekly_grid_renders_scheduled_entries(session: Session) -> None:
    period = _seed_period_with_teaching_blocks(session)
    math = Requirement(name="Math", duration_blocks=2, sessions_total=1, max_per_week=1)
    physics = Requirement(name="Physics", duration_blocks=1, sessions_total=1, max_per_week=1)
    session.add_all([math, physics])
    session.flush()

    monday_block_1 = (
        session.query(TimeBlock)
        .filter(
            TimeBlock.calendar_period_id == period.id,
            TimeBlock.date == date(2026, 3, 2),
            TimeBlock.order_in_day == 1,
        )
        .one()
    )
    tuesday_block_1 = (
        session.query(TimeBlock)
        .filter(
            TimeBlock.calendar_period_id == period.id,
            TimeBlock.date == date(2026, 3, 3),
            TimeBlock.order_in_day == 1,
        )
        .one()
    )

    session.add_all(
        [
            ScheduleEntry(requirement_id=math.id, start_block_id=monday_block_1.id, blocks_count=2),
            ScheduleEntry(requirement_id=physics.id, start_block_id=tuesday_block_1.id, blocks_count=1),
        ]
    )
    session.commit()

    service = ScheduleVisualizationService()
    grid = service.build_weekly_grid(
        session=session,
        calendar_period_id=period.id,
        week_start=date(2026, 3, 2),
    )

    assert grid.week_start == date(2026, 3, 2)
    assert len(grid.rows) == 2

    first_row = grid.rows[0]
    second_row = grid.rows[1]

    assert "Math" in first_row.cells[0]
    assert "Physics" in first_row.cells[1]
    assert "Math" in second_row.cells[0]
    assert second_row.cells[1] == ""


def test_week_start_is_normalized_to_monday(session: Session) -> None:
    period = _seed_period_with_teaching_blocks(session)
    service = ScheduleVisualizationService()

    grid = service.build_weekly_grid(
        session=session,
        calendar_period_id=period.id,
        week_start=date(2026, 3, 5),
    )

    assert grid.week_start == date(2026, 3, 2)


def test_weekly_grid_can_render_selected_scenario(session: Session) -> None:
    period = _seed_period_with_teaching_blocks(session)
    requirement = Requirement(name="Scenario Math", duration_blocks=1, sessions_total=1, max_per_week=1)
    session.add(requirement)
    session.flush()

    monday_block_1 = (
        session.query(TimeBlock)
        .filter(
            TimeBlock.calendar_period_id == period.id,
            TimeBlock.date == date(2026, 3, 2),
            TimeBlock.order_in_day == 1,
        )
        .one()
    )
    tuesday_block_1 = (
        session.query(TimeBlock)
        .filter(
            TimeBlock.calendar_period_id == period.id,
            TimeBlock.date == date(2026, 3, 3),
            TimeBlock.order_in_day == 1,
        )
        .one()
    )

    session.add(
        ScheduleEntry(
            requirement_id=requirement.id,
            start_block_id=monday_block_1.id,
            blocks_count=1,
        )
    )
    scenario = ScheduleScenario(calendar_period_id=period.id, name="Чернетка A", is_published=False)
    session.add(scenario)
    session.flush()
    session.add(
        ScheduleScenarioEntry(
            scenario_id=scenario.id,
            requirement_id=requirement.id,
            start_block_id=tuesday_block_1.id,
            blocks_count=1,
        )
    )
    session.commit()

    service = ScheduleVisualizationService()
    grid = service.build_weekly_grid(
        session=session,
        calendar_period_id=period.id,
        week_start=date(2026, 3, 2),
        scenario_id=scenario.id,
    )

    first_row = grid.rows[0]
    assert first_row.cells[0] == ""
    assert "Scenario Math" in first_row.cells[1]
