from sqlalchemy.orm import Session

from app.services.schedule_validator import ScheduleValidatorService, ValidationReport


class ScheduleValidationController:
    def __init__(
        self,
        session: Session,
        validator_service: ScheduleValidatorService | None = None,
    ) -> None:
        self.session = session
        self.validator_service = validator_service or ScheduleValidatorService()

    def validate_schedule(
        self,
        calendar_period_id: int,
        *,
        scenario_id: int | None = None,
    ) -> ValidationReport:
        return self.validator_service.validate_period(
            session=self.session,
            calendar_period_id=calendar_period_id,
            scenario_id=scenario_id,
        )
