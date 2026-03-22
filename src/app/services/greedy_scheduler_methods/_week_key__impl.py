def _week_key__impl(self, day: date) -> tuple[int, int]:
    iso_week = day.isocalendar()
    return (iso_week.year, iso_week.week)
