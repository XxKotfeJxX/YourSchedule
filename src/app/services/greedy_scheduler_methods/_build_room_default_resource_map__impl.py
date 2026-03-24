# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _build_room_default_resource_map__impl(
    self,
    *,
    room_options_by_requirement: dict[int, tuple[int, ...]],
) -> dict[int, int]:
    defaults: dict[int, int] = {}
    for requirement_id, room_options in room_options_by_requirement.items():
        if len(room_options) == 1:
            defaults[requirement_id] = room_options[0]
    return defaults
