# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _build_weekly_usage__impl(
    self,
    existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
    block_by_id: dict[int, TimeBlock],
) -> dict[tuple[int, int, int], int]:
    weekly_usage: dict[tuple[int, int, int], int] = defaultdict(int)
    for entry in existing_entries:
        start_block = block_by_id.get(entry.start_block_id)
        if start_block is None:
            continue
        week_key = self._week_key(start_block.date)
        weekly_usage[(entry.requirement_id, week_key[0], week_key[1])] += 1
    return weekly_usage
