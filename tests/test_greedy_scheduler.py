from collections import Counter
from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.requirement_controller import RequirementController
from app.controllers.resource_controller import ResourceController
from app.controllers.scheduler_controller import SchedulerController
from app.domain.base import Base
from app.domain.enums import MarkKind, ResourceType, RoomType, TimePreference
from app.domain.models import (
    Building,
    CalendarPeriod,
    Company,
    DayPattern,
    DayPatternItem,
    MarkType,
    RoomProfile,
    ScheduleEntry,
    TimeBlock,
    WeekPattern,
)
from app.services.time_block_generator import TimeBlockGeneratorService
from app.services.greedy_scheduler import SchedulerPolicyOptions


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


def test_scheduler_assigns_rooms_by_constraints(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[(MarkKind.TEACHING, 45), (MarkKind.TEACHING, 45)],
    )

    resource_controller = ResourceController(session=session)
    requirement_controller = RequirementController(session=session)
    scheduler_controller = SchedulerController(session=session)

    company = Company(name="Scheduler Rooms Company")
    session.add(company)
    session.flush()

    building = Building(company_id=company.id, name="A")
    session.add(building)
    session.flush()

    teacher = resource_controller.create_resource(
        name="Teacher Room Constraint",
        resource_type=ResourceType.TEACHER,
        company_id=company.id,
    )
    room_bad = resource_controller.create_resource(
        name="Room Bad",
        resource_type=ResourceType.ROOM,
        company_id=company.id,
    )
    room_good = resource_controller.create_resource(
        name="Room Good",
        resource_type=ResourceType.ROOM,
        company_id=company.id,
    )
    session.flush()

    session.add_all(
        [
            RoomProfile(
                company_id=company.id,
                building_id=building.id,
                resource_id=room_bad.id,
                name="Bad",
                room_type=RoomType.CLASSROOM,
                capacity=18,
                has_projector=False,
            ),
            RoomProfile(
                company_id=company.id,
                building_id=building.id,
                resource_id=room_good.id,
                name="Good",
                room_type=RoomType.LAB,
                capacity=30,
                has_projector=True,
            ),
        ]
    )
    session.flush()

    requirement = requirement_controller.create_requirement(
        name="Signal Processing",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
        company_id=company.id,
        room_type=RoomType.LAB,
        min_capacity=20,
        needs_projector=True,
    )
    requirement_controller.assign_resource(requirement.id, teacher.id, "TEACHER")
    session.commit()

    result = scheduler_controller.build_schedule(calendar_period_id=period.id)
    session.commit()

    assert len(result.created_entries) == 1
    entry = result.created_entries[0]
    assert entry.room_resource_id == room_good.id


def test_scheduler_respects_fixed_room_blackouts(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 3),
        marks=[(MarkKind.TEACHING, 45)],
    )

    resource_controller = ResourceController(session=session)
    requirement_controller = RequirementController(session=session)
    scheduler_controller = SchedulerController(session=session)

    company = Company(name="Scheduler Blackout Company")
    session.add(company)
    session.flush()

    building = Building(company_id=company.id, name="B")
    session.add(building)
    session.flush()

    teacher = resource_controller.create_resource(
        name="Teacher Fixed Room",
        resource_type=ResourceType.TEACHER,
        company_id=company.id,
    )
    fixed_room_resource = resource_controller.create_resource(
        name="Room Fixed",
        resource_type=ResourceType.ROOM,
        company_id=company.id,
    )
    session.flush()

    fixed_room = RoomProfile(
        company_id=company.id,
        building_id=building.id,
        resource_id=fixed_room_resource.id,
        name="F1",
        room_type=RoomType.CLASSROOM,
        capacity=40,
        has_projector=True,
    )
    session.add(fixed_room)
    session.flush()

    first_block = (
        session.query(TimeBlock)
        .filter(
            TimeBlock.calendar_period_id == period.id,
            TimeBlock.date == date(2026, 3, 2),
            TimeBlock.order_in_day == 1,
        )
        .one()
    )
    resource_controller.create_blackout(
        fixed_room_resource.id,
        starts_at=first_block.start_timestamp,
        ends_at=first_block.end_timestamp,
        title="Maintenance",
    )

    requirement = requirement_controller.create_requirement(
        name="Logic",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
        company_id=company.id,
        fixed_room_id=fixed_room.id,
    )
    requirement_controller.assign_resource(requirement.id, teacher.id, "TEACHER")
    session.commit()

    result = scheduler_controller.build_schedule(calendar_period_id=period.id)
    session.commit()

    assert len(result.created_entries) == 1
    entry = result.created_entries[0]
    start_block = session.get(TimeBlock, entry.start_block_id)
    assert start_block is not None
    assert start_block.date == date(2026, 3, 3)
    assert entry.room_resource_id == fixed_room_resource.id


