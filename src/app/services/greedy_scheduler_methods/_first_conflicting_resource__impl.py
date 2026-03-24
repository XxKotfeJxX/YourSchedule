# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _first_conflicting_resource__impl(
    self,
    *,
    block_ids: list[int],
    required_resources: set[int],
    resource_reservations: dict[int, set[int]],
) -> tuple[int, int] | None:
    if not required_resources:
        return None
    for block_id in block_ids:
        occupied_resources = resource_reservations.get(block_id, set())
        conflict_ids = occupied_resources & required_resources
        if conflict_ids:
            return min(conflict_ids), block_id
    return None
