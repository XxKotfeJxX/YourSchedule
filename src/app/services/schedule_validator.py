from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import MarkKind, ResourceType
from app.domain.models import (
    CalendarPeriod,
    Requirement,
    ResourceBlackout,
    RoomProfile,
    ScheduleEntry,
    ScheduleScenarioEntry,
    TimeBlock,
)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    schedule_entry_id: int | None = None
    requirement_id: int | None = None
    resource_id: int | None = None
    block_id: int | None = None


@dataclass
class ValidationReport:
    issues: list[ValidationIssue]

    @property
    def is_valid(self) -> bool:
        return not self.issues

    @property
    def issue_counts(self) -> dict[str, int]:
        return dict(Counter(issue.code for issue in self.issues))


class ScheduleValidatorService:
    def validate_period(
        self,
        session: Session,
        calendar_period_id: int,
        *,
        scenario_id: int | None = None,
    ) -> ValidationReport:
        period = session.get(CalendarPeriod, calendar_period_id)
        if period is None:
            raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")

        requirements = self._load_requirements(
            session=session,
            company_id=period.company_id,
        )
        requirement_by_id = {requirement.id: requirement for requirement in requirements}
        requirement_non_room_resource_ids: dict[int, set[int]] = {}
        requirement_manual_room_resource_ids: dict[int, set[int]] = {}
        for requirement in requirements:
            non_room_resources: set[int] = set()
            manual_room_resources: set[int] = set()
            for item in requirement.requirement_resources:
                if item.resource.type == ResourceType.ROOM:
                    manual_room_resources.add(item.resource_id)
                else:
                    non_room_resources.add(item.resource_id)
            requirement_non_room_resource_ids[requirement.id] = non_room_resources
            requirement_manual_room_resource_ids[requirement.id] = manual_room_resources

        requirement_default_room_resource_ids = self._build_requirement_default_room_resource_ids(
            session=session,
            requirements=requirements,
            requirement_manual_room_resource_ids=requirement_manual_room_resource_ids,
        )

        all_blocks = self._load_blocks_for_period(session=session, calendar_period_id=calendar_period_id)
        block_by_id = {block.id: block for block in all_blocks}
        block_by_order_key = {(block.date, block.order_in_day): block for block in all_blocks}

        schedule_entries = self._load_entries_for_period(
            session=session,
            calendar_period_id=calendar_period_id,
            scenario_id=scenario_id,
        )
        issues: list[ValidationIssue] = []

        valid_entry_blocks: dict[int, list[int]] = {}
        valid_sessions_count: dict[int, int] = defaultdict(int)
        valid_weekly_usage: dict[tuple[int, int, int], int] = defaultdict(int)

        for entry in schedule_entries:
            start_block = block_by_id.get(entry.start_block_id)
            if start_block is None:
                issues.append(
                    ValidationIssue(
                        code="START_BLOCK_NOT_FOUND",
                        message=(
                            f"ScheduleEntry {entry.id} references missing start block "
                            f"{entry.start_block_id}."
                        ),
                        schedule_entry_id=entry.id,
                        requirement_id=entry.requirement_id,
                    )
                )
                continue

            entry_block_ids: list[int] = []
            entry_is_valid = True
            previous_block: TimeBlock | None = None

            if start_block.block_kind != MarkKind.TEACHING:
                issues.append(
                    ValidationIssue(
                        code="START_BLOCK_NOT_TEACHING",
                        message=(
                            f"ScheduleEntry {entry.id} starts from non-teaching block "
                            f"{start_block.id}."
                        ),
                        schedule_entry_id=entry.id,
                        requirement_id=entry.requirement_id,
                        block_id=start_block.id,
                    )
                )
                entry_is_valid = False

            for offset in range(entry.blocks_count):
                key = (start_block.date, start_block.order_in_day + offset)
                current_block = block_by_order_key.get(key)
                if current_block is None:
                    issues.append(
                        ValidationIssue(
                            code="CONSECUTIVE_BLOCK_MISSING",
                            message=(
                                f"ScheduleEntry {entry.id} requires block order "
                                f"{start_block.order_in_day + offset} on {start_block.date}, "
                                "but it does not exist."
                            ),
                            schedule_entry_id=entry.id,
                            requirement_id=entry.requirement_id,
                            block_id=start_block.id,
                        )
                    )
                    entry_is_valid = False
                    break

                if current_block.block_kind != MarkKind.TEACHING:
                    issues.append(
                        ValidationIssue(
                            code="NON_TEACHING_BLOCK_IN_SPAN",
                            message=(
                                f"ScheduleEntry {entry.id} covers non-teaching block "
                                f"{current_block.id}."
                            ),
                            schedule_entry_id=entry.id,
                            requirement_id=entry.requirement_id,
                            block_id=current_block.id,
                        )
                    )
                    entry_is_valid = False

                if (
                    previous_block is not None
                    and current_block.start_timestamp != previous_block.end_timestamp
                ):
                    issues.append(
                        ValidationIssue(
                            code="NON_CONTIGUOUS_BLOCK_SPAN",
                            message=(
                                f"ScheduleEntry {entry.id} has non-contiguous blocks: "
                                f"{previous_block.id} -> {current_block.id}."
                            ),
                            schedule_entry_id=entry.id,
                            requirement_id=entry.requirement_id,
                            block_id=current_block.id,
                        )
                    )
                    entry_is_valid = False

                entry_block_ids.append(current_block.id)
                previous_block = current_block

            if not entry_is_valid:
                continue

            valid_entry_blocks[entry.id] = entry_block_ids
            valid_sessions_count[entry.requirement_id] += 1
            week_key = self._week_key(start_block.date)
            valid_weekly_usage[(entry.requirement_id, week_key[0], week_key[1])] += 1

        entry_resource_ids = self._build_entry_resource_ids(
            schedule_entries=schedule_entries,
            requirement_non_room_resource_ids=requirement_non_room_resource_ids,
            requirement_default_room_resource_ids=requirement_default_room_resource_ids,
        )

        issues.extend(
            self._validate_resource_conflicts(
                schedule_entries=schedule_entries,
                valid_entry_blocks=valid_entry_blocks,
                entry_resource_ids=entry_resource_ids,
            )
        )
        if all_blocks:
            blackouts_by_resource = self._load_blackouts_by_resource(
                session=session,
                resource_ids={
                    resource_id
                    for resources in entry_resource_ids.values()
                    for resource_id in resources
                },
                window_start=all_blocks[0].start_timestamp,
                window_end=all_blocks[-1].end_timestamp,
            )
            issues.extend(
                self._validate_blackout_conflicts(
                    schedule_entries=schedule_entries,
                    valid_entry_blocks=valid_entry_blocks,
                    entry_resource_ids=entry_resource_ids,
                    block_by_id=block_by_id,
                    blackouts_by_resource=blackouts_by_resource,
                )
            )

            room_profile_by_resource_id = self._load_room_profiles_by_resource_id(
                session=session,
                room_resource_ids={
                    entry.room_resource_id for entry in schedule_entries if entry.room_resource_id is not None
                },
            )
            issues.extend(
                self._validate_room_constraints(
                    schedule_entries=schedule_entries,
                    requirement_by_id=requirement_by_id,
                    room_profile_by_resource_id=room_profile_by_resource_id,
                )
            )
        issues.extend(
            self._validate_requirement_overlaps(
                schedule_entries=schedule_entries,
                valid_entry_blocks=valid_entry_blocks,
            )
        )
        issues.extend(
            self._validate_requirement_session_counts(
                requirements=requirements,
                valid_sessions_count=valid_sessions_count,
            )
        )
        issues.extend(
            self._validate_max_per_week(
                requirements=requirements,
                valid_weekly_usage=valid_weekly_usage,
            )
        )
        issues.extend(
            self._validate_missing_requirement_links(
                schedule_entries=schedule_entries,
                requirement_by_id=requirement_by_id,
            )
        )

        return ValidationReport(issues=issues)

    def _load_requirements(self, session: Session, company_id: int | None) -> list[Requirement]:
        statement = select(Requirement).order_by(Requirement.id.asc())
        if company_id is not None:
            statement = statement.where(Requirement.company_id == company_id)
        return list(session.scalars(statement).all())

    def _load_blocks_for_period(self, session: Session, calendar_period_id: int) -> list[TimeBlock]:
        statement = (
            select(TimeBlock)
            .where(TimeBlock.calendar_period_id == calendar_period_id)
            .order_by(TimeBlock.date.asc(), TimeBlock.order_in_day.asc())
        )
        return list(session.scalars(statement).all())

    def _load_entries_for_period(
        self,
        session: Session,
        calendar_period_id: int,
        *,
        scenario_id: int | None = None,
    ) -> list[ScheduleEntry | ScheduleScenarioEntry]:
        if scenario_id is None:
            statement = (
                select(ScheduleEntry)
                .join(TimeBlock, ScheduleEntry.start_block_id == TimeBlock.id)
                .where(TimeBlock.calendar_period_id == calendar_period_id)
                .order_by(ScheduleEntry.id.asc())
            )
            return list(session.scalars(statement).all())
        statement = (
            select(ScheduleScenarioEntry)
            .join(TimeBlock, ScheduleScenarioEntry.start_block_id == TimeBlock.id)
            .where(
                TimeBlock.calendar_period_id == calendar_period_id,
                ScheduleScenarioEntry.scenario_id == scenario_id,
            )
            .order_by(ScheduleScenarioEntry.id.asc())
        )
        return list(session.scalars(statement).all())

    def _validate_resource_conflicts(
        self,
        schedule_entries: list[ScheduleEntry],
        valid_entry_blocks: dict[int, list[int]],
        entry_resource_ids: dict[int, set[int]],
    ) -> list[ValidationIssue]:
        reservations: dict[tuple[int, int], list[int]] = defaultdict(list)
        for entry in schedule_entries:
            block_ids = valid_entry_blocks.get(entry.id)
            if not block_ids:
                continue
            resources = entry_resource_ids.get(entry.id, set())
            for block_id in block_ids:
                for resource_id in resources:
                    reservations[(block_id, resource_id)].append(entry.id)

        issues: list[ValidationIssue] = []
        for (block_id, resource_id), entry_ids in reservations.items():
            if len(entry_ids) <= 1:
                continue
            issues.append(
                ValidationIssue(
                    code="RESOURCE_CONFLICT",
                    message=(
                        f"Resource {resource_id} is assigned to multiple entries "
                        f"{sorted(set(entry_ids))} in block {block_id}."
                    ),
                    resource_id=resource_id,
                    block_id=block_id,
                )
            )
        return issues

    def _validate_blackout_conflicts(
        self,
        *,
        schedule_entries: list[ScheduleEntry],
        valid_entry_blocks: dict[int, list[int]],
        entry_resource_ids: dict[int, set[int]],
        block_by_id: dict[int, TimeBlock],
        blackouts_by_resource: dict[int, list[ResourceBlackout]],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for entry in schedule_entries:
            block_ids = valid_entry_blocks.get(entry.id)
            if not block_ids:
                continue
            resource_ids = entry_resource_ids.get(entry.id, set())
            if not resource_ids:
                continue

            for block_id in block_ids:
                block = block_by_id.get(block_id)
                if block is None:
                    continue
                for resource_id in resource_ids:
                    blackouts = blackouts_by_resource.get(resource_id, [])
                    for blackout in blackouts:
                        if blackout.starts_at >= block.end_timestamp:
                            continue
                        if blackout.ends_at <= block.start_timestamp:
                            continue
                        issues.append(
                            ValidationIssue(
                                code="RESOURCE_BLACKOUT_CONFLICT",
                                message=(
                                    f"Resource {resource_id} is unavailable in block {block_id} "
                                    f"for ScheduleEntry {entry.id}."
                                ),
                                schedule_entry_id=entry.id,
                                requirement_id=entry.requirement_id,
                                resource_id=resource_id,
                                block_id=block_id,
                            )
                        )
                        break
        return issues

    def _validate_room_constraints(
        self,
        *,
        schedule_entries: list[ScheduleEntry],
        requirement_by_id: dict[int, Requirement],
        room_profile_by_resource_id: dict[int, RoomProfile],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for entry in schedule_entries:
            requirement = requirement_by_id.get(entry.requirement_id)
            if requirement is None:
                continue

            room_required = (
                requirement.fixed_room_id is not None
                or requirement.room_type is not None
                or requirement.min_capacity is not None
                or requirement.needs_projector
            )
            if entry.room_resource_id is None:
                if room_required:
                    issues.append(
                        ValidationIssue(
                            code="ROOM_NOT_ASSIGNED",
                            message=(
                                f"ScheduleEntry {entry.id} requires room assignment by requirement "
                                f"{requirement.id}, but no room_resource_id is set."
                            ),
                            schedule_entry_id=entry.id,
                            requirement_id=requirement.id,
                        )
                    )
                continue

            room_profile = room_profile_by_resource_id.get(entry.room_resource_id)
            if room_profile is None:
                issues.append(
                    ValidationIssue(
                        code="ROOM_PROFILE_NOT_FOUND",
                        message=(
                            f"ScheduleEntry {entry.id} references room resource {entry.room_resource_id}, "
                            "but no RoomProfile was found."
                        ),
                        schedule_entry_id=entry.id,
                        requirement_id=requirement.id,
                        resource_id=entry.room_resource_id,
                    )
                )
                continue

            if requirement.fixed_room_id is not None and room_profile.id != requirement.fixed_room_id:
                issues.append(
                    ValidationIssue(
                        code="FIXED_ROOM_MISMATCH",
                        message=(
                            f"ScheduleEntry {entry.id} uses room profile {room_profile.id}, but "
                            f"requirement {requirement.id} requires fixed room {requirement.fixed_room_id}."
                        ),
                        schedule_entry_id=entry.id,
                        requirement_id=requirement.id,
                        resource_id=entry.room_resource_id,
                    )
                )

            if requirement.room_type is not None and room_profile.room_type != requirement.room_type:
                issues.append(
                    ValidationIssue(
                        code="ROOM_TYPE_MISMATCH",
                        message=(
                            f"ScheduleEntry {entry.id} uses room type {room_profile.room_type.value}, but "
                            f"requirement {requirement.id} expects {requirement.room_type.value}."
                        ),
                        schedule_entry_id=entry.id,
                        requirement_id=requirement.id,
                        resource_id=entry.room_resource_id,
                    )
                )

            if requirement.min_capacity is not None and (room_profile.capacity or 0) < requirement.min_capacity:
                issues.append(
                    ValidationIssue(
                        code="ROOM_CAPACITY_MISMATCH",
                        message=(
                            f"ScheduleEntry {entry.id} uses room capacity {room_profile.capacity}, but "
                            f"requirement {requirement.id} expects at least {requirement.min_capacity}."
                        ),
                        schedule_entry_id=entry.id,
                        requirement_id=requirement.id,
                        resource_id=entry.room_resource_id,
                    )
                )

            if requirement.needs_projector and not room_profile.has_projector:
                issues.append(
                    ValidationIssue(
                        code="ROOM_PROJECTOR_REQUIRED",
                        message=(
                            f"ScheduleEntry {entry.id} uses room profile {room_profile.id}, but "
                            f"requirement {requirement.id} requires a projector."
                        ),
                        schedule_entry_id=entry.id,
                        requirement_id=requirement.id,
                        resource_id=entry.room_resource_id,
                    )
                )
        return issues

    def _validate_requirement_overlaps(
        self,
        schedule_entries: list[ScheduleEntry],
        valid_entry_blocks: dict[int, list[int]],
    ) -> list[ValidationIssue]:
        by_requirement_block: dict[tuple[int, int], list[int]] = defaultdict(list)
        by_entry_id = {entry.id: entry for entry in schedule_entries}
        for entry_id, block_ids in valid_entry_blocks.items():
            requirement_id = by_entry_id[entry_id].requirement_id
            for block_id in block_ids:
                by_requirement_block[(requirement_id, block_id)].append(entry_id)

        issues: list[ValidationIssue] = []
        for (requirement_id, block_id), entry_ids in by_requirement_block.items():
            if len(entry_ids) <= 1:
                continue
            issues.append(
                ValidationIssue(
                    code="REQUIREMENT_OVERLAP",
                    message=(
                        f"Requirement {requirement_id} overlaps in block {block_id}: "
                        f"entries {sorted(set(entry_ids))}."
                    ),
                    requirement_id=requirement_id,
                    block_id=block_id,
                )
            )
        return issues

    def _validate_requirement_session_counts(
        self,
        requirements: list[Requirement],
        valid_sessions_count: dict[int, int],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for requirement in requirements:
            scheduled = valid_sessions_count.get(requirement.id, 0)
            if scheduled == requirement.sessions_total:
                continue
            issues.append(
                ValidationIssue(
                    code="SESSION_COUNT_MISMATCH",
                    message=(
                        f"Requirement {requirement.id} expects {requirement.sessions_total} sessions, "
                        f"but has {scheduled} valid scheduled sessions."
                    ),
                    requirement_id=requirement.id,
                )
            )
        return issues

    def _validate_max_per_week(
        self,
        requirements: list[Requirement],
        valid_weekly_usage: dict[tuple[int, int, int], int],
    ) -> list[ValidationIssue]:
        requirement_map = {requirement.id: requirement for requirement in requirements}
        issues: list[ValidationIssue] = []
        for (requirement_id, week_year, week_number), count in valid_weekly_usage.items():
            requirement = requirement_map.get(requirement_id)
            if requirement is None:
                continue
            if count <= requirement.max_per_week:
                continue
            issues.append(
                ValidationIssue(
                    code="MAX_PER_WEEK_EXCEEDED",
                    message=(
                        f"Requirement {requirement_id} exceeds max_per_week in ISO week "
                        f"{week_year}-W{week_number}: {count} > {requirement.max_per_week}."
                    ),
                    requirement_id=requirement_id,
                )
            )
        return issues

    def _validate_missing_requirement_links(
        self,
        schedule_entries: list[ScheduleEntry],
        requirement_by_id: dict[int, Requirement],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for entry in schedule_entries:
            if entry.requirement_id in requirement_by_id:
                continue
            issues.append(
                ValidationIssue(
                    code="REQUIREMENT_NOT_FOUND",
                    message=(
                        f"ScheduleEntry {entry.id} references missing requirement "
                        f"{entry.requirement_id}."
                    ),
                    schedule_entry_id=entry.id,
                    requirement_id=entry.requirement_id,
                )
            )
        return issues

    def _build_requirement_default_room_resource_ids(
        self,
        *,
        session: Session,
        requirements: list[Requirement],
        requirement_manual_room_resource_ids: dict[int, set[int]],
    ) -> dict[int, int]:
        fixed_room_ids = {
            requirement.fixed_room_id
            for requirement in requirements
            if requirement.fixed_room_id is not None
        }
        fixed_room_resource_map: dict[int, int] = {}
        if fixed_room_ids:
            statement = select(RoomProfile).where(RoomProfile.id.in_(sorted(fixed_room_ids)))
            for room_profile in session.scalars(statement).all():
                fixed_room_resource_map[room_profile.id] = room_profile.resource_id

        defaults: dict[int, int] = {}
        for requirement in requirements:
            if requirement.fixed_room_id is not None:
                fixed_resource_id = fixed_room_resource_map.get(requirement.fixed_room_id)
                if fixed_resource_id is not None:
                    defaults[requirement.id] = fixed_resource_id
                continue

            manual_rooms = requirement_manual_room_resource_ids.get(requirement.id, set())
            if len(manual_rooms) == 1:
                defaults[requirement.id] = next(iter(manual_rooms))
        return defaults

    def _build_entry_resource_ids(
        self,
        *,
        schedule_entries: list[ScheduleEntry],
        requirement_non_room_resource_ids: dict[int, set[int]],
        requirement_default_room_resource_ids: dict[int, int],
    ) -> dict[int, set[int]]:
        entry_resource_ids: dict[int, set[int]] = {}
        for entry in schedule_entries:
            resources = set(requirement_non_room_resource_ids.get(entry.requirement_id, set()))
            if entry.room_resource_id is not None:
                resources.add(entry.room_resource_id)
            elif entry.requirement_id in requirement_default_room_resource_ids:
                resources.add(requirement_default_room_resource_ids[entry.requirement_id])
            entry_resource_ids[entry.id] = resources
        return entry_resource_ids

    def _load_blackouts_by_resource(
        self,
        *,
        session: Session,
        resource_ids: set[int],
        window_start: datetime,
        window_end: datetime,
    ) -> dict[int, list[ResourceBlackout]]:
        if not resource_ids:
            return {}
        statement = (
            select(ResourceBlackout)
            .where(
                ResourceBlackout.resource_id.in_(sorted(resource_ids)),
                ResourceBlackout.starts_at < window_end,
                ResourceBlackout.ends_at > window_start,
            )
            .order_by(ResourceBlackout.starts_at.asc(), ResourceBlackout.id.asc())
        )
        blackouts_by_resource: dict[int, list[ResourceBlackout]] = defaultdict(list)
        for blackout in session.scalars(statement).all():
            blackouts_by_resource[blackout.resource_id].append(blackout)
        return blackouts_by_resource

    def _load_room_profiles_by_resource_id(
        self,
        *,
        session: Session,
        room_resource_ids: set[int],
    ) -> dict[int, RoomProfile]:
        if not room_resource_ids:
            return {}
        statement = select(RoomProfile).where(RoomProfile.resource_id.in_(sorted(room_resource_ids)))
        room_profiles = list(session.scalars(statement).all())
        return {room.resource_id: room for room in room_profiles}

    def _week_key(self, day: date) -> tuple[int, int]:
        iso = day.isocalendar()
        return (iso.year, iso.week)
