def create_manual_entry__impl(
    self,
    session: Session,
    *,
    calendar_period_id: int,
    scenario_id: int | None = None,
    requirement_id: int,
    day: date,
    order_in_day: int,
    room_resource_id: int | None = None,
    is_locked: bool = True,
) -> ScheduleEntry | ScheduleScenarioEntry:
    calendar_period = session.get(CalendarPeriod, calendar_period_id)
    if calendar_period is None:
        raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")
    self._validate_scenario_context(
        session=session,
        calendar_period_id=calendar_period_id,
        scenario_id=scenario_id,
    )

    requirement = session.get(Requirement, requirement_id)
    if requirement is None:
        raise ValueError(f"Requirement with id={requirement_id} was not found")
    if (
        calendar_period.company_id is not None
        and requirement.company_id is not None
        and calendar_period.company_id != requirement.company_id
    ):
        raise ValueError("Requirement and calendar period belong to different companies")

    policy = self.get_policy(session=session, company_id=calendar_period.company_id)
    teaching_blocks = self._load_teaching_blocks(session=session, calendar_period_id=calendar_period_id)
    if not teaching_blocks:
        raise ValueError("У періоді немає навчальних блоків")

    block_by_key = {(block.date, block.order_in_day): block for block in teaching_blocks}
    block_by_id = {block.id: block for block in teaching_blocks}
    start_block = block_by_key.get((day, order_in_day))
    if start_block is None:
        raise ValueError("Стартовий блок не знайдено у періоді")
    block_ids = self._resolve_block_ids(
        start_block=start_block,
        blocks_count=requirement.duration_blocks,
        block_by_key=block_by_key,
    )
    if not block_ids:
        raise ValueError("Немає потрібної безперервної послідовності блоків для цієї вимоги")

    requirements = self._load_requirements(session=session, company_id=calendar_period.company_id)
    requirement_non_room_resource_ids: dict[int, set[int]] = {}
    requirement_manual_room_resource_ids: dict[int, set[int]] = {}
    requirement_actor_resource_ids: dict[int, set[int]] = {}
    for item in requirements:
        non_room_resources: set[int] = set()
        manual_room_resources: set[int] = set()
        actor_resources: set[int] = set()
        for requirement_resource in item.requirement_resources:
            if requirement_resource.resource.type == ResourceType.ROOM:
                manual_room_resources.add(requirement_resource.resource_id)
            else:
                non_room_resources.add(requirement_resource.resource_id)
                if requirement_resource.resource.type in {ResourceType.TEACHER, ResourceType.GROUP, ResourceType.SUBGROUP}:
                    actor_resources.add(requirement_resource.resource_id)
        requirement_non_room_resource_ids[item.id] = non_room_resources
        requirement_manual_room_resource_ids[item.id] = manual_room_resources
        requirement_actor_resource_ids[item.id] = actor_resources

    room_options_by_requirement, room_building_by_resource_id = self._build_room_options_by_requirement(
        session=session,
        requirements=requirements,
        requirement_manual_room_resource_ids=requirement_manual_room_resource_ids,
        company_id=calendar_period.company_id,
    )
    room_default_resource_by_requirement = self._build_room_default_resource_map(
        room_options_by_requirement=room_options_by_requirement,
    )
    requirement_room_options = room_options_by_requirement.get(requirement_id)
    selected_room_resource_id = room_resource_id
    if requirement_room_options is not None:
        if selected_room_resource_id is None:
            if len(requirement_room_options) == 1:
                selected_room_resource_id = requirement_room_options[0]
            else:
                raise ValueError("Для цієї вимоги потрібно обрати аудиторію")
        elif selected_room_resource_id not in requirement_room_options:
            raise ValueError("Обрана аудиторія не відповідає обмеженням вимоги")
    if selected_room_resource_id is not None:
        selected_room = session.get(Resource, selected_room_resource_id)
        if selected_room is None or selected_room.type != ResourceType.ROOM:
            raise ValueError("Обрана аудиторія не існує")
        if (
            calendar_period.company_id is not None
            and selected_room.company_id is not None
            and calendar_period.company_id != selected_room.company_id
        ):
            raise ValueError("Обрана аудиторія належить іншій компанії")

    schedule_repository = self.schedule_repository_cls(session=session)
    existing_entries = schedule_repository.list_entries_for_period(
        calendar_period_id=calendar_period_id,
        scenario_id=scenario_id,
    )
    resource_reservations = self._build_resource_reservations(
        existing_entries=existing_entries,
        block_by_key=block_by_key,
        block_by_id=block_by_id,
        requirement_non_room_resource_ids=requirement_non_room_resource_ids,
        room_default_resource_by_requirement=room_default_resource_by_requirement,
    )
    requirement_block_reservations = self._build_requirement_block_reservations(
        existing_entries=existing_entries,
        block_by_key=block_by_key,
        block_by_id=block_by_id,
    )
    weekly_usage = self._build_weekly_usage(existing_entries=existing_entries, block_by_id=block_by_id)
    resource_day_orders, resource_day_sessions, _ = self._build_resource_day_states(
        existing_entries=existing_entries,
        block_by_id=block_by_id,
        block_by_key=block_by_key,
        requirement_actor_resource_ids=requirement_actor_resource_ids,
        room_default_resource_by_requirement=room_default_resource_by_requirement,
        room_building_by_resource_id=room_building_by_resource_id,
    )

    blackout_resource_ids = self._collect_blackout_resource_ids(
        requirement_non_room_resource_ids=requirement_non_room_resource_ids,
        room_options_by_requirement=room_options_by_requirement,
        existing_entries=existing_entries,
    )
    if selected_room_resource_id is not None:
        blackout_resource_ids.add(selected_room_resource_id)
    if blackout_resource_ids:
        blackouts = self._load_blackouts(
            session=session,
            resource_ids=blackout_resource_ids,
            window_start=teaching_blocks[0].start_timestamp,
            window_end=teaching_blocks[-1].end_timestamp,
        )
        blackout_reservations = self._build_blackout_reservations(
            teaching_blocks=teaching_blocks,
            blackouts=blackouts,
        )
        for block_id, blocked_resources in blackout_reservations.items():
            resource_reservations[block_id].update(blocked_resources)

    requirement_resources = set(requirement_non_room_resource_ids.get(requirement_id, set()))
    if selected_room_resource_id is not None:
        requirement_resources.add(selected_room_resource_id)
    if self._has_resource_conflict(
        block_ids=block_ids,
        required_resources=requirement_resources,
        resource_reservations=resource_reservations,
    ):
        raise ValueError("Слот конфліктує з існуючими заняттями або blackout-інтервалами")
    if any(block_id in requirement_block_reservations.get(requirement_id, set()) for block_id in block_ids):
        raise ValueError("Ця вимога вже має заняття у вибраному слоті")

    week_key = self._week_key(start_block.date)
    if weekly_usage[(requirement_id, week_key[0], week_key[1])] >= requirement.max_per_week:
        raise ValueError("Перевищено max_per_week для вимоги")

    candidate_orders = tuple(start_block.order_in_day + offset for offset in range(requirement.duration_blocks))
    if self._violates_hard_constraints(
        policy=policy,
        actor_resource_ids=requirement_actor_resource_ids.get(requirement_id, set()),
        day=start_block.date,
        candidate_orders=candidate_orders,
        resource_day_orders=resource_day_orders,
        resource_day_sessions=resource_day_sessions,
    ):
        raise ValueError("Слот порушує жорсткі обмеження навантаження")

    return schedule_repository.create_entry(
        company_id=calendar_period.company_id,
        requirement_id=requirement_id,
        start_block_id=start_block.id,
        blocks_count=requirement.duration_blocks,
        room_resource_id=selected_room_resource_id,
        is_locked=bool(is_locked),
        is_manual=True,
        scenario_id=scenario_id,
    )
