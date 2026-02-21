from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import MarkKind
from app.domain.models import CalendarPeriod, Requirement, ScheduleEntry, TimeBlock
from app.repositories.schedule_repository import ScheduleRepository


@dataclass(frozen=True)
class ScheduleCandidate:
    start_block_id: int
    block_ids: tuple[int, ...]
    week_key: tuple[int, int]


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

        requirement_resource_ids = {
            requirement.id: {item.resource_id for item in requirement.requirement_resources}
            for requirement in requirements
        }

        schedule_repository = self.schedule_repository_cls(session=session)
        existing_entries = schedule_repository.list_entries_for_period(calendar_period_id=calendar_period_id)
        if replace_existing:
            schedule_repository.clear_entries_for_period(calendar_period_id=calendar_period_id)
            existing_entries = []

        resource_reservations = self._build_resource_reservations(
            existing_entries=existing_entries,
            block_by_key=block_by_key,
            block_by_id=block_by_id,
            requirement_resource_ids=requirement_resource_ids,
        )
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
            requirement_resource_ids=requirement_resource_ids,
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
                    requirement_resource_ids=requirement_resource_ids,
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
                )
                created_entries.append(entry)
                placed_sessions += 1
                scheduled_sessions_by_requirement[requirement.id] += 1

                requirement_resources = requirement_resource_ids.get(requirement.id, set())
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
        requirement_resource_ids: dict[int, set[int]],
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
            resources = requirement_resource_ids.get(entry.requirement_id, set())
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
        requirement_resource_ids: dict[int, set[int]],
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
                requirement_resource_ids=requirement_resource_ids,
                resource_reservations=resource_reservations,
                requirement_block_reservations=requirement_block_reservations,
                weekly_usage=weekly_usage,
            )
            scored_requirements.append(
                (
                    requirement,
                    len(candidates),
                    requirement.sessions_total * requirement.duration_blocks,
                    len(requirement_resource_ids.get(requirement.id, set())),
                )
            )

        scored_requirements.sort(
            key=lambda item: (
                item[1],
                -item[2],
                -item[3],
                item[0].id,
            )
        )
        return [item[0] for item in scored_requirements]

    def _generate_candidates(
        self,
        requirement: Requirement,
        teaching_blocks: list[TimeBlock],
        block_by_key: dict[tuple[date, int], TimeBlock],
        requirement_resource_ids: dict[int, set[int]],
        resource_reservations: dict[int, set[int]],
        requirement_block_reservations: dict[int, set[int]],
        weekly_usage: dict[tuple[int, int, int], int],
    ) -> list[ScheduleCandidate]:
        candidates: list[ScheduleCandidate] = []
        required_resources = requirement_resource_ids.get(requirement.id, set())
        occupied_by_requirement = requirement_block_reservations.get(requirement.id, set())

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

            candidates.append(
                ScheduleCandidate(
                    start_block_id=start_block.id,
                    block_ids=tuple(block_ids),
                    week_key=week_key,
                )
            )
        return candidates

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
