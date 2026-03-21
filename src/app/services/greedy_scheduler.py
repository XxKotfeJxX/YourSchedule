from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import MarkKind, ResourceType, TimePreference
from app.domain.models import (
    CalendarPeriod,
    Requirement,
    Resource,
    ResourceBlackout,
    RoomProfile,
    ScheduleEntry,
    ScheduleScenario,
    ScheduleScenarioEntry,
    SchedulerPolicy,
    TimeBlock,
)
from app.repositories.schedule_repository import ScheduleRepository


@dataclass(frozen=True)
class ScheduleCandidate:
    start_block_id: int
    block_ids: tuple[int, ...]
    week_key: tuple[int, int]
    room_resource_id: int | None = None
    score: float = 0.0


@dataclass
class ScheduleRunResult:
    created_entries: list[ScheduleEntry | ScheduleScenarioEntry]
    unscheduled_sessions: dict[int, int]
    diagnostics: list["SchedulingDiagnostic"] = field(default_factory=list)


@dataclass(frozen=True)
class SchedulingDiagnostic:
    code: str
    message: str
    requirement_id: int | None = None
    resource_id: int | None = None
    block_id: int | None = None
    day: date | None = None
    order_in_day: int | None = None


@dataclass(frozen=True)
class FeasibilityIssue:
    code: str
    message: str
    requirement_id: int | None = None
    resource_id: int | None = None
    block_id: int | None = None
    day: date | None = None
    order_in_day: int | None = None


@dataclass(frozen=True)
class ScheduleScenarioSummary:
    id: int
    calendar_period_id: int
    name: str
    is_published: bool
    entries_count: int


@dataclass(frozen=True)
class ScenarioDiffItem:
    code: str
    requirement_id: int
    left_block_id: int | None
    right_block_id: int | None
    left_room_resource_id: int | None
    right_room_resource_id: int | None
    message: str


@dataclass
class ScenarioComparison:
    left_label: str
    right_label: str
    only_left_count: int
    only_right_count: int
    changed_count: int
    items: list[ScenarioDiffItem]


