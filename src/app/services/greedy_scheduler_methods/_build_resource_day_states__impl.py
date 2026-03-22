def _build_resource_day_states__impl(
    self,
    *,
    existing_entries: list[ScheduleEntry | ScheduleScenarioEntry],
    block_by_id: dict[int, TimeBlock],
    block_by_key: dict[tuple[date, int], TimeBlock],
    requirement_actor_resource_ids: dict[int, set[int]],
    room_default_resource_by_requirement: dict[int, int],
    room_building_by_resource_id: dict[int, int | None],
) -> tuple[
    dict[tuple[int, date], set[int]],
    dict[tuple[int, date], int],
    dict[tuple[int, date, int], int],
]:
    resource_day_orders: dict[tuple[int, date], set[int]] = defaultdict(set)
    resource_day_sessions: dict[tuple[int, date], int] = defaultdict(int)
    resource_day_room_buildings: dict[tuple[int, date, int], int] = {}

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
        actor_resource_ids = requirement_actor_resource_ids.get(entry.requirement_id, set())
        if not actor_resource_ids:
            continue

        day = start_block.date
        candidate_orders = tuple(start_block.order_in_day + offset for offset in range(entry.blocks_count))
        room_resource_id = entry.room_resource_id
        if room_resource_id is None:
            room_resource_id = room_default_resource_by_requirement.get(entry.requirement_id)
        building_id = room_building_by_resource_id.get(room_resource_id) if room_resource_id is not None else None

        for actor_id in actor_resource_ids:
            key = (actor_id, day)
            resource_day_sessions[key] += 1
            resource_day_orders[key].update(candidate_orders)
            if building_id is not None:
                for order in candidate_orders:
                    resource_day_room_buildings[(actor_id, day, order)] = building_id

    return resource_day_orders, resource_day_sessions, resource_day_room_buildings
