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


class UserRole(str, Enum):
    COMPANY = "COMPANY"
    PERSONAL = "PERSONAL"
