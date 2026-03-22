def build_coverage_dashboard__impl(
    self,
    session: Session,
    *,
    calendar_period_id: int,
    scenario_id: int | None = None,
    policy_options: SchedulerPolicyOptions | None = None,
) -> CoverageDashboard:
    calendar_period = session.get(CalendarPeriod, calendar_period_id)
    if calendar_period is None:
        raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")
    self._validate_scenario_context(
        session=session,
        calendar_period_id=calendar_period_id,
        scenario_id=scenario_id,
    )

    requirements = self._load_requirements(
        session=session,
        company_id=calendar_period.company_id,
    )
    if not requirements:
        return CoverageDashboard(
            total_requirements=0,
            covered_requirements=0,
            uncovered_requirements=0,
            total_sessions_required=0,
            total_sessions_scheduled=0,
            reasons=[],
            uncovered_items=[],
        )

    teaching_blocks = self._load_teaching_blocks(session=session, calendar_period_id=calendar_period_id)
    if not teaching_blocks:
        total_required = sum(int(item.sessions_total) for item in requirements)
        uncovered_items = [
            RequirementCoverageItem(
                requirement_id=int(item.id),
                requirement_name=str(item.name),
                expected_sessions=int(item.sessions_total),
                scheduled_sessions=0,
                missing_sessions=int(item.sessions_total),
                primary_reason_code="NO_TEACHING_BLOCKS",
                primary_reason_message="У періоді немає навчальних блоків.",
            )
            for item in requirements
        ]
        return CoverageDashboard(
            total_requirements=len(requirements),
            covered_requirements=0,
            uncovered_requirements=len(requirements),
            total_sessions_required=total_required,
            total_sessions_scheduled=0,
            reasons=[
                CoverageReason(
                    code="NO_TEACHING_BLOCKS",
                    requirements_count=len(requirements),
                    sessions_missing=total_required,
                    sample_message="У періоді немає навчальних блоків.",
                )
            ],
            uncovered_items=uncovered_items,
        )

    policy = self._resolve_policy(
        session=session,
        company_id=calendar_period.company_id,
        policy_options=policy_options,
    )
    block_by_key = {(block.date, block.order_in_day): block for block in teaching_blocks}
    block_by_id = {block.id: block for block in teaching_blocks}

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
    resource_day_orders, resource_day_sessions, _resource_day_room_buildings = self._build_resource_day_states(
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

    total_required_sessions = sum(int(item.sessions_total) for item in requirements)
    total_scheduled_sessions = 0
    covered_requirements = 0

    reason_requirements: dict[str, set[int]] = defaultdict(set)
    reason_missing_sessions: dict[str, int] = defaultdict(int)
    reason_sample_message: dict[str, str] = {}
    uncovered_items: list[RequirementCoverageItem] = []

    for requirement in requirements:
        scheduled_sessions = int(scheduled_sessions_by_requirement.get(requirement.id, 0))
        expected_sessions = int(requirement.sessions_total)
        total_scheduled_sessions += min(scheduled_sessions, expected_sessions)
        missing_sessions = max(0, expected_sessions - scheduled_sessions)
        if missing_sessions == 0:
            covered_requirements += 1
            continue

        diagnostics = self._diagnose_requirement_failures(
            requirement=requirement,
            remaining_sessions=missing_sessions,
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
        primary = diagnostics[0] if diagnostics else SchedulingDiagnostic(
            code="NO_CANDIDATES",
            message=f"Requirement {requirement.id}: no valid candidate slots.",
            requirement_id=requirement.id,
        )

        uncovered_items.append(
            RequirementCoverageItem(
                requirement_id=int(requirement.id),
                requirement_name=str(requirement.name),
                expected_sessions=expected_sessions,
                scheduled_sessions=scheduled_sessions,
                missing_sessions=missing_sessions,
                primary_reason_code=primary.code,
                primary_reason_message=primary.message,
            )
        )
        reason_requirements[primary.code].add(int(requirement.id))
        reason_missing_sessions[primary.code] += missing_sessions
        reason_sample_message.setdefault(primary.code, primary.message)

    reasons = [
        CoverageReason(
            code=code,
            requirements_count=len(req_ids),
            sessions_missing=int(reason_missing_sessions[code]),
            sample_message=reason_sample_message.get(code, ""),
        )
        for code, req_ids in reason_requirements.items()
    ]
    reasons.sort(key=lambda item: (-item.requirements_count, -item.sessions_missing, item.code))
    uncovered_items.sort(key=lambda item: (-item.missing_sessions, item.requirement_id))

    return CoverageDashboard(
        total_requirements=len(requirements),
        covered_requirements=covered_requirements,
        uncovered_requirements=len(requirements) - covered_requirements,
        total_sessions_required=total_required_sessions,
        total_sessions_scheduled=total_scheduled_sessions,
        reasons=reasons,
        uncovered_items=uncovered_items,
    )
