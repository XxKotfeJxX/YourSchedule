from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import MarkKind
from app.domain.models import CalendarPeriod, Requirement, ScheduleEntry, TimeBlock


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
    def validate_period(self, session: Session, calendar_period_id: int) -> ValidationReport:
        period = session.get(CalendarPeriod, calendar_period_id)
        if period is None:
            raise ValueError(f"CalendarPeriod with id={calendar_period_id} was not found")

        requirements = self._load_requirements(
            session=session,
            company_id=period.company_id,
        )
        requirement_by_id = {requirement.id: requirement for requirement in requirements}
        requirement_resource_ids = {
            requirement.id: {item.resource_id for item in requirement.requirement_resources}
            for requirement in requirements
        }

        all_blocks = self._load_blocks_for_period(session=session, calendar_period_id=calendar_period_id)
        block_by_id = {block.id: block for block in all_blocks}
        block_by_order_key = {(block.date, block.order_in_day): block for block in all_blocks}

        schedule_entries = self._load_entries_for_period(session=session, calendar_period_id=calendar_period_id)
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

        issues.extend(
            self._validate_resource_conflicts(
                schedule_entries=schedule_entries,
                valid_entry_blocks=valid_entry_blocks,
                requirement_resource_ids=requirement_resource_ids,
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

    def _load_entries_for_period(self, session: Session, calendar_period_id: int) -> list[ScheduleEntry]:
        statement = (
            select(ScheduleEntry)
            .join(TimeBlock, ScheduleEntry.start_block_id == TimeBlock.id)
            .where(TimeBlock.calendar_period_id == calendar_period_id)
            .order_by(ScheduleEntry.id.asc())
        )
        return list(session.scalars(statement).all())

    def _validate_resource_conflicts(
        self,
        schedule_entries: list[ScheduleEntry],
        valid_entry_blocks: dict[int, list[int]],
        requirement_resource_ids: dict[int, set[int]],
    ) -> list[ValidationIssue]:
        reservations: dict[tuple[int, int], list[int]] = defaultdict(list)
        for entry in schedule_entries:
            block_ids = valid_entry_blocks.get(entry.id)
            if not block_ids:
                continue
            resources = requirement_resource_ids.get(entry.requirement_id, set())
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

    def _week_key(self, day: date) -> tuple[int, int]:
        iso = day.isocalendar()
        return (iso.year, iso.week)
