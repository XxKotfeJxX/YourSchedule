from app.domain.models.auth import Company, CompanyProfile, User
from app.domain.models.academic import Course, Department, Specialty, Stream
from app.domain.models.calendar import (
    CalendarPeriod,
    DayPattern,
    DayPatternItem,
    MarkType,
    TimeBlock,
    WeekPattern,
)
from app.domain.models.requirement import Requirement, RequirementResource
from app.domain.models.schedule import ScheduleEntry
from app.domain.models.resource import Resource
from app.domain.models.facility import Building, RoomBooking, RoomProfile
from app.domain.models.curriculum import (
    CurriculumPlan,
    PlanComponent,
    PlanComponentAssignment,
    Subject,
)

__all__ = [
    "Company",
    "CompanyProfile",
    "User",
    "Department",
    "Specialty",
    "Course",
    "Stream",
    "MarkType",
    "DayPattern",
    "DayPatternItem",
    "WeekPattern",
    "CalendarPeriod",
    "TimeBlock",
    "Resource",
    "Building",
    "RoomBooking",
    "RoomProfile",
    "Requirement",
    "RequirementResource",
    "ScheduleEntry",
    "Subject",
    "CurriculumPlan",
    "PlanComponent",
    "PlanComponentAssignment",
]
