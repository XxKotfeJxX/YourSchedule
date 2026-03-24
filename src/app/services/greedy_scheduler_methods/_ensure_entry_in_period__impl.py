# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _ensure_entry_in_period__impl(
    self,
    *,
    session: Session,
    schedule_repository: ScheduleRepository,
    calendar_period_id: int,
    entry_id: int,
    scenario_id: int | None,
) -> tuple[ScheduleEntry | ScheduleScenarioEntry, TimeBlock]:
    calendar_period = session.get(CalendarPeriod, calendar_period_id)
    if calendar_period is None:
        raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")
    self._validate_scenario_context(
        session=session,
        calendar_period_id=calendar_period_id,
        scenario_id=scenario_id,
    )
    entry = schedule_repository.get_entry(entry_id=entry_id, scenario_id=scenario_id)
    if entry is None:
        raise ValueError(f"Schedule entry with id={entry_id} was not found")
    start_block = session.get(TimeBlock, int(entry.start_block_id))
    if start_block is None or int(start_block.calendar_period_id) != int(calendar_period_id):
        raise ValueError("Schedule entry does not belong to selected calendar period")
    return entry, start_block
