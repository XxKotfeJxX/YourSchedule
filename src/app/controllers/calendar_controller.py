from sqlalchemy.orm import Session

from app.domain.models import TimeBlock
from app.repositories.calendar_repository import CalendarRepository
from app.services.time_block_generator import TimeBlockGeneratorService


class CalendarController:
    def __init__(
        self,
        session: Session,
        generator_service: TimeBlockGeneratorService | None = None,
    ) -> None:
        self.session = session
        self.repository = CalendarRepository(session=session)
        self.generator_service = generator_service or TimeBlockGeneratorService()

    def generate_time_blocks(
        self,
        calendar_period_id: int,
        replace_existing: bool = True,
    ) -> list[TimeBlock]:
        return self.generator_service.generate_for_period(
            session=self.session,
            calendar_period_id=calendar_period_id,
            replace_existing=replace_existing,
        )

    def list_calendar_periods(self, company_id: int | None = None):
        return self.repository.list_calendar_periods(company_id=company_id)
