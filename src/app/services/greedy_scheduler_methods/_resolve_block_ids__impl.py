# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _resolve_block_ids__impl(
    self,
    start_block: TimeBlock,
    blocks_count: int,
    block_by_key: dict[tuple[date, int], TimeBlock],
) -> list[int]:
    block_ids: list[int] = []
    previous_block: TimeBlock | None = None

    for offset in range(blocks_count):
        key = (start_block.date, start_block.order_in_day + offset)
        current_block = block_by_key.get(key)
        if current_block is None:
            return []

        if previous_block is not None and current_block.start_timestamp != previous_block.end_timestamp:
            return []

        block_ids.append(current_block.id)
        previous_block = current_block

    return block_ids
