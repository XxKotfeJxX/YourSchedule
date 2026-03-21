from datetime import date

from sqlalchemy.orm import Session

from app.domain.models import ScheduleEntry
from app.services.greedy_scheduler import (
    FeasibilityReport,
    GreedySchedulerService,
    ScheduleRunResult,
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
        policy_options: SchedulerPolicyOptions | None = None,
    ) -> ScheduleRunResult:
        return self.scheduler_service.build_schedule(
            session=self.session,
            calendar_period_id=calendar_period_id,
            replace_existing=replace_existing,
            policy_options=policy_options,
        )

    def analyze_feasibility(
        self,
        calendar_period_id: int,
        replace_existing: bool = True,
        policy_options: SchedulerPolicyOptions | None = None,
    ) -> FeasibilityReport:
        return self.scheduler_service.analyze_feasibility(
            session=self.session,
            calendar_period_id=calendar_period_id,
            replace_existing=replace_existing,
            policy_options=policy_options,
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
        requirement_id: int,
        day: date,
        order_in_day: int,
        room_resource_id: int | None = None,
        is_locked: bool = True,
    ) -> ScheduleEntry:
        return self.scheduler_service.create_manual_entry(
            session=self.session,
            calendar_period_id=calendar_period_id,
            requirement_id=requirement_id,
            day=day,
            order_in_day=order_in_day,
            room_resource_id=room_resource_id,
            is_locked=is_locked,
        )