def test_scheduler_keeps_locked_manual_entries_on_regeneration(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[(MarkKind.TEACHING, 45), (MarkKind.TEACHING, 45)],
    )

    resource_controller = ResourceController(session=session)
    requirement_controller = RequirementController(session=session)
    scheduler_controller = SchedulerController(session=session)

    teacher = resource_controller.create_resource(
        name="Teacher Manual Lock",
        resource_type=ResourceType.TEACHER,
    )
    requirement = requirement_controller.create_requirement(
        name="Manual Slot Subject",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
    )
    requirement_controller.assign_resource(requirement.id, teacher.id, "TEACHER")
    session.commit()

    locked_entry = scheduler_controller.create_manual_entry(
        calendar_period_id=period.id,
        requirement_id=requirement.id,
        day=date(2026, 3, 2),
        order_in_day=2,
        is_locked=True,
    )
    session.commit()
    assert locked_entry.is_manual is True
    assert locked_entry.is_locked is True

    result = scheduler_controller.build_schedule(
        calendar_period_id=period.id,
        replace_existing=True,
    )
    session.commit()

    entries = session.query(ScheduleEntry).all()
    assert len(result.created_entries) == 0
    assert len(entries) == 1
    assert entries[0].id == locked_entry.id
    assert entries[0].is_manual is True
    assert entries[0].is_locked is True


def test_scheduler_feasibility_reports_capacity_shortage(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[(MarkKind.TEACHING, 45)],
    )

    resource_controller = ResourceController(session=session)
    requirement_controller = RequirementController(session=session)
    scheduler_controller = SchedulerController(session=session)

    teacher = resource_controller.create_resource(
        name="Teacher Feasibility",
        resource_type=ResourceType.TEACHER,
    )
    requirement = requirement_controller.create_requirement(
        name="Capacity Check Subject",
        duration_blocks=1,
        sessions_total=2,
        max_per_week=2,
    )
    requirement_controller.assign_resource(requirement.id, teacher.id, "TEACHER")
    session.commit()

    report = scheduler_controller.analyze_feasibility(
        calendar_period_id=period.id,
        replace_existing=True,
    )

    codes = {issue.code for issue in report.issues}
    assert report.is_feasible is False
    assert report.candidate_capacity[requirement.id] == 1
    assert "CANDIDATE_CAPACITY_LOW" in codes


def test_scheduler_policy_max_sessions_per_day_limit(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[(MarkKind.TEACHING, 45), (MarkKind.TEACHING, 45)],
    )

    resource_controller = ResourceController(session=session)
    requirement_controller = RequirementController(session=session)
    scheduler_controller = SchedulerController(session=session)

    teacher = resource_controller.create_resource(
        name="Teacher Max Per Day",
        resource_type=ResourceType.TEACHER,
    )
    requirement_a = requirement_controller.create_requirement(
        name="Constraint Subject A",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
    )
    requirement_controller.assign_resource(requirement_a.id, teacher.id, "TEACHER")
    requirement_b = requirement_controller.create_requirement(
        name="Constraint Subject B",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
    )
    requirement_controller.assign_resource(requirement_b.id, teacher.id, "TEACHER")
    session.commit()

    policy = SchedulerPolicyOptions(
        max_sessions_per_day=1,
        max_consecutive_blocks=None,
        enforce_no_gaps=False,
        time_preference=TimePreference.BALANCED,
        weight_time_preference=0,
        weight_compactness=0,
        weight_building_transition=0,
    )
    result = scheduler_controller.build_schedule(
        calendar_period_id=period.id,
        replace_existing=True,
        policy_options=policy,
    )
    session.commit()

    entries = session.query(ScheduleEntry).all()
    assert len(entries) == 1
    assert len(result.unscheduled_sessions) == 1
    assert sum(result.unscheduled_sessions.values()) == 1


