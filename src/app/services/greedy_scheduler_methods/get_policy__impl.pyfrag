def get_policy__impl(self, session: Session, company_id: int | None) -> SchedulerPolicyOptions:
    if company_id is None:
        return SchedulerPolicyOptions.defaults()
    statement = select(SchedulerPolicy).where(SchedulerPolicy.company_id == company_id)
    policy_model = session.scalar(statement)
    if policy_model is None:
        return SchedulerPolicyOptions.defaults()
    return SchedulerPolicyOptions(
        max_sessions_per_day=policy_model.max_sessions_per_day,
        max_consecutive_blocks=policy_model.max_consecutive_blocks,
        enforce_no_gaps=bool(policy_model.enforce_no_gaps),
        time_preference=policy_model.time_preference,
        weight_time_preference=policy_model.weight_time_preference,
        weight_compactness=policy_model.weight_compactness,
        weight_building_transition=policy_model.weight_building_transition,
    ).normalized()
