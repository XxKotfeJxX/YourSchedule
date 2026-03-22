def _resolve_policy__impl(
    self,
    *,
    session: Session,
    company_id: int | None,
    policy_options: SchedulerPolicyOptions | None,
) -> SchedulerPolicyOptions:
    options = self.get_policy(session=session, company_id=company_id) if policy_options is None else policy_options
    normalized = options.normalized()
    normalized.validate()
    return normalized
