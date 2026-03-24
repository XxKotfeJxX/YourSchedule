# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _has_resource_conflict__impl(
    self,
    block_ids: list[int],
    required_resources: set[int],
    resource_reservations: dict[int, set[int]],
) -> bool:
    if not required_resources:
        return False
    for block_id in block_ids:
        if resource_reservations.get(block_id, set()) & required_resources:
            return True
    return False
