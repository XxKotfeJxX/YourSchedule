from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.domain.models import TimeBlock
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.schedule_repository import ScheduleRepository
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

    def create_calendar_period_with_templates(
        self,
        *,
        company_id: int,
        name: str | None,
        start_date: date,
        weeks_count: int,
        week_pattern_by_week_index: dict[int, int],
    ):
        if weeks_count <= 0:
            raise ValueError("Кількість тижнів має бути більшою за нуль.")
        if not week_pattern_by_week_index:
            raise ValueError("Оберіть шаблон тижня хоча б для першого тижня.")

        default_week_pattern_id = int(week_pattern_by_week_index.get(1, 0))
        if default_week_pattern_id <= 0:
            raise ValueError("Для першого тижня треба вибрати шаблон.")
        default_week_pattern = self.repository.get_week_pattern(default_week_pattern_id)
        if default_week_pattern is None:
            raise ValueError(f"WeekPattern with id={default_week_pattern_id} was not found")

        end_date = start_date + timedelta(days=weeks_count * 7 - 1)
        period = self.repository.create_calendar_period(
            company_id=company_id,
            name=(name or "").strip() or None,
            start_date=start_date,
            end_date=end_date,
            week_pattern=default_week_pattern,
            week_pattern_by_week_index={
                int(week_index): int(pattern_id)
                for week_index, pattern_id in week_pattern_by_week_index.items()
                if 1 <= int(week_index) <= int(weeks_count)
            },
        )
        self.generate_time_blocks(calendar_period_id=period.id, replace_existing=True)
        return period

    def update_calendar_period_with_templates(
        self,
        *,
        period_id: int,
        name: str | None,
        start_date: date,
        weeks_count: int,
        week_pattern_by_week_index: dict[int, int],
    ):
        if weeks_count <= 0:
            raise ValueError("Кількість тижнів має бути більшою за нуль.")
        if not week_pattern_by_week_index:
            raise ValueError("Оберіть шаблон тижня хоча б для першого тижня.")

        default_week_pattern_id = int(week_pattern_by_week_index.get(1, 0))
        if default_week_pattern_id <= 0:
            raise ValueError("Для першого тижня треба вибрати шаблон.")
        if self.repository.get_week_pattern(default_week_pattern_id) is None:
            raise ValueError(f"WeekPattern with id={default_week_pattern_id} was not found")

        end_date = start_date + timedelta(days=weeks_count * 7 - 1)
        period = self.repository.update_calendar_period(
            period_id=period_id,
            name=(name or "").strip() or None,
            start_date=start_date,
            end_date=end_date,
            week_pattern_id=default_week_pattern_id,
            week_pattern_by_week_index={
                int(week_index): int(pattern_id)
                for week_index, pattern_id in week_pattern_by_week_index.items()
                if 1 <= int(week_index) <= int(weeks_count)
            },
        )

        schedule_repository = ScheduleRepository(session=self.session)
        schedule_repository.clear_entries_for_period(
            calendar_period_id=period.id,
            scenario_id=None,
            keep_locked=False,
        )
        for scenario in schedule_repository.list_scenarios(calendar_period_id=period.id):
            schedule_repository.clear_entries_for_period(
                calendar_period_id=period.id,
                scenario_id=int(scenario.id),
                keep_locked=False,
            )
        self.generate_time_blocks(calendar_period_id=period.id, replace_existing=True)
        return period

    def delete_calendar_period(self, *, period_id: int) -> bool:
        schedule_repository = ScheduleRepository(session=self.session)
        schedule_repository.clear_entries_for_period(
            calendar_period_id=period_id,
            scenario_id=None,
            keep_locked=False,
        )
        for scenario in schedule_repository.list_scenarios(calendar_period_id=period_id):
            schedule_repository.clear_entries_for_period(
                calendar_period_id=period_id,
                scenario_id=int(scenario.id),
                keep_locked=False,
            )
        return self.repository.delete_calendar_period(period_id=period_id)
