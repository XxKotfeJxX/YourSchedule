def list_schedule_entries__impl(
    self,
    session: Session,
    *,
    calendar_period_id: int,
    scenario_id: int | None = None,
) -> list[ScheduleEntryCrudItem]:
    calendar_period = session.get(CalendarPeriod, calendar_period_id)
    if calendar_period is None:
        raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")
    self._validate_scenario_context(
        session=session,
        calendar_period_id=calendar_period_id,
        scenario_id=scenario_id,
    )

    schedule_repository = self.schedule_repository_cls(session=session)
    entries = schedule_repository.list_entries_for_period(
        calendar_period_id=calendar_period_id,
        scenario_id=scenario_id,
    )
    if not entries:
        return []

    requirement_ids = sorted({int(item.requirement_id) for item in entries})
    requirement_name_by_id: dict[int, str] = {}
    if requirement_ids:
        requirement_rows = session.execute(
            select(Requirement.id, Requirement.name).where(Requirement.id.in_(requirement_ids))
        ).all()
        requirement_name_by_id = {int(item_id): str(name) for item_id, name in requirement_rows}

    room_resource_ids = sorted({int(item.room_resource_id) for item in entries if item.room_resource_id is not None})
    room_name_by_id: dict[int, str] = {}
    if room_resource_ids:
        room_rows = session.execute(
            select(Resource.id, Resource.name).where(
                Resource.id.in_(room_resource_ids),
                Resource.type == ResourceType.ROOM,
            )
        ).all()
        room_name_by_id = {int(item_id): str(name) for item_id, name in room_rows}

    block_ids = sorted({int(item.start_block_id) for item in entries})
    block_by_id: dict[int, TimeBlock] = {}
    if block_ids:
        block_models = session.scalars(
            select(TimeBlock).where(
                TimeBlock.id.in_(block_ids),
                TimeBlock.calendar_period_id == calendar_period_id,
            )
        ).all()
        block_by_id = {int(block.id): block for block in block_models}

    rows: list[ScheduleEntryCrudItem] = []
    for item in entries:
        start_block = block_by_id.get(int(item.start_block_id))
        if start_block is None:
            continue
        room_resource_id = None if item.room_resource_id is None else int(item.room_resource_id)
        rows.append(
            ScheduleEntryCrudItem(
                entry_id=int(item.id),
                requirement_id=int(item.requirement_id),
                requirement_name=requirement_name_by_id.get(int(item.requirement_id), f"#{item.requirement_id}"),
                day=start_block.date,
                order_in_day=int(start_block.order_in_day),
                blocks_count=int(item.blocks_count),
                room_resource_id=room_resource_id,
                room_name=room_name_by_id.get(room_resource_id) if room_resource_id is not None else None,
                is_locked=bool(item.is_locked),
                is_manual=bool(item.is_manual),
            )
        )

    rows.sort(key=lambda item: (item.day, item.order_in_day, item.requirement_name.lower(), item.entry_id))
    return rows
