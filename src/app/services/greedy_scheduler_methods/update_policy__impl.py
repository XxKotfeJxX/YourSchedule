def update_policy__impl(
    self,
    session: Session,
    company_id: int,
    options: SchedulerPolicyOptions,
) -> SchedulerPolicyOptions:
    normalized = options.normalized()
    normalized.validate()

    statement = select(SchedulerPolicy).where(SchedulerPolicy.company_id == company_id)
    policy_model = session.scalar(statement)
    if policy_model is None:
        policy_model = SchedulerPolicy(company_id=company_id)
        session.add(policy_model)

    policy_model.max_sessions_per_day = normalized.max_sessions_per_day
    policy_model.max_consecutive_blocks = normalized.max_consecutive_blocks
    policy_model.enforce_no_gaps = normalized.enforce_no_gaps
    policy_model.time_preference = normalized.time_preference
    policy_model.weight_time_preference = normalized.weight_time_preference
    policy_model.weight_compactness = normalized.weight_compactness
    policy_model.weight_building_transition = normalized.weight_building_transition
    session.flush()
    return self.get_policy(session=session, company_id=company_id)
