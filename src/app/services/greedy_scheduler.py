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

_UNSET = object()


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


@dataclass(frozen=True)
class CoverageReason:
    code: str
    requirements_count: int
    sessions_missing: int
    sample_message: str


@dataclass(frozen=True)
class RequirementCoverageItem:
    requirement_id: int
    requirement_name: str
    expected_sessions: int
    scheduled_sessions: int
    missing_sessions: int
    primary_reason_code: str
    primary_reason_message: str


@dataclass
class CoverageDashboard:
    total_requirements: int
    covered_requirements: int
    uncovered_requirements: int
    total_sessions_required: int
    total_sessions_scheduled: int
    reasons: list[CoverageReason]
    uncovered_items: list[RequirementCoverageItem]


@dataclass(frozen=True)
class ScheduleEntryCrudItem:
    entry_id: int
    requirement_id: int
    requirement_name: str
    day: date
    order_in_day: int
    blocks_count: int
    room_resource_id: int | None
    room_name: str | None
    is_locked: bool
    is_manual: bool


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


from app.services.greedy_scheduler_methods import ensure_greedy_scheduler_method_impls

ensure_greedy_scheduler_method_impls(globals())

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

    def build_coverage_dashboard(self, *args, **kwargs):
        return globals()["build_coverage_dashboard__impl"](self, *args, **kwargs)


    def get_policy(self, *args, **kwargs):
        return globals()["get_policy__impl"](self, *args, **kwargs)


    def update_policy(self, *args, **kwargs):
        return globals()["update_policy__impl"](self, *args, **kwargs)


    def _resolve_policy(self, *args, **kwargs):
        return globals()["_resolve_policy__impl"](self, *args, **kwargs)


    def _validate_scenario_context(self, *args, **kwargs):
        return globals()["_validate_scenario_context__impl"](self, *args, **kwargs)


    def analyze_feasibility(self, *args, **kwargs):
        return globals()["analyze_feasibility__impl"](self, *args, **kwargs)


    def list_schedule_entries(self, *args, **kwargs):
        return globals()["list_schedule_entries__impl"](self, *args, **kwargs)


    def delete_schedule_entry(self, *args, **kwargs):
        return globals()["delete_schedule_entry__impl"](self, *args, **kwargs)


    def set_schedule_entry_lock(self, *args, **kwargs):
        return globals()["set_schedule_entry_lock__impl"](self, *args, **kwargs)


    def update_manual_entry(self, *args, **kwargs):
        return globals()["update_manual_entry__impl"](self, *args, **kwargs)


    def create_manual_entry(self, *args, **kwargs):
        return globals()["create_manual_entry__impl"](self, *args, **kwargs)


    def build_schedule(self, *args, **kwargs):
        return globals()["build_schedule__impl"](self, *args, **kwargs)


    def _ensure_entry_in_period(self, *args, **kwargs):
        return globals()["_ensure_entry_in_period__impl"](self, *args, **kwargs)


    def _prepare_manual_slot(self, *args, **kwargs):
        return globals()["_prepare_manual_slot__impl"](self, *args, **kwargs)


    def _load_teaching_blocks(self, *args, **kwargs):
        return globals()["_load_teaching_blocks__impl"](self, *args, **kwargs)


    def _load_requirements(self, *args, **kwargs):
        return globals()["_load_requirements__impl"](self, *args, **kwargs)


    def _build_resource_reservations(self, *args, **kwargs):
        return globals()["_build_resource_reservations__impl"](self, *args, **kwargs)


    def _build_requirement_block_reservations(self, *args, **kwargs):
        return globals()["_build_requirement_block_reservations__impl"](self, *args, **kwargs)


    def _build_weekly_usage(self, *args, **kwargs):
        return globals()["_build_weekly_usage__impl"](self, *args, **kwargs)


    def _build_existing_session_counts(self, *args, **kwargs):
        return globals()["_build_existing_session_counts__impl"](self, *args, **kwargs)


    def _sort_requirements_by_difficulty(self, *args, **kwargs):
        return globals()["_sort_requirements_by_difficulty__impl"](self, *args, **kwargs)


    def _generate_candidates(self, *args, **kwargs):
        return globals()["_generate_candidates__impl"](self, *args, **kwargs)


    def _diagnose_requirement_failures(self, *args, **kwargs):
        return globals()["_diagnose_requirement_failures__impl"](self, *args, **kwargs)


    def _first_conflicting_resource(self, *args, **kwargs):
        return globals()["_first_conflicting_resource__impl"](self, *args, **kwargs)


    def _diagnose_hard_constraint_violation(self, *args, **kwargs):
        return globals()["_diagnose_hard_constraint_violation__impl"](self, *args, **kwargs)


    def _build_room_options_by_requirement(self, *args, **kwargs):
        return globals()["_build_room_options_by_requirement__impl"](self, *args, **kwargs)


    def _build_room_default_resource_map(self, *args, **kwargs):
        return globals()["_build_room_default_resource_map__impl"](self, *args, **kwargs)


    def _room_matches_requirement(self, *args, **kwargs):
        return globals()["_room_matches_requirement__impl"](self, *args, **kwargs)


    def _build_day_order_bounds(self, *args, **kwargs):
        return globals()["_build_day_order_bounds__impl"](self, *args, **kwargs)


    def _build_resource_day_states(self, *args, **kwargs):
        return globals()["_build_resource_day_states__impl"](self, *args, **kwargs)


    def _reserve_candidate_day_state(self, *args, **kwargs):
        return globals()["_reserve_candidate_day_state__impl"](self, *args, **kwargs)


    def _collect_blackout_resource_ids(self, *args, **kwargs):
        return globals()["_collect_blackout_resource_ids__impl"](self, *args, **kwargs)


    def _load_blackouts(self, *args, **kwargs):
        return globals()["_load_blackouts__impl"](self, *args, **kwargs)


    def _build_blackout_reservations(self, *args, **kwargs):
        return globals()["_build_blackout_reservations__impl"](self, *args, **kwargs)


    def _violates_hard_constraints(self, *args, **kwargs):
        return globals()["_violates_hard_constraints__impl"](self, *args, **kwargs)


    def _score_candidate(self, *args, **kwargs):
        return globals()["_score_candidate__impl"](self, *args, **kwargs)


    def _pick_available_room(self, *args, **kwargs):
        return globals()["_pick_available_room__impl"](self, *args, **kwargs)


    def _resolve_block_ids(self, *args, **kwargs):
        return globals()["_resolve_block_ids__impl"](self, *args, **kwargs)


    def _has_resource_conflict(self, *args, **kwargs):
        return globals()["_has_resource_conflict__impl"](self, *args, **kwargs)


    def _gap_count(self, *args, **kwargs):
        return globals()["_gap_count__impl"](self, *args, **kwargs)


    def _longest_streak(self, *args, **kwargs):
        return globals()["_longest_streak__impl"](self, *args, **kwargs)


    def _week_key(self, *args, **kwargs):
        return globals()["_week_key__impl"](self, *args, **kwargs)

