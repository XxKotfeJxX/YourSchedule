from __future__ import annotations

from dataclasses import dataclass

from app.ui.templates.catalog_filters import (
    SORT_AZ,
    SORT_MOST_USED,
    SORT_NEWEST,
    STATUS_ACTIVE,
    STATUS_ALL,
    STATUS_ARCHIVED,
    filter_and_sort_items,
)


@dataclass(frozen=True)
class _Item:
    id: int
    name: str
    is_archived: bool
    usage: int


def _run(items: list[_Item], *, search: str, status_filter: str, sort_mode: str) -> list[int]:
    result = filter_and_sort_items(
        items,
        search=search,
        status_filter=status_filter,
        sort_mode=sort_mode,
        get_name=lambda item: item.name,
        get_usage=lambda item: item.usage,
        get_is_archived=lambda item: item.is_archived,
        get_id=lambda item: item.id,
    )
    return [item.id for item in result]


def test_filter_by_search_and_status() -> None:
    items = [
        _Item(id=1, name="Math day", is_archived=False, usage=2),
        _Item(id=2, name="Physics day", is_archived=True, usage=9),
        _Item(id=3, name="Math week", is_archived=False, usage=4),
    ]

    assert _run(items, search="math", status_filter=STATUS_ALL, sort_mode=SORT_NEWEST) == [3, 1]
    assert _run(items, search="", status_filter=STATUS_ACTIVE, sort_mode=SORT_NEWEST) == [3, 1]
    assert _run(items, search="", status_filter=STATUS_ARCHIVED, sort_mode=SORT_NEWEST) == [2]


def test_sort_modes() -> None:
    items = [
        _Item(id=11, name="beta", is_archived=False, usage=3),
        _Item(id=3, name="alpha", is_archived=False, usage=7),
        _Item(id=20, name="gamma", is_archived=False, usage=1),
    ]

    assert _run(items, search="", status_filter=STATUS_ALL, sort_mode=SORT_NEWEST) == [20, 11, 3]
    assert _run(items, search="", status_filter=STATUS_ALL, sort_mode=SORT_AZ) == [3, 11, 20]
    assert _run(items, search="", status_filter=STATUS_ALL, sort_mode=SORT_MOST_USED) == [3, 11, 20]
