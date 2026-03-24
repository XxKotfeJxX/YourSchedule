# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _diagnose_hard_constraint_violation__impl(
    self,
    *,
    policy: SchedulerPolicyOptions,
    actor_resource_ids: set[int],
    day: date,
    candidate_orders: tuple[int, ...],
    resource_day_orders: dict[tuple[int, date], set[int]],
    resource_day_sessions: dict[tuple[int, date], int],
    requirement_id: int,
    block_id: int,
) -> SchedulingDiagnostic | None:
    if not actor_resource_ids:
        return None

    candidate_order_set = set(candidate_orders)
    for actor_id in actor_resource_ids:
        key = (actor_id, day)
        sessions = resource_day_sessions.get(key, 0)
        if (
            policy.max_sessions_per_day is not None
            and sessions + 1 > policy.max_sessions_per_day
        ):
            return SchedulingDiagnostic(
                code="MAX_SESSIONS_PER_DAY",
                message=(
                    f"Requirement {requirement_id}: actor resource {actor_id} exceeds "
                    f"max sessions/day ({policy.max_sessions_per_day})."
                ),
                requirement_id=requirement_id,
                resource_id=actor_id,
                block_id=block_id,
                day=day,
                order_in_day=candidate_orders[0],
            )

        existing_orders = resource_day_orders.get(key, set())
        merged_orders = set(existing_orders) | candidate_order_set
        if (
            policy.max_consecutive_blocks is not None
            and self._longest_streak(merged_orders) > policy.max_consecutive_blocks
        ):
            return SchedulingDiagnostic(
                code="MAX_CONSECUTIVE_BLOCKS",
                message=(
                    f"Requirement {requirement_id}: actor resource {actor_id} exceeds "
                    f"max consecutive blocks ({policy.max_consecutive_blocks})."
                ),
                requirement_id=requirement_id,
                resource_id=actor_id,
                block_id=block_id,
                day=day,
                order_in_day=candidate_orders[0],
            )
        if policy.enforce_no_gaps and self._gap_count(merged_orders) > 0:
            return SchedulingDiagnostic(
                code="NO_GAPS_VIOLATION",
                message=(
                    f"Requirement {requirement_id}: actor resource {actor_id} creates an "
                    "in-day gap while no-gaps policy is enabled."
                ),
                requirement_id=requirement_id,
                resource_id=actor_id,
                block_id=block_id,
                day=day,
                order_in_day=candidate_orders[0],
            )
    return None
