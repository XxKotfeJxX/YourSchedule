def analyze_feasibility__impl(
    self,
    session: Session,
    calendar_period_id: int,
    replace_existing: bool = True,
    scenario_id: int | None = None,
    policy_options: SchedulerPolicyOptions | None = None,
) -> FeasibilityReport:
    calendar_period = session.get(CalendarPeriod, calendar_period_id)
    if calendar_period is None:
        raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")
    self._validate_scenario_context(
        session=session,
        calendar_period_id=calendar_period_id,
        scenario_id=scenario_id,
    )
    policy = self._resolve_policy(
        session=session,
        company_id=calendar_period.company_id,
        policy_options=policy_options,
    )

    teaching_blocks = self._load_teaching_blocks(session=session, calendar_period_id=calendar_period_id)
    if not teaching_blocks:
        return FeasibilityReport(issues=[], candidate_capacity={})

    block_by_key = {(block.date, block.order_in_day): block for block in teaching_blocks}
    block_by_id = {block.id: block for block in teaching_blocks}
    day_order_bounds = self._build_day_order_bounds(teaching_blocks=teaching_blocks)

    requirements = self._load_requirements(
        session=session,
        company_id=calendar_period.company_id,
    )
    if not requirements:
        return FeasibilityReport(issues=[], candidate_capacity={})

    requirement_non_room_resource_ids: dict[int, set[int]] = {}
    requirement_manual_room_resource_ids: dict[int, set[int]] = {}
    requirement_actor_resource_ids: dict[int, set[int]] = {}
    for requirement in requirements:
        non_room_resources: set[int] = set()
        manual_room_resources: set[int] = set()
        actor_resources: set[int] = set()
        for item in requirement.requirement_resources:
            if item.resource.type == ResourceType.ROOM:
                manual_room_resources.add(item.resource_id)
            else:
                non_room_resources.add(item.resource_id)
                if item.resource.type in {ResourceType.TEACHER, ResourceType.GROUP, ResourceType.SUBGROUP}:
                    actor_resources.add(item.resource_id)
        requirement_non_room_resource_ids[requirement.id] = non_room_resources
        requirement_manual_room_resource_ids[requirement.id] = manual_room_resources
        requirement_actor_resource_ids[requirement.id] = actor_resources

    room_options_by_requirement, room_building_by_resource_id = self._build_room_options_by_requirement(
        session=session,
        requirements=requirements,
        requirement_manual_room_resource_ids=requirement_manual_room_resource_ids,
        company_id=calendar_period.company_id,
    )
    room_default_resource_by_requirement = self._build_room_default_resource_map(
        room_options_by_requirement=room_options_by_requirement,
    )

    schedule_repository = self.schedule_repository_cls(session=session)
    existing_entries = schedule_repository.list_entries_for_period(
        calendar_period_id=calendar_period_id,
        scenario_id=scenario_id,
    )
    if replace_existing:
        existing_entries = [entry for entry in existing_entries if bool(entry.is_locked)]

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
    scheduled_sessions_by_requirement = self._build_existing_session_counts(existing_entries=existing_entries)
    resource_day_orders, resource_day_sessions, resource_day_room_buildings = self._build_resource_day_states(
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

    issues: list[FeasibilityIssue] = []
    candidate_capacity: dict[int, int] = {}
    demand_by_resource: dict[int, int] = defaultdict(int)

    for requirement in requirements:
        required_sessions = max(
            0,
            requirement.sessions_total - scheduled_sessions_by_requirement.get(requirement.id, 0),
        )
        if required_sessions <= 0:
            candidate_capacity[requirement.id] = 0
            continue
        room_options = room_options_by_requirement.get(requirement.id)
        if room_options is not None and not room_options:
            issues.append(
                FeasibilityIssue(
                    code="ROOM_OPTIONS_EMPTY",
                    message=f"Вимога {requirement.id} не має сумісних аудиторій.",
                    requirement_id=requirement.id,
                )
            )
        for actor_id in requirement_actor_resource_ids.get(requirement.id, set()):
            demand_by_resource[actor_id] += required_sessions * requirement.duration_blocks

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
        candidate_capacity[requirement.id] = len(candidates)
        if not candidates:
            issues.append(
                FeasibilityIssue(
                    code="NO_CANDIDATES",
                    message=f"Вимога {requirement.id} не має доступних слотів.",
                    requirement_id=requirement.id,
                )
            )
        elif len(candidates) < required_sessions:
            issues.append(
                FeasibilityIssue(
                    code="CANDIDATE_CAPACITY_LOW",
                    message=(
                        f"Вимога {requirement.id}: доступних слотів {len(candidates)}, "
                        f"потрібно {required_sessions}."
                    ),
                    requirement_id=requirement.id,
                )
            )

    for resource_id, demand_blocks in demand_by_resource.items():
        available_blocks = 0
        for block in teaching_blocks:
            if resource_id not in resource_reservations.get(block.id, set()):
                available_blocks += 1
        if demand_blocks <= available_blocks:
            continue
        issues.append(
            FeasibilityIssue(
                code="RESOURCE_OVERLOAD",
                message=(
                    f"Ресурс {resource_id}: попит {demand_blocks} блоків, "
                    f"доступно {available_blocks}."
                ),
                resource_id=resource_id,
            )
        )

    return FeasibilityReport(issues=issues, candidate_capacity=candidate_capacity)
