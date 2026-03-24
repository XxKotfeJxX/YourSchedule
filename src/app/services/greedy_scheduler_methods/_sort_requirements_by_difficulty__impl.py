# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _sort_requirements_by_difficulty__impl(
    self,
    requirements: list[Requirement],
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
) -> list[Requirement]:
    scored_requirements = []
    for requirement in requirements:
        candidates = self._generate_candidates(
            requirement=requirement,
            teaching_blocks=teaching_blocks,
            block_by_key=block_by_key,
            requirement_non_room_resource_ids=requirement_non_room_resource_ids,
            requirement_actor_resource_ids=requirement_actor_resource_ids,
            room_options_by_requirement=room_options_by_requirement,
            room_building_by_resource_id=room_building_by_resource_id,
            resource_reservations=resource_reservations,
            requirement_block_reservations=requirement_block_reservations,
            weekly_usage=weekly_usage,
            resource_day_orders=resource_day_orders,
            resource_day_sessions=resource_day_sessions,
            resource_day_room_buildings=resource_day_room_buildings,
            day_order_bounds=day_order_bounds,
            policy=policy,
        )
        room_option_count = len(room_options_by_requirement.get(requirement.id, ()))
        scored_requirements.append(
            (
                requirement,
                len(candidates),
                requirement.sessions_total * requirement.duration_blocks,
                len(requirement_non_room_resource_ids.get(requirement.id, set())),
                room_option_count if room_options_by_requirement.get(requirement.id) is not None else 0,
            )
        )

    scored_requirements.sort(
        key=lambda item: (
            item[1],
            -item[2],
            -item[3],
            item[4],
            item[0].id,
        )
    )
    return [item[0] for item in scored_requirements]