def test_scheduler_policy_max_consecutive_blocks_limit(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
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
        name="Teacher Max Consecutive",
        resource_type=ResourceType.TEACHER,
    )
    long_requirement = requirement_controller.create_requirement(
        name="Long Requirement",
        duration_blocks=2,
        sessions_total=1,
        max_per_week=1,
    )
    requirement_controller.assign_resource(long_requirement.id, teacher.id, "TEACHER")
    short_requirement = requirement_controller.create_requirement(
        name="Short Requirement",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
    )
    requirement_controller.assign_resource(short_requirement.id, teacher.id, "TEACHER")
    session.commit()

    policy = SchedulerPolicyOptions(
        max_sessions_per_day=None,
        max_consecutive_blocks=2,
        enforce_no_gaps=False,
        time_preference=TimePreference.BALANCED,
        weight_time_preference=0,
        weight_compactness=0,
        weight_building_transition=0,
    )
    result = scheduler_controller.build_schedule(
        calendar_period_id=period.id,
        replace_existing=True,
        policy_options=policy,
    )
    session.commit()

    entries = session.query(ScheduleEntry).all()
    assert len(entries) == 1
    assert entries[0].requirement_id == long_requirement.id
    assert result.unscheduled_sessions == {short_requirement.id: 1}


def test_scheduler_policy_no_gaps_places_adjacent_blocks(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
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
        name="Teacher No Gaps",
        resource_type=ResourceType.TEACHER,
    )
    anchor_requirement = requirement_controller.create_requirement(
        name="Anchor Requirement",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
    )
    requirement_controller.assign_resource(anchor_requirement.id, teacher.id, "TEACHER")
    target_requirement = requirement_controller.create_requirement(
        name="Target Requirement",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
    )
    requirement_controller.assign_resource(target_requirement.id, teacher.id, "TEACHER")
    session.commit()

    scheduler_controller.create_manual_entry(
        calendar_period_id=period.id,
        requirement_id=anchor_requirement.id,
        day=date(2026, 3, 2),
        order_in_day=1,
        is_locked=True,
    )
    session.commit()

    policy = SchedulerPolicyOptions(
        max_sessions_per_day=None,
        max_consecutive_blocks=None,
        enforce_no_gaps=True,
        time_preference=TimePreference.BALANCED,
        weight_time_preference=0,
        weight_compactness=0,
        weight_building_transition=0,
    )
    scheduler_controller.build_schedule(
        calendar_period_id=period.id,
        replace_existing=True,
        policy_options=policy,
    )
    session.commit()

    target_entry = (
        session.query(ScheduleEntry)
        .filter(ScheduleEntry.requirement_id == target_requirement.id)
        .one()
    )
    target_start_block = session.get(TimeBlock, target_entry.start_block_id)
    assert target_start_block is not None
    assert target_start_block.order_in_day == 2


def test_scheduler_policy_time_preference_changes_selected_slot(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
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
        name="Teacher Time Preference",
        resource_type=ResourceType.TEACHER,
    )
    requirement = requirement_controller.create_requirement(
        name="Preference Requirement",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
    )
    requirement_controller.assign_resource(requirement.id, teacher.id, "TEACHER")
    session.commit()

    morning_policy = SchedulerPolicyOptions(
        max_sessions_per_day=None,
        max_consecutive_blocks=None,
        enforce_no_gaps=False,
        time_preference=TimePreference.MORNING,
        weight_time_preference=10,
        weight_compactness=0,
        weight_building_transition=0,
    )
    morning_result = scheduler_controller.build_schedule(
        calendar_period_id=period.id,
        replace_existing=True,
        policy_options=morning_policy,
    )
    session.commit()
    morning_start = session.get(TimeBlock, morning_result.created_entries[0].start_block_id)
    assert morning_start is not None
    assert morning_start.order_in_day == 1

    evening_policy = SchedulerPolicyOptions(
        max_sessions_per_day=None,
        max_consecutive_blocks=None,
        enforce_no_gaps=False,
        time_preference=TimePreference.EVENING,
        weight_time_preference=10,
        weight_compactness=0,
        weight_building_transition=0,
    )
    evening_result = scheduler_controller.build_schedule(
        calendar_period_id=period.id,
        replace_existing=True,
        policy_options=evening_policy,
    )
    session.commit()
    evening_start = session.get(TimeBlock, evening_result.created_entries[0].start_block_id)
    assert evening_start is not None
    assert evening_start.order_in_day == 3


