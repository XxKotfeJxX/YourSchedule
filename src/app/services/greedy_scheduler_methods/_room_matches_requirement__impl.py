def _room_matches_requirement__impl(self, *, requirement: Requirement, room: RoomProfile) -> bool:
    if requirement.room_type is not None and room.room_type != requirement.room_type:
        return False
    if requirement.min_capacity is not None and (room.capacity or 0) < requirement.min_capacity:
        return False
    if requirement.needs_projector and not room.has_projector:
        return False
    return True
