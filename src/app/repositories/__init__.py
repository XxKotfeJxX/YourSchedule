"""Repositories layer package."""

from app.repositories.auth_repository import AuthRepository
from app.repositories.academic_repository import AcademicRepository
from app.repositories.building_repository import BuildingRepository
from app.repositories.calendar_repository import CalendarRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.resource_repository import ResourceRepository
from app.repositories.room_repository import RoomRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.template_repository import TemplateRepository

__all__ = [
    "AuthRepository",
    "AcademicRepository",
    "BuildingRepository",
    "CalendarRepository",
    "ResourceRepository",
    "RoomRepository",
    "RequirementRepository",
    "ScheduleRepository",
    "TemplateRepository",
]
