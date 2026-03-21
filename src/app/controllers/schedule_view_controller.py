from datetime import date

from sqlalchemy.orm import Session

from app.services.schedule_visualization import ScheduleVisualizationService, WeeklyScheduleGrid


class ScheduleViewController:
    def __init__(
        self,
        session: Session,
        visualization_service: ScheduleVisualizationService | None = None,
    ) -> None:
        self.session = session
        self.visualization_service = visualization_service or ScheduleVisualizationService()

    def get_weekly_grid(
        self,
        calendar_period_id: int,
        week_start: date | None = None,
        resource_id: int | None = None,
        scenario_id: int | None = None,
    ) -> WeeklyScheduleGrid:
        return self.visualization_service.build_weekly_grid(
            session=self.session,
            calendar_period_id=calendar_period_id,
            week_start=week_start,
            resource_id=resource_id,
            scenario_id=scenario_id,
        )
