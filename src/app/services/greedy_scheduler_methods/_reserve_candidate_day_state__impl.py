def _reserve_candidate_day_state__impl(
    self,
    *,
    actor_resource_ids: set[int],
    day: date,
    candidate_orders: tuple[int, ...],
    room_resource_id: int | None,
    room_building_by_resource_id: dict[int, int | None],
    resource_day_orders: dict[tuple[int, date], set[int]],
    resource_day_sessions: dict[tuple[int, date], int],
    resource_day_room_buildings: dict[tuple[int, date, int], int],
) -> None:
    building_id = room_building_by_resource_id.get(room_resource_id) if room_resource_id is not None else None
    for actor_id in actor_resource_ids:
        key = (actor_id, day)
        resource_day_sessions[key] += 1
        resource_day_orders[key].update(candidate_orders)
        if building_id is not None:
            for order in candidate_orders:
                resource_day_room_buildings[(actor_id, day, order)] = building_id
