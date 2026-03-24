# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _build_day_order_bounds__impl(self, *, teaching_blocks: list[TimeBlock]) -> dict[date, tuple[int, int]]:
    bounds: dict[date, tuple[int, int]] = {}
    for block in teaching_blocks:
        current = bounds.get(block.date)
        if current is None:
            bounds[block.date] = (block.order_in_day, block.order_in_day)
            continue
        bounds[block.date] = (min(current[0], block.order_in_day), max(current[1], block.order_in_day))
    return bounds
