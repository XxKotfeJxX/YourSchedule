# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _collect_blackout_resource_ids__impl(
    self,
    *,
    requirement_non_room_resource_ids: dict[int, set[int]],
    room_options_by_requirement: dict[int, tuple[int, ...]],
    existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
) -> set[int]:
    resource_ids = {
        resource_id
        for resources in requirement_non_room_resource_ids.values()
        for resource_id in resources
    }
    for room_options in room_options_by_requirement.values():
        resource_ids.update(room_options)
    for entry in existing_entries:
        if entry.room_resource_id is not None:
            resource_ids.add(entry.room_resource_id)
    return resource_ids
