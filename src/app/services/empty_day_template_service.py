from __future__ import annotations

from app.repositories.template_repository import TemplateRepository


class EmptyDayTemplateService:
    BASE_NAME = "Empty Day"

    def __init__(self, repository_cls: type[TemplateRepository] = TemplateRepository) -> None:
        self.repository_cls = repository_cls

    def ensure_empty_day_template(self, *, session, company_id: int) -> int:
        repository = self.repository_cls(session)
        day_patterns = repository.list_day_patterns(company_id=company_id, include_archived=True)

        for day_pattern in day_patterns:
            if not day_pattern.is_archived and len(day_pattern.items) == 0:
                return day_pattern.id

        existing_names = {item.name for item in day_patterns}
        name = self.BASE_NAME
        suffix = 2
        while name in existing_names:
            name = f"{self.BASE_NAME} {suffix}"
            suffix += 1

        created = repository.create_day_pattern(
            company_id=company_id,
            name=name,
            mark_type_ids=[],
        )
        return created.id

