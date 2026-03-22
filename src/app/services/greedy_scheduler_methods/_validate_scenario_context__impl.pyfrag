def _validate_scenario_context__impl(
    self,
    *,
    session: Session,
    calendar_period_id: int,
    scenario_id: int | None,
) -> None:
    if scenario_id is None:
        return
    schedule_repository = self.schedule_repository_cls(session=session)
    scenario = schedule_repository.get_scenario(scenario_id)
    if scenario is None:
        raise ValueError(f"ScheduleScenario with id={scenario_id} was not found")
    if int(scenario.calendar_period_id) != int(calendar_period_id):
        raise ValueError("Scenario belongs to a different calendar period")
