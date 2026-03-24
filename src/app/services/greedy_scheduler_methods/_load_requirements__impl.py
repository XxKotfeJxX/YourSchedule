# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _load_requirements__impl(self, session: Session, company_id: int | None) -> list[Requirement]:
    statement = select(Requirement).order_by(Requirement.id.asc())
    if company_id is not None:
        statement = statement.where(Requirement.company_id == company_id)
    return list(session.scalars(statement).all())
