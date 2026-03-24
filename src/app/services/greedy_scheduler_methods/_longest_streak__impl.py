# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.services.greedy_scheduler import *  # noqa: F401,F403

def _longest_streak__impl(self, orders: set[int]) -> int:
    if not orders:
        return 0
    longest = 1
    current = 1
    sorted_orders = sorted(orders)
    for index in range(1, len(sorted_orders)):
        if sorted_orders[index] == sorted_orders[index - 1] + 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest
