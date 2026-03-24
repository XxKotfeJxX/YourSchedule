# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _load_teaching_blocks__impl(
    self,
    session: Session,
    calendar_period_id: int,
) -> list[TimeBlock]:
    statement = (
        select(TimeBlock)
        .where(
            TimeBlock.calendar_period_id == calendar_period_id,
            TimeBlock.block_kind == MarkKind.TEACHING,
        )
        .order_by(TimeBlock.date.asc(), TimeBlock.order_in_day.asc())
    )
    return list(session.scalars(statement).all())