def test_scheduler_returns_detailed_diagnostics_for_unscheduled_requirements(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[(MarkKind.TEACHING, 45)],
    )

    resource_controller = ResourceController(session=session)
    requirement_controller = RequirementController(session=session)
    scheduler_controller = SchedulerController(session=session)

    teacher = resource_controller.create_resource(
        name="Teacher Diagnostics",
        resource_type=ResourceType.TEACHER,
    )
    requirement = requirement_controller.create_requirement(
        name="Diagnostics Requirement",
        duration_blocks=1,
        sessions_total=2,
        max_per_week=2,
    )
    requirement_controller.assign_resource(requirement.id, teacher.id, "TEACHER")
    session.commit()

    result = scheduler_controller.build_schedule(calendar_period_id=period.id, replace_existing=True)
    session.commit()

    assert result.unscheduled_sessions == {requirement.id: 1}
    assert result.diagnostics
    assert any(item.requirement_id == requirement.id for item in result.diagnostics)
    assert any(item.code in {"REQUIREMENT_OVERLAP", "NO_CANDIDATES"} for item in result.diagnostics)


def test_scheduler_scenarios_compare_and_publish(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[(MarkKind.TEACHING, 45), (MarkKind.TEACHING, 45)],
    )

    resource_controller = ResourceController(session=session)
    requirement_controller = RequirementController(session=session)
    scheduler_controller = SchedulerController(session=session)

    teacher = resource_controller.create_resource(
        name="Teacher Scenario",
        resource_type=ResourceType.TEACHER,
    )
    requirement = requirement_controller.create_requirement(
        name="Scenario Requirement",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
    )
    requirement_controller.assign_resource(requirement.id, teacher.id, "TEACHER")
    session.commit()

    scheduler_controller.build_schedule(calendar_period_id=period.id, replace_existing=True)
    session.commit()

    scenario_a = scheduler_controller.create_scenario(
        calendar_period_id=period.id,
        name="Чернетка A",
        copy_from_published=True,
    )
    scenario_b = scheduler_controller.create_scenario(
        calendar_period_id=period.id,
        name="Чернетка B",
        copy_from_published=False,
    )

    scheduler_controller.create_manual_entry(
        calendar_period_id=period.id,
        scenario_id=scenario_b.id,
        requirement_id=requirement.id,
        day=date(2026, 3, 2),
        order_in_day=2,
        is_locked=True,
    )
    session.commit()

    comparison = scheduler_controller.compare_scenarios(
        calendar_period_id=period.id,
        left_scenario_id=scenario_a.id,
        right_scenario_id=scenario_b.id,
    )
    assert comparison.only_left_count >= 1
    assert comparison.only_right_count >= 1

    published_entries = scheduler_controller.publish_scenario(scenario_id=scenario_b.id)
    session.commit()
    assert published_entries == 1

    current_entry = session.query(ScheduleEntry).one()
    current_start = session.get(TimeBlock, current_entry.start_block_id)
    assert current_start is not None
    assert current_start.order_in_day == 2

    scenarios = scheduler_controller.list_scenarios(calendar_period_id=period.id)
    published_ids = {item.id for item in scenarios if item.is_published}
    assert published_ids == {scenario_b.id}


def test_scheduler_coverage_dashboard_reports_uncovered_requirements(session: Session) -> None:
    period = _create_calendar_period_with_blocks(
        session=session,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 2),
        marks=[(MarkKind.TEACHING, 45)],
    )

    resource_controller = ResourceController(session=session)
    requirement_controller = RequirementController(session=session)
    scheduler_controller = SchedulerController(session=session)

    teacher_ok = resource_controller.create_resource(
        name="Teacher Coverage OK",
        resource_type=ResourceType.TEACHER,
    )
    teacher_bad = resource_controller.create_resource(
        name="Teacher Coverage BAD",
        resource_type=ResourceType.TEACHER,
    )
    req_ok = requirement_controller.create_requirement(
        name="Covered Requirement",
        duration_blocks=1,
        sessions_total=1,
        max_per_week=1,
    )
    requirement_controller.assign_resource(req_ok.id, teacher_ok.id, "TEACHER")
    req_bad = requirement_controller.create_requirement(
        name="Uncovered Requirement",
        duration_blocks=1,
        sessions_total=2,
        max_per_week=2,
    )
    requirement_controller.assign_resource(req_bad.id, teacher_bad.id, "TEACHER")
    session.commit()

    scheduler_controller.build_schedule(calendar_period_id=period.id, replace_existing=True)
    session.commit()

    dashboard = scheduler_controller.get_coverage_dashboard(calendar_period_id=period.id)
    assert dashboard.total_requirements == 2
    assert dashboard.covered_requirements == 1
    assert dashboard.uncovered_requirements == 1
    assert dashboard.total_sessions_required == 3
    assert dashboard.total_sessions_scheduled == 2
    assert dashboard.reasons
    assert any(item.requirement_id == req_bad.id for item in dashboard.uncovered_items)
