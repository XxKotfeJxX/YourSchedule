from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.enums import MarkKind
from app.services.empty_day_template_service import EmptyDayTemplateService
from app.services.template_models import (
    DayTemplateOverview,
    MarkTypeOverview,
    TemplatesOverview,
    WeekTemplateOverview,
)
from app.services.template_service import TemplateService


class TemplateController:
    def __init__(
        self,
        session: Session,
        template_service: TemplateService | None = None,
        empty_day_template_service: EmptyDayTemplateService | None = None,
    ) -> None:
        self.session = session
        self.template_service = template_service or TemplateService()
        self.empty_day_template_service = empty_day_template_service or EmptyDayTemplateService()

    def load_templates_overview(self, company_id: int) -> TemplatesOverview:
        return self.template_service.load_templates_overview(
            session=self.session,
            company_id=company_id,
        )

    def create_mark_type(
        self,
        *,
        company_id: int,
        name: str,
        kind: MarkKind | str,
        duration_minutes: int,
    ) -> MarkTypeOverview:
        return self.template_service.create_mark_type(
            session=self.session,
            company_id=company_id,
            name=name,
            kind=kind,
            duration_minutes=duration_minutes,
        )

    def update_mark_type(
        self,
        *,
        company_id: int,
        mark_type_id: int,
        name: str | None = None,
        kind: MarkKind | str | None = None,
        duration_minutes: int | None = None,
    ) -> MarkTypeOverview:
        return self.template_service.update_mark_type(
            session=self.session,
            company_id=company_id,
            mark_type_id=mark_type_id,
            name=name,
            kind=kind,
            duration_minutes=duration_minutes,
        )

    def delete_mark_type(self, *, company_id: int, mark_type_id: int) -> MarkTypeOverview:
        return self.template_service.delete_mark_type(
            session=self.session,
            company_id=company_id,
            mark_type_id=mark_type_id,
        )

    def delete_mark_type_permanently(self, *, company_id: int, mark_type_id: int) -> None:
        self.template_service.delete_mark_type_permanently(
            session=self.session,
            company_id=company_id,
            mark_type_id=mark_type_id,
        )

    def duplicate_mark_type(self, *, company_id: int, mark_type_id: int) -> MarkTypeOverview:
        return self.template_service.duplicate_mark_type(
            session=self.session,
            company_id=company_id,
            mark_type_id=mark_type_id,
        )

    def create_day_template(
        self,
        *,
        company_id: int,
        name: str,
        mark_type_ids: list[int],
    ) -> DayTemplateOverview:
        return self.template_service.create_day_template(
            session=self.session,
            company_id=company_id,
            name=name,
            mark_type_ids=mark_type_ids,
        )

    def update_day_template(
        self,
        *,
        company_id: int,
        day_template_id: int,
        name: str | None = None,
        mark_type_ids: list[int] | None = None,
    ) -> DayTemplateOverview:
        return self.template_service.update_day_template(
            session=self.session,
            company_id=company_id,
            day_template_id=day_template_id,
            name=name,
            mark_type_ids=mark_type_ids,
        )

    def delete_day_template(self, *, company_id: int, day_template_id: int) -> DayTemplateOverview:
        return self.template_service.delete_day_template(
            session=self.session,
            company_id=company_id,
            day_template_id=day_template_id,
        )

    def delete_day_template_permanently(self, *, company_id: int, day_template_id: int) -> None:
        self.template_service.delete_day_template_permanently(
            session=self.session,
            company_id=company_id,
            day_template_id=day_template_id,
        )

    def duplicate_day_template(self, *, company_id: int, day_template_id: int) -> DayTemplateOverview:
        return self.template_service.duplicate_day_template(
            session=self.session,
            company_id=company_id,
            day_template_id=day_template_id,
        )

    def create_week_template(
        self,
        *,
        company_id: int,
        name: str,
        weekday_to_day_template_id: dict[int, int],
    ) -> WeekTemplateOverview:
        return self.template_service.create_week_template(
            session=self.session,
            company_id=company_id,
            name=name,
            weekday_to_day_template_id=weekday_to_day_template_id,
        )

    def update_week_template(
        self,
        *,
        company_id: int,
        week_template_id: int,
        name: str | None = None,
        weekday_to_day_template_id: dict[int, int] | None = None,
    ) -> WeekTemplateOverview:
        return self.template_service.update_week_template(
            session=self.session,
            company_id=company_id,
            week_template_id=week_template_id,
            name=name,
            weekday_to_day_template_id=weekday_to_day_template_id,
        )

    def delete_week_template(self, *, company_id: int, week_template_id: int) -> WeekTemplateOverview:
        return self.template_service.delete_week_template(
            session=self.session,
            company_id=company_id,
            week_template_id=week_template_id,
        )

    def delete_week_template_permanently(self, *, company_id: int, week_template_id: int) -> None:
        self.template_service.delete_week_template_permanently(
            session=self.session,
            company_id=company_id,
            week_template_id=week_template_id,
        )

    def duplicate_week_template(self, *, company_id: int, week_template_id: int) -> WeekTemplateOverview:
        return self.template_service.duplicate_week_template(
            session=self.session,
            company_id=company_id,
            week_template_id=week_template_id,
        )

    def ensure_empty_day_template(self, *, company_id: int) -> int:
        return self.empty_day_template_service.ensure_empty_day_template(
            session=self.session,
            company_id=company_id,
        )
