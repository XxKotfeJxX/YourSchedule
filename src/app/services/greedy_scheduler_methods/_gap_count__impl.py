# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _gap_count__impl(self, orders: set[int]) -> int:
    if not orders:
        return 0
    return max(orders) - min(orders) + 1 - len(orders)
