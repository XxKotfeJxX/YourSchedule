from datetime import date, datetime, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.base import Base
from app.domain.enums import MarkKind
from app.domain.models import CalendarPeriod, DayPattern, DayPatternItem, MarkType, TimeBlock, WeekPattern
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


def _seed_calendar_data(session: Session) -> CalendarPeriod:
    teaching_mark = MarkType(
        name="Teaching 45",
        kind=MarkKind.TEACHING,
        duration_minutes=45,
    )
    break_mark = MarkType(
        name="Break 10",
        kind=MarkKind.BREAK,
        duration_minutes=10,
    )

    day_pattern = DayPattern(name="Default day")
    day_pattern.items = [
        DayPatternItem(order_index=1, mark_type=teaching_mark),
        DayPatternItem(order_index=2, mark_type=break_mark),
        DayPatternItem(order_index=3, mark_type=teaching_mark),
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

    calendar_period = CalendarPeriod(
        start_date=date(2026, 2, 16),
        end_date=date(2026, 2, 17),
        week_pattern=week_pattern,
    )

    session.add(calendar_period)
    session.commit()
    return calendar_period


def test_generate_time_blocks_for_period(session: Session) -> None:
    calendar_period = _seed_calendar_data(session)
    generator = TimeBlockGeneratorService(day_start_time=time(hour=8, minute=30))

    generated = generator.generate_for_period(
        session=session,
        calendar_period_id=calendar_period.id,
    )
    session.commit()

    blocks = (
        session.query(TimeBlock)
        .order_by(TimeBlock.date.asc(), TimeBlock.order_in_day.asc())
        .all()
    )

    assert len(generated) == 6
    assert len(blocks) == 6

    first = blocks[0]
    second = blocks[1]
    third = blocks[2]

    assert first.date == date(2026, 2, 16)
    assert first.start_timestamp == datetime(2026, 2, 16, 8, 30)
    assert first.end_timestamp == datetime(2026, 2, 16, 9, 15)
    assert first.block_kind == MarkKind.TEACHING

    assert second.start_timestamp == datetime(2026, 2, 16, 9, 15)
    assert second.end_timestamp == datetime(2026, 2, 16, 9, 25)
    assert second.block_kind == MarkKind.BREAK

    assert third.start_timestamp == datetime(2026, 2, 16, 9, 25)
    assert third.end_timestamp == datetime(2026, 2, 16, 10, 10)
    assert third.block_kind == MarkKind.TEACHING


def test_regeneration_replaces_existing_blocks(session: Session) -> None:
    calendar_period = _seed_calendar_data(session)
    generator = TimeBlockGeneratorService(day_start_time=time(hour=8, minute=30))

    generator.generate_for_period(session=session, calendar_period_id=calendar_period.id)
    session.commit()
    generator.generate_for_period(
        session=session,
        calendar_period_id=calendar_period.id,
        replace_existing=True,
    )
    session.commit()

    total_blocks = session.query(TimeBlock).count()
    assert total_blocks == 6
