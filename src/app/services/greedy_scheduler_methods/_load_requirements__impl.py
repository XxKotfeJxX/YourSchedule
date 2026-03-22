def _load_requirements__impl(self, session: Session, company_id: int | None) -> list[Requirement]:
    statement = select(Requirement).order_by(Requirement.id.asc())
    if company_id is not None:
        statement = statement.where(Requirement.company_id == company_id)
    return list(session.scalars(statement).all())
