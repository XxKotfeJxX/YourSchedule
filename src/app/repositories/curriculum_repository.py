from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.enums import PlanComponentType, PlanTargetType, ResourceType
from app.domain.models import (
    Course,
    CurriculumPlan,
    Department,
    PlanComponent,
    PlanComponentAssignment,
    Requirement,
    RequirementResource,
    Resource,
    Specialty,
    Stream,
    Subject,
)

_UNSET = object()


class CurriculumRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # Subject catalog
    def create_subject(
        self,
        *,
        name: str,
        code: str | None = None,
        department_id: int | None = None,
        company_id: int | None = None,
    ) -> Subject:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Subject name is required")

        resolved_company_id = company_id
        if department_id is not None:
            department = self.session.get(Department, int(department_id))
            if department is None:
                raise ValueError(f"Department with id={department_id} was not found")
            if resolved_company_id is None:
                resolved_company_id = department.company_id
            if (
                resolved_company_id is not None
                and department.company_id is not None
                and resolved_company_id != department.company_id
            ):
                raise ValueError("Subject and department belong to different companies")

        subject = Subject(
            company_id=resolved_company_id,
            department_id=department_id,
            name=clean_name,
            code=(code or "").strip() or None,
            is_archived=False,
        )
        self.session.add(subject)
        self.session.flush()
        return subject

    def get_subject(self, subject_id: int) -> Subject | None:
        return self.session.get(Subject, subject_id)

    def list_subjects(
        self,
        *,
        company_id: int | None = None,
        department_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Subject]:
        statement = select(Subject).order_by(Subject.name.asc(), Subject.id.asc())
        if company_id is not None:
            statement = statement.where(Subject.company_id == company_id)
        if department_id is not None:
            statement = statement.where(Subject.department_id == department_id)
        if not include_archived:
            statement = statement.where(Subject.is_archived.is_(False))
        return list(self.session.scalars(statement).all())

    def update_subject(
        self,
        subject_id: int,
        *,
        name: str | object = _UNSET,
        code: str | None | object = _UNSET,
        department_id: int | None | object = _UNSET,
        is_archived: bool | object = _UNSET,
    ) -> Subject:
        subject = self.get_subject(subject_id)
        if subject is None:
            raise ValueError(f"Subject with id={subject_id} was not found")

        if name is not _UNSET:
            clean_name = str(name).strip()
            if not clean_name:
                raise ValueError("Subject name is required")
            subject.name = clean_name
        if code is not _UNSET:
            subject.code = (str(code).strip() if code is not None else "") or None
        if department_id is not _UNSET:
            if department_id is None:
                subject.department_id = None
            else:
                department = self.session.get(Department, int(department_id))
                if department is None:
                    raise ValueError(f"Department with id={department_id} was not found")
                if (
                    subject.company_id is not None
                    and department.company_id is not None
                    and subject.company_id != department.company_id
                ):
                    raise ValueError("Subject and department belong to different companies")
                subject.department_id = int(department_id)
        if is_archived is not _UNSET:
            subject.is_archived = bool(is_archived)

        self.session.flush()
        return subject

    def delete_subject(self, subject_id: int) -> bool:
        subject = self.get_subject(subject_id)
        if subject is None:
            return False
        self.session.delete(subject)
        self.session.flush()
        return True

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
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Plan name is required")

        resolved_company_id, resolved_specialty_id, resolved_course_id, resolved_stream_id = self._resolve_plan_scope(
            company_id=company_id,
            specialty_id=specialty_id,
            course_id=course_id,
            stream_id=stream_id,
        )

        resolved_semester: int | None = None
        if semester is not None:
            resolved_semester = int(semester)
            if resolved_semester <= 0:
                raise ValueError("Semester must be positive")

        plan = CurriculumPlan(
            company_id=resolved_company_id,
            name=clean_name,
            specialty_id=resolved_specialty_id,
            course_id=resolved_course_id,
            stream_id=resolved_stream_id,
            semester=resolved_semester,
            is_archived=False,
        )
        self.session.add(plan)
        self.session.flush()
        return plan

    def get_plan(self, plan_id: int) -> CurriculumPlan | None:
        return self.session.get(CurriculumPlan, plan_id)

    def list_plans(
        self,
        *,
        company_id: int | None = None,
        include_archived: bool = False,
    ) -> list[CurriculumPlan]:
        statement = select(CurriculumPlan).order_by(CurriculumPlan.name.asc(), CurriculumPlan.id.asc())
        if company_id is not None:
            statement = statement.where(CurriculumPlan.company_id == company_id)
        if not include_archived:
            statement = statement.where(CurriculumPlan.is_archived.is_(False))
        return list(self.session.scalars(statement).all())

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
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan with id={plan_id} was not found")

        next_name = plan.name if name is _UNSET else str(name).strip()
        if not next_name:
            raise ValueError("Plan name is required")

        next_specialty_id = plan.specialty_id if specialty_id is _UNSET else specialty_id
        next_course_id = plan.course_id if course_id is _UNSET else course_id
        next_stream_id = plan.stream_id if stream_id is _UNSET else stream_id

        (
            resolved_company_id,
            resolved_specialty_id,
            resolved_course_id,
            resolved_stream_id,
        ) = self._resolve_plan_scope(
            company_id=plan.company_id,
            specialty_id=next_specialty_id,
            course_id=next_course_id,
            stream_id=next_stream_id,
        )

        plan.name = next_name
        plan.company_id = resolved_company_id
        plan.specialty_id = resolved_specialty_id
        plan.course_id = resolved_course_id
        plan.stream_id = resolved_stream_id

        if semester is not _UNSET:
            if semester is None:
                plan.semester = None
            else:
                resolved_semester = int(semester)
                if resolved_semester <= 0:
                    raise ValueError("Semester must be positive")
                plan.semester = resolved_semester
        if is_archived is not _UNSET:
            plan.is_archived = bool(is_archived)

        self.session.flush()
        return plan

    def delete_plan(self, plan_id: int, *, delete_requirements: bool = True) -> bool:
        plan = self.get_plan(plan_id)
        if plan is None:
            return False
        for component in list(self.list_components(plan_id=plan.id)):
            self.delete_component(component.id, delete_requirements=delete_requirements)
        self.session.delete(plan)
        self.session.flush()
        return True

    # Plan components
    def create_component(
        self,
        *,
        plan_id: int,
        subject_id: int,
        component_type: PlanComponentType,
        duration_blocks: int,
        sessions_total: int,
        max_per_week: int,
        notes: str | None = None,
    ) -> PlanComponent:
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan with id={plan_id} was not found")
        subject = self.get_subject(subject_id)
        if subject is None:
            raise ValueError(f"Subject with id={subject_id} was not found")
        if (
            plan.company_id is not None
            and subject.company_id is not None
            and plan.company_id != subject.company_id
        ):
            raise ValueError("Plan and subject belong to different companies")

        self._validate_component_numbers(
            duration_blocks=int(duration_blocks),
            sessions_total=int(sessions_total),
            max_per_week=int(max_per_week),
        )

        component = PlanComponent(
            plan_id=plan.id,
            subject_id=subject.id,
            component_type=component_type,
            duration_blocks=int(duration_blocks),
            sessions_total=int(sessions_total),
            max_per_week=int(max_per_week),
            notes=(notes or "").strip() or None,
        )
        self.session.add(component)
        self.session.flush()
        return component

    def get_component(self, component_id: int) -> PlanComponent | None:
        return self.session.get(PlanComponent, component_id)

    def list_components(self, *, plan_id: int) -> list[PlanComponent]:
        statement = (
            select(PlanComponent)
            .where(PlanComponent.plan_id == plan_id)
            .order_by(PlanComponent.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def update_component(
        self,
        component_id: int,
        *,
        subject_id: int | object = _UNSET,
        component_type: PlanComponentType | object = _UNSET,
        duration_blocks: int | object = _UNSET,
        sessions_total: int | object = _UNSET,
        max_per_week: int | object = _UNSET,
        notes: str | None | object = _UNSET,
    ) -> PlanComponent:
        component = self.get_component(component_id)
        if component is None:
            raise ValueError(f"Plan component with id={component_id} was not found")

        if subject_id is not _UNSET:
            subject = self.get_subject(int(subject_id))
            if subject is None:
                raise ValueError(f"Subject with id={subject_id} was not found")
            plan = self.get_plan(component.plan_id)
            if plan is not None and plan.company_id is not None and subject.company_id is not None and plan.company_id != subject.company_id:
                raise ValueError("Plan and subject belong to different companies")
            component.subject_id = int(subject_id)
        if component_type is not _UNSET:
            component.component_type = component_type

        next_duration = component.duration_blocks if duration_blocks is _UNSET else int(duration_blocks)
        next_sessions = component.sessions_total if sessions_total is _UNSET else int(sessions_total)
        next_max_per_week = component.max_per_week if max_per_week is _UNSET else int(max_per_week)
        self._validate_component_numbers(
            duration_blocks=next_duration,
            sessions_total=next_sessions,
            max_per_week=next_max_per_week,
        )
        component.duration_blocks = next_duration
        component.sessions_total = next_sessions
        component.max_per_week = next_max_per_week

        if notes is not _UNSET:
            component.notes = (str(notes).strip() if notes is not None else "") or None

        self.session.flush()
        return component

    def delete_component(self, component_id: int, *, delete_requirements: bool = True) -> bool:
        component = self.get_component(component_id)
        if component is None:
            return False
        for assignment in list(self.list_assignments(component_id=component.id)):
            self.delete_assignment(assignment.id, delete_requirement=delete_requirements)
        self.session.delete(component)
        self.session.flush()
        return True

    # Component assignments
    def create_assignment(
        self,
        *,
        component_id: int,
        teacher_resource_id: int,
        target_type: PlanTargetType,
        target_resource_id: int | None = None,
        stream_id: int | None = None,
        sessions_total: int | None = None,
        max_per_week: int | None = None,
    ) -> PlanComponentAssignment:
        component = self.get_component(component_id)
        if component is None:
            raise ValueError(f"Plan component with id={component_id} was not found")
        plan = self.get_plan(component.plan_id)
        if plan is None:
            raise ValueError("Plan was not found")

        teacher = self._validate_teacher_resource(
            resource_id=int(teacher_resource_id),
            owner_company_id=plan.company_id,
        )
        resolved_target_resource_id, resolved_stream_id = self._validate_assignment_target(
            target_type=target_type,
            target_resource_id=target_resource_id,
            stream_id=stream_id,
            owner_company_id=plan.company_id,
        )

        resolved_sessions = component.sessions_total if sessions_total is None else int(sessions_total)
        resolved_max_per_week = component.max_per_week if max_per_week is None else int(max_per_week)
        self._validate_assignment_numbers(
            sessions_total=resolved_sessions,
            max_per_week=resolved_max_per_week,
        )

        if self._assignment_exists(
            component_id=component.id,
            teacher_resource_id=teacher.id,
            target_type=target_type,
            target_resource_id=resolved_target_resource_id,
            stream_id=resolved_stream_id,
            exclude_assignment_id=None,
        ):
            raise ValueError("Such assignment already exists for this plan component")

        assignment = PlanComponentAssignment(
            component_id=component.id,
            teacher_resource_id=teacher.id,
            target_type=target_type,
            target_resource_id=resolved_target_resource_id,
            stream_id=resolved_stream_id,
            sessions_total=resolved_sessions,
            max_per_week=resolved_max_per_week,
        )
        self.session.add(assignment)
        self.session.flush()
        return assignment

    def get_assignment(self, assignment_id: int) -> PlanComponentAssignment | None:
        return self.session.get(PlanComponentAssignment, assignment_id)

    def list_assignments(self, *, component_id: int) -> list[PlanComponentAssignment]:
        statement = (
            select(PlanComponentAssignment)
            .where(PlanComponentAssignment.component_id == component_id)
            .order_by(PlanComponentAssignment.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def list_plan_assignments(self, *, plan_id: int) -> list[PlanComponentAssignment]:
        statement = (
            select(PlanComponentAssignment)
            .join(PlanComponent, PlanComponentAssignment.component_id == PlanComponent.id)
            .where(PlanComponent.plan_id == plan_id)
            .order_by(PlanComponentAssignment.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def update_assignment(
        self,
        assignment_id: int,
        *,
        teacher_resource_id: int | object = _UNSET,
        target_type: PlanTargetType | object = _UNSET,
        target_resource_id: int | None | object = _UNSET,
        stream_id: int | None | object = _UNSET,
        sessions_total: int | object = _UNSET,
        max_per_week: int | object = _UNSET,
    ) -> PlanComponentAssignment:
        assignment = self.get_assignment(assignment_id)
        if assignment is None:
            raise ValueError(f"Plan component assignment with id={assignment_id} was not found")
        component = self.get_component(assignment.component_id)
        if component is None:
            raise ValueError("Plan component was not found")
        plan = self.get_plan(component.plan_id)
        if plan is None:
            raise ValueError("Plan was not found")

        next_teacher_resource_id = assignment.teacher_resource_id if teacher_resource_id is _UNSET else int(teacher_resource_id)
        self._validate_teacher_resource(resource_id=next_teacher_resource_id, owner_company_id=plan.company_id)

        next_target_type = assignment.target_type if target_type is _UNSET else target_type
        next_target_resource_id = assignment.target_resource_id if target_resource_id is _UNSET else target_resource_id
        next_stream_id = assignment.stream_id if stream_id is _UNSET else stream_id
        resolved_target_resource_id, resolved_stream_id = self._validate_assignment_target(
            target_type=next_target_type,
            target_resource_id=next_target_resource_id,
            stream_id=next_stream_id,
            owner_company_id=plan.company_id,
        )

        next_sessions = assignment.sessions_total if sessions_total is _UNSET else int(sessions_total)
        next_max_per_week = assignment.max_per_week if max_per_week is _UNSET else int(max_per_week)
        self._validate_assignment_numbers(
            sessions_total=next_sessions,
            max_per_week=next_max_per_week,
        )

        if self._assignment_exists(
            component_id=component.id,
            teacher_resource_id=next_teacher_resource_id,
            target_type=next_target_type,
            target_resource_id=resolved_target_resource_id,
            stream_id=resolved_stream_id,
            exclude_assignment_id=assignment.id,
        ):
            raise ValueError("Such assignment already exists for this plan component")

        assignment.teacher_resource_id = next_teacher_resource_id
        assignment.target_type = next_target_type
        assignment.target_resource_id = resolved_target_resource_id
        assignment.stream_id = resolved_stream_id
        assignment.sessions_total = next_sessions
        assignment.max_per_week = next_max_per_week
        self.session.flush()
        return assignment

    def delete_assignment(self, assignment_id: int, *, delete_requirement: bool = True) -> bool:
        assignment = self.get_assignment(assignment_id)
        if assignment is None:
            return False
        if delete_requirement and assignment.requirement_id is not None:
            requirement = self.session.get(Requirement, int(assignment.requirement_id))
            if requirement is not None:
                self.session.delete(requirement)
        self.session.delete(assignment)
        self.session.flush()
        return True

    # Synchronization with scheduler requirements
    def sync_assignment_requirement(self, assignment_id: int) -> Requirement:
        assignment = self.get_assignment(assignment_id)
        if assignment is None:
            raise ValueError(f"Plan component assignment with id={assignment_id} was not found")
        component = self.get_component(assignment.component_id)
        if component is None:
            raise ValueError("Plan component was not found")
        plan = self.get_plan(component.plan_id)
        if plan is None:
            raise ValueError("Plan was not found")
        subject = self.get_subject(component.subject_id)
        if subject is None:
            raise ValueError("Subject was not found")

        requirement = self.session.get(Requirement, assignment.requirement_id) if assignment.requirement_id is not None else None
        requirement_name = self._build_requirement_name(
            plan=plan,
            component=component,
            assignment=assignment,
            subject=subject,
        )

        if requirement is None:
            requirement = Requirement(
                company_id=plan.company_id,
                name=requirement_name,
                duration_blocks=component.duration_blocks,
                sessions_total=assignment.sessions_total,
                max_per_week=assignment.max_per_week,
            )
            self.session.add(requirement)
            self.session.flush()
            assignment.requirement_id = requirement.id
        else:
            requirement.company_id = plan.company_id
            requirement.name = requirement_name
            requirement.duration_blocks = component.duration_blocks
            requirement.sessions_total = assignment.sessions_total
            requirement.max_per_week = assignment.max_per_week

        self.session.execute(
            delete(RequirementResource).where(RequirementResource.requirement_id == requirement.id)
        )

        self._assign_requirement_resource(
            requirement_id=requirement.id,
            resource_id=assignment.teacher_resource_id,
            role="TEACHER",
        )

        if assignment.target_type == PlanTargetType.STREAM:
            groups = list(
                self.session.scalars(
                    select(Resource)
                    .where(
                        Resource.type == ResourceType.GROUP,
                        Resource.stream_id == assignment.stream_id,
                    )
                    .order_by(Resource.id.asc())
                ).all()
            )
            if not groups:
                raise ValueError("Selected stream has no groups for requirement assignment")
            for group in groups:
                self._assign_requirement_resource(
                    requirement_id=requirement.id,
                    resource_id=group.id,
                    role="GROUP",
                )
        elif assignment.target_type == PlanTargetType.GROUP:
            if assignment.target_resource_id is None:
                raise ValueError("Group target is missing")
            self._assign_requirement_resource(
                requirement_id=requirement.id,
                resource_id=assignment.target_resource_id,
                role="GROUP",
            )
        else:
            if assignment.target_resource_id is None:
                raise ValueError("Subgroup target is missing")
            self._assign_requirement_resource(
                requirement_id=requirement.id,
                resource_id=assignment.target_resource_id,
                role="SUBGROUP",
            )

        self.session.flush()
        return requirement

    def sync_plan_requirements(self, plan_id: int) -> list[Requirement]:
        plan = self.get_plan(plan_id)
        if plan is None:
            raise ValueError(f"Plan with id={plan_id} was not found")
        synced: list[Requirement] = []
        for assignment in self.list_plan_assignments(plan_id=plan.id):
            synced.append(self.sync_assignment_requirement(assignment.id))
        return synced

    # Internal helpers
    def _resolve_plan_scope(
        self,
        *,
        company_id: int | None,
        specialty_id: int | None,
        course_id: int | None,
        stream_id: int | None,
    ) -> tuple[int | None, int | None, int | None, int | None]:
        resolved_company_id = company_id
        resolved_specialty_id = int(specialty_id) if specialty_id is not None else None
        resolved_course_id = int(course_id) if course_id is not None else None
        resolved_stream_id = int(stream_id) if stream_id is not None else None

        specialty = self.session.get(Specialty, resolved_specialty_id) if resolved_specialty_id is not None else None
        if resolved_specialty_id is not None and specialty is None:
            raise ValueError(f"Specialty with id={resolved_specialty_id} was not found")
        if specialty is not None:
            if resolved_company_id is None:
                resolved_company_id = specialty.company_id
            if (
                resolved_company_id is not None
                and specialty.company_id is not None
                and resolved_company_id != specialty.company_id
            ):
                raise ValueError("Plan and specialty belong to different companies")

        course = self.session.get(Course, resolved_course_id) if resolved_course_id is not None else None
        if resolved_course_id is not None and course is None:
            raise ValueError(f"Course with id={resolved_course_id} was not found")
        if course is not None:
            if resolved_specialty_id is None:
                resolved_specialty_id = course.specialty_id
            elif resolved_specialty_id != course.specialty_id:
                raise ValueError("Course and specialty mismatch")
            if resolved_company_id is None:
                resolved_company_id = course.company_id
            if (
                resolved_company_id is not None
                and course.company_id is not None
                and resolved_company_id != course.company_id
            ):
                raise ValueError("Plan and course belong to different companies")

        stream = self.session.get(Stream, resolved_stream_id) if resolved_stream_id is not None else None
        if resolved_stream_id is not None and stream is None:
            raise ValueError(f"Stream with id={resolved_stream_id} was not found")
        if stream is not None:
            if resolved_course_id is None:
                resolved_course_id = stream.course_id
            elif stream.course_id is not None and resolved_course_id != stream.course_id:
                raise ValueError("Stream and course mismatch")
            if resolved_specialty_id is None:
                resolved_specialty_id = stream.specialty_id
            elif resolved_specialty_id != stream.specialty_id:
                raise ValueError("Stream and specialty mismatch")
            if resolved_company_id is None:
                resolved_company_id = stream.company_id
            if (
                resolved_company_id is not None
                and stream.company_id is not None
                and resolved_company_id != stream.company_id
            ):
                raise ValueError("Plan and stream belong to different companies")

        return resolved_company_id, resolved_specialty_id, resolved_course_id, resolved_stream_id

    def _validate_component_numbers(
        self,
        *,
        duration_blocks: int,
        sessions_total: int,
        max_per_week: int,
    ) -> None:
        if int(duration_blocks) <= 0:
            raise ValueError("Duration blocks must be positive")
        if int(sessions_total) <= 0:
            raise ValueError("Sessions total must be positive")
        if int(max_per_week) <= 0:
            raise ValueError("Max per week must be positive")
        if int(max_per_week) > int(sessions_total):
            raise ValueError("Max per week cannot exceed sessions total")

    def _validate_assignment_numbers(self, *, sessions_total: int, max_per_week: int) -> None:
        if int(sessions_total) <= 0:
            raise ValueError("Sessions total must be positive")
        if int(max_per_week) <= 0:
            raise ValueError("Max per week must be positive")
        if int(max_per_week) > int(sessions_total):
            raise ValueError("Max per week cannot exceed sessions total")

    def _validate_teacher_resource(self, *, resource_id: int, owner_company_id: int | None) -> Resource:
        resource = self.session.get(Resource, int(resource_id))
        if resource is None:
            raise ValueError(f"Resource with id={resource_id} was not found")
        if resource.type != ResourceType.TEACHER:
            raise ValueError("Selected resource is not a teacher")
        if (
            owner_company_id is not None
            and resource.company_id is not None
            and owner_company_id != resource.company_id
        ):
            raise ValueError("Teacher belongs to another company")
        return resource

    def _validate_assignment_target(
        self,
        *,
        target_type: PlanTargetType,
        target_resource_id: int | None,
        stream_id: int | None,
        owner_company_id: int | None,
    ) -> tuple[int | None, int | None]:
        if target_type == PlanTargetType.STREAM:
            if stream_id is None:
                raise ValueError("Stream target requires stream_id")
            resolved_stream_id = int(stream_id)
            stream = self.session.get(Stream, resolved_stream_id)
            if stream is None:
                raise ValueError(f"Stream with id={resolved_stream_id} was not found")
            if (
                owner_company_id is not None
                and stream.company_id is not None
                and owner_company_id != stream.company_id
            ):
                raise ValueError("Stream belongs to another company")
            return None, resolved_stream_id

        if target_resource_id is None:
            raise ValueError("Target resource is required")
        resolved_target_resource_id = int(target_resource_id)
        target_resource = self.session.get(Resource, resolved_target_resource_id)
        if target_resource is None:
            raise ValueError(f"Resource with id={resolved_target_resource_id} was not found")

        expected_type = ResourceType.GROUP if target_type == PlanTargetType.GROUP else ResourceType.SUBGROUP
        if target_resource.type != expected_type:
            raise ValueError("Target resource type mismatch")
        if (
            owner_company_id is not None
            and target_resource.company_id is not None
            and owner_company_id != target_resource.company_id
        ):
            raise ValueError("Target resource belongs to another company")
        return resolved_target_resource_id, None

    def _build_requirement_name(
        self,
        *,
        plan: CurriculumPlan,
        component: PlanComponent,
        assignment: PlanComponentAssignment,
        subject: Subject,
    ) -> str:
        component_label = component.component_type.value.lower()
        full_name = f"a{assignment.id}:plan-{plan.id}:{component_label}:{subject.name.strip()}"
        return full_name[:150]

    def _assignment_exists(
        self,
        *,
        component_id: int,
        teacher_resource_id: int,
        target_type: PlanTargetType,
        target_resource_id: int | None,
        stream_id: int | None,
        exclude_assignment_id: int | None,
    ) -> bool:
        statement = select(PlanComponentAssignment.id).where(
            PlanComponentAssignment.component_id == component_id,
            PlanComponentAssignment.teacher_resource_id == teacher_resource_id,
            PlanComponentAssignment.target_type == target_type,
        )

        if target_resource_id is None:
            statement = statement.where(PlanComponentAssignment.target_resource_id.is_(None))
        else:
            statement = statement.where(PlanComponentAssignment.target_resource_id == target_resource_id)

        if stream_id is None:
            statement = statement.where(PlanComponentAssignment.stream_id.is_(None))
        else:
            statement = statement.where(PlanComponentAssignment.stream_id == stream_id)

        if exclude_assignment_id is not None:
            statement = statement.where(PlanComponentAssignment.id != exclude_assignment_id)

        return self.session.scalar(statement.limit(1)) is not None

    def _assign_requirement_resource(self, *, requirement_id: int, resource_id: int, role: str) -> None:
        self.session.add(
            RequirementResource(
                requirement_id=requirement_id,
                resource_id=resource_id,
                role=role,
            )
        )

