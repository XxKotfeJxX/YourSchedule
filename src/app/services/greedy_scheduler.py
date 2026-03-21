from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import MarkKind, ResourceType
from app.domain.models import (
    CalendarPeriod,
    Requirement,
    Resource,
    ResourceBlackout,
    RoomProfile,
    ScheduleEntry,
    TimeBlock,
)
from app.repositories.schedule_repository import ScheduleRepository


@dataclass(frozen=True)
class ScheduleCandidate:
    start_block_id: int
    block_ids: tuple[int, ...]
    week_key: tuple[int, int]
    room_resource_id: int | None = None


@dataclass
class ScheduleRunResult:
    created_entries: list[ScheduleEntry]
    unscheduled_sessions: dict[int, int]


class GreedySchedulerService:
    def __init__(self) -> None:
        self.schedule_repository_cls = ScheduleRepository

    def build_schedule(
        self,
        session: Session,
        calendar_period_id: int,
        replace_existing: bool = True,
    ) -> ScheduleRunResult:
        calendar_period = session.get(CalendarPeriod, calendar_period_id)
        if calendar_period is None:
            raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")

        teaching_blocks = self._load_teaching_blocks(session=session, calendar_period_id=calendar_period_id)
        if not teaching_blocks:
            return ScheduleRunResult(created_entries=[], unscheduled_sessions={})

        block_by_key = {(block.date, block.order_in_day): block for block in teaching_blocks}
        block_by_id = {block.id: block for block in teaching_blocks}
        requirements = self._load_requirements(
            session=session,
            company_id=calendar_period.company_id,
        )
        if not requirements:
            return ScheduleRunResult(created_entries=[], unscheduled_sessions={})

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

        room_options_by_requirement = self._build_room_options_by_requirement(
            session=session,
            requirements=requirements,
            requirement_manual_room_resource_ids=requirement_manual_room_resource_ids,
            company_id=calendar_period.company_id,
        )
        room_default_resource_by_requirement = self._build_room_default_resource_map(
            room_options_by_requirement=room_options_by_requirement,
        )

        schedule_repository = self.schedule_repository_cls(session=session)
        existing_entries = schedule_repository.list_entries_for_period(calendar_period_id=calendar_period_id)
        if replace_existing:
            schedule_repository.clear_entries_for_period(calendar_period_id=calendar_period_id)
            existing_entries = []

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

        sorted_requirements = self._sort_requirements_by_difficulty(
            requirements=requirements,
            teaching_blocks=teaching_blocks,
            block_by_key=block_by_key,
            requirement_non_room_resource_ids=requirement_non_room_resource_ids,
            room_options_by_requirement=room_options_by_requirement,
            resource_reservations=resource_reservations,
            requirement_block_reservations=requirement_block_reservations,
            weekly_usage=weekly_usage,
        )

        created_entries: list[ScheduleEntry] = []
        unscheduled_sessions: dict[int, int] = {}

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
                    room_options_by_requirement=room_options_by_requirement,
                    resource_reservations=resource_reservations,
                    requirement_block_reservations=requirement_block_reservations,
                    weekly_usage=weekly_usage,
                )
                if not candidates:
                    unscheduled_sessions[requirement.id] = required_sessions - placed_sessions
                    break

                candidate = candidates[0]
                entry = schedule_repository.create_entry(
                    company_id=calendar_period.company_id,
                    requirement_id=requirement.id,
                    start_block_id=candidate.start_block_id,
                    blocks_count=requirement.duration_blocks,
                    room_resource_id=candidate.room_resource_id,
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

                weekly_usage[(requirement.id, candidate.week_key[0], candidate.week_key[1])] += 1

        return ScheduleRunResult(
            created_entries=created_entries,
            unscheduled_sessions=unscheduled_sessions,
        )

    def _load_teaching_blocks(
        self,
        session: Session,
        calendar_period_id: int,
    ) -> list[TimeBlock]:
        statement = (
            select(TimeBlock)
            .where(
                TimeBlock.calendar_period_id == calendar_period_id,
                TimeBlock.block_kind == MarkKind.TEACHING,
            )
            .order_by(TimeBlock.date.asc(), TimeBlock.order_in_day.asc())
        )
        return list(session.scalars(statement).all())

    def _load_requirements(self, session: Session, company_id: int | None) -> list[Requirement]:
        statement = select(Requirement).order_by(Requirement.id.asc())
        if company_id is not None:
            statement = statement.where(Requirement.company_id == company_id)
        return list(session.scalars(statement).all())

    def _build_resource_reservations(
        self,
        existing_entries: list[ScheduleEntry],
        block_by_key: dict[tuple[date, int], TimeBlock],
        block_by_id: dict[int, TimeBlock],
        requirement_non_room_resource_ids: dict[int, set[int]],
        room_default_resource_by_requirement: dict[int, int],
    ) -> dict[int, set[int]]:
        reservations: dict[int, set[int]] = defaultdict(set)
        for entry in existing_entries:
            start_block = block_by_id.get(entry.start_block_id)
            if start_block is None:
                continue
            block_ids = self._resolve_block_ids(
                start_block=start_block,
                blocks_count=entry.blocks_count,
                block_by_key=block_by_key,
            )
            if not block_ids:
                continue
            resources = set(requirement_non_room_resource_ids.get(entry.requirement_id, set()))
            if entry.room_resource_id is not None:
                resources.add(entry.room_resource_id)
            elif entry.requirement_id in room_default_resource_by_requirement:
                resources.add(room_default_resource_by_requirement[entry.requirement_id])
            for block_id in block_ids:
                reservations[block_id].update(resources)
        return reservations

    def _build_requirement_block_reservations(
        self,
        existing_entries: list[ScheduleEntry],
        block_by_key: dict[tuple[date, int], TimeBlock],
        block_by_id: dict[int, TimeBlock],
    ) -> dict[int, set[int]]:
        reservations: dict[int, set[int]] = defaultdict(set)
        for entry in existing_entries:
            start_block = block_by_id.get(entry.start_block_id)
            if start_block is None:
                continue
            block_ids = self._resolve_block_ids(
                start_block=start_block,
                blocks_count=entry.blocks_count,
                block_by_key=block_by_key,
            )
            if not block_ids:
                continue
            reservations[entry.requirement_id].update(block_ids)
        return reservations

    def _build_weekly_usage(
        self,
        existing_entries: list[ScheduleEntry],
        block_by_id: dict[int, TimeBlock],
    ) -> dict[tuple[int, int, int], int]:
        weekly_usage: dict[tuple[int, int, int], int] = defaultdict(int)
        for entry in existing_entries:
            start_block = block_by_id.get(entry.start_block_id)
            if start_block is None:
                continue
            week_key = self._week_key(start_block.date)
            weekly_usage[(entry.requirement_id, week_key[0], week_key[1])] += 1
        return weekly_usage

    def _build_existing_session_counts(
        self,
        existing_entries: list[ScheduleEntry],
    ) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for entry in existing_entries:
            counts[entry.requirement_id] += 1
        return counts

    def _sort_requirements_by_difficulty(
        self,
        requirements: list[Requirement],
        teaching_blocks: list[TimeBlock],
        block_by_key: dict[tuple[date, int], TimeBlock],
        requirement_non_room_resource_ids: dict[int, set[int]],
        room_options_by_requirement: dict[int, tuple[int, ...]],
        resource_reservations: dict[int, set[int]],
        requirement_block_reservations: dict[int, set[int]],
        weekly_usage: dict[tuple[int, int, int], int],
    ) -> list[Requirement]:
        scored_requirements = []
        for requirement in requirements:
            candidates = self._generate_candidates(
                requirement=requirement,
                teaching_blocks=teaching_blocks,
                block_by_key=block_by_key,
                requirement_non_room_resource_ids=requirement_non_room_resource_ids,
                room_options_by_requirement=room_options_by_requirement,
                resource_reservations=resource_reservations,
                requirement_block_reservations=requirement_block_reservations,
                weekly_usage=weekly_usage,
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

    def _generate_candidates(
        self,
        requirement: Requirement,
        teaching_blocks: list[TimeBlock],
        block_by_key: dict[tuple[date, int], TimeBlock],
        requirement_non_room_resource_ids: dict[int, set[int]],
        room_options_by_requirement: dict[int, tuple[int, ...]],
        resource_reservations: dict[int, set[int]],
        requirement_block_reservations: dict[int, set[int]],
        weekly_usage: dict[tuple[int, int, int], int],
    ) -> list[ScheduleCandidate]:
        candidates: list[ScheduleCandidate] = []
        required_resources = requirement_non_room_resource_ids.get(requirement.id, set())
        occupied_by_requirement = requirement_block_reservations.get(requirement.id, set())
        room_options = room_options_by_requirement.get(requirement.id)

        if room_options is not None and not room_options:
            return candidates

        for start_block in teaching_blocks:
            week_key = self._week_key(start_block.date)
            if weekly_usage[(requirement.id, week_key[0], week_key[1])] >= requirement.max_per_week:
                continue

            block_ids = self._resolve_block_ids(
                start_block=start_block,
                blocks_count=requirement.duration_blocks,
                block_by_key=block_by_key,
            )
            if not block_ids:
                continue

            if any(block_id in occupied_by_requirement for block_id in block_ids):
                continue

            if self._has_resource_conflict(
                block_ids=block_ids,
                required_resources=required_resources,
                resource_reservations=resource_reservations,
            ):
                continue

            selected_room_resource_id: int | None = None
            if room_options is not None:
                selected_room_resource_id = self._pick_available_room(
                    block_ids=block_ids,
                    room_options=room_options,
                    resource_reservations=resource_reservations,
                )
                if selected_room_resource_id is None:
                    continue

            candidates.append(
                ScheduleCandidate(
                    start_block_id=start_block.id,
                    block_ids=tuple(block_ids),
                    week_key=week_key,
                    room_resource_id=selected_room_resource_id,
                )
            )
        return candidates

    def _build_room_options_by_requirement(
        self,
        *,
        session: Session,
        requirements: list[Requirement],
        requirement_manual_room_resource_ids: dict[int, set[int]],
        company_id: int | None,
    ) -> dict[int, tuple[int, ...]]:
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

        return options_by_requirement

    def _build_room_default_resource_map(
        self,
        *,
        room_options_by_requirement: dict[int, tuple[int, ...]],
    ) -> dict[int, int]:
        defaults: dict[int, int] = {}
        for requirement_id, room_options in room_options_by_requirement.items():
            if len(room_options) == 1:
                defaults[requirement_id] = room_options[0]
        return defaults

    def _room_matches_requirement(self, *, requirement: Requirement, room: RoomProfile) -> bool:
        if requirement.room_type is not None and room.room_type != requirement.room_type:
            return False
        if requirement.min_capacity is not None and (room.capacity or 0) < requirement.min_capacity:
            return False
        if requirement.needs_projector and not room.has_projector:
            return False
        return True

    def _collect_blackout_resource_ids(
        self,
        *,
        requirement_non_room_resource_ids: dict[int, set[int]],
        room_options_by_requirement: dict[int, tuple[int, ...]],
        existing_entries: list[ScheduleEntry],
    ) -> set[int]:
        resource_ids = {
            resource_id
            for resources in requirement_non_room_resource_ids.values()
            for resource_id in resources
        }
        for room_options in room_options_by_requirement.values():
            resource_ids.update(room_options)
        for entry in existing_entries:
            if entry.room_resource_id is not None:
                resource_ids.add(entry.room_resource_id)
        return resource_ids

    def _load_blackouts(
        self,
        *,
        session: Session,
        resource_ids: set[int],
        window_start: datetime,
        window_end: datetime,
    ) -> list[ResourceBlackout]:
        statement = (
            select(ResourceBlackout)
            .where(
                ResourceBlackout.resource_id.in_(sorted(resource_ids)),
                ResourceBlackout.starts_at < window_end,
                ResourceBlackout.ends_at > window_start,
            )
            .order_by(ResourceBlackout.starts_at.asc(), ResourceBlackout.id.asc())
        )
        return list(session.scalars(statement).all())

    def _build_blackout_reservations(
        self,
        *,
        teaching_blocks: list[TimeBlock],
        blackouts: list[ResourceBlackout],
    ) -> dict[int, set[int]]:
        reservations: dict[int, set[int]] = defaultdict(set)
        for blackout in blackouts:
            for block in teaching_blocks:
                if blackout.starts_at >= block.end_timestamp:
                    continue
                if blackout.ends_at <= block.start_timestamp:
                    continue
                reservations[block.id].add(blackout.resource_id)
        return reservations

    def _pick_available_room(
        self,
        *,
        block_ids: list[int],
        room_options: tuple[int, ...],
        resource_reservations: dict[int, set[int]],
    ) -> int | None:
        for room_resource_id in room_options:
            if all(room_resource_id not in resource_reservations.get(block_id, set()) for block_id in block_ids):
                return room_resource_id
        return None

    def _resolve_block_ids(
        self,
        start_block: TimeBlock,
        blocks_count: int,
        block_by_key: dict[tuple[date, int], TimeBlock],
    ) -> list[int]:
        block_ids: list[int] = []
        previous_block: TimeBlock | None = None

        for offset in range(blocks_count):
            key = (start_block.date, start_block.order_in_day + offset)
            current_block = block_by_key.get(key)
            if current_block is None:
                return []

            if previous_block is not None and current_block.start_timestamp != previous_block.end_timestamp:
                return []

            block_ids.append(current_block.id)
            previous_block = current_block

        return block_ids

    def _has_resource_conflict(
        self,
        block_ids: list[int],
        required_resources: set[int],
        resource_reservations: dict[int, set[int]],
    ) -> bool:
        if not required_resources:
            return False
        for block_id in block_ids:
            if resource_reservations.get(block_id, set()) & required_resources:
                return True
        return False

    def _week_key(self, day: date) -> tuple[int, int]:
        iso_week = day.isocalendar()
        return (iso_week.year, iso_week.week)
