def _generate_candidates__impl(
    self,
    requirement: Requirement,
    teaching_blocks: list[TimeBlock],
    block_by_key: dict[tuple[date, int], TimeBlock],
    requirement_non_room_resource_ids: dict[int, set[int]],
    requirement_actor_resource_ids: dict[int, set[int]],
    room_options_by_requirement: dict[int, tuple[int, ...]],
    room_building_by_resource_id: dict[int, int | None],
    resource_reservations: dict[int, set[int]],
    requirement_block_reservations: dict[int, set[int]],
    weekly_usage: dict[tuple[int, int, int], int],
    resource_day_orders: dict[tuple[int, date], set[int]],
    resource_day_sessions: dict[tuple[int, date], int],
    resource_day_room_buildings: dict[tuple[int, date, int], int],
    day_order_bounds: dict[date, tuple[int, int]],
    policy: SchedulerPolicyOptions,
) -> list[ScheduleCandidate]:
    candidates: list[ScheduleCandidate] = []
    required_resources = requirement_non_room_resource_ids.get(requirement.id, set())
    actor_resources = requirement_actor_resource_ids.get(requirement.id, set())
    occupied_by_requirement = requirement_block_reservations.get(requirement.id, set())
    room_options = room_options_by_requirement.get(requirement.id)

    if room_options is not None and not room_options:
        return candidates

    for start_block in teaching_blocks:
        week_key = self._week_key(start_block.date)
        if weekly_usage[(requirement.id, week_key[0], week_key[1])] >= requirement.max_per_week:
            continue

        block_ids = self._resolve_block_ids(
            start_block=start_block,
            blocks_count=requirement.duration_blocks,
            block_by_key=block_by_key,
        )
        if not block_ids:
            continue
        candidate_orders = tuple(start_block.order_in_day + offset for offset in range(requirement.duration_blocks))

        if any(block_id in occupied_by_requirement for block_id in block_ids):
            continue

        if self._has_resource_conflict(
            block_ids=block_ids,
            required_resources=required_resources,
            resource_reservations=resource_reservations,
        ):
            continue

        if self._violates_hard_constraints(
            policy=policy,
            actor_resource_ids=actor_resources,
            day=start_block.date,
            candidate_orders=candidate_orders,
            resource_day_orders=resource_day_orders,
            resource_day_sessions=resource_day_sessions,
        ):
            continue

        if room_options is None:
            score = self._score_candidate(
                policy=policy,
                start_block=start_block,
                candidate_orders=candidate_orders,
                actor_resource_ids=actor_resources,
                room_resource_id=None,
                day_order_bounds=day_order_bounds,
                room_building_by_resource_id=room_building_by_resource_id,
                resource_day_orders=resource_day_orders,
                resource_day_room_buildings=resource_day_room_buildings,
            )
            candidates.append(
                ScheduleCandidate(
                    start_block_id=start_block.id,
                    block_ids=tuple(block_ids),
                    week_key=week_key,
                    room_resource_id=None,
                    score=score,
                )
            )
            continue

        for room_resource_id in room_options:
            room_conflict = any(
                room_resource_id in resource_reservations.get(block_id, set())
                for block_id in block_ids
            )
            if room_conflict:
                continue
            score = self._score_candidate(
                policy=policy,
                start_block=start_block,
                candidate_orders=candidate_orders,
                actor_resource_ids=actor_resources,
                room_resource_id=room_resource_id,
                day_order_bounds=day_order_bounds,
                room_building_by_resource_id=room_building_by_resource_id,
                resource_day_orders=resource_day_orders,
                resource_day_room_buildings=resource_day_room_buildings,
            )
            candidates.append(
                ScheduleCandidate(
                    start_block_id=start_block.id,
                    block_ids=tuple(block_ids),
                    week_key=week_key,
                    room_resource_id=room_resource_id,
                    score=score,
                )
            )

    candidates.sort(
        key=lambda item: (
            item.score,
            item.start_block_id,
            -1 if item.room_resource_id is None else item.room_resource_id,
        )
    )
    return candidates
