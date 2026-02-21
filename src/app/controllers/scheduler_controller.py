from sqlalchemy.orm import Session

from app.services.greedy_scheduler import GreedySchedulerService, ScheduleRunResult


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
    ) -> ScheduleRunResult:
        return self.scheduler_service.build_schedule(
            session=self.session,
            calendar_period_id=calendar_period_id,
            replace_existing=replace_existing,
        )
