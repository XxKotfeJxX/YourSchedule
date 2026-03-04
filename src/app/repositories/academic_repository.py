from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.domain.models import Course, Department, Specialty, Stream

_UNSET = object()


class AcademicRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_department(
        self,
        *,
        name: str,
        short_name: str | None = None,
        company_id: int | None = None,
    ) -> Department:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Department name is required")
        department = Department(
            company_id=company_id,
            name=clean_name,
            short_name=(short_name or "").strip() or None,
            is_archived=False,
        )
        self.session.add(department)
        self.session.flush()
        return department

    def get_department(self, department_id: int) -> Department | None:
        return self.session.get(Department, department_id)

    def list_departments(
        self,
        *,
        company_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Department]:
        statement = select(Department).order_by(Department.name.asc(), Department.id.asc())
        if company_id is not None:
            statement = statement.where(Department.company_id == company_id)
        if not include_archived:
            statement = statement.where(Department.is_archived.is_(False))
        return list(self.session.scalars(statement).all())

    def update_department(
        self,
        department_id: int,
        *,
        name: str | object = _UNSET,
        short_name: str | None | object = _UNSET,
        is_archived: bool | object = _UNSET,
    ) -> Department:
        department = self.get_department(department_id)
        if department is None:
            raise ValueError(f"Department with id={department_id} was not found")
        if name is not _UNSET:
            clean_name = str(name).strip()
            if not clean_name:
                raise ValueError("Department name is required")
            department.name = clean_name
        if short_name is not _UNSET:
            department.short_name = (str(short_name).strip() if short_name is not None else "") or None
        if is_archived is not _UNSET:
            department.is_archived = bool(is_archived)
        self.session.flush()
        return department

    def create_specialty(
        self,
        *,
        department_id: int,
        name: str,
        code: str | None = None,
        degree_level: str = "BACHELOR",
        duration_years: int | None = None,
        company_id: int | None = None,
    ) -> Specialty:
        department = self.get_department(department_id)
        if department is None:
            raise ValueError(f"Department with id={department_id} was not found")
        owner_company_id = company_id if company_id is not None else department.company_id
        if department.company_id is not None and owner_company_id is not None and department.company_id != owner_company_id:
            raise ValueError("Department and specialty must belong to the same company")

        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Specialty name is required")
        specialty = Specialty(
            company_id=owner_company_id,
            department_id=department_id,
            name=clean_name,
            code=(code or "").strip() or None,
            degree_level=(degree_level or "").strip().upper() or "BACHELOR",
            duration_years=duration_years,
            is_archived=False,
        )
        self.session.add(specialty)
        self.session.flush()
        return specialty

    def get_specialty(self, specialty_id: int) -> Specialty | None:
        return self.session.get(Specialty, specialty_id)

    def list_specialties(
        self,
        *,
        company_id: int | None = None,
        department_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Specialty]:
        statement = select(Specialty).order_by(Specialty.name.asc(), Specialty.id.asc())
        if company_id is not None:
            statement = statement.where(Specialty.company_id == company_id)
        if department_id is not None:
            statement = statement.where(Specialty.department_id == department_id)
        if not include_archived:
            statement = statement.where(Specialty.is_archived.is_(False))
        return list(self.session.scalars(statement).all())

    def update_specialty(
        self,
        specialty_id: int,
        *,
        department_id: int | object = _UNSET,
        name: str | object = _UNSET,
        code: str | None | object = _UNSET,
        degree_level: str | object = _UNSET,
        duration_years: int | None | object = _UNSET,
        is_archived: bool | object = _UNSET,
    ) -> Specialty:
        specialty = self.get_specialty(specialty_id)
        if specialty is None:
            raise ValueError(f"Specialty with id={specialty_id} was not found")

        if department_id is not _UNSET:
            department = self.get_department(int(department_id))
            if department is None:
                raise ValueError(f"Department with id={department_id} was not found")
            if (
                department.company_id is not None
                and specialty.company_id is not None
                and department.company_id != specialty.company_id
            ):
                raise ValueError("Department and specialty must belong to the same company")
            specialty.department_id = int(department_id)
        if name is not _UNSET:
            clean_name = str(name).strip()
            if not clean_name:
                raise ValueError("Specialty name is required")
            specialty.name = clean_name
        if code is not _UNSET:
            specialty.code = (str(code).strip() if code is not None else "") or None
        if degree_level is not _UNSET:
            clean_level = str(degree_level).strip().upper()
            if not clean_level:
                raise ValueError("Degree level is required")
            specialty.degree_level = clean_level
        if duration_years is not _UNSET:
            specialty.duration_years = duration_years
        if is_archived is not _UNSET:
            specialty.is_archived = bool(is_archived)
        self.session.flush()
        return specialty

    def create_course(
        self,
        *,
        specialty_id: int,
        name: str,
        code: str | None = None,
        study_year: int | None = None,
        company_id: int | None = None,
    ) -> Course:
        specialty = self.get_specialty(specialty_id)
        if specialty is None:
            raise ValueError(f"Specialty with id={specialty_id} was not found")

        owner_company_id = company_id if company_id is not None else specialty.company_id
        if specialty.company_id is not None and owner_company_id is not None and specialty.company_id != owner_company_id:
            raise ValueError("Specialty and course must belong to the same company")

        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Course name is required")

        course = Course(
            company_id=owner_company_id,
            specialty_id=specialty_id,
            name=clean_name,
            code=(code or "").strip() or None,
            study_year=study_year,
            is_archived=False,
        )
        self.session.add(course)
        self.session.flush()
        return course

    def get_course(self, course_id: int) -> Course | None:
        return self.session.get(Course, course_id)

    def list_courses(
        self,
        *,
        company_id: int | None = None,
        specialty_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Course]:
        statement = select(Course).order_by(Course.name.asc(), Course.id.asc())
        if company_id is not None:
            statement = statement.where(Course.company_id == company_id)
        if specialty_id is not None:
            statement = statement.where(Course.specialty_id == specialty_id)
        if not include_archived:
            statement = statement.where(Course.is_archived.is_(False))
        return list(self.session.scalars(statement).all())

    def update_course(
        self,
        course_id: int,
        *,
        specialty_id: int | object = _UNSET,
        name: str | object = _UNSET,
        code: str | None | object = _UNSET,
        study_year: int | None | object = _UNSET,
        is_archived: bool | object = _UNSET,
    ) -> Course:
        course = self.get_course(course_id)
        if course is None:
            raise ValueError(f"Course with id={course_id} was not found")

        if specialty_id is not _UNSET:
            specialty = self.get_specialty(int(specialty_id))
            if specialty is None:
                raise ValueError(f"Specialty with id={specialty_id} was not found")
            if (
                specialty.company_id is not None
                and course.company_id is not None
                and specialty.company_id != course.company_id
            ):
                raise ValueError("Specialty and course must belong to the same company")
            course.specialty_id = int(specialty_id)
        if name is not _UNSET:
            clean_name = str(name).strip()
            if not clean_name:
                raise ValueError("Course name is required")
            course.name = clean_name
        if code is not _UNSET:
            course.code = (str(code).strip() if code is not None else "") or None
        if study_year is not _UNSET:
            course.study_year = study_year
        if is_archived is not _UNSET:
            course.is_archived = bool(is_archived)

        self.session.flush()
        return course

    def create_stream(
        self,
        *,
        specialty_id: int | None = None,
        course_id: int | None = None,
        name: str,
        admission_year: int | None = None,
        expected_graduation_year: int | None = None,
        study_year: int | None = None,
        company_id: int | None = None,
    ) -> Stream:
        course: Course | None = None
        resolved_specialty_id = specialty_id
        if course_id is not None:
            course = self.get_course(course_id)
            if course is None:
                raise ValueError(f"Course with id={course_id} was not found")
            resolved_specialty_id = course.specialty_id
            if specialty_id is not None and specialty_id != resolved_specialty_id:
                raise ValueError("Course and specialty mismatch for stream")

        if resolved_specialty_id is None:
            raise ValueError("specialty_id is required when course_id is not provided")

        specialty = self.get_specialty(resolved_specialty_id)
        if specialty is None:
            raise ValueError(f"Specialty with id={resolved_specialty_id} was not found")
        owner_company_id = company_id if company_id is not None else specialty.company_id
        if specialty.company_id is not None and owner_company_id is not None and specialty.company_id != owner_company_id:
            raise ValueError("Specialty and stream must belong to the same company")
        if course is not None and course.company_id is not None and owner_company_id is not None and course.company_id != owner_company_id:
            raise ValueError("Course and stream must belong to the same company")
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Stream name is required")
        stream = Stream(
            company_id=owner_company_id,
            specialty_id=resolved_specialty_id,
            course_id=course_id,
            name=clean_name,
            admission_year=admission_year,
            expected_graduation_year=expected_graduation_year,
            study_year=study_year,
            is_archived=False,
        )
        self.session.add(stream)
        self.session.flush()
        return stream

    def get_stream(self, stream_id: int) -> Stream | None:
        return self.session.get(Stream, stream_id)

    def list_streams(
        self,
        *,
        company_id: int | None = None,
        specialty_id: int | None = None,
        course_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Stream]:
        statement = select(Stream).order_by(Stream.name.asc(), Stream.id.asc())
        if company_id is not None:
            statement = statement.where(Stream.company_id == company_id)
        if specialty_id is not None:
            statement = statement.where(Stream.specialty_id == specialty_id)
        if course_id is not None:
            statement = statement.where(Stream.course_id == course_id)
        if not include_archived:
            statement = statement.where(Stream.is_archived.is_(False))
        return list(self.session.scalars(statement).all())

    def update_stream(
        self,
        stream_id: int,
        *,
        specialty_id: int | object = _UNSET,
        course_id: int | None | object = _UNSET,
        name: str | object = _UNSET,
        admission_year: int | None | object = _UNSET,
        expected_graduation_year: int | None | object = _UNSET,
        study_year: int | None | object = _UNSET,
        is_archived: bool | object = _UNSET,
    ) -> Stream:
        stream = self.get_stream(stream_id)
        if stream is None:
            raise ValueError(f"Stream with id={stream_id} was not found")
        if specialty_id is not _UNSET:
            specialty = self.get_specialty(int(specialty_id))
            if specialty is None:
                raise ValueError(f"Specialty with id={specialty_id} was not found")
            if (
                specialty.company_id is not None
                and stream.company_id is not None
                and specialty.company_id != stream.company_id
            ):
                raise ValueError("Specialty and stream must belong to the same company")
            stream.specialty_id = int(specialty_id)
        if course_id is not _UNSET:
            if course_id is None:
                stream.course_id = None
            else:
                course = self.get_course(int(course_id))
                if course is None:
                    raise ValueError(f"Course with id={course_id} was not found")
                if (
                    course.company_id is not None
                    and stream.company_id is not None
                    and course.company_id != stream.company_id
                ):
                    raise ValueError("Course and stream must belong to the same company")
                stream.course_id = int(course_id)
                stream.specialty_id = int(course.specialty_id)
        if name is not _UNSET:
            clean_name = str(name).strip()
            if not clean_name:
                raise ValueError("Stream name is required")
            stream.name = clean_name
        if admission_year is not _UNSET:
            stream.admission_year = admission_year
        if expected_graduation_year is not _UNSET:
            stream.expected_graduation_year = expected_graduation_year
        if study_year is not _UNSET:
            stream.study_year = study_year
        if is_archived is not _UNSET:
            stream.is_archived = bool(is_archived)
        if stream.admission_year is not None and stream.expected_graduation_year is not None:
            if stream.expected_graduation_year < stream.admission_year:
                raise ValueError("Expected graduation year cannot be earlier than admission year")
        self.session.flush()
        return stream

    def list_courses_with_specialties(
        self,
        *,
        company_id: int | None = None,
    ) -> list[tuple[Course, Specialty]]:
        statement = (
            select(Course, Specialty)
            .join(Specialty, Course.specialty_id == Specialty.id)
            .order_by(Specialty.name.asc(), Course.name.asc(), Course.id.asc())
        )
        if company_id is not None:
            statement = statement.where(
                and_(
                    Course.company_id == company_id,
                    Specialty.company_id == company_id,
                )
            )
        return list(self.session.execute(statement).all())

    def list_specialties_with_departments(
        self,
        *,
        company_id: int | None = None,
    ) -> list[tuple[Specialty, Department]]:
        statement = (
            select(Specialty, Department)
            .join(Department, Specialty.department_id == Department.id)
            .order_by(Department.name.asc(), Specialty.name.asc(), Specialty.id.asc())
        )
        if company_id is not None:
            statement = statement.where(
                and_(
                    Specialty.company_id == company_id,
                    Department.company_id == company_id,
                )
            )
        return list(self.session.execute(statement).all())
