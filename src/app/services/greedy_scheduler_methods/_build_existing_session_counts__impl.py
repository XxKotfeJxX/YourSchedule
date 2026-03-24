# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _build_existing_session_counts__impl(
    self,
    existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for entry in existing_entries:
        counts[entry.requirement_id] += 1
    return counts
