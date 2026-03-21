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
        is_locked: bool = False,
        is_manual: bool = False,
    ) -> ScheduleEntry:
        entry = ScheduleEntry(
            company_id=company_id,
            requirement_id=requirement_id,
            start_block_id=start_block_id,
            blocks_count=blocks_count,
            room_resource_id=room_resource_id,
            is_locked=is_locked,
            is_manual=is_manual,
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

    def clear_entries_for_period(self, calendar_period_id: int, *, keep_locked: bool = False) -> None:
        block_ids_subquery = select(TimeBlock.id).where(TimeBlock.calendar_period_id == calendar_period_id)
        statement = delete(ScheduleEntry).where(ScheduleEntry.start_block_id.in_(block_ids_subquery))
        if keep_locked:
            statement = statement.where(ScheduleEntry.is_locked.is_(False))
        self.session.execute(statement)
        self.session.flush()

    def get_entry(self, entry_id: int) -> ScheduleEntry | None:
        return self.session.get(ScheduleEntry, entry_id)

    def update_entry_lock(self, entry_id: int, *, is_locked: bool) -> ScheduleEntry:
        entry = self.get_entry(entry_id)
        if entry is None:
            raise ValueError(f"ScheduleEntry with id={entry_id} was not found")
        entry.is_locked = bool(is_locked)
        self.session.flush()
        return entry
