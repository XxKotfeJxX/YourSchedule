def _build_resource_reservations__impl(
    self,
    existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
    block_by_key: dict[tuple[date, int], TimeBlock],
    block_by_id: dict[int, TimeBlock],
    requirement_non_room_resource_ids: dict[int, set[int]],
    room_default_resource_by_requirement: dict[int, int],
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
        resources = set(requirement_non_room_resource_ids.get(entry.requirement_id, set()))
        if entry.room_resource_id is not None:
            resources.add(entry.room_resource_id)
        elif entry.requirement_id in room_default_resource_by_requirement:
            resources.add(room_default_resource_by_requirement[entry.requirement_id])
        for block_id in block_ids:
            reservations[block_id].update(resources)
    return reservations
