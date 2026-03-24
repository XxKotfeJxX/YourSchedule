def update_manual_entry__impl(
    self,
    session: Session,
    *,
    calendar_period_id: int,
    entry_id: int,
    day: date,
    order_in_day: int,
    scenario_id: int | None = None,
    room_resource_id: int | None | object = _UNSET,
    is_locked: bool | None = None,
) -> ScheduleEntry | ScheduleScenarioEntry:
    schedule_repository = self.schedule_repository_cls(session=session)
    current_entry, _ = self._ensure_entry_in_period(
        session=session,
        schedule_repository=schedule_repository,
        calendar_period_id=calendar_period_id,
        entry_id=entry_id,
        scenario_id=scenario_id,
    )
    resolved_room_resource_id: int | None
    if room_resource_id is _UNSET:
        resolved_room_resource_id = (
            None if current_entry.room_resource_id is None else int(current_entry.room_resource_id)
        )
    else:
        resolved_room_resource_id = None if room_resource_id is None else int(room_resource_id)
    _, requirement, start_block, resolved_room_resource_id = self._prepare_manual_slot(
        session=session,
        calendar_period_id=calendar_period_id,
        scenario_id=scenario_id,
        requirement_id=int(current_entry.requirement_id),
        day=day,
        order_in_day=order_in_day,
        room_resource_id=resolved_room_resource_id,
        exclude_entry_id=entry_id,
    )
    lock_value = bool(current_entry.is_locked) if is_locked is None else bool(is_locked)
    return schedule_repository.update_entry(
        entry_id=entry_id,
        scenario_id=scenario_id,
        start_block_id=int(start_block.id),
        blocks_count=int(requirement.duration_blocks),
        room_resource_id=resolved_room_resource_id,
        is_locked=lock_value,
        is_manual=True,
    )
