import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.academic_controller import AcademicController
from app.controllers.curriculum_controller import CurriculumController
from app.controllers.requirement_controller import RequirementController
from app.controllers.resource_controller import ResourceController
from app.domain.base import Base
from app.domain.enums import PlanComponentType, PlanTargetType, ResourceType
from app.domain.models import Company


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _seed_academic_scope(session: Session, company_id: int) -> dict[str, int]:
    academic = AcademicController(session=session)
    department = academic.create_department(name="CS", company_id=company_id)
    specialty = academic.create_specialty(
        department_id=department.id,
        name="Computer Science",
        company_id=company_id,
    )
    course = academic.create_course(
        specialty_id=specialty.id,
        name="Course 1",
        company_id=company_id,
    )
    stream = academic.create_stream(
        course_id=course.id,
        name="CS-2026",
        company_id=company_id,
    )
    session.flush()
    return {
        "department_id": department.id,
        "specialty_id": specialty.id,
        "course_id": course.id,
        "stream_id": stream.id,
    }


def test_curriculum_plan_component_and_assignment_sync_flow(session: Session) -> None:
    company = Company(name="Curriculum Co")
    session.add(company)
    session.flush()

    scope = _seed_academic_scope(session, company.id)
    resources = ResourceController(session=session)
    curriculum = CurriculumController(session=session)
    requirement = RequirementController(session=session)

    teacher_a = resources.create_resource(
        name="Teacher A",
        resource_type=ResourceType.TEACHER,
        company_id=company.id,
    )
    teacher_b = resources.create_resource(
        name="Teacher B",
        resource_type=ResourceType.TEACHER,
        company_id=company.id,
    )
    group_1 = resources.create_resource(
        name="CS-11",
        resource_type=ResourceType.GROUP,
        company_id=company.id,
        stream_id=scope["stream_id"],
    )
    group_2 = resources.create_resource(
        name="CS-12",
        resource_type=ResourceType.GROUP,
        company_id=company.id,
        stream_id=scope["stream_id"],
    )
    subgroup_1 = resources.create_resource(
        name="CS-11::A",
        resource_type=ResourceType.SUBGROUP,
        company_id=company.id,
        parent_group_id=group_1.id,
    )

    subject = curriculum.create_subject(
        name="Algorithms",
        code="ALG-101",
        department_id=scope["department_id"],
        company_id=company.id,
    )
    plan = curriculum.create_plan(
        name="Plan CS-1",
        company_id=company.id,
        specialty_id=scope["specialty_id"],
        course_id=scope["course_id"],
        stream_id=scope["stream_id"],
        semester=1,
    )
    component = curriculum.create_component(
        plan_id=plan.id,
        subject_id=subject.id,
        component_type=PlanComponentType.PRACTICE,
        duration_blocks=2,
        sessions_total=10,
        max_per_week=2,
    )
    assignment_stream = curriculum.create_assignment(
        component_id=component.id,
        teacher_resource_id=teacher_a.id,
        target_type=PlanTargetType.STREAM,
        stream_id=scope["stream_id"],
    )
    assignment_subgroup = curriculum.create_assignment(
        component_id=component.id,
        teacher_resource_id=teacher_b.id,
        target_type=PlanTargetType.SUBGROUP,
        target_resource_id=subgroup_1.id,
        sessions_total=6,
        max_per_week=2,
    )
    session.commit()

    synced_requirements = curriculum.sync_plan_requirements(plan.id)
    session.commit()
    assert len(synced_requirements) == 2

    assignment_stream_synced = curriculum.get_assignment(assignment_stream.id)
    assignment_subgroup_synced = curriculum.get_assignment(assignment_subgroup.id)
    assert assignment_stream_synced is not None
    assert assignment_subgroup_synced is not None
    assert assignment_stream_synced.requirement_id is not None
    assert assignment_subgroup_synced.requirement_id is not None

    stream_resources = requirement.list_requirement_resources(assignment_stream_synced.requirement_id)
    assert {(item.resource_id, item.role) for item in stream_resources} == {
        (teacher_a.id, "TEACHER"),
        (group_1.id, "GROUP"),
        (group_2.id, "GROUP"),
    }

    subgroup_resources = requirement.list_requirement_resources(assignment_subgroup_synced.requirement_id)
    assert {(item.resource_id, item.role) for item in subgroup_resources} == {
        (teacher_b.id, "TEACHER"),
        (subgroup_1.id, "SUBGROUP"),
    }


