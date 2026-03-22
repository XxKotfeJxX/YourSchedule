def _gap_count__impl(self, orders: set[int]) -> int:
    if not orders:
        return 0
    return max(orders) - min(orders) + 1 - len(orders)
