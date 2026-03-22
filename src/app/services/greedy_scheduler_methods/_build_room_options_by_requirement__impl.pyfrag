def _build_room_options_by_requirement__impl(
    self,
    *,
    session: Session,
    requirements: list[Requirement],
    requirement_manual_room_resource_ids: dict[int, set[int]],
    company_id: int | None,
) -> tuple[dict[int, tuple[int, ...]], dict[int, int | None]]:
    statement = (
        select(RoomProfile)
        .join(Resource, RoomProfile.resource_id == Resource.id)
        .where(
            Resource.type == ResourceType.ROOM,
            RoomProfile.is_archived.is_(False),
        )
        .order_by(RoomProfile.id.asc())
    )
    if company_id is not None:
        statement = statement.where(RoomProfile.company_id == company_id)
    room_profiles = list(session.scalars(statement).all())
    room_profile_by_id = {item.id: item for item in room_profiles}
    room_building_by_resource_id = {int(item.resource_id): item.building_id for item in room_profiles}

    options_by_requirement: dict[int, tuple[int, ...]] = {}
    for requirement in requirements:
        manual_room_resource_ids = requirement_manual_room_resource_ids.get(requirement.id, set())
        requires_room = (
            bool(manual_room_resource_ids)
            or requirement.fixed_room_id is not None
            or requirement.room_type is not None
            or requirement.min_capacity is not None
            or requirement.needs_projector
        )
        if not requires_room:
            continue

        candidate_resource_ids: list[int] = []
        if requirement.fixed_room_id is not None:
            fixed_room = room_profile_by_id.get(requirement.fixed_room_id)
            if (
                fixed_room is not None
                and self._room_matches_requirement(requirement=requirement, room=fixed_room)
                and (not manual_room_resource_ids or fixed_room.resource_id in manual_room_resource_ids)
            ):
                candidate_resource_ids.append(fixed_room.resource_id)
        else:
            for room in room_profiles:
                if manual_room_resource_ids and room.resource_id not in manual_room_resource_ids:
                    continue
                if not self._room_matches_requirement(requirement=requirement, room=room):
                    continue
                candidate_resource_ids.append(room.resource_id)

        options_by_requirement[requirement.id] = tuple(sorted(set(candidate_resource_ids)))

    return options_by_requirement, room_building_by_resource_id
