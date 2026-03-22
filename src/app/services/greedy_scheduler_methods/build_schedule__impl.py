def build_schedule__impl(
    self,
    session: Session,
    calendar_period_id: int,
    replace_existing: bool = True,
    scenario_id: int | None = None,
    policy_options: SchedulerPolicyOptions | None = None,
) -> ScheduleRunResult:
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
        return ScheduleRunResult(created_entries=[], unscheduled_sessions={})

    block_by_key = {(block.date, block.order_in_day): block for block in teaching_blocks}
    block_by_id = {block.id: block for block in teaching_blocks}
    day_order_bounds = self._build_day_order_bounds(teaching_blocks=teaching_blocks)
    requirements = self._load_requirements(
        session=session,
        company_id=calendar_period.company_id,
    )
    if not requirements:
        return ScheduleRunResult(created_entries=[], unscheduled_sessions={})

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
    if replace_existing:
        schedule_repository.clear_entries_for_period(
            calendar_period_id=calendar_period_id,
            keep_locked=True,
            scenario_id=scenario_id,
        )
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

    sorted_requirements = self._sort_requirements_by_difficulty(
        requirements=requirements,
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

    created_entries: list[ScheduleEntry | ScheduleScenarioEntry] = []
    unscheduled_sessions: dict[int, int] = {}
    diagnostics: list[SchedulingDiagnostic] = []

    for requirement in sorted_requirements:
        required_sessions = max(
            0,
            requirement.sessions_total - scheduled_sessions_by_requirement[requirement.id],
        )
        placed_sessions = 0
        while placed_sessions < required_sessions:
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
            if not candidates:
                remaining = required_sessions - placed_sessions
                unscheduled_sessions[requirement.id] = remaining
                diagnostics.extend(
                    self._diagnose_requirement_failures(
                        requirement=requirement,
                        remaining_sessions=remaining,
                        teaching_blocks=teaching_blocks,
                        block_by_key=block_by_key,
                        block_by_id=block_by_id,
                        requirement_non_room_resource_ids=requirement_non_room_resource_ids,
                        requirement_actor_resource_ids=requirement_actor_resource_ids,
                        room_options_by_requirement=room_options_by_requirement,
                        resource_reservations=resource_reservations,
                        requirement_block_reservations=requirement_block_reservations,
                        weekly_usage=weekly_usage,
                        resource_day_orders=resource_day_orders,
                        resource_day_sessions=resource_day_sessions,
                        policy=policy,
                    )
                )
                break

            candidate = candidates[0]
            entry = schedule_repository.create_entry(
                company_id=calendar_period.company_id,
                requirement_id=requirement.id,
                start_block_id=candidate.start_block_id,
                blocks_count=requirement.duration_blocks,
                room_resource_id=candidate.room_resource_id,
                is_locked=False,
                is_manual=False,
                scenario_id=scenario_id,
            )
            created_entries.append(entry)
            placed_sessions += 1
            scheduled_sessions_by_requirement[requirement.id] += 1

            requirement_resources = set(requirement_non_room_resource_ids.get(requirement.id, set()))
            if candidate.room_resource_id is not None:
                requirement_resources.add(candidate.room_resource_id)
            for block_id in candidate.block_ids:
                requirement_block_reservations[requirement.id].add(block_id)
                if requirement_resources:
                    resource_reservations[block_id].update(requirement_resources)

            start_block = block_by_id[candidate.start_block_id]
            candidate_orders = tuple(start_block.order_in_day + offset for offset in range(requirement.duration_blocks))
            self._reserve_candidate_day_state(
                actor_resource_ids=requirement_actor_resource_ids.get(requirement.id, set()),
                day=start_block.date,
                candidate_orders=candidate_orders,
                room_resource_id=candidate.room_resource_id,
                room_building_by_resource_id=room_building_by_resource_id,
                resource_day_orders=resource_day_orders,
                resource_day_sessions=resource_day_sessions,
                resource_day_room_buildings=resource_day_room_buildings,
            )
            weekly_usage[(requirement.id, candidate.week_key[0], candidate.week_key[1])] += 1

    return ScheduleRunResult(
        created_entries=created_entries,
        unscheduled_sessions=unscheduled_sessions,
        diagnostics=diagnostics,
    )
