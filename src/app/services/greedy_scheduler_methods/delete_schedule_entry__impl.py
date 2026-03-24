# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def delete_schedule_entry__impl(
    self,
    session: Session,
    *,
    calendar_period_id: int,
    entry_id: int,
    scenario_id: int | None = None,
    allow_locked: bool = False,
) -> bool:
    schedule_repository = self.schedule_repository_cls(session=session)
    entry, _ = self._ensure_entry_in_period(
        session=session,
        schedule_repository=schedule_repository,
        calendar_period_id=calendar_period_id,
        entry_id=entry_id,
        scenario_id=scenario_id,
    )
    if entry.is_locked and not allow_locked:
        raise ValueError("Locked schedule entry cannot be deleted without override")
    return schedule_repository.delete_entry(entry_id=entry_id, scenario_id=scenario_id)
