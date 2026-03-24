def _pick_available_room__impl(
    self,
    *,
    block_ids: list[int],
    room_options: tuple[int, ...],
    resource_reservations: dict[int, set[int]],
) -> int | None:
    for room_resource_id in room_options:
        if all(room_resource_id not in resource_reservations.get(block_id, set()) for block_id in block_ids):
            return room_resource_id
    return None
