def _violates_hard_constraints__impl(
    self,
    *,
    policy: SchedulerPolicyOptions,
    actor_resource_ids: set[int],
    day: date,
    candidate_orders: tuple[int, ...],
    resource_day_orders: dict[tuple[int, date], set[int]],
    resource_day_sessions: dict[tuple[int, date], int],
) -> bool:
    if not actor_resource_ids:
        return False

    candidate_order_set = set(candidate_orders)
    for actor_id in actor_resource_ids:
        key = (actor_id, day)
        sessions = resource_day_sessions.get(key, 0)
        if (
            policy.max_sessions_per_day is not None
            and sessions + 1 > policy.max_sessions_per_day
        ):
            return True

        existing_orders = resource_day_orders.get(key, set())
        merged_orders = set(existing_orders) | candidate_order_set
        if (
            policy.max_consecutive_blocks is not None
            and self._longest_streak(merged_orders) > policy.max_consecutive_blocks
        ):
            return True
        if policy.enforce_no_gaps and self._gap_count(merged_orders) > 0:
            return True

    return False
