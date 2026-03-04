import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.controllers.academic_controller import AcademicController
from app.domain.base import Base
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


def test_academic_hierarchy_crud_flow(session: Session) -> None:
    company = Company(name="Uni")
    session.add(company)
    session.commit()

    controller = AcademicController(session=session)
    department = controller.create_department(
        name="Кафедра інформатики",
        short_name="КІ",
        company_id=company.id,
    )
    specialty = controller.create_specialty(
        department_id=department.id,
        name="Комп'ютерні науки",
        code="122",
        degree_level="bachelor",
        duration_years=4,
        company_id=company.id,
    )
    course = controller.create_course(
        specialty_id=specialty.id,
        name="2 курс",
        code="CS2",
        study_year=2,
        company_id=company.id,
    )
    stream = controller.create_stream(
        course_id=course.id,
        name="КН-2024",
        admission_year=2024,
        expected_graduation_year=2028,
        study_year=2,
        company_id=company.id,
    )
    session.commit()

    assert controller.get_department(department.id) is not None
    assert controller.get_specialty(specialty.id) is not None
    assert controller.get_course(course.id) is not None
    assert controller.get_stream(stream.id) is not None

    departments = controller.list_departments(company_id=company.id)
    specialties = controller.list_specialties(company_id=company.id, department_id=department.id)
    courses = controller.list_courses(company_id=company.id, specialty_id=specialty.id)
    streams = controller.list_streams(company_id=company.id, specialty_id=specialty.id, course_id=course.id)
    assert [item.id for item in departments] == [department.id]
    assert [item.id for item in specialties] == [specialty.id]
    assert [item.id for item in courses] == [course.id]
    assert [item.id for item in streams] == [stream.id]

    updated_stream = controller.update_stream(
        stream.id,
        name="КН-2024 (оновлено)",
        study_year=3,
    )
    session.commit()
    assert updated_stream.name == "КН-2024 (оновлено)"
    assert updated_stream.study_year == 3

    pairs = controller.list_specialties_with_departments(company_id=company.id)
    assert len(pairs) == 1
    pair_specialty, pair_department = pairs[0]
    assert pair_specialty.id == specialty.id
    assert pair_department.id == department.id

    with pytest.raises(ValueError):
        controller.update_stream(
            stream.id,
            admission_year=2026,
            expected_graduation_year=2025,
        )


def test_academic_hierarchy_company_isolation(session: Session) -> None:
    company_a = Company(name="A")
    company_b = Company(name="B")
    session.add_all([company_a, company_b])
    session.commit()

    controller = AcademicController(session=session)
    dep_a = controller.create_department(name="Dept A", company_id=company_a.id)
    session.commit()

    with pytest.raises(ValueError):
        controller.create_specialty(
            department_id=dep_a.id,
            name="Spec B Wrong",
            company_id=company_b.id,
        )

    spec_a = controller.create_specialty(
        department_id=dep_a.id,
        name="Spec A",
        company_id=company_a.id,
    )
    course_a = controller.create_course(
        specialty_id=spec_a.id,
        name="Course A",
        company_id=company_a.id,
    )
    session.commit()

    with pytest.raises(ValueError):
        controller.create_course(
            specialty_id=spec_a.id,
            name="Course B Wrong",
            company_id=company_b.id,
        )

    with pytest.raises(ValueError):
        controller.create_stream(
            course_id=course_a.id,
            name="Stream B Wrong",
            company_id=company_b.id,
        )
