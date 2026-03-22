def set_schedule_entry_lock__impl(
    self,
    session: Session,
    *,
    calendar_period_id: int,
    entry_id: int,
    is_locked: bool,
    scenario_id: int | None = None,
) -> ScheduleEntry | ScheduleScenarioEntry:
    schedule_repository = self.schedule_repository_cls(session=session)
    self._ensure_entry_in_period(
        session=session,
        schedule_repository=schedule_repository,
        calendar_period_id=calendar_period_id,
        entry_id=entry_id,
        scenario_id=scenario_id,
    )
    return schedule_repository.update_entry_lock(
        entry_id=entry_id,
        scenario_id=scenario_id,
        is_locked=is_locked,
    )
