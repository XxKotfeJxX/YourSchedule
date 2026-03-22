def _has_resource_conflict__impl(
    self,
    block_ids: list[int],
    required_resources: set[int],
    resource_reservations: dict[int, set[int]],
) -> bool:
    if not required_resources:
        return False
    for block_id in block_ids:
        if resource_reservations.get(block_id, set()) & required_resources:
            return True
    return False
