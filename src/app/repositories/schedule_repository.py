from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.domain.models import ScheduleEntry, ScheduleScenario, ScheduleScenarioEntry, TimeBlock


ScheduleEntryLike = ScheduleEntry | ScheduleScenarioEntry


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
        scenario_id: int | None = None,
    ) -> ScheduleEntryLike:
        if scenario_id is None:
            entry = ScheduleEntry(
                company_id=company_id,
                requirement_id=requirement_id,
                start_block_id=start_block_id,
                blocks_count=blocks_count,
                room_resource_id=room_resource_id,
                is_locked=is_locked,
                is_manual=is_manual,
            )
        else:
            entry = ScheduleScenarioEntry(
                scenario_id=scenario_id,
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

    def list_entries_for_period(
        self,
        calendar_period_id: int,
        *,
        scenario_id: int | None = None,
    ) -> list[ScheduleEntryLike]:
        if scenario_id is None:
            statement = (
                select(ScheduleEntry)
                .join(TimeBlock, ScheduleEntry.start_block_id == TimeBlock.id)
                .where(TimeBlock.calendar_period_id == calendar_period_id)
                .order_by(TimeBlock.date.asc(), TimeBlock.order_in_day.asc())
            )
            return list(self.session.scalars(statement).all())

        statement = (
            select(ScheduleScenarioEntry)
            .join(TimeBlock, ScheduleScenarioEntry.start_block_id == TimeBlock.id)
            .where(
                TimeBlock.calendar_period_id == calendar_period_id,
                ScheduleScenarioEntry.scenario_id == scenario_id,
            )
            .order_by(TimeBlock.date.asc(), TimeBlock.order_in_day.asc())
        )
        return list(self.session.scalars(statement).all())

    def clear_entries_for_period(
        self,
        calendar_period_id: int,
        *,
        keep_locked: bool = False,
        scenario_id: int | None = None,
    ) -> None:
        block_ids_subquery = select(TimeBlock.id).where(TimeBlock.calendar_period_id == calendar_period_id)
        if scenario_id is None:
            statement = delete(ScheduleEntry).where(ScheduleEntry.start_block_id.in_(block_ids_subquery))
            if keep_locked:
                statement = statement.where(ScheduleEntry.is_locked.is_(False))
            self.session.execute(statement)
            self.session.flush()
            return

        statement = delete(ScheduleScenarioEntry).where(
            ScheduleScenarioEntry.start_block_id.in_(block_ids_subquery),
            ScheduleScenarioEntry.scenario_id == scenario_id,
        )
        if keep_locked:
            statement = statement.where(ScheduleScenarioEntry.is_locked.is_(False))
        self.session.execute(statement)
        self.session.flush()

    def get_entry(self, entry_id: int, *, scenario_id: int | None = None) -> ScheduleEntryLike | None:
        if scenario_id is None:
            return self.session.get(ScheduleEntry, entry_id)
        statement = select(ScheduleScenarioEntry).where(
            ScheduleScenarioEntry.id == entry_id,
            ScheduleScenarioEntry.scenario_id == scenario_id,
        )
        return self.session.scalar(statement)

    def update_entry_lock(
        self,
        entry_id: int,
        *,
        is_locked: bool,
        scenario_id: int | None = None,
    ) -> ScheduleEntryLike:
        entry = self.get_entry(entry_id, scenario_id=scenario_id)
        if entry is None:
            raise ValueError(f"ScheduleEntry with id={entry_id} was not found")
        entry.is_locked = bool(is_locked)
        self.session.flush()
        return entry

    def list_scenarios(self, calendar_period_id: int) -> list[ScheduleScenario]:
        statement = (
            select(ScheduleScenario)
            .where(ScheduleScenario.calendar_period_id == calendar_period_id)
            .order_by(ScheduleScenario.created_at.asc(), ScheduleScenario.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def get_scenario(self, scenario_id: int) -> ScheduleScenario | None:
        return self.session.get(ScheduleScenario, scenario_id)

    def create_scenario(
        self,
        *,
        company_id: int | None,
        calendar_period_id: int,
        name: str,
    ) -> ScheduleScenario:
        scenario = ScheduleScenario(
            company_id=company_id,
            calendar_period_id=calendar_period_id,
            name=name,
            is_published=False,
        )
        self.session.add(scenario)
        self.session.flush()
        return scenario

    def delete_scenario(self, scenario_id: int) -> bool:
        scenario = self.get_scenario(scenario_id)
        if scenario is None:
            return False
        self.session.delete(scenario)
        self.session.flush()
        return True

    def clear_published_flag(self, calendar_period_id: int) -> None:
        statement = (
            update(ScheduleScenario)
            .where(ScheduleScenario.calendar_period_id == calendar_period_id)
            .values(is_published=False)
        )
        self.session.execute(statement)
        self.session.flush()

    def set_published_scenario(self, scenario_id: int) -> ScheduleScenario:
        scenario = self.get_scenario(scenario_id)
        if scenario is None:
            raise ValueError(f"ScheduleScenario with id={scenario_id} was not found")
        self.clear_published_flag(calendar_period_id=scenario.calendar_period_id)
        scenario.is_published = True
        self.session.flush()
        return scenario
