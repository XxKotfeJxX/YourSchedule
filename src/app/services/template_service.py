from __future__ import annotations

"""Template UI spec v1: linked templates, snapshot only for CalendarPeriod, archive-first deletes."""

from datetime import datetime, time, timedelta

from sqlalchemy.orm import Session

from app.domain.enums import MarkKind
from app.domain.models import DayPattern, MarkType, WeekPattern
from app.repositories.template_repository import TemplateRepository
from app.services.template_models import (
    DayTemplateOverview,
    DayTemplatePreview,
    MarkTypeOverview,
    TemplatesOverview,
    WeekTemplateOverview,
    WeekTemplatePreview,
)

WEEKDAY_INDEXES = (0, 1, 2, 3, 4, 5, 6)

class TemplateService:
    def __init__(self, repository_cls: type[TemplateRepository] = TemplateRepository) -> None:
        self.repository_cls = repository_cls

    def load_templates_overview(self, *, session: Session, company_id: int) -> TemplatesOverview:
        repository = self.repository_cls(session)
        mark_types = repository.list_mark_types(company_id=company_id, include_archived=True)
        day_patterns = repository.list_day_patterns(company_id=company_id, include_archived=True)
        week_patterns = repository.list_week_patterns(company_id=company_id, include_archived=True)

        mark_type_usage = repository.mark_type_usage_counts(company_id=company_id)
        day_pattern_usage = repository.day_pattern_usage_counts(company_id=company_id)
        week_pattern_usage = repository.week_pattern_usage_counts(company_id=company_id)

        mark_type_by_id = {item.id: item for item in mark_types}
        day_pattern_by_id = {item.id: item for item in day_patterns}

        mark_type_items = [
            self._build_mark_type_overview(
                mark_type=item,
                used_in_day_templates=mark_type_usage.get(item.id, 0),
            )
            for item in mark_types
        ]
        day_template_items = [
            self._build_day_template_overview(
                day_pattern=item,
                mark_type_by_id=mark_type_by_id,
                used_in_week_templates=day_pattern_usage.get(item.id, 0),
            )
            for item in day_patterns
        ]
        week_template_items = [
            self._build_week_template_overview(
                week_pattern=item,
                day_pattern_by_id=day_pattern_by_id,
                mark_type_by_id=mark_type_by_id,
                used_in_calendar_periods=week_pattern_usage.get(item.id, 0),
            )
            for item in week_patterns
        ]

        return TemplatesOverview(
            mark_types=mark_type_items,
            day_templates=day_template_items,
            week_templates=week_template_items,
        )

    def create_mark_type(
        self,
        *,
        session: Session,
        company_id: int,
        name: str,
        kind: MarkKind | str,
        duration_minutes: int,
    ) -> MarkTypeOverview:
        clean_name = self._require_name(name=name, field_label="Назва блоку")
        normalized_kind = self._normalize_mark_kind(kind)
        if duration_minutes <= 0:
            raise ValueError("Тривалість блоку має бути більшою за 0.")

        repository = self.repository_cls(session)
        mark_type = repository.create_mark_type(
            company_id=company_id,
            name=clean_name,
            kind=normalized_kind,
            duration_minutes=duration_minutes,
        )
        return self._build_mark_type_overview(mark_type=mark_type, used_in_day_templates=0)

    def update_mark_type(
        self,
        *,
        session: Session,
        company_id: int,
        mark_type_id: int,
        name: str | None = None,
        kind: MarkKind | str | None = None,
        duration_minutes: int | None = None,
    ) -> MarkTypeOverview:
        repository = self.repository_cls(session)
        mark_type = self._get_mark_type_for_company(
            repository=repository,
            company_id=company_id,
            mark_type_id=mark_type_id,
        )

        clean_name = self._require_name(name=name, field_label="Назва блоку") if name is not None else None
        normalized_kind = self._normalize_mark_kind(kind) if kind is not None else None
        if duration_minutes is not None and duration_minutes <= 0:
            raise ValueError("Тривалість блоку має бути більшою за 0.")

        updated = repository.update_mark_type(
            mark_type_id=mark_type.id,
            name=clean_name,
            kind=normalized_kind,
            duration_minutes=duration_minutes,
        )
        usage = repository.mark_type_usage_counts(company_id=company_id).get(updated.id, 0)
        return self._build_mark_type_overview(mark_type=updated, used_in_day_templates=usage)

    def delete_mark_type(
        self,
        *,
        session: Session,
        company_id: int,
        mark_type_id: int,
    ) -> MarkTypeOverview:
        repository = self.repository_cls(session)
        mark_type = self._get_mark_type_for_company(
            repository=repository,
            company_id=company_id,
            mark_type_id=mark_type_id,
        )
        archived = repository.archive_mark_type(mark_type_id=mark_type.id)
        usage = repository.mark_type_usage_counts(company_id=company_id).get(archived.id, 0)
        return self._build_mark_type_overview(mark_type=archived, used_in_day_templates=usage)

    def delete_mark_type_permanently(
        self,
        *,
        session: Session,
        company_id: int,
        mark_type_id: int,
    ) -> None:
        repository = self.repository_cls(session)
        mark_type = self._get_mark_type_for_company(
            repository=repository,
            company_id=company_id,
            mark_type_id=mark_type_id,
        )
        usage_count = repository.mark_type_usage_counts(company_id=company_id).get(mark_type.id, 0)
        if usage_count > 0:
            raise ValueError("Блок використовується у шаблонах дня. Доступна лише архівація.")
        deleted = repository.delete_mark_type(mark_type_id=mark_type.id)
        if not deleted:
            raise ValueError("Блок не знайдено.")

    def duplicate_mark_type(
        self,
        *,
        session: Session,
        company_id: int,
        mark_type_id: int,
    ) -> MarkTypeOverview:
        repository = self.repository_cls(session)
        source = self._get_mark_type_for_company(
            repository=repository,
            company_id=company_id,
            mark_type_id=mark_type_id,
        )
        existing_names = {item.name for item in repository.list_mark_types(company_id=company_id, include_archived=True)}
        duplicate_name = self._build_duplicate_name(source.name, existing_names)
        duplicate = repository.create_mark_type(
            company_id=company_id,
            name=duplicate_name,
            kind=source.kind,
            duration_minutes=source.duration_minutes,
        )
        return self._build_mark_type_overview(mark_type=duplicate, used_in_day_templates=0)

    def create_day_template(
        self,
        *,
        session: Session,
        company_id: int,
        name: str,
        mark_type_ids: list[int],
    ) -> DayTemplateOverview:
        clean_name = self._require_name(name=name, field_label="Назва шаблону дня")
        self._validate_mark_type_ids(session=session, company_id=company_id, mark_type_ids=mark_type_ids)
        repository = self.repository_cls(session)
        day_pattern = repository.create_day_pattern(
            company_id=company_id,
            name=clean_name,
            mark_type_ids=mark_type_ids,
        )
        mark_types = repository.list_mark_types(company_id=company_id, include_archived=True)
        return self._build_day_template_overview(
            day_pattern=day_pattern,
            mark_type_by_id={item.id: item for item in mark_types},
            used_in_week_templates=0,
        )

    def update_day_template(
        self,
        *,
        session: Session,
        company_id: int,
        day_template_id: int,
        name: str | None = None,
        mark_type_ids: list[int] | None = None,
    ) -> DayTemplateOverview:
        repository = self.repository_cls(session)
        day_pattern = self._get_day_pattern_for_company(
            repository=repository,
            company_id=company_id,
            day_pattern_id=day_template_id,
        )

        clean_name = self._require_name(name=name, field_label="Назва шаблону дня") if name is not None else None
        if mark_type_ids is not None:
            self._validate_mark_type_ids(session=session, company_id=company_id, mark_type_ids=mark_type_ids)

        updated = repository.update_day_pattern(
            day_pattern_id=day_pattern.id,
            name=clean_name,
            mark_type_ids=mark_type_ids,
        )
        day_usage = repository.day_pattern_usage_counts(company_id=company_id).get(updated.id, 0)
        mark_types = repository.list_mark_types(company_id=company_id, include_archived=True)
        return self._build_day_template_overview(
            day_pattern=updated,
            mark_type_by_id={item.id: item for item in mark_types},
            used_in_week_templates=day_usage,
        )

    def delete_day_template(
        self,
        *,
        session: Session,
        company_id: int,
        day_template_id: int,
    ) -> DayTemplateOverview:
        repository = self.repository_cls(session)
        day_pattern = self._get_day_pattern_for_company(
            repository=repository,
            company_id=company_id,
            day_pattern_id=day_template_id,
        )
        archived = repository.archive_day_pattern(day_pattern_id=day_pattern.id)
        day_usage = repository.day_pattern_usage_counts(company_id=company_id).get(archived.id, 0)
        mark_types = repository.list_mark_types(company_id=company_id, include_archived=True)
        return self._build_day_template_overview(
            day_pattern=archived,
            mark_type_by_id={item.id: item for item in mark_types},
            used_in_week_templates=day_usage,
        )

    def delete_day_template_permanently(
        self,
        *,
        session: Session,
        company_id: int,
        day_template_id: int,
    ) -> None:
        repository = self.repository_cls(session)
        day_pattern = self._get_day_pattern_for_company(
            repository=repository,
            company_id=company_id,
            day_pattern_id=day_template_id,
        )
        usage_count = repository.day_pattern_usage_counts(company_id=company_id).get(day_pattern.id, 0)
        if usage_count > 0:
            raise ValueError("Day template is used in week templates. Archive is required.")
        deleted = repository.delete_day_pattern(day_pattern_id=day_pattern.id)
        if not deleted:
            raise ValueError("Day template was not found.")

    def duplicate_day_template(
        self,
        *,
        session: Session,
        company_id: int,
        day_template_id: int,
    ) -> DayTemplateOverview:
        repository = self.repository_cls(session)
        source = self._get_day_pattern_for_company(
            repository=repository,
            company_id=company_id,
            day_pattern_id=day_template_id,
        )
        existing_names = {item.name for item in repository.list_day_patterns(company_id=company_id, include_archived=True)}
        duplicate_name = self._build_duplicate_name(source.name, existing_names)
        mark_type_ids = [item.mark_type_id for item in sorted(source.items, key=lambda value: value.order_index)]
        duplicate = repository.create_day_pattern(
            company_id=company_id,
            name=duplicate_name,
            mark_type_ids=mark_type_ids,
        )
        mark_types = repository.list_mark_types(company_id=company_id, include_archived=True)
        return self._build_day_template_overview(
            day_pattern=duplicate,
            mark_type_by_id={item.id: item for item in mark_types},
            used_in_week_templates=0,
        )

    def create_week_template(
        self,
        *,
        session: Session,
        company_id: int,
        name: str,
        weekday_to_day_template_id: dict[int, int],
    ) -> WeekTemplateOverview:
        clean_name = self._require_name(name=name, field_label="Назва шаблону тижня")
        normalized_mapping = self._validate_weekday_mapping(weekday_to_day_template_id)
        self._validate_day_template_ids(
            session=session,
            company_id=company_id,
            day_template_ids=list(normalized_mapping.values()),
        )
        repository = self.repository_cls(session)
        week_pattern = repository.create_week_pattern(
            company_id=company_id,
            name=clean_name,
            weekday_to_day_pattern_id=normalized_mapping,
        )
        return self._build_week_template_for_company(
            repository=repository,
            company_id=company_id,
            week_pattern=week_pattern,
        )

    def update_week_template(
        self,
        *,
        session: Session,
        company_id: int,
        week_template_id: int,
        name: str | None = None,
        weekday_to_day_template_id: dict[int, int] | None = None,
    ) -> WeekTemplateOverview:
        repository = self.repository_cls(session)
        week_pattern = self._get_week_pattern_for_company(
            repository=repository,
            company_id=company_id,
            week_pattern_id=week_template_id,
        )

        clean_name = self._require_name(name=name, field_label="Назва шаблону тижня") if name is not None else None
        normalized_mapping: dict[int, int] | None = None
        if weekday_to_day_template_id is not None:
            normalized_mapping = self._validate_weekday_mapping(weekday_to_day_template_id)
            self._validate_day_template_ids(
                session=session,
                company_id=company_id,
                day_template_ids=list(normalized_mapping.values()),
            )

        updated = repository.update_week_pattern(
            week_pattern_id=week_pattern.id,
            name=clean_name,
            weekday_to_day_pattern_id=normalized_mapping,
        )
        return self._build_week_template_for_company(
            repository=repository,
            company_id=company_id,
            week_pattern=updated,
        )

    def delete_week_template(
        self,
        *,
        session: Session,
        company_id: int,
        week_template_id: int,
    ) -> WeekTemplateOverview:
        repository = self.repository_cls(session)
        week_pattern = self._get_week_pattern_for_company(
            repository=repository,
            company_id=company_id,
            week_pattern_id=week_template_id,
        )
        archived = repository.archive_week_pattern(week_pattern_id=week_pattern.id)
        return self._build_week_template_for_company(
            repository=repository,
            company_id=company_id,
            week_pattern=archived,
        )

    def delete_week_template_permanently(
        self,
        *,
        session: Session,
        company_id: int,
        week_template_id: int,
    ) -> None:
        repository = self.repository_cls(session)
        week_pattern = self._get_week_pattern_for_company(
            repository=repository,
            company_id=company_id,
            week_pattern_id=week_template_id,
        )
        usage_count = repository.week_pattern_usage_counts(company_id=company_id).get(week_pattern.id, 0)
        if usage_count > 0:
            raise ValueError("Week template is used in calendar periods. Archive is required.")
        deleted = repository.delete_week_pattern(week_pattern_id=week_pattern.id)
        if not deleted:
            raise ValueError("Week template was not found.")

    def duplicate_week_template(
        self,
        *,
        session: Session,
        company_id: int,
        week_template_id: int,
    ) -> WeekTemplateOverview:
        repository = self.repository_cls(session)
        source = self._get_week_pattern_for_company(
            repository=repository,
            company_id=company_id,
            week_pattern_id=week_template_id,
        )
        existing_names = {
            (item.name or f"Тиждень #{item.id}")
            for item in repository.list_week_patterns(company_id=company_id, include_archived=True)
        }
        source_name = source.name or f"Тиждень #{source.id}"
        duplicate_name = self._build_duplicate_name(source_name, existing_names)
        duplicate = repository.create_week_pattern(
            company_id=company_id,
            name=duplicate_name,
            weekday_to_day_pattern_id=repository.weekday_mapping(source),
        )
        return self._build_week_template_for_company(
            repository=repository,
            company_id=company_id,
            week_pattern=duplicate,
        )

    def _build_mark_type_overview(self, *, mark_type: MarkType, used_in_day_templates: int) -> MarkTypeOverview:
        return MarkTypeOverview(
            id=mark_type.id,
            name=mark_type.name,
            kind=mark_type.kind,
            duration_minutes=mark_type.duration_minutes,
            is_archived=mark_type.is_archived,
            used_in_day_templates=used_in_day_templates,
        )

    def _build_day_template_overview(
        self,
        *,
        day_pattern: DayPattern,
        mark_type_by_id: dict[int, MarkType],
        used_in_week_templates: int,
    ) -> DayTemplateOverview:
        preview = self._build_day_preview(day_pattern=day_pattern, mark_type_by_id=mark_type_by_id)
        mark_type_ids = tuple(item.mark_type_id for item in sorted(day_pattern.items, key=lambda value: value.order_index))
        return DayTemplateOverview(
            id=day_pattern.id,
            name=day_pattern.name,
            mark_type_ids=mark_type_ids,
            is_archived=day_pattern.is_archived,
            used_in_week_templates=used_in_week_templates,
            preview=preview,
        )

    def _build_week_template_overview(
        self,
        *,
        week_pattern: WeekPattern,
        day_pattern_by_id: dict[int, DayPattern],
        mark_type_by_id: dict[int, MarkType],
        used_in_calendar_periods: int,
    ) -> WeekTemplateOverview:
        weekday_mapping = self.repository_cls.weekday_mapping(week_pattern)
        day_name_mapping = {
            weekday: (day_pattern_by_id.get(day_pattern_id).name if day_pattern_by_id.get(day_pattern_id) else "N/A")
            for weekday, day_pattern_id in weekday_mapping.items()
        }
        preview = self._build_week_preview(
            weekday_mapping=weekday_mapping,
            day_pattern_by_id=day_pattern_by_id,
            mark_type_by_id=mark_type_by_id,
        )
        return WeekTemplateOverview(
            id=week_pattern.id,
            name=week_pattern.name or f"Тиждень #{week_pattern.id}",
            weekday_to_day_template_id=weekday_mapping,
            weekday_to_day_template_name=day_name_mapping,
            is_archived=week_pattern.is_archived,
            used_in_calendar_periods=used_in_calendar_periods,
            preview=preview,
        )

    def _build_week_template_for_company(
        self,
        *,
        repository: TemplateRepository,
        company_id: int,
        week_pattern: WeekPattern,
    ) -> WeekTemplateOverview:
        day_patterns = repository.list_day_patterns(company_id=company_id, include_archived=True)
        mark_types = repository.list_mark_types(company_id=company_id, include_archived=True)
        usage = repository.week_pattern_usage_counts(company_id=company_id).get(week_pattern.id, 0)
        return self._build_week_template_overview(
            week_pattern=week_pattern,
            day_pattern_by_id={item.id: item for item in day_patterns},
            mark_type_by_id={item.id: item for item in mark_types},
            used_in_calendar_periods=usage,
        )

    @staticmethod
    def _build_day_preview(*, day_pattern: DayPattern, mark_type_by_id: dict[int, MarkType]) -> DayTemplatePreview:
        teaching = 0
        breaks = 0
        total_minutes = 0
        for item in sorted(day_pattern.items, key=lambda value: value.order_index):
            mark_type = mark_type_by_id.get(item.mark_type_id)
            if mark_type is None:
                continue
            total_minutes += mark_type.duration_minutes
            if mark_type.kind == MarkKind.TEACHING:
                teaching += 1
            elif mark_type.kind == MarkKind.BREAK:
                breaks += 1
        estimated_end = (datetime.combine(datetime.today(), time(hour=8, minute=30)) + timedelta(minutes=total_minutes)).strftime(
            "%H:%M"
        )
        return DayTemplatePreview(
            total_blocks=teaching + breaks,
            teaching_blocks=teaching,
            break_blocks=breaks,
            total_minutes=total_minutes,
            estimated_end_time=estimated_end,
        )

    def _build_week_preview(
        self,
        *,
        weekday_mapping: dict[int, int],
        day_pattern_by_id: dict[int, DayPattern],
        mark_type_by_id: dict[int, MarkType],
    ) -> WeekTemplatePreview:
        assigned_days = 0
        unique_ids: set[int] = set()
        total_blocks = 0
        teaching_blocks = 0
        break_blocks = 0
        total_minutes = 0

        for day_pattern_id in weekday_mapping.values():
            day_pattern = day_pattern_by_id.get(day_pattern_id)
            if day_pattern is None:
                continue
            assigned_days += 1
            unique_ids.add(day_pattern_id)
            preview = self._build_day_preview(day_pattern=day_pattern, mark_type_by_id=mark_type_by_id)
            total_blocks += preview.total_blocks
            teaching_blocks += preview.teaching_blocks
            break_blocks += preview.break_blocks
            total_minutes += preview.total_minutes

        return WeekTemplatePreview(
            assigned_days=assigned_days,
            unique_day_templates=len(unique_ids),
            total_blocks=total_blocks,
            teaching_blocks=teaching_blocks,
            break_blocks=break_blocks,
            total_minutes=total_minutes,
        )

    @staticmethod
    def _normalize_mark_kind(kind: MarkKind | str) -> MarkKind:
        if isinstance(kind, MarkKind):
            return kind
        try:
            return MarkKind(str(kind).strip().upper())
        except ValueError as exc:
            raise ValueError("Тип блоку має бути TEACHING або BREAK.") from exc

    @staticmethod
    def _require_name(*, name: str, field_label: str) -> str:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError(f"{field_label} обов'язкова.")
        return cleaned

    @staticmethod
    def _build_duplicate_name(base_name: str, existing_names: set[str]) -> str:
        candidate = f"{base_name} (Copy)"
        index = 2
        while candidate in existing_names:
            candidate = f"{base_name} (Copy {index})"
            index += 1
        return candidate

    @staticmethod
    def _validate_weekday_mapping(mapping: dict[int, int]) -> dict[int, int]:
        normalized = {int(key): int(value) for key, value in mapping.items()}
        if set(normalized.keys()) != set(WEEKDAY_INDEXES):
            raise ValueError("Шаблон тижня має містити 7 днів (0..6).")
        if any(day_pattern_id <= 0 for day_pattern_id in normalized.values()):
            raise ValueError("Ідентифікатор шаблону дня має бути додатнім.")
        return normalized

    def _validate_mark_type_ids(self, *, session: Session, company_id: int, mark_type_ids: list[int]) -> None:
        if not mark_type_ids:
            raise ValueError("Шаблон дня має містити щонайменше один блок.")
        if any(mark_type_id <= 0 for mark_type_id in mark_type_ids):
            raise ValueError("Ідентифікатор блоку має бути додатнім.")
        repository = self.repository_cls(session)
        distinct_ids = list(dict.fromkeys(mark_type_ids))
        mark_types = repository.get_mark_types_by_ids(company_id=company_id, mark_type_ids=distinct_ids)
        found_ids = {item.id for item in mark_types}
        if found_ids != set(distinct_ids):
            raise ValueError("Деякі блоки не знайдено або вони належать іншій компанії.")
        if any(item.is_archived for item in mark_types):
            raise ValueError("Не можна використати архівний блок у шаблоні дня.")

    def _validate_day_template_ids(self, *, session: Session, company_id: int, day_template_ids: list[int]) -> None:
        if any(day_template_id <= 0 for day_template_id in day_template_ids):
            raise ValueError("Ідентифікатор шаблону дня має бути додатнім.")
        repository = self.repository_cls(session)
        distinct_ids = list(dict.fromkeys(day_template_ids))
        day_patterns = repository.get_day_patterns_by_ids(company_id=company_id, day_pattern_ids=distinct_ids)
        found_ids = {item.id for item in day_patterns}
        if found_ids != set(distinct_ids):
            raise ValueError("Деякі шаблони дня не знайдено або вони належать іншій компанії.")
        if any(item.is_archived for item in day_patterns):
            raise ValueError("Не можна використати архівний шаблон дня у шаблоні тижня.")

    @staticmethod
    def _ensure_company_scope(*, entity_company_id: int | None, company_id: int, entity_label: str) -> None:
        if entity_company_id != company_id:
            raise ValueError(f"{entity_label} не належить цій компанії.")

    def _get_mark_type_for_company(
        self,
        *,
        repository: TemplateRepository,
        company_id: int,
        mark_type_id: int,
    ) -> MarkType:
        mark_type = repository.get_mark_type(mark_type_id)
        if mark_type is None:
            raise ValueError(f"MarkType with id={mark_type_id} was not found")
        self._ensure_company_scope(entity_company_id=mark_type.company_id, company_id=company_id, entity_label="Блок")
        return mark_type

    def _get_day_pattern_for_company(
        self,
        *,
        repository: TemplateRepository,
        company_id: int,
        day_pattern_id: int,
    ) -> DayPattern:
        day_pattern = repository.get_day_pattern(day_pattern_id)
        if day_pattern is None:
            raise ValueError(f"DayPattern with id={day_pattern_id} was not found")
        self._ensure_company_scope(
            entity_company_id=day_pattern.company_id,
            company_id=company_id,
            entity_label="Шаблон дня",
        )
        return day_pattern

    def _get_week_pattern_for_company(
        self,
        *,
        repository: TemplateRepository,
        company_id: int,
        week_pattern_id: int,
    ) -> WeekPattern:
        week_pattern = repository.get_week_pattern(week_pattern_id)
        if week_pattern is None:
            raise ValueError(f"WeekPattern with id={week_pattern_id} was not found")
        self._ensure_company_scope(
            entity_company_id=week_pattern.company_id,
            company_id=company_id,
            entity_label="Шаблон тижня",
        )
        return week_pattern
