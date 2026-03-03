from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar


T = TypeVar("T")

STATUS_ALL = "Усі"
STATUS_ACTIVE = "Активні"
STATUS_ARCHIVED = "Архівні"

SORT_NEWEST = "Найновіші"
SORT_AZ = "А-Я"
SORT_MOST_USED = "Найуживаніші"


def filter_and_sort_items(
    items: Sequence[T],
    *,
    search: str,
    status_filter: str,
    sort_mode: str,
    get_name: Callable[[T], str],
    get_usage: Callable[[T], int],
    get_is_archived: Callable[[T], bool],
    get_id: Callable[[T], int],
) -> list[T]:
    normalized_search = search.strip().lower()

    filtered: list[T] = []
    for item in items:
        name = get_name(item).strip()
        is_archived = bool(get_is_archived(item))

        if normalized_search and normalized_search not in name.lower():
            continue
        if status_filter == STATUS_ACTIVE and is_archived:
            continue
        if status_filter == STATUS_ARCHIVED and not is_archived:
            continue
        filtered.append(item)

    if sort_mode == SORT_AZ:
        return sorted(filtered, key=lambda value: (get_name(value).strip().lower(), get_id(value)))
    if sort_mode == SORT_MOST_USED:
        return sorted(
            filtered,
            key=lambda value: (-int(get_usage(value)), get_name(value).strip().lower(), -int(get_id(value))),
        )
    return sorted(filtered, key=lambda value: -int(get_id(value)))
