from enum import Enum, IntEnum


class MarkKind(str, Enum):
    TEACHING = "TEACHING"
    BREAK = "BREAK"


class Weekday(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class ResourceType(str, Enum):
    TEACHER = "TEACHER"
    ROOM = "ROOM"
    GROUP = "GROUP"
    SUBGROUP = "SUBGROUP"


class RoomType(str, Enum):
    LECTURE_HALL = "LECTURE_HALL"
    CLASSROOM = "CLASSROOM"
    LAB = "LAB"
    COMPUTER_LAB = "COMPUTER_LAB"
    TEACHERS_OFFICE = "TEACHERS_OFFICE"
    TECHNICAL = "TECHNICAL"
    OTHER = "OTHER"


class PlanComponentType(str, Enum):
    LECTURE = "LECTURE"
    PRACTICE = "PRACTICE"
    LAB = "LAB"
    OTHER = "OTHER"


class PlanTargetType(str, Enum):
    STREAM = "STREAM"
    GROUP = "GROUP"
    SUBGROUP = "SUBGROUP"


class UserRole(str, Enum):
    COMPANY = "COMPANY"
    PERSONAL = "PERSONAL"
