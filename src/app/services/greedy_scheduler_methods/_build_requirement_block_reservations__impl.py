# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _build_requirement_block_reservations__impl(
    self,
    existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
    block_by_key: dict[tuple[date, int], TimeBlock],
    block_by_id: dict[int, TimeBlock],
) -> dict[int, set[int]]:
    reservations: dict[int, set[int]] = defaultdict(set)
    for entry in existing_entries:
        start_block = block_by_id.get(entry.start_block_id)
        if start_block is None:
            continue
        block_ids = self._resolve_block_ids(
            start_block=start_block,
            blocks_count=entry.blocks_count,
            block_by_key=block_by_key,
        )
        if not block_ids:
            continue
        reservations[entry.requirement_id].update(block_ids)
    return reservations
