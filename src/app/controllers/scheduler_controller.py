from datetime import date

from sqlalchemy.orm import Session

from app.domain.models import ScheduleEntry, ScheduleScenarioEntry
from app.services.greedy_scheduler import (
    CoverageDashboard,
    FeasibilityReport,
    GreedySchedulerService,
    ScheduleEntryCrudItem,
    ScheduleRunResult,
    ScheduleScenarioSummary,
    ScenarioComparison,
    SchedulerPolicyOptions,
)


class SchedulerController:
    def __init__(
        self,
        session: Session,
        scheduler_service: GreedySchedulerService | None = None,
    ) -> None:
        self.session = session
        self.scheduler_service = scheduler_service or GreedySchedulerService()

    def build_schedule(
        self,
        calendar_period_id: int,
        replace_existing: bool = True,
        scenario_id: int | None = None,
        policy_options: SchedulerPolicyOptions | None = None,
    ) -> ScheduleRunResult:
        return self.scheduler_service.build_schedule(
            session=self.session,
            calendar_period_id=calendar_period_id,
            replace_existing=replace_existing,
            scenario_id=scenario_id,
            policy_options=policy_options,
        )

    def analyze_feasibility(
        self,
        calendar_period_id: int,
        replace_existing: bool = True,
        scenario_id: int | None = None,
        policy_options: SchedulerPolicyOptions | None = None,
    ) -> FeasibilityReport:
        return self.scheduler_service.analyze_feasibility(
            session=self.session,
            calendar_period_id=calendar_period_id,
            replace_existing=replace_existing,
            scenario_id=scenario_id,
            policy_options=policy_options,
        )

    def get_coverage_dashboard(
        self,
        *,
        calendar_period_id: int,
        scenario_id: int | None = None,
        policy_options: SchedulerPolicyOptions | None = None,
    ) -> CoverageDashboard:
        return self.scheduler_service.build_coverage_dashboard(
            session=self.session,
            calendar_period_id=calendar_period_id,
            scenario_id=scenario_id,
            policy_options=policy_options,
        )

    def list_scenarios(self, calendar_period_id: int) -> list[ScheduleScenarioSummary]:
        return self.scheduler_service.list_scenarios(
            session=self.session,
            calendar_period_id=calendar_period_id,
        )

    def create_scenario(
        self,
        *,
        calendar_period_id: int,
        name: str,
        source_scenario_id: int | None = None,
        copy_from_published: bool = True,
    ) -> ScheduleScenarioSummary:
        return self.scheduler_service.create_scenario(
            session=self.session,
            calendar_period_id=calendar_period_id,
            name=name,
            source_scenario_id=source_scenario_id,
            copy_from_published=copy_from_published,
        )

    def publish_scenario(self, *, scenario_id: int) -> int:
        return self.scheduler_service.publish_scenario(
            session=self.session,
            scenario_id=scenario_id,
        )

    def compare_scenarios(
        self,
        *,
        calendar_period_id: int,
        left_scenario_id: int | None,
        right_scenario_id: int | None,
    ) -> ScenarioComparison:
        return self.scheduler_service.compare_scenarios(
            session=self.session,
            calendar_period_id=calendar_period_id,
            left_scenario_id=left_scenario_id,
            right_scenario_id=right_scenario_id,
        )

    def get_policy(self, company_id: int | None) -> SchedulerPolicyOptions:
        return self.scheduler_service.get_policy(session=self.session, company_id=company_id)

    def update_policy(
        self,
        company_id: int,
        *,
        max_sessions_per_day: int | None,
        max_consecutive_blocks: int | None,
        enforce_no_gaps: bool,
        time_preference: str,
        weight_time_preference: int,
        weight_compactness: int,
        weight_building_transition: int,
    ) -> SchedulerPolicyOptions:
        options = SchedulerPolicyOptions(
            max_sessions_per_day=max_sessions_per_day,
            max_consecutive_blocks=max_consecutive_blocks,
            enforce_no_gaps=enforce_no_gaps,
            time_preference=time_preference,
            weight_time_preference=weight_time_preference,
            weight_compactness=weight_compactness,
            weight_building_transition=weight_building_transition,
        )
        return self.scheduler_service.update_policy(
            session=self.session,
            company_id=company_id,
            options=options,
        )

    def create_manual_entry(
        self,
        *,
        calendar_period_id: int,
        scenario_id: int | None = None,
        requirement_id: int,
        day: date,
        order_in_day: int,
        room_resource_id: int | None = None,
        is_locked: bool = True,
    ) -> ScheduleEntry | ScheduleScenarioEntry:
        return self.scheduler_service.create_manual_entry(
            session=self.session,
            calendar_period_id=calendar_period_id,
            scenario_id=scenario_id,
            requirement_id=requirement_id,
            day=day,
            order_in_day=order_in_day,
            room_resource_id=room_resource_id,
            is_locked=is_locked,
        )

    def list_schedule_entries(
        self,
        *,
        calendar_period_id: int,
        scenario_id: int | None = None,
    ) -> list[ScheduleEntryCrudItem]:
        return self.scheduler_service.list_schedule_entries(
            session=self.session,
            calendar_period_id=calendar_period_id,
            scenario_id=scenario_id,
        )

    def update_manual_entry(
        self,
        *,
        calendar_period_id: int,
        entry_id: int,
        day: date,
        order_in_day: int,
        scenario_id: int | None = None,
        room_resource_id: int | None = None,
        is_locked: bool | None = None,
    ) -> ScheduleEntry | ScheduleScenarioEntry:
        return self.scheduler_service.update_manual_entry(
            session=self.session,
            calendar_period_id=calendar_period_id,
            entry_id=entry_id,
            day=day,
            order_in_day=order_in_day,
            scenario_id=scenario_id,
            room_resource_id=room_resource_id,
            is_locked=is_locked,
        )

    def set_schedule_entry_lock(
        self,
        *,
        calendar_period_id: int,
        entry_id: int,
        is_locked: bool,
        scenario_id: int | None = None,
    ) -> ScheduleEntry | ScheduleScenarioEntry:
        return self.scheduler_service.set_schedule_entry_lock(
            session=self.session,
            calendar_period_id=calendar_period_id,
            entry_id=entry_id,
            is_locked=is_locked,
            scenario_id=scenario_id,
        )

    def delete_schedule_entry(
        self,
        *,
        calendar_period_id: int,
        entry_id: int,
        scenario_id: int | None = None,
        allow_locked: bool = False,
    ) -> bool:
        return self.scheduler_service.delete_schedule_entry(
            session=self.session,
            calendar_period_id=calendar_period_id,
            entry_id=entry_id,
            scenario_id=scenario_id,
            allow_locked=allow_locked,
        )
