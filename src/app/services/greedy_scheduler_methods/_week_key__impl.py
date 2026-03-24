# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _week_key__impl(self, day: date) -> tuple[int, int]:
    iso_week = day.isocalendar()
    return (iso_week.year, iso_week.week)
