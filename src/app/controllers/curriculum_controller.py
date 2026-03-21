from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.enums import PlanComponentType, PlanTargetType
from app.domain.models import (
    CurriculumPlan,
    PlanComponent,
    PlanComponentAssignment,
    Requirement,
    Subject,
)
from app.repositories.curriculum_repository import CurriculumRepository

_UNSET = object()


class CurriculumController:
    def __init__(self, session: Session) -> None:
        self.repository = CurriculumRepository(session=session)

    # Subject catalog
    def create_subject(
        self,
        *,
        name: str,
        code: str | None = None,
        department_id: int | None = None,
        company_id: int | None = None,
    ) -> Subject:
        return self.repository.create_subject(
            name=name,
            code=code,
            department_id=department_id,
            company_id=company_id,
        )

    def get_subject(self, subject_id: int) -> Subject | None:
        return self.repository.get_subject(subject_id)

    def list_subjects(
        self,
        *,
        company_id: int | None = None,
        department_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Subject]:
        return self.repository.list_subjects(
            company_id=company_id,
            department_id=department_id,
            include_archived=include_archived,
        )

    def update_subject(
        self,
        subject_id: int,
        *,
        name: str | object = _UNSET,
        code: str | None | object = _UNSET,
        department_id: int | None | object = _UNSET,
        is_archived: bool | object = _UNSET,
    ) -> Subject:
        kwargs: dict[str, object] = {}
        if name is not _UNSET:
            kwargs["name"] = name
        if code is not _UNSET:
            kwargs["code"] = code
        if department_id is not _UNSET:
            kwargs["department_id"] = department_id
        if is_archived is not _UNSET:
            kwargs["is_archived"] = is_archived
        return self.repository.update_subject(subject_id, **kwargs)

    def delete_subject(self, subject_id: int) -> bool:
        return self.repository.delete_subject(subject_id)

    # Plans
    def create_plan(
        self,
        *,
        name: str,
        company_id: int | None = None,
        specialty_id: int | None = None,
        course_id: int | None = None,
        stream_id: int | None = None,
        semester: int | None = None,
    ) -> CurriculumPlan:
        return self.repository.create_plan(
            name=name,
            company_id=company_id,
            specialty_id=specialty_id,
            course_id=course_id,
            stream_id=stream_id,
            semester=semester,
        )

    def get_plan(self, plan_id: int) -> CurriculumPlan | None:
        return self.repository.get_plan(plan_id)

    def list_plans(
        self,
        *,
        company_id: int | None = None,
        include_archived: bool = False,
    ) -> list[CurriculumPlan]:
        return self.repository.list_plans(
            company_id=company_id,
            include_archived=include_archived,
        )

    def update_plan(
        self,
        plan_id: int,
        *,
        name: str | object = _UNSET,
        specialty_id: int | None | object = _UNSET,
        course_id: int | None | object = _UNSET,
        stream_id: int | None | object = _UNSET,
        semester: int | None | object = _UNSET,
        is_archived: bool | object = _UNSET,
    ) -> CurriculumPlan:
        kwargs: dict[str, object] = {}
        if name is not _UNSET:
            kwargs["name"] = name
        if specialty_id is not _UNSET:
            kwargs["specialty_id"] = specialty_id
        if course_id is not _UNSET:
            kwargs["course_id"] = course_id
        if stream_id is not _UNSET:
            kwargs["stream_id"] = stream_id
        if semester is not _UNSET:
            kwargs["semester"] = semester
        if is_archived is not _UNSET:
            kwargs["is_archived"] = is_archived
        return self.repository.update_plan(plan_id, **kwargs)

    def delete_plan(self, plan_id: int, *, delete_requirements: bool = True) -> bool:
        return self.repository.delete_plan(plan_id, delete_requirements=delete_requirements)

    # Plan components
    def create_component(
        self,
        *,
        plan_id: int,
        subject_id: int,
        component_type: PlanComponentType | str,
        duration_blocks: int,
        sessions_total: int,
        max_per_week: int,
        notes: str | None = None,
    ) -> PlanComponent:
        return self.repository.create_component(
            plan_id=plan_id,
            subject_id=subject_id,
            component_type=self._normalize_component_type(component_type),
            duration_blocks=duration_blocks,
            sessions_total=sessions_total,
            max_per_week=max_per_week,
            notes=notes,
        )

    def get_component(self, component_id: int) -> PlanComponent | None:
        return self.repository.get_component(component_id)

    def list_components(self, *, plan_id: int) -> list[PlanComponent]:
        return self.repository.list_components(plan_id=plan_id)

    def update_component(
        self,
        component_id: int,
        *,
        subject_id: int | object = _UNSET,
        component_type: PlanComponentType | str | object = _UNSET,
        duration_blocks: int | object = _UNSET,
        sessions_total: int | object = _UNSET,
        max_per_week: int | object = _UNSET,
        notes: str | None | object = _UNSET,
    ) -> PlanComponent:
        kwargs: dict[str, object] = {}
        if subject_id is not _UNSET:
            kwargs["subject_id"] = subject_id
        if component_type is not _UNSET:
            kwargs["component_type"] = self._normalize_component_type(component_type)
        if duration_blocks is not _UNSET:
            kwargs["duration_blocks"] = duration_blocks
        if sessions_total is not _UNSET:
            kwargs["sessions_total"] = sessions_total
        if max_per_week is not _UNSET:
            kwargs["max_per_week"] = max_per_week
        if notes is not _UNSET:
            kwargs["notes"] = notes
        return self.repository.update_component(component_id, **kwargs)

    def delete_component(self, component_id: int, *, delete_requirements: bool = True) -> bool:
        return self.repository.delete_component(component_id, delete_requirements=delete_requirements)

    # Component assignments
    def create_assignment(
        self,
        *,
        component_id: int,
        teacher_resource_id: int,
        target_type: PlanTargetType | str,
        target_resource_id: int | None = None,
        stream_id: int | None = None,
        sessions_total: int | None = None,
        max_per_week: int | None = None,
    ) -> PlanComponentAssignment:
        return self.repository.create_assignment(
            component_id=component_id,
            teacher_resource_id=teacher_resource_id,
            target_type=self._normalize_target_type(target_type),
            target_resource_id=target_resource_id,
            stream_id=stream_id,
            sessions_total=sessions_total,
            max_per_week=max_per_week,
        )

    def get_assignment(self, assignment_id: int) -> PlanComponentAssignment | None:
        return self.repository.get_assignment(assignment_id)

    def list_assignments(self, *, component_id: int) -> list[PlanComponentAssignment]:
        return self.repository.list_assignments(component_id=component_id)

    def list_plan_assignments(self, *, plan_id: int) -> list[PlanComponentAssignment]:
        return self.repository.list_plan_assignments(plan_id=plan_id)

    def update_assignment(
        self,
        assignment_id: int,
        *,
        teacher_resource_id: int | object = _UNSET,
        target_type: PlanTargetType | str | object = _UNSET,
        target_resource_id: int | None | object = _UNSET,
        stream_id: int | None | object = _UNSET,
        sessions_total: int | object = _UNSET,
        max_per_week: int | object = _UNSET,
    ) -> PlanComponentAssignment:
        kwargs: dict[str, object] = {}
        if teacher_resource_id is not _UNSET:
            kwargs["teacher_resource_id"] = teacher_resource_id
        if target_type is not _UNSET:
            kwargs["target_type"] = self._normalize_target_type(target_type)
        if target_resource_id is not _UNSET:
            kwargs["target_resource_id"] = target_resource_id
        if stream_id is not _UNSET:
            kwargs["stream_id"] = stream_id
        if sessions_total is not _UNSET:
            kwargs["sessions_total"] = sessions_total
        if max_per_week is not _UNSET:
            kwargs["max_per_week"] = max_per_week
        return self.repository.update_assignment(assignment_id, **kwargs)

    def delete_assignment(self, assignment_id: int, *, delete_requirement: bool = True) -> bool:
        return self.repository.delete_assignment(assignment_id, delete_requirement=delete_requirement)

    # Sync with scheduler requirements
    def sync_assignment_requirement(self, assignment_id: int) -> Requirement:
        return self.repository.sync_assignment_requirement(assignment_id)

    def sync_plan_requirements(self, plan_id: int) -> list[Requirement]:
        return self.repository.sync_plan_requirements(plan_id)

    def _normalize_component_type(self, value: PlanComponentType | str) -> PlanComponentType:
        if isinstance(value, PlanComponentType):
            return value
        normalized = str(value).strip().upper()
        try:
            return PlanComponentType(normalized)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in PlanComponentType)
            raise ValueError(f"Unsupported component type: {value!r}. Allowed: {allowed}") from exc

    def _normalize_target_type(self, value: PlanTargetType | str) -> PlanTargetType:
        if isinstance(value, PlanTargetType):
            return value
        normalized = str(value).strip().upper()
        try:
            return PlanTargetType(normalized)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in PlanTargetType)
            raise ValueError(f"Unsupported target type: {value!r}. Allowed: {allowed}") from exc