def test_curriculum_duplicate_assignment_and_scope_validation(session: Session) -> None:
    company = Company(name="Validation Co")
    session.add(company)
    session.flush()

    scope = _seed_academic_scope(session, company.id)
    resources = ResourceController(session=session)
    curriculum = CurriculumController(session=session)

    teacher = resources.create_resource(
        name="Teacher X",
        resource_type=ResourceType.TEACHER,
        company_id=company.id,
    )
    group = resources.create_resource(
        name="VAL-11",
        resource_type=ResourceType.GROUP,
        company_id=company.id,
        stream_id=scope["stream_id"],
    )
    subject = curriculum.create_subject(name="Math", company_id=company.id)
    plan = curriculum.create_plan(
        name="Validation Plan",
        company_id=company.id,
        course_id=scope["course_id"],
        stream_id=scope["stream_id"],
    )
    component = curriculum.create_component(
        plan_id=plan.id,
        subject_id=subject.id,
        component_type="LECTURE",
        duration_blocks=1,
        sessions_total=8,
        max_per_week=2,
    )
    curriculum.create_assignment(
        component_id=component.id,
        teacher_resource_id=teacher.id,
        target_type=PlanTargetType.GROUP,
        target_resource_id=group.id,
    )
    session.commit()

    with pytest.raises(ValueError):
        curriculum.create_assignment(
            component_id=component.id,
            teacher_resource_id=teacher.id,
            target_type=PlanTargetType.GROUP,
            target_resource_id=group.id,
        )

    with pytest.raises(ValueError):
        curriculum.create_plan(
            name="Bad Plan",
            company_id=company.id,
            stream_id=999999,
        )


def test_curriculum_assignment_update_and_resync(session: Session) -> None:
    company = Company(name="Rebind Co")
    session.add(company)
    session.flush()

    scope = _seed_academic_scope(session, company.id)
    resources = ResourceController(session=session)
    curriculum = CurriculumController(session=session)
    requirement = RequirementController(session=session)

    teacher_a = resources.create_resource(
        name="Teacher A",
        resource_type=ResourceType.TEACHER,
        company_id=company.id,
    )
    teacher_b = resources.create_resource(
        name="Teacher B",
        resource_type=ResourceType.TEACHER,
        company_id=company.id,
    )
    group = resources.create_resource(
        name="RB-11",
        resource_type=ResourceType.GROUP,
        company_id=company.id,
        stream_id=scope["stream_id"],
    )
    subgroup = resources.create_resource(
        name="RB-11::A",
        resource_type=ResourceType.SUBGROUP,
        company_id=company.id,
        parent_group_id=group.id,
    )

    subject = curriculum.create_subject(name="Networks", company_id=company.id)
    plan = curriculum.create_plan(
        name="Rebind Plan",
        company_id=company.id,
        stream_id=scope["stream_id"],
    )
    component = curriculum.create_component(
        plan_id=plan.id,
        subject_id=subject.id,
        component_type=PlanComponentType.LAB,
        duration_blocks=2,
        sessions_total=7,
        max_per_week=2,
    )
    assignment = curriculum.create_assignment(
        component_id=component.id,
        teacher_resource_id=teacher_a.id,
        target_type=PlanTargetType.GROUP,
        target_resource_id=group.id,
    )
    synced = curriculum.sync_assignment_requirement(assignment.id)
    session.commit()

    updated = curriculum.update_assignment(
        assignment.id,
        teacher_resource_id=teacher_b.id,
        target_type=PlanTargetType.SUBGROUP,
        target_resource_id=subgroup.id,
        sessions_total=5,
        max_per_week=1,
    )
    synced_updated = curriculum.sync_assignment_requirement(updated.id)
    session.commit()

    assert synced_updated.id == synced.id
    assert synced_updated.sessions_total == 5
    assert synced_updated.max_per_week == 1

    resources_after = requirement.list_requirement_resources(synced_updated.id)
    assert {(item.resource_id, item.role) for item in resources_after} == {
        (teacher_b.id, "TEACHER"),
        (subgroup.id, "SUBGROUP"),
    }
