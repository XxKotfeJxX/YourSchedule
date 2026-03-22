def _score_candidate__impl(
    self,
    *,
    policy: SchedulerPolicyOptions,
    start_block: TimeBlock,
    candidate_orders: tuple[int, ...],
    actor_resource_ids: set[int],
    room_resource_id: int | None,
    day_order_bounds: dict[date, tuple[int, int]],
    room_building_by_resource_id: dict[int, int | None],
    resource_day_orders: dict[tuple[int, date], set[int]],
    resource_day_room_buildings: dict[tuple[int, date, int], int],
) -> float:
    score = 0.0
    day = start_block.date
    preference = policy.time_preference if isinstance(policy.time_preference, TimePreference) else TimePreference.BALANCED

    if policy.weight_time_preference > 0 and preference != TimePreference.BALANCED:
        bounds = day_order_bounds.get(day)
        if bounds is not None:
            min_order, max_order = bounds
            if max_order > min_order:
                position = (start_block.order_in_day - min_order) / (max_order - min_order)
            else:
                position = 0.0
            if preference == TimePreference.MORNING:
                score += policy.weight_time_preference * position
            else:
                score += policy.weight_time_preference * (1.0 - position)

    if policy.weight_compactness > 0:
        candidate_set = set(candidate_orders)
        for actor_id in actor_resource_ids:
            key = (actor_id, day)
            existing = resource_day_orders.get(key, set())
            old_gap = self._gap_count(existing)
            new_gap = self._gap_count(set(existing) | candidate_set)
            if new_gap > old_gap:
                score += policy.weight_compactness * (new_gap - old_gap)

    if policy.weight_building_transition > 0 and room_resource_id is not None:
        building_id = room_building_by_resource_id.get(room_resource_id)
        if building_id is not None:
            first_order = candidate_orders[0]
            last_order = candidate_orders[-1]
            for actor_id in actor_resource_ids:
                prev_building = resource_day_room_buildings.get((actor_id, day, first_order - 1))
                if prev_building is not None and prev_building != building_id:
                    score += policy.weight_building_transition
                next_building = resource_day_room_buildings.get((actor_id, day, last_order + 1))
                if next_building is not None and next_building != building_id:
                    score += policy.weight_building_transition

    return score
