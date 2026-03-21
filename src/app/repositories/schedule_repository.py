from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.models import ScheduleEntry, TimeBlock


class ScheduleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_entry(
        self,
        company_id: int | None,
        requirement_id: int,
        start_block_id: int,
        blocks_count: int,
        room_resource_id: int | None = None,
    ) -> ScheduleEntry:
        entry = ScheduleEntry(
            company_id=company_id,
            requirement_id=requirement_id,
            start_block_id=start_block_id,
            blocks_count=blocks_count,
            room_resource_id=room_resource_id,
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def list_entries_for_period(self, calendar_period_id: int) -> list[ScheduleEntry]:
        statement = (
            select(ScheduleEntry)
            .join(TimeBlock, ScheduleEntry.start_block_id == TimeBlock.id)
            .where(TimeBlock.calendar_period_id == calendar_period_id)
            .order_by(TimeBlock.date.asc(), TimeBlock.order_in_day.asc())
        )
        return list(self.session.scalars(statement).all())

    def clear_entries_for_period(self, calendar_period_id: int) -> None:
        block_ids_subquery = select(TimeBlock.id).where(TimeBlock.calendar_period_id == calendar_period_id)
        self.session.execute(
            delete(ScheduleEntry).where(ScheduleEntry.start_block_id.in_(block_ids_subquery))
        )
        self.session.flush()