@dataclass
class FeasibilityReport:
    issues: list[FeasibilityIssue]
    candidate_capacity: dict[int, int]

    @property
    def is_feasible(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class SchedulerPolicyOptions:
    max_sessions_per_day: int | None = 4
    max_consecutive_blocks: int | None = 3
    enforce_no_gaps: bool = False
    time_preference: TimePreference | str = TimePreference.BALANCED
    weight_time_preference: int = 2
    weight_compactness: int = 3
    weight_building_transition: int = 2

    @classmethod
    def defaults(cls) -> "SchedulerPolicyOptions":
        return cls()

    def normalized(self) -> "SchedulerPolicyOptions":
        preference = self.time_preference
        if not isinstance(preference, TimePreference):
            preference = TimePreference(str(preference).strip().upper())
        return SchedulerPolicyOptions(
            max_sessions_per_day=self.max_sessions_per_day,
            max_consecutive_blocks=self.max_consecutive_blocks,
            enforce_no_gaps=bool(self.enforce_no_gaps),
            time_preference=preference,
            weight_time_preference=int(self.weight_time_preference),
            weight_compactness=int(self.weight_compactness),
            weight_building_transition=int(self.weight_building_transition),
        )

    def validate(self) -> None:
        if self.max_sessions_per_day is not None and self.max_sessions_per_day <= 0:
            raise ValueError("max_sessions_per_day must be positive or null")
        if self.max_consecutive_blocks is not None and self.max_consecutive_blocks <= 0:
            raise ValueError("max_consecutive_blocks must be positive or null")
        if self.weight_time_preference < 0:
            raise ValueError("weight_time_preference must be >= 0")
        if self.weight_compactness < 0:
            raise ValueError("weight_compactness must be >= 0")
        if self.weight_building_transition < 0:
            raise ValueError("weight_building_transition must be >= 0")


class GreedySchedulerService:
    def __init__(self) -> None:
        self.schedule_repository_cls = ScheduleRepository

    def _scenario_summary_from_model(
        self,
        *,
        model: ScheduleScenario,
        entries_count: int,
    ) -> ScheduleScenarioSummary:
        return ScheduleScenarioSummary(
            id=int(model.id),
            calendar_period_id=int(model.calendar_period_id),
            name=str(model.name),
            is_published=bool(model.is_published),
            entries_count=int(entries_count),
        )

    def list_scenarios(self, session: Session, calendar_period_id: int) -> list[ScheduleScenarioSummary]:
        schedule_repository = self.schedule_repository_cls(session=session)
        scenarios = schedule_repository.list_scenarios(calendar_period_id=calendar_period_id)
        if not scenarios:
            return []
        summaries: list[ScheduleScenarioSummary] = []
        for scenario in scenarios:
            entry_count = len(
                schedule_repository.list_entries_for_period(
                    calendar_period_id=calendar_period_id,
                    scenario_id=int(scenario.id),
                )
            )
            summaries.append(
                self._scenario_summary_from_model(
                    model=scenario,
                    entries_count=entry_count,
                )
            )
        return summaries

    def create_scenario(
        self,
        session: Session,
        *,
        calendar_period_id: int,
        name: str,
        source_scenario_id: int | None = None,
        copy_from_published: bool = True,
    ) -> ScheduleScenarioSummary:
        trimmed_name = name.strip()
        if not trimmed_name:
            raise ValueError("Scenario name must not be empty")

        calendar_period = session.get(CalendarPeriod, calendar_period_id)
        if calendar_period is None:
            raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")

        schedule_repository = self.schedule_repository_cls(session=session)
        existing_scenarios = schedule_repository.list_scenarios(calendar_period_id=calendar_period_id)
        if any(str(item.name).strip().lower() == trimmed_name.lower() for item in existing_scenarios):
            raise ValueError(f"Scenario '{trimmed_name}' already exists")

        scenario = schedule_repository.create_scenario(
            company_id=calendar_period.company_id,
            calendar_period_id=calendar_period_id,
            name=trimmed_name,
        )

        source_entries: list[ScheduleEntry | ScheduleScenarioEntry] = []
        if source_scenario_id is not None:
            source_model = schedule_repository.get_scenario(source_scenario_id)
            if source_model is None:
                raise ValueError(f"ScheduleScenario with id={source_scenario_id} was not found")
            if int(source_model.calendar_period_id) != int(calendar_period_id):
                raise ValueError("Source scenario belongs to a different calendar period")
            source_entries = schedule_repository.list_entries_for_period(
                calendar_period_id=calendar_period_id,
                scenario_id=source_scenario_id,
            )
        elif copy_from_published:
            source_entries = schedule_repository.list_entries_for_period(
                calendar_period_id=calendar_period_id,
                scenario_id=None,
            )

        for entry in source_entries:
            schedule_repository.create_entry(
                company_id=calendar_period.company_id,
                requirement_id=int(entry.requirement_id),
                start_block_id=int(entry.start_block_id),
                blocks_count=int(entry.blocks_count),
                room_resource_id=None if entry.room_resource_id is None else int(entry.room_resource_id),
                is_locked=bool(entry.is_locked),
                is_manual=bool(entry.is_manual),
                scenario_id=int(scenario.id),
            )

        return self._scenario_summary_from_model(
            model=scenario,
            entries_count=len(source_entries),
        )

    def publish_scenario(self, session: Session, *, scenario_id: int) -> int:
        schedule_repository = self.schedule_repository_cls(session=session)
        scenario = schedule_repository.get_scenario(scenario_id)
        if scenario is None:
            raise ValueError(f"ScheduleScenario with id={scenario_id} was not found")

        calendar_period = session.get(CalendarPeriod, scenario.calendar_period_id)
        if calendar_period is None:
            raise ValueError(f"CalendarPeriod with id={scenario.calendar_period_id} was not found")

        draft_entries = schedule_repository.list_entries_for_period(
            calendar_period_id=calendar_period.id,
            scenario_id=scenario_id,
        )
        schedule_repository.clear_entries_for_period(
            calendar_period_id=calendar_period.id,
            keep_locked=False,
            scenario_id=None,
        )
        for entry in draft_entries:
            schedule_repository.create_entry(
                company_id=calendar_period.company_id,
                requirement_id=int(entry.requirement_id),
                start_block_id=int(entry.start_block_id),
                blocks_count=int(entry.blocks_count),
                room_resource_id=None if entry.room_resource_id is None else int(entry.room_resource_id),
                is_locked=bool(entry.is_locked),
                is_manual=bool(entry.is_manual),
                scenario_id=None,
            )
        schedule_repository.set_published_scenario(scenario_id=scenario_id)
        return len(draft_entries)

    def compare_scenarios(
        self,
        session: Session,
        *,
        calendar_period_id: int,
        left_scenario_id: int | None,
        right_scenario_id: int | None,
    ) -> ScenarioComparison:
        schedule_repository = self.schedule_repository_cls(session=session)

        left_entries = schedule_repository.list_entries_for_period(
            calendar_period_id=calendar_period_id,
            scenario_id=left_scenario_id,
        )
        right_entries = schedule_repository.list_entries_for_period(
            calendar_period_id=calendar_period_id,
            scenario_id=right_scenario_id,
        )

        def entry_key(item: ScheduleEntry | ScheduleScenarioEntry) -> tuple[int, int, int, int | None]:
            return (
                int(item.requirement_id),
                int(item.start_block_id),
                int(item.blocks_count),
                None if item.room_resource_id is None else int(item.room_resource_id),
            )

        left_set = {entry_key(item) for item in left_entries}
        right_set = {entry_key(item) for item in right_entries}
        only_left = sorted(left_set - right_set)
        only_right = sorted(right_set - left_set)

        left_by_requirement: dict[int, set[tuple[int, int, int | None]]] = defaultdict(set)
        right_by_requirement: dict[int, set[tuple[int, int, int | None]]] = defaultdict(set)
        for requirement_id, start_block_id, blocks_count, room_resource_id in left_set:
            left_by_requirement[requirement_id].add((start_block_id, blocks_count, room_resource_id))
        for requirement_id, start_block_id, blocks_count, room_resource_id in right_set:
            right_by_requirement[requirement_id].add((start_block_id, blocks_count, room_resource_id))

        changed_requirements = {
            requirement_id
            for requirement_id in set(left_by_requirement) | set(right_by_requirement)
            if left_by_requirement.get(requirement_id, set()) != right_by_requirement.get(requirement_id, set())
            and left_by_requirement.get(requirement_id, set())
            and right_by_requirement.get(requirement_id, set())
        }

        items: list[ScenarioDiffItem] = []
        for requirement_id, start_block_id, blocks_count, room_resource_id in only_left[:10]:
            items.append(
                ScenarioDiffItem(
                    code="ONLY_LEFT",
                    requirement_id=requirement_id,
                    left_block_id=start_block_id,
                    right_block_id=None,
                    left_room_resource_id=room_resource_id,
                    right_room_resource_id=None,
                    message=f"Requirement {requirement_id} exists only in left scenario at block {start_block_id}.",
                )
            )
        for requirement_id, start_block_id, blocks_count, room_resource_id in only_right[:10]:
            items.append(
                ScenarioDiffItem(
                    code="ONLY_RIGHT",
                    requirement_id=requirement_id,
                    left_block_id=None,
                    right_block_id=start_block_id,
                    left_room_resource_id=None,
                    right_room_resource_id=room_resource_id,
                    message=f"Requirement {requirement_id} exists only in right scenario at block {start_block_id}.",
                )
            )

        return ScenarioComparison(
            left_label="Published" if left_scenario_id is None else f"Scenario #{left_scenario_id}",
            right_label="Published" if right_scenario_id is None else f"Scenario #{right_scenario_id}",
            only_left_count=len(only_left),
            only_right_count=len(only_right),
            changed_count=len(changed_requirements),
            items=items,
        )

    def get_policy(self, session: Session, company_id: int | None) -> SchedulerPolicyOptions:
        if company_id is None:
            return SchedulerPolicyOptions.defaults()
        statement = select(SchedulerPolicy).where(SchedulerPolicy.company_id == company_id)
        policy_model = session.scalar(statement)
        if policy_model is None:
            return SchedulerPolicyOptions.defaults()
        return SchedulerPolicyOptions(
            max_sessions_per_day=policy_model.max_sessions_per_day,
            max_consecutive_blocks=policy_model.max_consecutive_blocks,
            enforce_no_gaps=bool(policy_model.enforce_no_gaps),
            time_preference=policy_model.time_preference,
            weight_time_preference=policy_model.weight_time_preference,
            weight_compactness=policy_model.weight_compactness,
            weight_building_transition=policy_model.weight_building_transition,
        ).normalized()

    def update_policy(
        self,
        session: Session,
        company_id: int,
        options: SchedulerPolicyOptions,
    ) -> SchedulerPolicyOptions:
        normalized = options.normalized()
        normalized.validate()

        statement = select(SchedulerPolicy).where(SchedulerPolicy.company_id == company_id)
        policy_model = session.scalar(statement)
        if policy_model is None:
            policy_model = SchedulerPolicy(company_id=company_id)
            session.add(policy_model)

        policy_model.max_sessions_per_day = normalized.max_sessions_per_day
        policy_model.max_consecutive_blocks = normalized.max_consecutive_blocks
        policy_model.enforce_no_gaps = normalized.enforce_no_gaps
        policy_model.time_preference = normalized.time_preference
        policy_model.weight_time_preference = normalized.weight_time_preference
        policy_model.weight_compactness = normalized.weight_compactness
        policy_model.weight_building_transition = normalized.weight_building_transition
        session.flush()
        return self.get_policy(session=session, company_id=company_id)

    def _resolve_policy(
        self,
        *,
        session: Session,
        company_id: int | None,
        policy_options: SchedulerPolicyOptions | None,
    ) -> SchedulerPolicyOptions:
        options = self.get_policy(session=session, company_id=company_id) if policy_options is None else policy_options
        normalized = options.normalized()
        normalized.validate()
        return normalized

    def _validate_scenario_context(
        self,
        *,
        session: Session,
        calendar_period_id: int,
        scenario_id: int | None,
    ) -> None:
        if scenario_id is None:
            return
        schedule_repository = self.schedule_repository_cls(session=session)
        scenario = schedule_repository.get_scenario(scenario_id)
        if scenario is None:
            raise ValueError(f"ScheduleScenario with id={scenario_id} was not found")
        if int(scenario.calendar_period_id) != int(calendar_period_id):
            raise ValueError("Scenario belongs to a different calendar period")

    def analyze_feasibility(
        self,
        session: Session,
        calendar_period_id: int,
        replace_existing: bool = True,
        scenario_id: int | None = None,
        policy_options: SchedulerPolicyOptions | None = None,
    ) -> FeasibilityReport:
        calendar_period = session.get(CalendarPeriod, calendar_period_id)
        if calendar_period is None:
            raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")
        self._validate_scenario_context(
            session=session,
            calendar_period_id=calendar_period_id,
            scenario_id=scenario_id,
        )
        policy = self._resolve_policy(
            session=session,
            company_id=calendar_period.company_id,
            policy_options=policy_options,
        )

        teaching_blocks = self._load_teaching_blocks(session=session, calendar_period_id=calendar_period_id)
        if not teaching_blocks:
            return FeasibilityReport(issues=[], candidate_capacity={})

        block_by_key = {(block.date, block.order_in_day): block for block in teaching_blocks}
        block_by_id = {block.id: block for block in teaching_blocks}
        day_order_bounds = self._build_day_order_bounds(teaching_blocks=teaching_blocks)

        requirements = self._load_requirements(
            session=session,
            company_id=calendar_period.company_id,
        )
        if not requirements:
            return FeasibilityReport(issues=[], candidate_capacity={})

        requirement_non_room_resource_ids: dict[int, set[int]] = {}
        requirement_manual_room_resource_ids: dict[int, set[int]] = {}
        requirement_actor_resource_ids: dict[int, set[int]] = {}
        for requirement in requirements:
            non_room_resources: set[int] = set()
            manual_room_resources: set[int] = set()
            actor_resources: set[int] = set()
            for item in requirement.requirement_resources:
                if item.resource.type == ResourceType.ROOM:
                    manual_room_resources.add(item.resource_id)
                else:
                    non_room_resources.add(item.resource_id)
                    if item.resource.type in {ResourceType.TEACHER, ResourceType.GROUP, ResourceType.SUBGROUP}:
                        actor_resources.add(item.resource_id)
            requirement_non_room_resource_ids[requirement.id] = non_room_resources
            requirement_manual_room_resource_ids[requirement.id] = manual_room_resources
            requirement_actor_resource_ids[requirement.id] = actor_resources

        room_options_by_requirement, room_building_by_resource_id = self._build_room_options_by_requirement(
            session=session,
            requirements=requirements,
            requirement_manual_room_resource_ids=requirement_manual_room_resource_ids,
            company_id=calendar_period.company_id,
        )
        room_default_resource_by_requirement = self._build_room_default_resource_map(
            room_options_by_requirement=room_options_by_requirement,
        )

        schedule_repository = self.schedule_repository_cls(session=session)
        existing_entries = schedule_repository.list_entries_for_period(
            calendar_period_id=calendar_period_id,
            scenario_id=scenario_id,
        )
        if replace_existing:
            existing_entries = [entry for entry in existing_entries if bool(entry.is_locked)]

        resource_reservations = self._build_resource_reservations(
            existing_entries=existing_entries,
            block_by_key=block_by_key,
            block_by_id=block_by_id,
            requirement_non_room_resource_ids=requirement_non_room_resource_ids,
            room_default_resource_by_requirement=room_default_resource_by_requirement,
        )
        requirement_block_reservations = self._build_requirement_block_reservations(
            existing_entries=existing_entries,
            block_by_key=block_by_key,
            block_by_id=block_by_id,
        )
        weekly_usage = self._build_weekly_usage(existing_entries=existing_entries, block_by_id=block_by_id)
        scheduled_sessions_by_requirement = self._build_existing_session_counts(existing_entries=existing_entries)
        resource_day_orders, resource_day_sessions, resource_day_room_buildings = self._build_resource_day_states(
            existing_entries=existing_entries,
            block_by_id=block_by_id,
            block_by_key=block_by_key,
            requirement_actor_resource_ids=requirement_actor_resource_ids,
            room_default_resource_by_requirement=room_default_resource_by_requirement,
            room_building_by_resource_id=room_building_by_resource_id,
        )

        blackout_resource_ids = self._collect_blackout_resource_ids(
            requirement_non_room_resource_ids=requirement_non_room_resource_ids,
            room_options_by_requirement=room_options_by_requirement,
            existing_entries=existing_entries,
        )
        if blackout_resource_ids:
            blackouts = self._load_blackouts(
                session=session,
                resource_ids=blackout_resource_ids,
                window_start=teaching_blocks[0].start_timestamp,
                window_end=teaching_blocks[-1].end_timestamp,
            )
            blackout_reservations = self._build_blackout_reservations(
                teaching_blocks=teaching_blocks,
                blackouts=blackouts,
            )
            for block_id, blocked_resources in blackout_reservations.items():
                resource_reservations[block_id].update(blocked_resources)

        issues: list[FeasibilityIssue] = []
        candidate_capacity: dict[int, int] = {}
        demand_by_resource: dict[int, int] = defaultdict(int)

        for requirement in requirements:
            required_sessions = max(
                0,
                requirement.sessions_total - scheduled_sessions_by_requirement.get(requirement.id, 0),
            )
            if required_sessions <= 0:
                candidate_capacity[requirement.id] = 0
                continue
            room_options = room_options_by_requirement.get(requirement.id)
            if room_options is not None and not room_options:
                issues.append(
                    FeasibilityIssue(
                        code="ROOM_OPTIONS_EMPTY",
                        message=f"Вимога {requirement.id} не має сумісних аудиторій.",
                        requirement_id=requirement.id,
                    )
                )
            for actor_id in requirement_actor_resource_ids.get(requirement.id, set()):
                demand_by_resource[actor_id] += required_sessions * requirement.duration_blocks

            candidates = self._generate_candidates(
                requirement=requirement,
                teaching_blocks=teaching_blocks,
                block_by_key=block_by_key,
                requirement_non_room_resource_ids=requirement_non_room_resource_ids,
                requirement_actor_resource_ids=requirement_actor_resource_ids,
                room_options_by_requirement=room_options_by_requirement,
                room_building_by_resource_id=room_building_by_resource_id,
                resource_reservations=resource_reservations,
                requirement_block_reservations=requirement_block_reservations,
                weekly_usage=weekly_usage,
                resource_day_orders=resource_day_orders,
                resource_day_sessions=resource_day_sessions,
                resource_day_room_buildings=resource_day_room_buildings,
                day_order_bounds=day_order_bounds,
                policy=policy,
            )
            candidate_capacity[requirement.id] = len(candidates)
            if not candidates:
                issues.append(
                    FeasibilityIssue(
                        code="NO_CANDIDATES",
                        message=f"Вимога {requirement.id} не має доступних слотів.",
                        requirement_id=requirement.id,
                    )
                )
            elif len(candidates) < required_sessions:
                issues.append(
                    FeasibilityIssue(
                        code="CANDIDATE_CAPACITY_LOW",
                        message=(
                            f"Вимога {requirement.id}: доступних слотів {len(candidates)}, "
                            f"потрібно {required_sessions}."
                        ),
                        requirement_id=requirement.id,
                    )
                )

        for resource_id, demand_blocks in demand_by_resource.items():
            available_blocks = 0
            for block in teaching_blocks:
                if resource_id not in resource_reservations.get(block.id, set()):
                    available_blocks += 1
            if demand_blocks <= available_blocks:
                continue
            issues.append(
                FeasibilityIssue(
                    code="RESOURCE_OVERLOAD",
                    message=(
                        f"Ресурс {resource_id}: попит {demand_blocks} блоків, "
                        f"доступно {available_blocks}."
                    ),
                    resource_id=resource_id,
                )
            )

        return FeasibilityReport(issues=issues, candidate_capacity=candidate_capacity)

    def create_manual_entry(
        self,
        session: Session,
        *,
        calendar_period_id: int,
        scenario_id: int | None = None,
        requirement_id: int,
        day: date,
        order_in_day: int,
        room_resource_id: int | None = None,
        is_locked: bool = True,
    ) -> ScheduleEntry | ScheduleScenarioEntry:
        calendar_period = session.get(CalendarPeriod, calendar_period_id)
        if calendar_period is None:
            raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")
        self._validate_scenario_context(
            session=session,
            calendar_period_id=calendar_period_id,
            scenario_id=scenario_id,
        )

        requirement = session.get(Requirement, requirement_id)
        if requirement is None:
            raise ValueError(f"Requirement with id={requirement_id} was not found")
        if (
            calendar_period.company_id is not None
            and requirement.company_id is not None
            and calendar_period.company_id != requirement.company_id
        ):
            raise ValueError("Requirement and calendar period belong to different companies")

        policy = self.get_policy(session=session, company_id=calendar_period.company_id)
        teaching_blocks = self._load_teaching_blocks(session=session, calendar_period_id=calendar_period_id)
        if not teaching_blocks:
            raise ValueError("У періоді немає навчальних блоків")

        block_by_key = {(block.date, block.order_in_day): block for block in teaching_blocks}
        block_by_id = {block.id: block for block in teaching_blocks}
        start_block = block_by_key.get((day, order_in_day))
        if start_block is None:
            raise ValueError("Стартовий блок не знайдено у періоді")
        block_ids = self._resolve_block_ids(
            start_block=start_block,
            blocks_count=requirement.duration_blocks,
            block_by_key=block_by_key,
        )
        if not block_ids:
            raise ValueError("Немає потрібної безперервної послідовності блоків для цієї вимоги")

        requirements = self._load_requirements(session=session, company_id=calendar_period.company_id)
        requirement_non_room_resource_ids: dict[int, set[int]] = {}
        requirement_manual_room_resource_ids: dict[int, set[int]] = {}
        requirement_actor_resource_ids: dict[int, set[int]] = {}
        for item in requirements:
            non_room_resources: set[int] = set()
            manual_room_resources: set[int] = set()
            actor_resources: set[int] = set()
            for requirement_resource in item.requirement_resources:
                if requirement_resource.resource.type == ResourceType.ROOM:
                    manual_room_resources.add(requirement_resource.resource_id)
                else:
                    non_room_resources.add(requirement_resource.resource_id)
                    if requirement_resource.resource.type in {ResourceType.TEACHER, ResourceType.GROUP, ResourceType.SUBGROUP}:
                        actor_resources.add(requirement_resource.resource_id)
            requirement_non_room_resource_ids[item.id] = non_room_resources
            requirement_manual_room_resource_ids[item.id] = manual_room_resources
            requirement_actor_resource_ids[item.id] = actor_resources

        room_options_by_requirement, room_building_by_resource_id = self._build_room_options_by_requirement(
            session=session,
            requirements=requirements,
            requirement_manual_room_resource_ids=requirement_manual_room_resource_ids,
            company_id=calendar_period.company_id,
        )
        room_default_resource_by_requirement = self._build_room_default_resource_map(
            room_options_by_requirement=room_options_by_requirement,
        )
        requirement_room_options = room_options_by_requirement.get(requirement_id)
        selected_room_resource_id = room_resource_id
        if requirement_room_options is not None:
            if selected_room_resource_id is None:
                if len(requirement_room_options) == 1:
                    selected_room_resource_id = requirement_room_options[0]
                else:
                    raise ValueError("Для цієї вимоги потрібно обрати аудиторію")
            elif selected_room_resource_id not in requirement_room_options:
                raise ValueError("Обрана аудиторія не відповідає обмеженням вимоги")
        if selected_room_resource_id is not None:
            selected_room = session.get(Resource, selected_room_resource_id)
            if selected_room is None or selected_room.type != ResourceType.ROOM:
                raise ValueError("Обрана аудиторія не існує")
            if (
                calendar_period.company_id is not None
                and selected_room.company_id is not None
                and calendar_period.company_id != selected_room.company_id
            ):
                raise ValueError("Обрана аудиторія належить іншій компанії")

        schedule_repository = self.schedule_repository_cls(session=session)
        existing_entries = schedule_repository.list_entries_for_period(
            calendar_period_id=calendar_period_id,
            scenario_id=scenario_id,
        )
        resource_reservations = self._build_resource_reservations(
            existing_entries=existing_entries,
            block_by_key=block_by_key,
            block_by_id=block_by_id,
            requirement_non_room_resource_ids=requirement_non_room_resource_ids,
            room_default_resource_by_requirement=room_default_resource_by_requirement,
        )
        requirement_block_reservations = self._build_requirement_block_reservations(
            existing_entries=existing_entries,
            block_by_key=block_by_key,
            block_by_id=block_by_id,
        )
        weekly_usage = self._build_weekly_usage(existing_entries=existing_entries, block_by_id=block_by_id)
        resource_day_orders, resource_day_sessions, _ = self._build_resource_day_states(
            existing_entries=existing_entries,
            block_by_id=block_by_id,
            block_by_key=block_by_key,
            requirement_actor_resource_ids=requirement_actor_resource_ids,
            room_default_resource_by_requirement=room_default_resource_by_requirement,
            room_building_by_resource_id=room_building_by_resource_id,
        )

        blackout_resource_ids = self._collect_blackout_resource_ids(
            requirement_non_room_resource_ids=requirement_non_room_resource_ids,
            room_options_by_requirement=room_options_by_requirement,
            existing_entries=existing_entries,
        )
        if selected_room_resource_id is not None:
            blackout_resource_ids.add(selected_room_resource_id)
        if blackout_resource_ids:
            blackouts = self._load_blackouts(
                session=session,
                resource_ids=blackout_resource_ids,
                window_start=teaching_blocks[0].start_timestamp,
                window_end=teaching_blocks[-1].end_timestamp,
            )
            blackout_reservations = self._build_blackout_reservations(
                teaching_blocks=teaching_blocks,
                blackouts=blackouts,
            )
            for block_id, blocked_resources in blackout_reservations.items():
                resource_reservations[block_id].update(blocked_resources)

        requirement_resources = set(requirement_non_room_resource_ids.get(requirement_id, set()))
        if selected_room_resource_id is not None:
            requirement_resources.add(selected_room_resource_id)
        if self._has_resource_conflict(
            block_ids=block_ids,
            required_resources=requirement_resources,
            resource_reservations=resource_reservations,
        ):
            raise ValueError("Слот конфліктує з існуючими заняттями або blackout-інтервалами")
        if any(block_id in requirement_block_reservations.get(requirement_id, set()) for block_id in block_ids):
            raise ValueError("Ця вимога вже має заняття у вибраному слоті")

        week_key = self._week_key(start_block.date)
        if weekly_usage[(requirement_id, week_key[0], week_key[1])] >= requirement.max_per_week:
            raise ValueError("Перевищено max_per_week для вимоги")

        candidate_orders = tuple(start_block.order_in_day + offset for offset in range(requirement.duration_blocks))
        if self._violates_hard_constraints(
            policy=policy,
            actor_resource_ids=requirement_actor_resource_ids.get(requirement_id, set()),
            day=start_block.date,
            candidate_orders=candidate_orders,
            resource_day_orders=resource_day_orders,
            resource_day_sessions=resource_day_sessions,
        ):
            raise ValueError("Слот порушує жорсткі обмеження навантаження")

        return schedule_repository.create_entry(
            company_id=calendar_period.company_id,
            requirement_id=requirement_id,
            start_block_id=start_block.id,
            blocks_count=requirement.duration_blocks,
            room_resource_id=selected_room_resource_id,
            is_locked=bool(is_locked),
            is_manual=True,
            scenario_id=scenario_id,
        )

    def build_schedule(
        self,
        session: Session,
        calendar_period_id: int,
        replace_existing: bool = True,
        scenario_id: int | None = None,
        policy_options: SchedulerPolicyOptions | None = None,
    ) -> ScheduleRunResult:
        calendar_period = session.get(CalendarPeriod, calendar_period_id)
        if calendar_period is None:
            raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")
        self._validate_scenario_context(
            session=session,
            calendar_period_id=calendar_period_id,
            scenario_id=scenario_id,
        )
        policy = self._resolve_policy(
            session=session,
            company_id=calendar_period.company_id,
            policy_options=policy_options,
        )

        teaching_blocks = self._load_teaching_blocks(session=session, calendar_period_id=calendar_period_id)
        if not teaching_blocks:
            return ScheduleRunResult(created_entries=[], unscheduled_sessions={})

        block_by_key = {(block.date, block.order_in_day): block for block in teaching_blocks}
        block_by_id = {block.id: block for block in teaching_blocks}
        day_order_bounds = self._build_day_order_bounds(teaching_blocks=teaching_blocks)
        requirements = self._load_requirements(
            session=session,
            company_id=calendar_period.company_id,
        )
        if not requirements:
            return ScheduleRunResult(created_entries=[], unscheduled_sessions={})

        requirement_non_room_resource_ids: dict[int, set[int]] = {}
        requirement_manual_room_resource_ids: dict[int, set[int]] = {}
        requirement_actor_resource_ids: dict[int, set[int]] = {}
        for requirement in requirements:
            non_room_resources: set[int] = set()
            manual_room_resources: set[int] = set()
            actor_resources: set[int] = set()
            for item in requirement.requirement_resources:
                if item.resource.type == ResourceType.ROOM:
                    manual_room_resources.add(item.resource_id)
                else:
                    non_room_resources.add(item.resource_id)
                    if item.resource.type in {ResourceType.TEACHER, ResourceType.GROUP, ResourceType.SUBGROUP}:
                        actor_resources.add(item.resource_id)
            requirement_non_room_resource_ids[requirement.id] = non_room_resources
            requirement_manual_room_resource_ids[requirement.id] = manual_room_resources
            requirement_actor_resource_ids[requirement.id] = actor_resources

        room_options_by_requirement, room_building_by_resource_id = self._build_room_options_by_requirement(
            session=session,
            requirements=requirements,
            requirement_manual_room_resource_ids=requirement_manual_room_resource_ids,
            company_id=calendar_period.company_id,
        )
        room_default_resource_by_requirement = self._build_room_default_resource_map(
            room_options_by_requirement=room_options_by_requirement,
        )

        schedule_repository = self.schedule_repository_cls(session=session)
        if replace_existing:
            schedule_repository.clear_entries_for_period(
                calendar_period_id=calendar_period_id,
                keep_locked=True,
                scenario_id=scenario_id,
            )
        existing_entries = schedule_repository.list_entries_for_period(
            calendar_period_id=calendar_period_id,
            scenario_id=scenario_id,
        )

        resource_reservations = self._build_resource_reservations(
            existing_entries=existing_entries,
            block_by_key=block_by_key,
            block_by_id=block_by_id,
            requirement_non_room_resource_ids=requirement_non_room_resource_ids,
            room_default_resource_by_requirement=room_default_resource_by_requirement,
        )
        blackout_resource_ids = self._collect_blackout_resource_ids(
            requirement_non_room_resource_ids=requirement_non_room_resource_ids,
            room_options_by_requirement=room_options_by_requirement,
            existing_entries=existing_entries,
        )
        if blackout_resource_ids:
            blackouts = self._load_blackouts(
                session=session,
                resource_ids=blackout_resource_ids,
                window_start=teaching_blocks[0].start_timestamp,
                window_end=teaching_blocks[-1].end_timestamp,
            )
            blackout_reservations = self._build_blackout_reservations(
                teaching_blocks=teaching_blocks,
                blackouts=blackouts,
            )
            for block_id, blocked_resources in blackout_reservations.items():
                resource_reservations[block_id].update(blocked_resources)

        requirement_block_reservations = self._build_requirement_block_reservations(
            existing_entries=existing_entries,
            block_by_key=block_by_key,
            block_by_id=block_by_id,
        )
        weekly_usage = self._build_weekly_usage(existing_entries=existing_entries, block_by_id=block_by_id)
        scheduled_sessions_by_requirement = self._build_existing_session_counts(existing_entries=existing_entries)
        resource_day_orders, resource_day_sessions, resource_day_room_buildings = self._build_resource_day_states(
            existing_entries=existing_entries,
            block_by_id=block_by_id,
            block_by_key=block_by_key,
            requirement_actor_resource_ids=requirement_actor_resource_ids,
            room_default_resource_by_requirement=room_default_resource_by_requirement,
            room_building_by_resource_id=room_building_by_resource_id,
        )

        sorted_requirements = self._sort_requirements_by_difficulty(
            requirements=requirements,
            teaching_blocks=teaching_blocks,
            block_by_key=block_by_key,
            requirement_non_room_resource_ids=requirement_non_room_resource_ids,
            requirement_actor_resource_ids=requirement_actor_resource_ids,
            room_options_by_requirement=room_options_by_requirement,
            room_building_by_resource_id=room_building_by_resource_id,
            resource_reservations=resource_reservations,
            requirement_block_reservations=requirement_block_reservations,
            weekly_usage=weekly_usage,
            resource_day_orders=resource_day_orders,
            resource_day_sessions=resource_day_sessions,
            resource_day_room_buildings=resource_day_room_buildings,
            day_order_bounds=day_order_bounds,
            policy=policy,
        )

        created_entries: list[ScheduleEntry | ScheduleScenarioEntry] = []
        unscheduled_sessions: dict[int, int] = {}
        diagnostics: list[SchedulingDiagnostic] = []

        for requirement in sorted_requirements:
            required_sessions = max(
                0,
                requirement.sessions_total - scheduled_sessions_by_requirement[requirement.id],
            )
            placed_sessions = 0
            while placed_sessions < required_sessions:
                candidates = self._generate_candidates(
                    requirement=requirement,
                    teaching_blocks=teaching_blocks,
                    block_by_key=block_by_key,
                    requirement_non_room_resource_ids=requirement_non_room_resource_ids,
                    requirement_actor_resource_ids=requirement_actor_resource_ids,
                    room_options_by_requirement=room_options_by_requirement,
                    room_building_by_resource_id=room_building_by_resource_id,
                    resource_reservations=resource_reservations,
                    requirement_block_reservations=requirement_block_reservations,
                    weekly_usage=weekly_usage,
                    resource_day_orders=resource_day_orders,
                    resource_day_sessions=resource_day_sessions,
                    resource_day_room_buildings=resource_day_room_buildings,
                    day_order_bounds=day_order_bounds,
                    policy=policy,
                )
                if not candidates:
                    remaining = required_sessions - placed_sessions
                    unscheduled_sessions[requirement.id] = remaining
                    diagnostics.extend(
                        self._diagnose_requirement_failures(
                            requirement=requirement,
                            remaining_sessions=remaining,
                            teaching_blocks=teaching_blocks,
                            block_by_key=block_by_key,
                            block_by_id=block_by_id,
                            requirement_non_room_resource_ids=requirement_non_room_resource_ids,
                            requirement_actor_resource_ids=requirement_actor_resource_ids,
                            room_options_by_requirement=room_options_by_requirement,
                            resource_reservations=resource_reservations,
                            requirement_block_reservations=requirement_block_reservations,
                            weekly_usage=weekly_usage,
                            resource_day_orders=resource_day_orders,
                            resource_day_sessions=resource_day_sessions,
                            policy=policy,
                        )
                    )
                    break

                candidate = candidates[0]
                entry = schedule_repository.create_entry(
                    company_id=calendar_period.company_id,
                    requirement_id=requirement.id,
                    start_block_id=candidate.start_block_id,
                    blocks_count=requirement.duration_blocks,
                    room_resource_id=candidate.room_resource_id,
                    is_locked=False,
                    is_manual=False,
                    scenario_id=scenario_id,
                )
                created_entries.append(entry)
                placed_sessions += 1
                scheduled_sessions_by_requirement[requirement.id] += 1

                requirement_resources = set(requirement_non_room_resource_ids.get(requirement.id, set()))
                if candidate.room_resource_id is not None:
                    requirement_resources.add(candidate.room_resource_id)
                for block_id in candidate.block_ids:
                    requirement_block_reservations[requirement.id].add(block_id)
                    if requirement_resources:
                        resource_reservations[block_id].update(requirement_resources)

                start_block = block_by_id[candidate.start_block_id]
                candidate_orders = tuple(start_block.order_in_day + offset for offset in range(requirement.duration_blocks))
                self._reserve_candidate_day_state(
                    actor_resource_ids=requirement_actor_resource_ids.get(requirement.id, set()),
                    day=start_block.date,
                    candidate_orders=candidate_orders,
                    room_resource_id=candidate.room_resource_id,
                    room_building_by_resource_id=room_building_by_resource_id,
                    resource_day_orders=resource_day_orders,
                    resource_day_sessions=resource_day_sessions,
                    resource_day_room_buildings=resource_day_room_buildings,
                )
                weekly_usage[(requirement.id, candidate.week_key[0], candidate.week_key[1])] += 1

        return ScheduleRunResult(
            created_entries=created_entries,
            unscheduled_sessions=unscheduled_sessions,
            diagnostics=diagnostics,
        )

    def _load_teaching_blocks(
        self,
        session: Session,
        calendar_period_id: int,
    ) -> list[TimeBlock]:
        statement = (
            select(TimeBlock)
            .where(
                TimeBlock.calendar_period_id == calendar_period_id,
                TimeBlock.block_kind == MarkKind.TEACHING,
            )
            .order_by(TimeBlock.date.asc(), TimeBlock.order_in_day.asc())
        )
        return list(session.scalars(statement).all())

    def _load_requirements(self, session: Session, company_id: int | None) -> list[Requirement]:
        statement = select(Requirement).order_by(Requirement.id.asc())
        if company_id is not None:
            statement = statement.where(Requirement.company_id == company_id)
        return list(session.scalars(statement).all())

    def _build_resource_reservations(
        self,
        existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
        block_by_key: dict[tuple[date, int], TimeBlock],
        block_by_id: dict[int, TimeBlock],
        requirement_non_room_resource_ids: dict[int, set[int]],
        room_default_resource_by_requirement: dict[int, int],
    ) -> dict[int, set[int]]:
        reservations: dict[int, set[int]] = defaultdict(set)
        for entry in existing_entries:
            start_block = block_by_id.get(entry.start_block_id)
            if start_block is None:
                continue
            block_ids = self._resolve_block_ids(
                start_block=start_block,
                blocks_count=entry.blocks_count,
                block_by_key=block_by_key,
            )
            if not block_ids:
                continue
            resources = set(requirement_non_room_resource_ids.get(entry.requirement_id, set()))
            if entry.room_resource_id is not None:
                resources.add(entry.room_resource_id)
            elif entry.requirement_id in room_default_resource_by_requirement:
                resources.add(room_default_resource_by_requirement[entry.requirement_id])
            for block_id in block_ids:
                reservations[block_id].update(resources)
        return reservations

    def _build_requirement_block_reservations(
        self,
        existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
        block_by_key: dict[tuple[date, int], TimeBlock],
        block_by_id: dict[int, TimeBlock],
    ) -> dict[int, set[int]]:
        reservations: dict[int, set[int]] = defaultdict(set)
        for entry in existing_entries:
            start_block = block_by_id.get(entry.start_block_id)
            if start_block is None:
                continue
            block_ids = self._resolve_block_ids(
                start_block=start_block,
                blocks_count=entry.blocks_count,
                block_by_key=block_by_key,
            )
            if not block_ids:
                continue
            reservations[entry.requirement_id].update(block_ids)
        return reservations

    def _build_weekly_usage(
        self,
        existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
        block_by_id: dict[int, TimeBlock],
    ) -> dict[tuple[int, int, int], int]:
        weekly_usage: dict[tuple[int, int, int], int] = defaultdict(int)
        for entry in existing_entries:
            start_block = block_by_id.get(entry.start_block_id)
            if start_block is None:
                continue
            week_key = self._week_key(start_block.date)
            weekly_usage[(entry.requirement_id, week_key[0], week_key[1])] += 1
        return weekly_usage

    def _build_existing_session_counts(
        self,
        existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
    ) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for entry in existing_entries:
            counts[entry.requirement_id] += 1
        return counts

    def _sort_requirements_by_difficulty(
        self,
        requirements: list[Requirement],
        teaching_blocks: list[TimeBlock],
        block_by_key: dict[tuple[date, int], TimeBlock],
        requirement_non_room_resource_ids: dict[int, set[int]],
        requirement_actor_resource_ids: dict[int, set[int]],
        room_options_by_requirement: dict[int, tuple[int, ...]],
        room_building_by_resource_id: dict[int, int | None],
        resource_reservations: dict[int, set[int]],
        requirement_block_reservations: dict[int, set[int]],
        weekly_usage: dict[tuple[int, int, int], int],
        resource_day_orders: dict[tuple[int, date], set[int]],
        resource_day_sessions: dict[tuple[int, date], int],
        resource_day_room_buildings: dict[tuple[int, date, int], int],
        day_order_bounds: dict[date, tuple[int, int]],
        policy: SchedulerPolicyOptions,
    ) -> list[Requirement]:
        scored_requirements = []
        for requirement in requirements:
            candidates = self._generate_candidates(
                requirement=requirement,
                teaching_blocks=teaching_blocks,
                block_by_key=block_by_key,
                requirement_non_room_resource_ids=requirement_non_room_resource_ids,
                requirement_actor_resource_ids=requirement_actor_resource_ids,
                room_options_by_requirement=room_options_by_requirement,
                room_building_by_resource_id=room_building_by_resource_id,
                resource_reservations=resource_reservations,
                requirement_block_reservations=requirement_block_reservations,
                weekly_usage=weekly_usage,
                resource_day_orders=resource_day_orders,
                resource_day_sessions=resource_day_sessions,
                resource_day_room_buildings=resource_day_room_buildings,
                day_order_bounds=day_order_bounds,
                policy=policy,
            )
            room_option_count = len(room_options_by_requirement.get(requirement.id, ()))
            scored_requirements.append(
                (
                    requirement,
                    len(candidates),
                    requirement.sessions_total * requirement.duration_blocks,
                    len(requirement_non_room_resource_ids.get(requirement.id, set())),
                    room_option_count if room_options_by_requirement.get(requirement.id) is not None else 0,
                )
            )

        scored_requirements.sort(
            key=lambda item: (
                item[1],
                -item[2],
                -item[3],
                item[4],
                item[0].id,
            )
        )
        return [item[0] for item in scored_requirements]

    def _generate_candidates(
        self,
        requirement: Requirement,
        teaching_blocks: list[TimeBlock],
        block_by_key: dict[tuple[date, int], TimeBlock],
        requirement_non_room_resource_ids: dict[int, set[int]],
        requirement_actor_resource_ids: dict[int, set[int]],
        room_options_by_requirement: dict[int, tuple[int, ...]],
        room_building_by_resource_id: dict[int, int | None],
        resource_reservations: dict[int, set[int]],
        requirement_block_reservations: dict[int, set[int]],
        weekly_usage: dict[tuple[int, int, int], int],
        resource_day_orders: dict[tuple[int, date], set[int]],
        resource_day_sessions: dict[tuple[int, date], int],
        resource_day_room_buildings: dict[tuple[int, date, int], int],
        day_order_bounds: dict[date, tuple[int, int]],
        policy: SchedulerPolicyOptions,
    ) -> list[ScheduleCandidate]:
        candidates: list[ScheduleCandidate] = []
        required_resources = requirement_non_room_resource_ids.get(requirement.id, set())
        actor_resources = requirement_actor_resource_ids.get(requirement.id, set())
        occupied_by_requirement = requirement_block_reservations.get(requirement.id, set())
        room_options = room_options_by_requirement.get(requirement.id)

        if room_options is not None and not room_options:
            return candidates

        for start_block in teaching_blocks:
            week_key = self._week_key(start_block.date)
            if weekly_usage[(requirement.id, week_key[0], week_key[1])] >= requirement.max_per_week:
                continue

            block_ids = self._resolve_block_ids(
                start_block=start_block,
                blocks_count=requirement.duration_blocks,
                block_by_key=block_by_key,
            )
            if not block_ids:
                continue
            candidate_orders = tuple(start_block.order_in_day + offset for offset in range(requirement.duration_blocks))

            if any(block_id in occupied_by_requirement for block_id in block_ids):
                continue

            if self._has_resource_conflict(
                block_ids=block_ids,
                required_resources=required_resources,
                resource_reservations=resource_reservations,
            ):
                continue

            if self._violates_hard_constraints(
                policy=policy,
                actor_resource_ids=actor_resources,
                day=start_block.date,
                candidate_orders=candidate_orders,
                resource_day_orders=resource_day_orders,
                resource_day_sessions=resource_day_sessions,
            ):
                continue

            if room_options is None:
                score = self._score_candidate(
                    policy=policy,
                    start_block=start_block,
                    candidate_orders=candidate_orders,
                    actor_resource_ids=actor_resources,
                    room_resource_id=None,
                    day_order_bounds=day_order_bounds,
                    room_building_by_resource_id=room_building_by_resource_id,
                    resource_day_orders=resource_day_orders,
                    resource_day_room_buildings=resource_day_room_buildings,
                )
                candidates.append(
                    ScheduleCandidate(
                        start_block_id=start_block.id,
                        block_ids=tuple(block_ids),
                        week_key=week_key,
                        room_resource_id=None,
                        score=score,
                    )
                )
                continue

            for room_resource_id in room_options:
                room_conflict = any(
                    room_resource_id in resource_reservations.get(block_id, set())
                    for block_id in block_ids
                )
                if room_conflict:
                    continue
                score = self._score_candidate(
                    policy=policy,
                    start_block=start_block,
                    candidate_orders=candidate_orders,
                    actor_resource_ids=actor_resources,
                    room_resource_id=room_resource_id,
                    day_order_bounds=day_order_bounds,
                    room_building_by_resource_id=room_building_by_resource_id,
                    resource_day_orders=resource_day_orders,
                    resource_day_room_buildings=resource_day_room_buildings,
                )
                candidates.append(
                    ScheduleCandidate(
                        start_block_id=start_block.id,
                        block_ids=tuple(block_ids),
                        week_key=week_key,
                        room_resource_id=room_resource_id,
                        score=score,
                    )
                )

        candidates.sort(
            key=lambda item: (
                item.score,
                item.start_block_id,
                -1 if item.room_resource_id is None else item.room_resource_id,
            )
        )
        return candidates

    def _diagnose_requirement_failures(
        self,
        *,
        requirement: Requirement,
        remaining_sessions: int,
        teaching_blocks: list[TimeBlock],
        block_by_key: dict[tuple[date, int], TimeBlock],
        block_by_id: dict[int, TimeBlock],
        requirement_non_room_resource_ids: dict[int, set[int]],
        requirement_actor_resource_ids: dict[int, set[int]],
        room_options_by_requirement: dict[int, tuple[int, ...]],
        resource_reservations: dict[int, set[int]],
        requirement_block_reservations: dict[int, set[int]],
        weekly_usage: dict[tuple[int, int, int], int],
        resource_day_orders: dict[tuple[int, date], set[int]],
        resource_day_sessions: dict[tuple[int, date], int],
        policy: SchedulerPolicyOptions,
    ) -> list[SchedulingDiagnostic]:
        diagnostics: list[SchedulingDiagnostic] = []
        dedup: set[tuple[str, int | None, int | None]] = set()

        def append_diagnostic(item: SchedulingDiagnostic) -> None:
            key = (item.code, item.resource_id, item.block_id)
            if key in dedup:
                return
            dedup.add(key)
            diagnostics.append(item)

        room_options = room_options_by_requirement.get(requirement.id)
        if room_options is not None and not room_options:
            append_diagnostic(
                SchedulingDiagnostic(
                    code="ROOM_OPTIONS_EMPTY",
                    message=(
                        f"Requirement {requirement.id}: no compatible rooms for room constraints."
                    ),
                    requirement_id=requirement.id,
                )
            )
            return diagnostics

        required_resources = requirement_non_room_resource_ids.get(requirement.id, set())
        actor_resources = requirement_actor_resource_ids.get(requirement.id, set())
        occupied_by_requirement = requirement_block_reservations.get(requirement.id, set())
        all_weekly_limited = True

        for start_block in teaching_blocks:
            if len(diagnostics) >= 12:
                break
            week_key = self._week_key(start_block.date)
            if weekly_usage[(requirement.id, week_key[0], week_key[1])] >= requirement.max_per_week:
                continue
            all_weekly_limited = False

            block_ids = self._resolve_block_ids(
                start_block=start_block,
                blocks_count=requirement.duration_blocks,
                block_by_key=block_by_key,
            )
            if not block_ids:
                append_diagnostic(
                    SchedulingDiagnostic(
                        code="NO_CONTIGUOUS_BLOCKS",
                        message=(
                            f"Requirement {requirement.id}: slot {start_block.date} "
                            f"#{start_block.order_in_day} has no contiguous span of "
                            f"{requirement.duration_blocks} blocks."
                        ),
                        requirement_id=requirement.id,
                        block_id=start_block.id,
                        day=start_block.date,
                        order_in_day=start_block.order_in_day,
                    )
                )
                continue

            overlap_block_id = next((block_id for block_id in block_ids if block_id in occupied_by_requirement), None)
            if overlap_block_id is not None:
                overlap_block = block_by_id.get(overlap_block_id)
                append_diagnostic(
                    SchedulingDiagnostic(
                        code="REQUIREMENT_OVERLAP",
                        message=(
                            f"Requirement {requirement.id} already has a session in block {overlap_block_id}."
                        ),
                        requirement_id=requirement.id,
                        block_id=overlap_block_id,
                        day=None if overlap_block is None else overlap_block.date,
                        order_in_day=None if overlap_block is None else overlap_block.order_in_day,
                    )
                )
                continue

            conflict = self._first_conflicting_resource(
                block_ids=block_ids,
                required_resources=required_resources,
                resource_reservations=resource_reservations,
            )
            if conflict is not None:
                conflict_resource_id, conflict_block_id = conflict
                conflict_block = block_by_id.get(conflict_block_id)
                append_diagnostic(
                    SchedulingDiagnostic(
                        code="RESOURCE_BUSY",
                        message=(
                            f"Requirement {requirement.id}: resource {conflict_resource_id} "
                            f"is busy in block {conflict_block_id}."
                        ),
                        requirement_id=requirement.id,
                        resource_id=conflict_resource_id,
                        block_id=conflict_block_id,
                        day=None if conflict_block is None else conflict_block.date,
                        order_in_day=None if conflict_block is None else conflict_block.order_in_day,
                    )
                )
                continue

            candidate_orders = tuple(start_block.order_in_day + offset for offset in range(requirement.duration_blocks))
            hard_violation = self._diagnose_hard_constraint_violation(
                policy=policy,
                actor_resource_ids=actor_resources,
                day=start_block.date,
                candidate_orders=candidate_orders,
                resource_day_orders=resource_day_orders,
                resource_day_sessions=resource_day_sessions,
                requirement_id=requirement.id,
                block_id=start_block.id,
            )
            if hard_violation is not None:
                append_diagnostic(hard_violation)
                continue

            if room_options is None:
                continue

            first_room_conflict: tuple[int, int] | None = None
            has_available_room = False
            for room_resource_id in room_options:
                room_conflict_block_id = next(
                    (
                        block_id
                        for block_id in block_ids
                        if room_resource_id in resource_reservations.get(block_id, set())
                    ),
                    None,
                )
                if room_conflict_block_id is None:
                    has_available_room = True
                    break
                if first_room_conflict is None:
                    first_room_conflict = (room_resource_id, room_conflict_block_id)
            if has_available_room:
                continue
            if first_room_conflict is not None:
                room_resource_id, room_conflict_block_id = first_room_conflict
                conflict_block = block_by_id.get(room_conflict_block_id)
                append_diagnostic(
                    SchedulingDiagnostic(
                        code="ROOM_BUSY",
                        message=(
                            f"Requirement {requirement.id}: all rooms are busy; "
                            f"room resource {room_resource_id} conflicts in block {room_conflict_block_id}."
                        ),
                        requirement_id=requirement.id,
                        resource_id=room_resource_id,
                        block_id=room_conflict_block_id,
                        day=None if conflict_block is None else conflict_block.date,
                        order_in_day=None if conflict_block is None else conflict_block.order_in_day,
                    )
                )

        if all_weekly_limited:
            append_diagnostic(
                SchedulingDiagnostic(
                    code="MAX_PER_WEEK_REACHED",
                    message=(
                        f"Requirement {requirement.id}: weekly limit {requirement.max_per_week} "
                        "already reached in all weeks."
                    ),
                    requirement_id=requirement.id,
                )
            )

        if not diagnostics:
            append_diagnostic(
                SchedulingDiagnostic(
                    code="NO_CANDIDATES",
                    message=f"Requirement {requirement.id}: no valid candidate slots.",
                    requirement_id=requirement.id,
                )
            )

        if remaining_sessions > 1:
            append_diagnostic(
                SchedulingDiagnostic(
                    code="UNSCHEDULED_REMAINING",
                    message=(
                        f"Requirement {requirement.id}: {remaining_sessions} sessions left unscheduled."
                    ),
                    requirement_id=requirement.id,
                )
            )

        return diagnostics

    def _first_conflicting_resource(
        self,
        *,
        block_ids: list[int],
        required_resources: set[int],
        resource_reservations: dict[int, set[int]],
    ) -> tuple[int, int] | None:
        if not required_resources:
            return None
        for block_id in block_ids:
            occupied_resources = resource_reservations.get(block_id, set())
            conflict_ids = occupied_resources & required_resources
            if conflict_ids:
                return min(conflict_ids), block_id
        return None

    def _diagnose_hard_constraint_violation(
        self,
        *,
        policy: SchedulerPolicyOptions,
        actor_resource_ids: set[int],
        day: date,
        candidate_orders: tuple[int, ...],
        resource_day_orders: dict[tuple[int, date], set[int]],
        resource_day_sessions: dict[tuple[int, date], int],
        requirement_id: int,
        block_id: int,
    ) -> SchedulingDiagnostic | None:
        if not actor_resource_ids:
            return None

        candidate_order_set = set(candidate_orders)
        for actor_id in actor_resource_ids:
            key = (actor_id, day)
            sessions = resource_day_sessions.get(key, 0)
            if (
                policy.max_sessions_per_day is not None
                and sessions + 1 > policy.max_sessions_per_day
            ):
                return SchedulingDiagnostic(
                    code="MAX_SESSIONS_PER_DAY",
                    message=(
                        f"Requirement {requirement_id}: actor resource {actor_id} exceeds "
                        f"max sessions/day ({policy.max_sessions_per_day})."
                    ),
                    requirement_id=requirement_id,
                    resource_id=actor_id,
                    block_id=block_id,
                    day=day,
                    order_in_day=candidate_orders[0],
                )

            existing_orders = resource_day_orders.get(key, set())
            merged_orders = set(existing_orders) | candidate_order_set
            if (
                policy.max_consecutive_blocks is not None
                and self._longest_streak(merged_orders) > policy.max_consecutive_blocks
            ):
                return SchedulingDiagnostic(
                    code="MAX_CONSECUTIVE_BLOCKS",
                    message=(
                        f"Requirement {requirement_id}: actor resource {actor_id} exceeds "
                        f"max consecutive blocks ({policy.max_consecutive_blocks})."
                    ),
                    requirement_id=requirement_id,
                    resource_id=actor_id,
                    block_id=block_id,
                    day=day,
                    order_in_day=candidate_orders[0],
                )
            if policy.enforce_no_gaps and self._gap_count(merged_orders) > 0:
                return SchedulingDiagnostic(
                    code="NO_GAPS_VIOLATION",
                    message=(
                        f"Requirement {requirement_id}: actor resource {actor_id} creates an "
                        "in-day gap while no-gaps policy is enabled."
                    ),
                    requirement_id=requirement_id,
                    resource_id=actor_id,
                    block_id=block_id,
                    day=day,
                    order_in_day=candidate_orders[0],
                )
        return None

    def _build_room_options_by_requirement(
        self,
        *,
        session: Session,
        requirements: list[Requirement],
        requirement_manual_room_resource_ids: dict[int, set[int]],
        company_id: int | None,
    ) -> tuple[dict[int, tuple[int, ...]], dict[int, int | None]]:
        statement = (
            select(RoomProfile)
            .join(Resource, RoomProfile.resource_id == Resource.id)
            .where(
                Resource.type == ResourceType.ROOM,
                RoomProfile.is_archived.is_(False),
            )
            .order_by(RoomProfile.id.asc())
        )
        if company_id is not None:
            statement = statement.where(RoomProfile.company_id == company_id)
        room_profiles = list(session.scalars(statement).all())
        room_profile_by_id = {item.id: item for item in room_profiles}
        room_building_by_resource_id = {int(item.resource_id): item.building_id for item in room_profiles}

        options_by_requirement: dict[int, tuple[int, ...]] = {}
        for requirement in requirements:
            manual_room_resource_ids = requirement_manual_room_resource_ids.get(requirement.id, set())
            requires_room = (
                bool(manual_room_resource_ids)
                or requirement.fixed_room_id is not None
                or requirement.room_type is not None
                or requirement.min_capacity is not None
                or requirement.needs_projector
            )
            if not requires_room:
                continue

            candidate_resource_ids: list[int] = []
            if requirement.fixed_room_id is not None:
                fixed_room = room_profile_by_id.get(requirement.fixed_room_id)
                if (
                    fixed_room is not None
                    and self._room_matches_requirement(requirement=requirement, room=fixed_room)
                    and (not manual_room_resource_ids or fixed_room.resource_id in manual_room_resource_ids)
                ):
                    candidate_resource_ids.append(fixed_room.resource_id)
            else:
                for room in room_profiles:
                    if manual_room_resource_ids and room.resource_id not in manual_room_resource_ids:
                        continue
                    if not self._room_matches_requirement(requirement=requirement, room=room):
                        continue
                    candidate_resource_ids.append(room.resource_id)

            options_by_requirement[requirement.id] = tuple(sorted(set(candidate_resource_ids)))

        return options_by_requirement, room_building_by_resource_id

    def _build_room_default_resource_map(
        self,
        *,
        room_options_by_requirement: dict[int, tuple[int, ...]],
    ) -> dict[int, int]:
        defaults: dict[int, int] = {}
        for requirement_id, room_options in room_options_by_requirement.items():
            if len(room_options) == 1:
                defaults[requirement_id] = room_options[0]
        return defaults

    def _room_matches_requirement(self, *, requirement: Requirement, room: RoomProfile) -> bool:
        if requirement.room_type is not None and room.room_type != requirement.room_type:
            return False
        if requirement.min_capacity is not None and (room.capacity or 0) < requirement.min_capacity:
            return False
        if requirement.needs_projector and not room.has_projector:
            return False
        return True

    def _build_day_order_bounds(self, *, teaching_blocks: list[TimeBlock]) -> dict[date, tuple[int, int]]:
        bounds: dict[date, tuple[int, int]] = {}
        for block in teaching_blocks:
            current = bounds.get(block.date)
            if current is None:
                bounds[block.date] = (block.order_in_day, block.order_in_day)
                continue
            bounds[block.date] = (min(current[0], block.order_in_day), max(current[1], block.order_in_day))
        return bounds

    def _build_resource_day_states(
        self,
        *,
        existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
        block_by_id: dict[int, TimeBlock],
        block_by_key: dict[tuple[date, int], TimeBlock],
        requirement_actor_resource_ids: dict[int, set[int]],
        room_default_resource_by_requirement: dict[int, int],
        room_building_by_resource_id: dict[int, int | None],
    ) -> tuple[
        dict[tuple[int, date], set[int]],
        dict[tuple[int, date], int],
        dict[tuple[int, date, int], int],
    ]:
        resource_day_orders: dict[tuple[int, date], set[int]] = defaultdict(set)
        resource_day_sessions: dict[tuple[int, date], int] = defaultdict(int)
        resource_day_room_buildings: dict[tuple[int, date, int], int] = {}

        for entry in existing_entries:
            start_block = block_by_id.get(entry.start_block_id)
            if start_block is None:
                continue
            block_ids = self._resolve_block_ids(
                start_block=start_block,
                blocks_count=entry.blocks_count,
                block_by_key=block_by_key,
            )
            if not block_ids:
                continue
            actor_resource_ids = requirement_actor_resource_ids.get(entry.requirement_id, set())
            if not actor_resource_ids:
                continue

            day = start_block.date
            candidate_orders = tuple(start_block.order_in_day + offset for offset in range(entry.blocks_count))
            room_resource_id = entry.room_resource_id
            if room_resource_id is None:
                room_resource_id = room_default_resource_by_requirement.get(entry.requirement_id)
            building_id = room_building_by_resource_id.get(room_resource_id) if room_resource_id is not None else None

            for actor_id in actor_resource_ids:
                key = (actor_id, day)
                resource_day_sessions[key] += 1
                resource_day_orders[key].update(candidate_orders)
                if building_id is not None:
                    for order in candidate_orders:
                        resource_day_room_buildings[(actor_id, day, order)] = building_id

        return resource_day_orders, resource_day_sessions, resource_day_room_buildings

    def _reserve_candidate_day_state(
        self,
        *,
        actor_resource_ids: set[int],
        day: date,
        candidate_orders: tuple[int, ...],
        room_resource_id: int | None,
        room_building_by_resource_id: dict[int, int | None],
        resource_day_orders: dict[tuple[int, date], set[int]],
        resource_day_sessions: dict[tuple[int, date], int],
        resource_day_room_buildings: dict[tuple[int, date, int], int],
    ) -> None:
        building_id = room_building_by_resource_id.get(room_resource_id) if room_resource_id is not None else None
        for actor_id in actor_resource_ids:
            key = (actor_id, day)
            resource_day_sessions[key] += 1
            resource_day_orders[key].update(candidate_orders)
            if building_id is not None:
                for order in candidate_orders:
                    resource_day_room_buildings[(actor_id, day, order)] = building_id

    def _collect_blackout_resource_ids(
        self,
        *,
        requirement_non_room_resource_ids: dict[int, set[int]],
        room_options_by_requirement: dict[int, tuple[int, ...]],
        existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
    ) -> set[int]:
        resource_ids = {
            resource_id
            for resources in requirement_non_room_resource_ids.values()
            for resource_id in resources
        }
        for room_options in room_options_by_requirement.values():
            resource_ids.update(room_options)
        for entry in existing_entries:
            if entry.room_resource_id is not None:
                resource_ids.add(entry.room_resource_id)
        return resource_ids

    def _load_blackouts(
        self,
        *,
        session: Session,
        resource_ids: set[int],
        window_start: datetime,
        window_end: datetime,
    ) -> list[ResourceBlackout]:
        statement = (
            select(ResourceBlackout)
            .where(
                ResourceBlackout.resource_id.in_(sorted(resource_ids)),
                ResourceBlackout.starts_at < window_end,
                ResourceBlackout.ends_at > window_start,
            )
            .order_by(ResourceBlackout.starts_at.asc(), ResourceBlackout.id.asc())
        )
        return list(session.scalars(statement).all())

    def _build_blackout_reservations(
        self,
        *,
        teaching_blocks: list[TimeBlock],
        blackouts: list[ResourceBlackout],
    ) -> dict[int, set[int]]:
        reservations: dict[int, set[int]] = defaultdict(set)
        for blackout in blackouts:
            for block in teaching_blocks:
                if blackout.starts_at >= block.end_timestamp:
                    continue
                if blackout.ends_at <= block.start_timestamp:
                    continue
                reservations[block.id].add(blackout.resource_id)
        return reservations

    def _violates_hard_constraints(
        self,
        *,
        policy: SchedulerPolicyOptions,
        actor_resource_ids: set[int],
        day: date,
        candidate_orders: tuple[int, ...],
        resource_day_orders: dict[tuple[int, date], set[int]],
        resource_day_sessions: dict[tuple[int, date], int],
    ) -> bool:
        if not actor_resource_ids:
            return False

        candidate_order_set = set(candidate_orders)
        for actor_id in actor_resource_ids:
            key = (actor_id, day)
            sessions = resource_day_sessions.get(key, 0)
            if (
                policy.max_sessions_per_day is not None
                and sessions + 1 > policy.max_sessions_per_day
            ):
                return True

            existing_orders = resource_day_orders.get(key, set())
            merged_orders = set(existing_orders) | candidate_order_set
            if (
                policy.max_consecutive_blocks is not None
                and self._longest_streak(merged_orders) > policy.max_consecutive_blocks
            ):
                return True
            if policy.enforce_no_gaps and self._gap_count(merged_orders) > 0:
                return True

        return False

    def _score_candidate(
        self,
        *,
        policy: SchedulerPolicyOptions,
        start_block: TimeBlock,
        candidate_orders: tuple[int, ...],
        actor_resource_ids: set[int],
        room_resource_id: int | None,
        day_order_bounds: dict[date, tuple[int, int]],
        room_building_by_resource_id: dict[int, int | None],
        resource_day_orders: dict[tuple[int, date], set[int]],
        resource_day_room_buildings: dict[tuple[int, date, int], int],
    ) -> float:
        score = 0.0
        day = start_block.date
        preference = policy.time_preference if isinstance(policy.time_preference, TimePreference) else TimePreference.BALANCED

        if policy.weight_time_preference > 0 and preference != TimePreference.BALANCED:
            bounds = day_order_bounds.get(day)
            if bounds is not None:
                min_order, max_order = bounds
                if max_order > min_order:
                    position = (start_block.order_in_day - min_order) / (max_order - min_order)
                else:
                    position = 0.0
                if preference == TimePreference.MORNING:
                    score += policy.weight_time_preference * position
                else:
                    score += policy.weight_time_preference * (1.0 - position)

        if policy.weight_compactness > 0:
            candidate_set = set(candidate_orders)
            for actor_id in actor_resource_ids:
                key = (actor_id, day)
                existing = resource_day_orders.get(key, set())
                old_gap = self._gap_count(existing)
                new_gap = self._gap_count(set(existing) | candidate_set)
                if new_gap > old_gap:
                    score += policy.weight_compactness * (new_gap - old_gap)

        if policy.weight_building_transition > 0 and room_resource_id is not None:
            building_id = room_building_by_resource_id.get(room_resource_id)
            if building_id is not None:
                first_order = candidate_orders[0]
                last_order = candidate_orders[-1]
                for actor_id in actor_resource_ids:
                    prev_building = resource_day_room_buildings.get((actor_id, day, first_order - 1))
                    if prev_building is not None and prev_building != building_id:
                        score += policy.weight_building_transition
                    next_building = resource_day_room_buildings.get((actor_id, day, last_order + 1))
                    if next_building is not None and next_building != building_id:
                        score += policy.weight_building_transition

        return score

    def _pick_available_room(
        self,
        *,
        block_ids: list[int],
        room_options: tuple[int, ...],
        resource_reservations: dict[int, set[int]],
    ) -> int | None:
        for room_resource_id in room_options:
            if all(room_resource_id not in resource_reservations.get(block_id, set()) for block_id in block_ids):
                return room_resource_id
        return None

    def _resolve_block_ids(
        self,
        start_block: TimeBlock,
        blocks_count: int,
        block_by_key: dict[tuple[date, int], TimeBlock],
    ) -> list[int]:
        block_ids: list[int] = []
        previous_block: TimeBlock | None = None

        for offset in range(blocks_count):
            key = (start_block.date, start_block.order_in_day + offset)
            current_block = block_by_key.get(key)
            if current_block is None:
                return []

            if previous_block is not None and current_block.start_timestamp != previous_block.end_timestamp:
                return []

            block_ids.append(current_block.id)
            previous_block = current_block

        return block_ids

    def _has_resource_conflict(
        self,
        block_ids: list[int],
        required_resources: set[int],
        resource_reservations: dict[int, set[int]],
    ) -> bool:
        if not required_resources:
            return False
        for block_id in block_ids:
            if resource_reservations.get(block_id, set()) & required_resources:
                return True
        return False

    def _gap_count(self, orders: set[int]) -> int:
        if not orders:
            return 0
        return max(orders) - min(orders) + 1 - len(orders)

    def _longest_streak(self, orders: set[int]) -> int:
        if not orders:
            return 0
        longest = 1
        current = 1
        sorted_orders = sorted(orders)
        for index in range(1, len(sorted_orders)):
            if sorted_orders[index] == sorted_orders[index - 1] + 1:
                current += 1
                longest = max(longest, current)
            else:
                current = 1
        return longest

    def _week_key(self, day: date) -> tuple[int, int]:
        iso_week = day.isocalendar()
        return (iso_week.year, iso_week.week)
