# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _build_blackout_reservations__impl(
    self,
    *,
    teaching_blocks: list[TimeBlock],
    blackouts: list[ResourceBlackout],
) -> dict[int, set[int]]:
    reservations: dict[int, set[int]] = defaultdict(set)
    for blackout in blackouts:
        for block in teaching_blocks:
            if blackout.starts_at >= block.end_timestamp:
                continue
            if blackout.ends_at <= block.start_timestamp:
                continue
            reservations[block.id].add(blackout.resource_id)
    return reservations
