# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _diagnose_requirement_failures__impl(
    self,
    *,
    requirement: Requirement,
    remaining_sessions: int,
    teaching_blocks: list[TimeBlock],
    block_by_key: dict[tuple[date, int], TimeBlock],
    block_by_id: dict[int, TimeBlock],
    requirement_non_room_resource_ids: dict[int, set[int]],
    requirement_actor_resource_ids: dict[int, set[int]],
    room_options_by_requirement: dict[int, tuple[int, ...]],
    resource_reservations: dict[int, set[int]],
    requirement_block_reservations: dict[int, set[int]],
    weekly_usage: dict[tuple[int, int, int], int],
    resource_day_orders: dict[tuple[int, date], set[int]],
    resource_day_sessions: dict[tuple[int, date], int],
    policy: SchedulerPolicyOptions,
) -> list[SchedulingDiagnostic]:
    diagnostics: list[SchedulingDiagnostic] = []
    dedup: set[tuple[str, int | None, int | None]] = set()

    def append_diagnostic(item: SchedulingDiagnostic) -> None:
        key = (item.code, item.resource_id, item.block_id)
        if key in dedup:
            return
        dedup.add(key)
        diagnostics.append(item)

    room_options = room_options_by_requirement.get(requirement.id)
    if room_options is not None and not room_options:
        append_diagnostic(
            SchedulingDiagnostic(
                code="ROOM_OPTIONS_EMPTY",
                message=(
                    f"Requirement {requirement.id}: no compatible rooms for room constraints."
                ),
                requirement_id=requirement.id,
            )
        )
        return diagnostics

    required_resources = requirement_non_room_resource_ids.get(requirement.id, set())
    actor_resources = requirement_actor_resource_ids.get(requirement.id, set())
    occupied_by_requirement = requirement_block_reservations.get(requirement.id, set())
    all_weekly_limited = True

    for start_block in teaching_blocks:
        if len(diagnostics) >= 12:
            break
        week_key = self._week_key(start_block.date)
        if weekly_usage[(requirement.id, week_key[0], week_key[1])] >= requirement.max_per_week:
            continue
        all_weekly_limited = False

        block_ids = self._resolve_block_ids(
            start_block=start_block,
            blocks_count=requirement.duration_blocks,
            block_by_key=block_by_key,
        )
        if not block_ids:
            append_diagnostic(
                SchedulingDiagnostic(
                    code="NO_CONTIGUOUS_BLOCKS",
                    message=(
                        f"Requirement {requirement.id}: slot {start_block.date} "
                        f"#{start_block.order_in_day} has no contiguous span of "
                        f"{requirement.duration_blocks} blocks."
                    ),
                    requirement_id=requirement.id,
                    block_id=start_block.id,
                    day=start_block.date,
                    order_in_day=start_block.order_in_day,
                )
            )
            continue

        overlap_block_id = next((block_id for block_id in block_ids if block_id in occupied_by_requirement), None)
        if overlap_block_id is not None:
            overlap_block = block_by_id.get(overlap_block_id)
            append_diagnostic(
                SchedulingDiagnostic(
                    code="REQUIREMENT_OVERLAP",
                    message=(
                        f"Requirement {requirement.id} already has a session in block {overlap_block_id}."
                    ),
                    requirement_id=requirement.id,
                    block_id=overlap_block_id,
                    day=None if overlap_block is None else overlap_block.date,
                    order_in_day=None if overlap_block is None else overlap_block.order_in_day,
                )
            )
            continue

        conflict = self._first_conflicting_resource(
            block_ids=block_ids,
            required_resources=required_resources,
            resource_reservations=resource_reservations,
        )
        if conflict is not None:
            conflict_resource_id, conflict_block_id = conflict
            conflict_block = block_by_id.get(conflict_block_id)
            append_diagnostic(
                SchedulingDiagnostic(
                    code="RESOURCE_BUSY",
                    message=(
                        f"Requirement {requirement.id}: resource {conflict_resource_id} "
                        f"is busy in block {conflict_block_id}."
                    ),
                    requirement_id=requirement.id,
                    resource_id=conflict_resource_id,
                    block_id=conflict_block_id,
                    day=None if conflict_block is None else conflict_block.date,
                    order_in_day=None if conflict_block is None else conflict_block.order_in_day,
                )
            )
            continue

        candidate_orders = tuple(start_block.order_in_day + offset for offset in range(requirement.duration_blocks))
        hard_violation = self._diagnose_hard_constraint_violation(
            policy=policy,
            actor_resource_ids=actor_resources,
            day=start_block.date,
            candidate_orders=candidate_orders,
            resource_day_orders=resource_day_orders,
            resource_day_sessions=resource_day_sessions,
            requirement_id=requirement.id,
            block_id=start_block.id,
        )
        if hard_violation is not None:
            append_diagnostic(hard_violation)
            continue

        if room_options is None:
            continue

        first_room_conflict: tuple[int, int] | None = None
        has_available_room = False
        for room_resource_id in room_options:
            room_conflict_block_id = next(
                (
                    block_id
                    for block_id in block_ids
                    if room_resource_id in resource_reservations.get(block_id, set())
                ),
                None,
            )
            if room_conflict_block_id is None:
                has_available_room = True
                break
            if first_room_conflict is None:
                first_room_conflict = (room_resource_id, room_conflict_block_id)
        if has_available_room:
            continue
        if first_room_conflict is not None:
            room_resource_id, room_conflict_block_id = first_room_conflict
            conflict_block = block_by_id.get(room_conflict_block_id)
            append_diagnostic(
                SchedulingDiagnostic(
                    code="ROOM_BUSY",
                    message=(
                        f"Requirement {requirement.id}: all rooms are busy; "
                        f"room resource {room_resource_id} conflicts in block {room_conflict_block_id}."
                    ),
                    requirement_id=requirement.id,
                    resource_id=room_resource_id,
                    block_id=room_conflict_block_id,
                    day=None if conflict_block is None else conflict_block.date,
                    order_in_day=None if conflict_block is None else conflict_block.order_in_day,
                )
            )

    if all_weekly_limited:
        append_diagnostic(
            SchedulingDiagnostic(
                code="MAX_PER_WEEK_REACHED",
                message=(
                    f"Requirement {requirement.id}: weekly limit {requirement.max_per_week} "
                    "already reached in all weeks."
                ),
                requirement_id=requirement.id,
            )
        )

    if not diagnostics:
        append_diagnostic(
            SchedulingDiagnostic(
                code="NO_CANDIDATES",
                message=f"Requirement {requirement.id}: no valid candidate slots.",
                requirement_id=requirement.id,
            )
        )

    if remaining_sessions > 1:
        append_diagnostic(
            SchedulingDiagnostic(
                code="UNSCHEDULED_REMAINING",
                message=(
                    f"Requirement {requirement.id}: {remaining_sessions} sessions left unscheduled."
                ),
                requirement_id=requirement.id,
            )
        )

    return diagnostics
