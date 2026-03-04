from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.models import Course, Department, Specialty, Stream
from app.repositories.academic_repository import AcademicRepository

_UNSET = object()


class AcademicController:
    def __init__(self, session: Session) -> None:
        self.repository = AcademicRepository(session=session)

    def create_department(
        self,
        *,
        name: str,
        short_name: str | None = None,
        company_id: int | None = None,
    ) -> Department:
        return self.repository.create_department(
            name=name,
            short_name=short_name,
            company_id=company_id,
        )

    def get_department(self, department_id: int) -> Department | None:
        return self.repository.get_department(department_id)

    def list_departments(
        self,
        *,
        company_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Department]:
        return self.repository.list_departments(
            company_id=company_id,
            include_archived=include_archived,
        )

    def update_department(
        self,
        department_id: int,
        *,
        name: str | object = _UNSET,
        short_name: str | None | object = _UNSET,
        is_archived: bool | object = _UNSET,
    ) -> Department:
        kwargs: dict[str, object] = {}
        if name is not _UNSET:
            kwargs["name"] = name
        if short_name is not _UNSET:
            kwargs["short_name"] = short_name
        if is_archived is not _UNSET:
            kwargs["is_archived"] = is_archived
        return self.repository.update_department(department_id, **kwargs)

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
        return self.repository.create_specialty(
            department_id=department_id,
            name=name,
            code=code,
            degree_level=degree_level,
            duration_years=duration_years,
            company_id=company_id,
        )

    def get_specialty(self, specialty_id: int) -> Specialty | None:
        return self.repository.get_specialty(specialty_id)

    def list_specialties(
        self,
        *,
        company_id: int | None = None,
        department_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Specialty]:
        return self.repository.list_specialties(
            company_id=company_id,
            department_id=department_id,
            include_archived=include_archived,
        )

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
        kwargs: dict[str, object] = {}
        if department_id is not _UNSET:
            kwargs["department_id"] = department_id
        if name is not _UNSET:
            kwargs["name"] = name
        if code is not _UNSET:
            kwargs["code"] = code
        if degree_level is not _UNSET:
            kwargs["degree_level"] = degree_level
        if duration_years is not _UNSET:
            kwargs["duration_years"] = duration_years
        if is_archived is not _UNSET:
            kwargs["is_archived"] = is_archived
        return self.repository.update_specialty(specialty_id, **kwargs)

    def create_course(
        self,
        *,
        specialty_id: int,
        name: str,
        code: str | None = None,
        study_year: int | None = None,
        company_id: int | None = None,
    ) -> Course:
        return self.repository.create_course(
            specialty_id=specialty_id,
            name=name,
            code=code,
            study_year=study_year,
            company_id=company_id,
        )

    def get_course(self, course_id: int) -> Course | None:
        return self.repository.get_course(course_id)

    def list_courses(
        self,
        *,
        company_id: int | None = None,
        specialty_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Course]:
        return self.repository.list_courses(
            company_id=company_id,
            specialty_id=specialty_id,
            include_archived=include_archived,
        )

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
        kwargs: dict[str, object] = {}
        if specialty_id is not _UNSET:
            kwargs["specialty_id"] = specialty_id
        if name is not _UNSET:
            kwargs["name"] = name
        if code is not _UNSET:
            kwargs["code"] = code
        if study_year is not _UNSET:
            kwargs["study_year"] = study_year
        if is_archived is not _UNSET:
            kwargs["is_archived"] = is_archived
        return self.repository.update_course(course_id, **kwargs)

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
        return self.repository.create_stream(
            specialty_id=specialty_id,
            course_id=course_id,
            name=name,
            admission_year=admission_year,
            expected_graduation_year=expected_graduation_year,
            study_year=study_year,
            company_id=company_id,
        )

    def get_stream(self, stream_id: int) -> Stream | None:
        return self.repository.get_stream(stream_id)

    def list_streams(
        self,
        *,
        company_id: int | None = None,
        specialty_id: int | None = None,
        course_id: int | None = None,
        include_archived: bool = False,
    ) -> list[Stream]:
        return self.repository.list_streams(
            company_id=company_id,
            specialty_id=specialty_id,
            course_id=course_id,
            include_archived=include_archived,
        )

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
        kwargs: dict[str, object] = {}
        if specialty_id is not _UNSET:
            kwargs["specialty_id"] = specialty_id
        if course_id is not _UNSET:
            kwargs["course_id"] = course_id
        if name is not _UNSET:
            kwargs["name"] = name
        if admission_year is not _UNSET:
            kwargs["admission_year"] = admission_year
        if expected_graduation_year is not _UNSET:
            kwargs["expected_graduation_year"] = expected_graduation_year
        if study_year is not _UNSET:
            kwargs["study_year"] = study_year
        if is_archived is not _UNSET:
            kwargs["is_archived"] = is_archived
        return self.repository.update_stream(stream_id, **kwargs)

    def list_specialties_with_departments(
        self,
        *,
        company_id: int | None = None,
    ) -> list[tuple[Specialty, Department]]:
        return self.repository.list_specialties_with_departments(company_id=company_id)

    def list_courses_with_specialties(
        self,
        *,
        company_id: int | None = None,
    ) -> list[tuple[Course, Specialty]]:
        return self.repository.list_courses_with_specialties(company_id=company_id)
