"""UI layer package."""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.ui.main_window import ScheduleMainWindow

__all__ = ["ScheduleMainWindow"]


def __getattr__(name: str):
    if name == "ScheduleMainWindow":
        from app.ui.main_window import ScheduleMainWindow

        return ScheduleMainWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
