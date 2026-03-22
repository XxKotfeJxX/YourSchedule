def _load_blackouts__impl(
    self,
    *,
    session: Session,
    resource_ids: set[int],
    window_start: datetime,
    window_end: datetime,
) -> list[ResourceBlackout]:
    statement = (
        select(ResourceBlackout)
        .where(
            ResourceBlackout.resource_id.in_(sorted(resource_ids)),
            ResourceBlackout.starts_at < window_end,
            ResourceBlackout.ends_at > window_start,
        )
        .order_by(ResourceBlackout.starts_at.asc(), ResourceBlackout.id.asc())
    )
    return list(session.scalars(statement).all())
