from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from app.ui.templates.catalog_filters import (
    SORT_AZ,
    SORT_MOST_USED,
    SORT_NEWEST,
    STATUS_ACTIVE,
    STATUS_ALL,
    STATUS_ARCHIVED,
    filter_and_sort_items,
)


MotionButtonFactory = Callable[..., object]
CardBuilder = Callable[[ttk.Frame, object], tk.Widget]
NameGetter = Callable[[object], str]
UsageGetter = Callable[[object], int]
ArchivedGetter = Callable[[object], bool]
IdGetter = Callable[[object], int]
WheelHandler = Callable[[tk.Event], str]
WheelStepHandler = Callable[[tk.Event | None], str]
LayoutChangedHandler = Callable[[], None]


class TemplateShelf(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Frame,
        *,
        title: str,
        add_button_text: str,
        empty_text: str,
        on_add,
        motion_button_factory: MotionButtonFactory,
        theme,
        item_name_getter: NameGetter,
        item_usage_getter: UsageGetter,
        item_archived_getter: ArchivedGetter,
        item_id_getter: IdGetter,
        wheel_handler: WheelHandler | None = None,
        wheel_up_handler: WheelStepHandler | None = None,
        wheel_down_handler: WheelStepHandler | None = None,
        on_layout_changed: LayoutChangedHandler | None = None,
        card_min_width: int = 250,
    ) -> None:
        super().__init__(parent, style="Card.TFrame")
        self.theme = theme
        self.card_min_width = card_min_width
        self._empty_text = empty_text
        self._motion_button_factory = motion_button_factory
        self._item_name_getter = item_name_getter
        self._item_usage_getter = item_usage_getter
        self._item_archived_getter = item_archived_getter
        self._item_id_getter = item_id_getter
        self._wheel_handler = wheel_handler
        self._wheel_up_handler = wheel_up_handler
        self._wheel_down_handler = wheel_down_handler
        self._on_layout_changed = on_layout_changed
        self._layout_notify_job: str | None = None
        self._wheel_bound_widgets: set[str] = set()
        self._items: list[object] = []
        self._card_builder: CardBuilder | None = None
        self._current_columns: int | None = None
        self._max_configured_columns = 0
        self._last_width: int = 0
        self._resize_job: str | None = None
        self._is_loading = False

        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill=tk.X, pady=(0, 10))
        title_box = ttk.Frame(header, style="Card.TFrame")
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(title_box, text=title, style="CardTitle.TLabel").pack(anchor="w")
        self._count_var = tk.StringVar(value="0")
        ttk.Label(title_box, textvariable=self._count_var, style="CardSubtle.TLabel").pack(anchor="w", pady=(2, 0))

        self._motion_button_factory(
            header,
            text=add_button_text,
            command=on_add,
            primary=True,
            width=150,
            height=40,
        ).pack(side=tk.RIGHT)

        controls = ttk.Frame(self, style="Card.TFrame")
        controls.pack(fill=tk.X, pady=(0, 10))
        controls.grid_columnconfigure(1, weight=1)

        ttk.Label(controls, text="Пошук", style="CardSubtle.TLabel").grid(row=0, column=0, sticky="w")
        self._search_var = tk.StringVar(value="")
        search_entry = ttk.Entry(controls, textvariable=self._search_var)
        search_entry.grid(row=0, column=1, sticky="ew", padx=(6, 8))

        ttk.Label(controls, text="Фільтр", style="CardSubtle.TLabel").grid(row=0, column=2, sticky="w")
        self._status_var = tk.StringVar(value=STATUS_ALL)
        status_box = ttk.Combobox(
            controls,
            textvariable=self._status_var,
            state="readonly",
            values=(STATUS_ALL, STATUS_ACTIVE, STATUS_ARCHIVED),
            width=11,
        )
        status_box.grid(row=0, column=3, sticky="w", padx=(6, 8))

        ttk.Label(controls, text="Сортування", style="CardSubtle.TLabel").grid(row=0, column=4, sticky="w")
        self._sort_var = tk.StringVar(value=SORT_NEWEST)
        sort_box = ttk.Combobox(
            controls,
            textvariable=self._sort_var,
            state="readonly",
            values=(SORT_NEWEST, SORT_AZ, SORT_MOST_USED),
            width=12,
        )
        sort_box.grid(row=0, column=5, sticky="w", padx=(6, 0))

        self._search_var.trace_add("write", lambda *_args: self._render_cards(force=True))
        self._status_var.trace_add("write", lambda *_args: self._render_cards(force=True))
        self._sort_var.trace_add("write", lambda *_args: self._render_cards(force=True))

        self.cards_host = ttk.Frame(self, style="Card.TFrame")
        self.cards_host.pack(fill=tk.X)
        self.cards_host.bind("<Configure>", self._on_cards_resize, add="+")
        self._bind_wheel_recursive(self)

    def show_loading(self) -> None:
        self._is_loading = True
        self._count_var.set("Завантаження...")
        self._render_loading_message()

    def set_items(self, *, items: list[object], card_builder: CardBuilder) -> None:
        self._is_loading = False
        self._items = list(items)
        self._card_builder = card_builder
        self._render_cards(force=True)

    def _on_cards_resize(self, _event=None) -> None:
        if self._resize_job is not None:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.after(40, self._render_cards)

    def _visible_items(self) -> list[object]:
        return filter_and_sort_items(
            self._items,
            search=self._search_var.get(),
            status_filter=self._status_var.get(),
            sort_mode=self._sort_var.get(),
            get_name=self._item_name_getter,
            get_usage=self._item_usage_getter,
            get_is_archived=self._item_archived_getter,
            get_id=self._item_id_getter,
        )

    def _render_cards(self, force: bool = False) -> None:
        self._resize_job = None
        if self._is_loading:
            self._render_loading_message()
            return

        width = self.cards_host.winfo_width()
        if width <= 1:
            self.after(40, self._render_cards)
            return

        visible_items = self._visible_items()
        total_count = len(self._items)
        visible_count = len(visible_items)
        self._count_var.set(f"{visible_count} / {total_count}" if total_count else "0")

        columns = self._calculate_columns(width=width, items_count=visible_count)
        width_changed = abs(width - self._last_width) >= 14
        if not force and not width_changed and columns == self._current_columns:
            return

        self._last_width = width
        self._current_columns = columns
        for child in self.cards_host.winfo_children():
            child.destroy()

        if not visible_items:
            text = self._empty_text if not self._items else "Немає результатів для поточного пошуку/фільтра."
            self._configure_cards_grid(columns=1)
            empty_label = ttk.Label(self.cards_host, text=text, style="CardSubtle.TLabel")
            empty_label.grid(row=0, column=0, sticky="w")
            self._bind_wheel_recursive(empty_label)
            self._notify_layout_changed()
            return

        if self._card_builder is None:
            self._notify_layout_changed()
            return

        self._configure_cards_grid(columns=columns)
        for index, item in enumerate(visible_items):
            row = index // columns
            column = index % columns
            widget = self._card_builder(self.cards_host, item)
            widget.grid(row=row, column=column, padx=7, pady=7, sticky="nsew")
            self._bind_wheel_recursive(widget)
        self._notify_layout_changed()

    def _render_loading_message(self) -> None:
        for child in self.cards_host.winfo_children():
            child.destroy()
        self._configure_cards_grid(columns=1)
        loading_label = ttk.Label(self.cards_host, text="Завантаження...", style="CardSubtle.TLabel")
        loading_label.grid(row=0, column=0, sticky="w")
        self._bind_wheel_recursive(loading_label)
        self._notify_layout_changed()

    def _calculate_columns(self, *, width: int, items_count: int) -> int:
        if items_count <= 0:
            return 1
        card_gap = 14
        max_columns = max(1, (width + card_gap) // (self.card_min_width + card_gap))
        return max(1, min(max_columns, items_count))

    def _configure_cards_grid(self, *, columns: int) -> None:
        max_columns = max(self._max_configured_columns, columns)
        for column in range(max_columns):
            weight = 1 if column < columns else 0
            self.cards_host.grid_columnconfigure(column, weight=weight, minsize=0)
        self._max_configured_columns = max_columns

    def _bind_wheel_recursive(self, widget: tk.Widget) -> None:
        if self._wheel_handler is None:
            return
        widget_key = str(widget)
        if widget_key not in self._wheel_bound_widgets:
            widget.bind("<MouseWheel>", self._wheel_handler, add="+")
            if self._wheel_up_handler is not None:
                widget.bind("<Button-4>", self._wheel_up_handler, add="+")
            if self._wheel_down_handler is not None:
                widget.bind("<Button-5>", self._wheel_down_handler, add="+")
            self._wheel_bound_widgets.add(widget_key)
        for child in widget.winfo_children():
            self._bind_wheel_recursive(child)

    def _notify_layout_changed(self) -> None:
        if self._on_layout_changed is None:
            return
        if self._layout_notify_job is not None:
            try:
                self.after_cancel(self._layout_notify_job)
            except Exception:
                pass
        self._layout_notify_job = self.after_idle(self._run_layout_changed)

    def _run_layout_changed(self) -> None:
        self._layout_notify_job = None
        if self._on_layout_changed is not None:
            self._on_layout_changed()
