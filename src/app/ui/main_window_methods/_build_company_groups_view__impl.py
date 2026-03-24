# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.main_window import *  # noqa: F401,F403

def _build_company_groups_view__impl(self, parent: ttk.Frame, company_id: int) -> None:
    group_state: dict[str, int | str | None] = {"id": None, "name": None}
    browse_state: dict[str, int | str | None] = {
        "level": "departments",
        "department_id": None,
        "specialty_id": None,
    }
    structure_state: dict[str, object] = {
        "departments": [],
        "specialties": [],
        "courses": [],
        "streams": [],
        "department_by_id": {},
        "specialty_by_id": {},
        "course_by_id": {},
        "stream_by_id": {},
    }
    course_filter_var = tk.StringVar(value="Усі курси")
    stream_filter_var = tk.StringVar(value="Усі потоки")

    def subgroup_short_name(full_name: str) -> str:
        marker = "::"
        if marker not in full_name:
            return full_name
        return full_name.split(marker, maxsplit=1)[1]

    def parse_selected_prefixed_id(raw: str) -> int | None:
        value = raw.strip()
        if not value or "|" not in value:
            return None
        try:
            return int(value.split("|", maxsplit=1)[0].strip())
        except ValueError:
            return None

    def parse_optional_positive_int(raw: str, *, field_name: str) -> int | None:
        value = raw.strip()
        if not value:
            return None
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"Поле '{field_name}' має бути цілим числом.") from exc
        if parsed <= 0:
            raise ValueError(f"Поле '{field_name}' має бути більше нуля.")
        return parsed

    content = ttk.Frame(parent, style="Card.TFrame")
    content.pack(fill=tk.BOTH, expand=True)

    main_view = ttk.Frame(content, style="Card.TFrame")
    detail_view = ttk.Frame(content, style="Card.TFrame")
    for frame in (main_view, detail_view):
        frame.pack(fill=tk.BOTH, expand=True)
        frame.pack_forget()

    header = ttk.Frame(main_view, style="Card.TFrame")
    header.pack(fill=tk.X, pady=(0, 8))
    header_actions = ttk.Frame(header, style="Card.TFrame")
    header_actions.pack(side=tk.RIGHT)
    add_group_button = self._motion_button(
        header_actions,
        text="+ Група",
        command=lambda: open_create_group_modal(),
        primary=True,
        width=128,
    )
    add_stream_button = self._motion_button(
        header_actions,
        text="+ Потік",
        command=lambda: open_create_stream_modal(),
        primary=False,
        width=110,
    )
    add_course_button = self._motion_button(
        header_actions,
        text="+ Курс",
        command=lambda: open_create_course_modal(),
        primary=False,
        width=110,
    )
    add_specialty_button = self._motion_button(
        header_actions,
        text="+ Спеціальність",
        command=lambda: open_create_specialty_modal(),
        primary=False,
        width=150,
    )
    add_department_button = self._motion_button(
        header_actions,
        text="+ Кафедра",
        command=lambda: open_create_department_modal(),
        primary=False,
        width=128,
    )
    titles = ttk.Frame(header, style="Card.TFrame")
    titles.pack(side=tk.LEFT, fill=tk.X, expand=True)
    ttk.Label(titles, text="Групи", style="CardTitle.TLabel").pack(anchor="w")
    ttk.Label(
        titles,
        text="Ієрархія: кафедра → спеціальність → група. Усередині груп працюють фільтри за курсом і потоком.",
        style="CardSubtle.TLabel",
    ).pack(anchor="w", pady=(2, 0))

    hierarchy_nav = ttk.Frame(main_view, style="Card.TFrame")
    hierarchy_nav.pack(fill=tk.X, pady=(0, 6))
    hierarchy_back_button = HoverCircleIconButton(
        hierarchy_nav,
        text="←",
        command=lambda: None,
        diameter=44,
        canvas_bg=self.theme.SURFACE,
        icon_color=self.theme.TEXT_PRIMARY,
        hover_bg=self.theme.SECONDARY_HOVER,
        hover_icon_color=self.theme.TEXT_PRIMARY,
        pressed_bg=self.theme.SECONDARY_PRESSED,
    )
    hierarchy_back_button.pack(side=tk.LEFT)
    hierarchy_path_var = tk.StringVar(value="Кафедри")
    ttk.Label(hierarchy_nav, textvariable=hierarchy_path_var, style="CardSubtle.TLabel").pack(
        side=tk.LEFT,
        padx=(10, 0),
        pady=(6, 0),
    )

    group_filters = ttk.Frame(main_view, style="Card.TFrame")
    group_filters.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(group_filters, text="Фільтри груп:", style="CardSubtle.TLabel").pack(side=tk.LEFT, padx=(0, 12))
    ttk.Label(group_filters, text="Курс", style="Card.TLabel").pack(side=tk.LEFT)
    course_filter_box = ttk.Combobox(
        group_filters,
        textvariable=course_filter_var,
        state="readonly",
        width=26,
    )
    course_filter_box.pack(side=tk.LEFT, padx=(8, 12))
    ttk.Label(group_filters, text="Потік", style="Card.TLabel").pack(side=tk.LEFT)
    stream_filter_box = ttk.Combobox(
        group_filters,
        textvariable=stream_filter_var,
        state="readonly",
        width=26,
    )
    stream_filter_box.pack(side=tk.LEFT, padx=(8, 0))

    cards_scroll_wrap = ttk.Frame(main_view, style="Card.TFrame")
    cards_scroll_wrap.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
    cards_canvas = tk.Canvas(
        cards_scroll_wrap,
        bg=self.theme.SURFACE,
        bd=0,
        highlightthickness=0,
        relief=tk.FLAT,
    )
    cards_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    cards_scroll = ttk.Scrollbar(
        cards_scroll_wrap,
        orient=tk.VERTICAL,
        command=cards_canvas.yview,
        style="App.Vertical.TScrollbar",
    )
    cards_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    cards_canvas.configure(yscrollcommand=cards_scroll.set)

    cards_container = ttk.Frame(cards_canvas, style="Card.TFrame")
    cards_window = cards_canvas.create_window((0, 0), anchor="nw", window=cards_container)

    def _sync_cards_scroll(_event=None) -> None:
        cards_canvas.configure(scrollregion=cards_canvas.bbox("all"))
        cards_canvas.itemconfigure(cards_window, width=cards_canvas.winfo_width())

    cards_container.bind("<Configure>", _sync_cards_scroll)
    cards_canvas.bind("<Configure>", _sync_cards_scroll)

    detail_scroll_wrap = ttk.Frame(detail_view, style="Card.TFrame")
    detail_scroll_wrap.pack(fill=tk.BOTH, expand=True)
    detail_canvas = tk.Canvas(
        detail_scroll_wrap,
        bg=self.theme.SURFACE,
        bd=0,
        highlightthickness=0,
        relief=tk.FLAT,
    )
    detail_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    detail_scroll = ttk.Scrollbar(
        detail_scroll_wrap,
        orient=tk.VERTICAL,
        command=detail_canvas.yview,
        style="App.Vertical.TScrollbar",
    )
    detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    detail_canvas.configure(yscrollcommand=detail_scroll.set)
    detail_body = ttk.Frame(detail_canvas, style="Card.TFrame")
    detail_body_window = detail_canvas.create_window((0, 0), anchor="nw", window=detail_body)

    def _sync_detail_scroll(_event=None) -> None:
        detail_canvas.configure(scrollregion=detail_canvas.bbox("all"))
        detail_canvas.itemconfigure(detail_body_window, width=detail_canvas.winfo_width())

    detail_body.bind("<Configure>", _sync_detail_scroll)
    detail_canvas.bind("<Configure>", _sync_detail_scroll)

    detail_nav = ttk.Frame(detail_body, style="Card.TFrame")
    detail_nav.pack(fill=tk.X, pady=(0, 6))
    detail_title_var = tk.StringVar(value="")
    back_button = HoverCircleIconButton(
        detail_nav,
        text="←",
        command=lambda: None,
        diameter=44,
        canvas_bg=self.theme.SURFACE,
        icon_color=self.theme.TEXT_PRIMARY,
        hover_bg=self.theme.SECONDARY_HOVER,
        hover_icon_color=self.theme.TEXT_PRIMARY,
        pressed_bg=self.theme.SECONDARY_PRESSED,
    )
    back_button.pack(side=tk.LEFT)
    ttk.Label(detail_nav, textvariable=detail_title_var, style="CardTitle.TLabel").pack(side=tk.LEFT, padx=(10, 0))
    detail_actions = ttk.Frame(detail_nav, style="Card.TFrame")
    detail_actions.pack(side=tk.RIGHT)
    reassign_stream_button = self._motion_button(
        detail_actions,
        text="Змінити курс/потік",
        command=lambda: open_reassign_group_stream_modal(),
        primary=False,
        width=188,
        height=38,
    )
    reassign_stream_button.pack(side=tk.RIGHT)
    detail_meta_var = tk.StringVar(value="")
    detail_subtitle = ttk.Label(
        detail_body,
        textvariable=detail_meta_var,
        style="CardSubtle.TLabel",
    )
    detail_subtitle.pack(anchor="w", pady=(0, 10))

    participant_username_var = tk.StringVar()

    participants_panel = ttk.Frame(detail_body, style="Card.TFrame")
    participants_panel.pack(fill=tk.X, pady=(0, 12))
    ttk.Label(participants_panel, text="Учасники", style="CardTitle.TLabel").pack(anchor="w")

    participant_row = ttk.Frame(participants_panel, style="Card.TFrame")
    participant_row.pack(fill=tk.X, pady=(8, 10))
    participant_login_label = ttk.Label(participant_row, text="Логін", style="Card.TLabel")
    participant_login_label.grid(row=0, column=0, sticky="w")
    participant_row.grid_columnconfigure(0, weight=1)
    participant_input_box = ttk.Combobox(participant_row, textvariable=participant_username_var, width=26, state="normal")
    participant_input_box.grid(row=1, column=0, sticky="ew", pady=(6, 8))
    participant_add_button = self._motion_button(
        participant_row,
        text="Додати учасника",
        command=lambda: on_add_participant(),
        primary=True,
        width=180,
    )
    participant_add_button.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(6, 8))

    participants_scroll_wrap = ttk.Frame(participants_panel, style="Card.TFrame")
    participants_scroll_wrap.pack(fill=tk.X)
    participants_scroll_wrap.configure(height=250)
    participants_scroll_wrap.pack_propagate(False)
    participants_canvas = tk.Canvas(
        participants_scroll_wrap,
        bg=self.theme.SURFACE,
        bd=0,
        highlightthickness=0,
        relief=tk.FLAT,
        height=250,
    )
    participants_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
    participants_scroll = ttk.Scrollbar(
        participants_scroll_wrap,
        orient=tk.VERTICAL,
        command=participants_canvas.yview,
        style="App.Vertical.TScrollbar",
    )
    participants_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    participants_canvas.configure(yscrollcommand=participants_scroll.set)
    participants_cards_frame = ttk.Frame(participants_canvas, style="Card.TFrame")
    participants_cards_window = participants_canvas.create_window((0, 0), anchor="nw", window=participants_cards_frame)

    def _sync_participants_scroll(_event=None) -> None:
        participants_canvas.configure(scrollregion=participants_canvas.bbox("all"))
        participants_canvas.itemconfigure(participants_cards_window, width=participants_canvas.winfo_width())

    participants_cards_frame.bind("<Configure>", _sync_participants_scroll)
    participants_canvas.bind("<Configure>", _sync_participants_scroll)

    subgroups_panel = ttk.Frame(detail_body, style="Card.TFrame")
    subgroups_panel.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(subgroups_panel, text="Підгрупи", style="CardTitle.TLabel").pack(anchor="w")
    ttk.Label(
        subgroups_panel,
        text="Перетягни картку учасника в підгрупу. Щоб прибрати з підгрупи - перетягни у 'Без підгрупи'.",
        style="CardSubtle.TLabel",
    ).pack(anchor="w", pady=(2, 8))

    subgroup_name_var = tk.StringVar()
    subgroup_row = ttk.Frame(subgroups_panel, style="Card.TFrame")
    subgroup_row.pack(fill=tk.X, pady=(0, 8))
    subgroup_name_label = ttk.Label(subgroup_row, text="Нова підгрупа", style="Card.TLabel")
    subgroup_name_label.grid(row=0, column=0, sticky="w")
    subgroup_row.grid_columnconfigure(0, weight=1)
    subgroup_entry = ttk.Entry(subgroup_row, textvariable=subgroup_name_var, width=24)
    subgroup_entry.grid(row=1, column=0, sticky="ew", pady=(6, 8))
    subgroup_create_button = self._motion_button(
        subgroup_row,
        text="Створити підгрупу",
        command=lambda: on_create_subgroup(),
        primary=False,
        width=180,
    )
    subgroup_create_button.grid(row=1, column=1, sticky="w", padx=(10, 6), pady=(6, 8))
    subgroup_delete_button = self._motion_button(
        subgroup_row,
        text="Видалити підгрупу",
        command=lambda: on_delete_subgroup(),
        primary=False,
        width=180,
    )
    subgroup_delete_button.grid(row=1, column=2, sticky="w", pady=(6, 8))

    subgroup_tree_wrap = ttk.Frame(subgroups_panel, style="Card.TFrame")
    subgroup_tree_wrap.pack(fill=tk.X)
    subgroup_tree_wrap.configure(height=300)
    subgroup_tree_wrap.pack_propagate(False)
    subgroup_tree = ttk.Treeview(
        subgroup_tree_wrap,
        show="tree headings",
        height=14,
        selectmode="browse",
    )
    subgroup_tree.heading("#0", text="Підгрупи та учасники", anchor="w")
    subgroup_tree.column("#0", anchor="w", minwidth=280, width=460, stretch=True)
    subgroup_tree.tag_configure(
        "bucket",
        font=("Segoe UI", 10, "bold"),
        background=self.theme.SURFACE_ALT,
        foreground=self.theme.TEXT_PRIMARY,
    )
    subgroup_tree.tag_configure(
        "participant",
        font=("Segoe UI", 10),
        foreground=self.theme.TEXT_PRIMARY,
    )
    subgroup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    subgroup_tree_scroll = ttk.Scrollbar(
        subgroup_tree_wrap,
        orient=tk.VERTICAL,
        command=subgroup_tree.yview,
        style="App.Vertical.TScrollbar",
    )
    subgroup_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    subgroup_tree.configure(yscrollcommand=subgroup_tree_scroll.set)

    tree_subgroup_id_by_iid: dict[str, int | None] = {}
    tree_drag_state: dict[str, str | bool | None] = {"item": None, "active": False}
    current_users_by_id: dict[int, User] = {}
    current_subgroups_by_id: dict[int, object] = {}
    detail_layout_state = {"compact": False}

    def _update_detail_responsive(_event=None) -> None:
        width = detail_canvas.winfo_width()
        compact = width < 980
        if detail_layout_state["compact"] == compact:
            return
        detail_layout_state["compact"] = compact

        participant_add_button.grid_forget()
        if compact:
            participant_add_button.grid(row=2, column=0, sticky="w", pady=(0, 4))
        else:
            participant_add_button.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(6, 8))

        subgroup_create_button.grid_forget()
        subgroup_delete_button.grid_forget()
        if compact:
            subgroup_create_button.grid(row=2, column=0, sticky="w", pady=(0, 4))
            subgroup_delete_button.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(0, 4))
        else:
            subgroup_create_button.grid(row=1, column=1, sticky="w", padx=(10, 6), pady=(6, 8))
            subgroup_delete_button.grid(row=1, column=2, sticky="w", pady=(6, 8))

    def _create_smooth_wheel_handlers(get_view, set_view, *, gain: float = 0.14):
        # Keep scroll deterministic (no async inertia loop) to avoid jitter
        # while still smoothing raw wheel/touchpad input.
        state: dict[str, float] = {"velocity": 0.0}

        def _wheel_step(step_units: float) -> str:
            first, last = get_view()
            first_f = float(first)
            last_f = float(last)
            visible = max(0.0001, last_f - first_f)
            if visible >= 0.999:
                return "break"

            smoothed_units = state["velocity"] * 0.35 + max(-4.0, min(4.0, step_units)) * 0.65
            if abs(smoothed_units) < 0.01:
                smoothed_units = step_units
            state["velocity"] = smoothed_units

            max_first = max(0.0, 1.0 - visible)
            next_first = max(0.0, min(first_f + smoothed_units * visible * gain, max_first))
            if abs(next_first - first_f) < 0.00001:
                return "break"
            set_view(next_first)
            return "break"

        def _on_wheel(event: tk.Event) -> str:
            delta = float(getattr(event, "delta", 0.0))
            if delta == 0:
                return "break"
            return _wheel_step(-delta / 120.0)

        def _on_button4(_event: tk.Event) -> str:
            return _wheel_step(-1.0)

        def _on_button5(_event: tk.Event) -> str:
            return _wheel_step(1.0)

        return _on_wheel, _on_button4, _on_button5

    def _bind_wheel_recursive(widget: tk.Widget, on_wheel, on_up, on_down) -> None:
        widget.bind("<MouseWheel>", on_wheel, add="+")
        widget.bind("<Button-4>", on_up, add="+")
        widget.bind("<Button-5>", on_down, add="+")
        for child in widget.winfo_children():
            _bind_wheel_recursive(child, on_wheel, on_up, on_down)

    def _with_fallback(primary_handler, primary_view, fallback_handler):
        def _handler(event: tk.Event) -> str:
            first, last = primary_view()
            first_f = float(first)
            last_f = float(last)
            if last_f - first_f >= 0.999:
                return fallback_handler(event)
            event_num = getattr(event, "num", 0)
            delta = float(getattr(event, "delta", 0.0))
            scroll_up = bool(event_num == 4 or delta > 0)
            scroll_down = bool(event_num == 5 or delta < 0)
            if scroll_up and first_f <= 0.0001:
                return fallback_handler(event)
            if scroll_down and last_f >= 0.9999:
                return fallback_handler(event)
            return primary_handler(event)

        return _handler

    detail_canvas.bind("<Configure>", _update_detail_responsive, add="+")
    def dismiss_group_popdowns() -> None:
        self._dismiss_combobox_popdowns(parent)

    detail_wheel_raw, detail_wheel_up_raw, detail_wheel_down_raw = _create_smooth_wheel_handlers(
        detail_canvas.yview,
        detail_canvas.yview_moveto,
        gain=0.14,
    )

    def detail_wheel(event: tk.Event) -> str:
        dismiss_group_popdowns()
        return detail_wheel_raw(event)

    def detail_wheel_up(event: tk.Event) -> str:
        dismiss_group_popdowns()
        return detail_wheel_up_raw(event)

    def detail_wheel_down(event: tk.Event) -> str:
        dismiss_group_popdowns()
        return detail_wheel_down_raw(event)

    participants_wheel, participants_wheel_up, participants_wheel_down = _create_smooth_wheel_handlers(
        participants_canvas.yview,
        participants_canvas.yview_moveto,
        gain=0.13,
    )
    participants_wheel_f_raw = _with_fallback(participants_wheel, participants_canvas.yview, detail_wheel)
    participants_wheel_up_f_raw = _with_fallback(participants_wheel_up, participants_canvas.yview, detail_wheel_up)
    participants_wheel_down_f_raw = _with_fallback(participants_wheel_down, participants_canvas.yview, detail_wheel_down)

    def participants_wheel_f(event: tk.Event) -> str:
        dismiss_group_popdowns()
        return participants_wheel_f_raw(event)

    def participants_wheel_up_f(event: tk.Event) -> str:
        dismiss_group_popdowns()
        return participants_wheel_up_f_raw(event)

    def participants_wheel_down_f(event: tk.Event) -> str:
        dismiss_group_popdowns()
        return participants_wheel_down_f_raw(event)

    tree_wheel, tree_wheel_up, tree_wheel_down = _create_smooth_wheel_handlers(
        subgroup_tree.yview,
        subgroup_tree.yview_moveto,
        gain=0.14,
    )
    tree_wheel_f_raw = _with_fallback(tree_wheel, subgroup_tree.yview, detail_wheel)
    tree_wheel_up_f_raw = _with_fallback(tree_wheel_up, subgroup_tree.yview, detail_wheel_up)
    tree_wheel_down_f_raw = _with_fallback(tree_wheel_down, subgroup_tree.yview, detail_wheel_down)

    def tree_wheel_f(event: tk.Event) -> str:
        dismiss_group_popdowns()
        return tree_wheel_f_raw(event)

    def tree_wheel_up_f(event: tk.Event) -> str:
        dismiss_group_popdowns()
        return tree_wheel_up_f_raw(event)

    def tree_wheel_down_f(event: tk.Event) -> str:
        dismiss_group_popdowns()
        return tree_wheel_down_f_raw(event)

    _bind_wheel_recursive(detail_nav, detail_wheel, detail_wheel_up, detail_wheel_down)
    _bind_wheel_recursive(detail_subtitle, detail_wheel, detail_wheel_up, detail_wheel_down)
    _bind_wheel_recursive(participants_panel, participants_wheel_f, participants_wheel_up_f, participants_wheel_down_f)
    _bind_wheel_recursive(subgroups_panel, tree_wheel_f, tree_wheel_up_f, tree_wheel_down_f)
    detail_canvas.bind("<MouseWheel>", detail_wheel, add="+")
    detail_canvas.bind("<Button-4>", detail_wheel_up, add="+")
    detail_canvas.bind("<Button-5>", detail_wheel_down, add="+")

    filter_sync_state = {"busy": False}

    def selected_department_id() -> int | None:
        value = browse_state.get("department_id")
        return int(value) if isinstance(value, int) else None

    def selected_specialty_id() -> int | None:
        value = browse_state.get("specialty_id")
        return int(value) if isinstance(value, int) else None

    def selected_course_id() -> int | None:
        return parse_selected_prefixed_id(course_filter_var.get())

    def selected_stream_id() -> int | None:
        return parse_selected_prefixed_id(stream_filter_var.get())

    def compute_main_columns(width: int) -> int:
        return 4

    def compute_main_card_width(width: int, columns: int) -> int:
        spacing_per_card = 12
        usable_width = max(320, int(width) - 8)
        raw_width = (usable_width - (columns * spacing_per_card)) // max(1, columns)
        return max(140, min(420, raw_width))

    def refresh_header_actions() -> None:
        for widget in (add_group_button, add_stream_button, add_course_button, add_specialty_button, add_department_button):
            widget.pack_forget()
        level = str(browse_state["level"])
        if level == "departments":
            add_department_button.pack(side=tk.RIGHT)
        elif level == "specialties":
            add_specialty_button.pack(side=tk.RIGHT)
        else:
            add_group_button.pack(side=tk.RIGHT)
            add_stream_button.pack(side=tk.RIGHT, padx=(0, 6))
            add_course_button.pack(side=tk.RIGHT, padx=(0, 6))
    def refresh_hierarchy_nav() -> None:
        level = str(browse_state["level"])
        department = structure_state["department_by_id"].get(selected_department_id())
        specialty = structure_state["specialty_by_id"].get(selected_specialty_id())

        if level == "departments":
            hierarchy_path_var.set("Кафедри")
            hierarchy_back_button.pack_forget()
        elif level == "specialties":
            dep_name = department.name if department is not None else "Кафедра"
            hierarchy_path_var.set(f"Кафедри / {dep_name}")
            if not hierarchy_back_button.winfo_ismapped():
                hierarchy_back_button.pack(side=tk.LEFT)
        else:
            dep_name = department.name if department is not None else "Кафедра"
            spec_name = specialty.code or specialty.name if specialty is not None else "Спеціальність"
            hierarchy_path_var.set(f"Кафедри / {dep_name} / {spec_name}")
            if not hierarchy_back_button.winfo_ismapped():
                hierarchy_back_button.pack(side=tk.LEFT)

    def refresh_group_filter_options() -> None:
        specialty_id = selected_specialty_id()
        all_courses = [item for item in structure_state["courses"] if specialty_id is None or item.specialty_id == specialty_id]
        current_course = selected_course_id()
        allowed_course_ids = {item.id for item in all_courses}
        if current_course not in allowed_course_ids:
            current_course = None

        all_streams = [
            item
            for item in structure_state["streams"]
            if (specialty_id is None or item.specialty_id == specialty_id)
            and (current_course is None or item.course_id == current_course)
        ]
        current_stream = selected_stream_id()
        allowed_stream_ids = {item.id for item in all_streams}
        if current_stream not in allowed_stream_ids:
            current_stream = None

        course_values = [
            f"{item.id} | {item.code} — {item.name}" if item.code else f"{item.id} | {item.name}"
            for item in all_courses
        ]
        stream_values = [
            f"{item.id} | {item.name}{f' • набір {item.admission_year}' if item.admission_year is not None else ''}"
            for item in all_streams
        ]

        filter_sync_state["busy"] = True
        course_filter_box["values"] = ["Усі курси"] + course_values
        stream_filter_box["values"] = ["Усі потоки"] + stream_values
        if current_course is None:
            course_filter_var.set("Усі курси")
        else:
            course = structure_state["course_by_id"][current_course]
            course_filter_var.set(f"{course.id} | {course.code} — {course.name}" if course.code else f"{course.id} | {course.name}")
        if current_stream is None:
            stream_filter_var.set("Усі потоки")
        else:
            stream = structure_state["stream_by_id"][current_stream]
            year_suffix = f" • набір {stream.admission_year}" if stream.admission_year is not None else ""
            stream_filter_var.set(f"{stream.id} | {stream.name}{year_suffix}")
        filter_sync_state["busy"] = False

    def load_structure_state() -> None:
        with session_scope() as session:
            academic = AcademicController(session=session)
            departments = academic.list_departments(company_id=company_id, include_archived=False)
            specialties = academic.list_specialties(company_id=company_id, include_archived=False)
            courses = academic.list_courses(company_id=company_id, include_archived=False)
            streams = academic.list_streams(company_id=company_id, include_archived=False)

        structure_state["departments"] = departments
        structure_state["specialties"] = specialties
        structure_state["courses"] = courses
        structure_state["streams"] = streams
        structure_state["department_by_id"] = {item.id: item for item in departments}
        structure_state["specialty_by_id"] = {item.id: item for item in specialties}
        structure_state["course_by_id"] = {item.id: item for item in courses}
        structure_state["stream_by_id"] = {item.id: item for item in streams}

        if selected_department_id() not in structure_state["department_by_id"]:
            browse_state["department_id"] = None
            browse_state["specialty_id"] = None
            browse_state["level"] = "departments"
        elif selected_specialty_id() not in structure_state["specialty_by_id"]:
            browse_state["specialty_id"] = None
            browse_state["level"] = "specialties"

    def set_hierarchy_level(level: str, *, department_id: int | None = None, specialty_id: int | None = None) -> None:
        previous_level = str(browse_state["level"])
        previous_department_id = selected_department_id()
        previous_specialty_id = selected_specialty_id()
        browse_state["level"] = level
        browse_state["department_id"] = department_id
        browse_state["specialty_id"] = specialty_id
        if (
            previous_level != level
            or previous_department_id != department_id
            or previous_specialty_id != specialty_id
        ):
            cards_canvas.yview_moveto(0.0)
    def on_hierarchy_back() -> None:
        level = str(browse_state["level"])
        if level == "groups":
            department_id = selected_department_id()
            if department_id is None:
                specialty_id = selected_specialty_id()
                if specialty_id is not None:
                    specialty = structure_state["specialty_by_id"].get(specialty_id)
                    if specialty is not None:
                        department_id = specialty.department_id
            set_hierarchy_level("specialties", department_id=department_id, specialty_id=None)
        elif level == "specialties":
            set_hierarchy_level("departments", department_id=None, specialty_id=None)
        render_main_cards()

    def on_course_filter_change(_event=None) -> None:
        if filter_sync_state["busy"] or str(browse_state["level"]) != "groups":
            return
        refresh_group_filter_options()
        render_main_cards()

    def on_stream_filter_change(_event=None) -> None:
        if filter_sync_state["busy"] or str(browse_state["level"]) != "groups":
            return
        render_main_cards()

    def open_create_department_modal() -> None:
        modal = tk.Toplevel(self.root)
        modal.title("Нова кафедра")
        modal.transient(self.root)
        modal.resizable(False, False)
        modal.grab_set()

        shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        ttk.Label(shell, text="Створення кафедри", style="CardTitle.TLabel").pack(anchor="w")

        name_var = tk.StringVar(value="")
        short_name_var = tk.StringVar(value="")

        ttk.Label(shell, text="Назва", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
        name_entry = ttk.Entry(shell, textvariable=name_var, width=44)
        name_entry.pack(fill=tk.X, pady=(6, 8))
        ttk.Label(shell, text="Скорочення (опціонально)", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=short_name_var, width=24).pack(fill=tk.X, pady=(6, 12))

        footer = ttk.Frame(shell, style="Card.TFrame")
        footer.pack(fill=tk.X)

        def on_submit_department() -> None:
            clean_name = name_var.get().strip()
            if not clean_name:
                messagebox.showerror("Некоректні дані", "Назва кафедри обов'язкова.", parent=modal)
                return
            try:
                with session_scope() as session:
                    created = AcademicController(session=session).create_department(
                        name=clean_name,
                        short_name=short_name_var.get().strip() or None,
                        company_id=company_id,
                    )
            except IntegrityError:
                messagebox.showerror("Не вдалося створити кафедру", "Кафедра з такою назвою або скороченням вже існує.", parent=modal)
                return
            except Exception as exc:
                messagebox.showerror("Не вдалося створити кафедру", str(exc), parent=modal)
                return

            modal.destroy()
            load_structure_state()
            set_hierarchy_level("specialties", department_id=created.id, specialty_id=None)
            render_main_cards()

        self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
        self._motion_button(footer, text="Створити", command=on_submit_department, primary=True, width=130).pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )
        name_entry.focus_set()

    def open_create_specialty_modal() -> None:
        with session_scope() as session:
            departments = AcademicController(session=session).list_departments(company_id=company_id, include_archived=False)
        if not departments:
            messagebox.showerror("Спеціальність", "Спочатку створіть кафедру.", parent=self.root)
            return

        modal = tk.Toplevel(self.root)
        modal.title("Нова спеціальність")
        modal.transient(self.root)
        modal.resizable(False, False)
        modal.grab_set()

        shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        ttk.Label(shell, text="Створення спеціальності", style="CardTitle.TLabel").pack(anchor="w")

        department_values = [
            f"{item.id} | {item.short_name} — {item.name}" if item.short_name else f"{item.id} | {item.name}"
            for item in departments
        ]
        department_var = tk.StringVar(value=department_values[0])
        current_department_id = selected_department_id()
        if current_department_id is not None:
            for value in department_values:
                if value.startswith(f"{current_department_id} |"):
                    department_var.set(value)
                    break
        name_var = tk.StringVar(value="")
        code_var = tk.StringVar(value="")
        duration_var = tk.StringVar(value="")
        degree_var = tk.StringVar(value="Бакалавр")
        degree_code_by_label = {
            "Бакалавр": "BACHELOR",
            "Магістр": "MASTER",
            "Доктор": "PHD",
            "Інше": "OTHER",
        }

        ttk.Label(shell, text="Кафедра", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Combobox(shell, textvariable=department_var, values=department_values, state="readonly", width=46).pack(
            fill=tk.X,
            pady=(6, 8),
        )
        ttk.Label(shell, text="Назва", style="Card.TLabel").pack(anchor="w")
        name_entry = ttk.Entry(shell, textvariable=name_var, width=46)
        name_entry.pack(fill=tk.X, pady=(6, 8))
        ttk.Label(shell, text="Код (опціонально)", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=code_var, width=26).pack(fill=tk.X, pady=(6, 8))
        ttk.Label(shell, text="Рівень", style="Card.TLabel").pack(anchor="w")
        ttk.Combobox(shell, textvariable=degree_var, values=list(degree_code_by_label.keys()), state="readonly", width=18).pack(
            fill=tk.X,
            pady=(6, 8),
        )
        ttk.Label(shell, text="Тривалість (років, опціонально)", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=duration_var, width=12).pack(fill=tk.X, pady=(6, 12))

        footer = ttk.Frame(shell, style="Card.TFrame")
        footer.pack(fill=tk.X)

        def on_submit_specialty() -> None:
            specialty_name = name_var.get().strip()
            if not specialty_name:
                messagebox.showerror("Некоректні дані", "Назва спеціальності обов'язкова.", parent=modal)
                return
            department_id = parse_selected_prefixed_id(department_var.get())
            if department_id is None:
                messagebox.showerror("Некоректні дані", "Оберіть кафедру зі списку.", parent=modal)
                return
            try:
                duration_years = parse_optional_positive_int(duration_var.get(), field_name="Тривалість")
                with session_scope() as session:
                    created = AcademicController(session=session).create_specialty(
                        department_id=department_id,
                        name=specialty_name,
                        code=code_var.get().strip() or None,
                        degree_level=degree_code_by_label[degree_var.get()],
                        duration_years=duration_years,
                        company_id=company_id,
                    )
            except IntegrityError:
                messagebox.showerror("Не вдалося створити спеціальність", "Спеціальність з такою назвою або кодом вже існує.", parent=modal)
                return
            except Exception as exc:
                messagebox.showerror("Не вдалося створити спеціальність", str(exc), parent=modal)
                return

            modal.destroy()
            load_structure_state()
            set_hierarchy_level("groups", department_id=department_id, specialty_id=created.id)
            course_filter_var.set("Усі курси")
            stream_filter_var.set("Усі потоки")
            render_main_cards()

        self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
        self._motion_button(footer, text="Створити", command=on_submit_specialty, primary=True, width=130).pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )
        name_entry.focus_set()

    def open_create_course_modal() -> None:
        with session_scope() as session:
            specialties_with_departments = AcademicController(session=session).list_specialties_with_departments(company_id=company_id)
        if not specialties_with_departments:
            messagebox.showerror("Курс", "Спочатку створіть спеціальність.", parent=self.root)
            return

        modal = tk.Toplevel(self.root)
        modal.title("Новий курс")
        modal.transient(self.root)
        modal.resizable(False, False)
        modal.grab_set()

        shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        ttk.Label(shell, text="Створення курсу", style="CardTitle.TLabel").pack(anchor="w")

        specialty_values = []
        for specialty, department in specialties_with_departments:
            dep_label = department.short_name or department.name
            specialty_values.append(f"{specialty.id} | {specialty.name} ({dep_label})")
        specialty_var = tk.StringVar(value=specialty_values[0])
        current_specialty_id = selected_specialty_id()
        if current_specialty_id is not None:
            for value in specialty_values:
                if value.startswith(f"{current_specialty_id} |"):
                    specialty_var.set(value)
                    break
        name_var = tk.StringVar(value="")
        code_var = tk.StringVar(value="")
        study_year_var = tk.StringVar(value="")

        ttk.Label(shell, text="Спеціальність", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Combobox(shell, textvariable=specialty_var, values=specialty_values, state="readonly", width=48).pack(
            fill=tk.X,
            pady=(6, 8),
        )
        ttk.Label(shell, text="Назва курсу", style="Card.TLabel").pack(anchor="w")
        name_entry = ttk.Entry(shell, textvariable=name_var, width=38)
        name_entry.pack(fill=tk.X, pady=(6, 8))
        ttk.Label(shell, text="Код (опціонально)", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=code_var, width=26).pack(fill=tk.X, pady=(6, 8))
        ttk.Label(shell, text="Номер курсу (опціонально)", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=study_year_var, width=12).pack(fill=tk.X, pady=(6, 12))

        footer = ttk.Frame(shell, style="Card.TFrame")
        footer.pack(fill=tk.X)

        def on_submit_course() -> None:
            course_name = name_var.get().strip()
            if not course_name:
                messagebox.showerror("Некоректні дані", "Назва курсу обов'язкова.", parent=modal)
                return
            specialty_id = parse_selected_prefixed_id(specialty_var.get())
            if specialty_id is None:
                messagebox.showerror("Некоректні дані", "Оберіть спеціальність зі списку.", parent=modal)
                return
            try:
                study_year = parse_optional_positive_int(study_year_var.get(), field_name="Номер курсу")
                with session_scope() as session:
                    created = AcademicController(session=session).create_course(
                        specialty_id=specialty_id,
                        name=course_name,
                        code=code_var.get().strip() or None,
                        study_year=study_year,
                        company_id=company_id,
                    )
            except IntegrityError:
                messagebox.showerror("Не вдалося створити курс", "Курс із такою назвою або кодом уже існує.", parent=modal)
                return
            except Exception as exc:
                messagebox.showerror("Не вдалося створити курс", str(exc), parent=modal)
                return

            modal.destroy()
            load_structure_state()
            specialty = structure_state["specialty_by_id"].get(created.specialty_id)
            department = structure_state["department_by_id"].get(specialty.department_id) if specialty is not None else None
            set_hierarchy_level(
                "groups",
                department_id=department.id if department is not None else selected_department_id(),
                specialty_id=created.specialty_id,
            )
            course_filter_var.set(f"{created.id} | {created.code} — {created.name}" if created.code else f"{created.id} | {created.name}")
            stream_filter_var.set("Усі потоки")
            render_main_cards()

        self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
        self._motion_button(footer, text="Створити", command=on_submit_course, primary=True, width=130).pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )
        name_entry.focus_set()

    def open_create_stream_modal() -> None:
        with session_scope() as session:
            academic_controller = AcademicController(session=session)
            courses = academic_controller.list_courses(
                company_id=company_id,
                specialty_id=selected_specialty_id(),
                include_archived=False,
            )
            specialties = academic_controller.list_specialties(company_id=company_id, include_archived=True)
            departments = academic_controller.list_departments(company_id=company_id, include_archived=True)
        if not courses:
            messagebox.showerror("Потік", "Спочатку створіть курс (спеціальність → курс).", parent=self.root)
            return

        modal = tk.Toplevel(self.root)
        modal.title("Новий потік")
        modal.transient(self.root)
        modal.resizable(False, False)
        modal.grab_set()

        shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        ttk.Label(shell, text="Створення потоку", style="CardTitle.TLabel").pack(anchor="w")

        specialty_by_id = {item.id: item for item in specialties}
        department_by_id = {item.id: item for item in departments}
        course_values = []
        for course in courses:
            specialty = specialty_by_id.get(course.specialty_id)
            department = department_by_id.get(specialty.department_id) if specialty is not None else None
            dep_label = (department.short_name or department.name) if department is not None else "Кафедра?"
            spec_label = (specialty.code or specialty.name) if specialty is not None else "Спеціальність?"
            year_label = f" • {course.study_year} курс" if course.study_year is not None else ""
            course_values.append(f"{course.id} | {course.name} ({dep_label} / {spec_label}{year_label})")
        course_var = tk.StringVar(value=course_values[0])
        name_var = tk.StringVar(value="")
        admission_year_var = tk.StringVar(value="")
        graduation_year_var = tk.StringVar(value="")
        study_year_var = tk.StringVar(value="")

        ttk.Label(shell, text="Курс", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Combobox(shell, textvariable=course_var, values=course_values, state="readonly", width=58).pack(
            fill=tk.X,
            pady=(6, 8),
        )
        ttk.Label(shell, text="Назва потоку", style="Card.TLabel").pack(anchor="w")
        name_entry = ttk.Entry(shell, textvariable=name_var, width=36)
        name_entry.pack(fill=tk.X, pady=(6, 8))
        ttk.Label(shell, text="Рік набору (опціонально)", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=admission_year_var, width=12).pack(fill=tk.X, pady=(6, 8))
        ttk.Label(shell, text="Очікуваний рік випуску (опціонально)", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=graduation_year_var, width=12).pack(fill=tk.X, pady=(6, 8))
        ttk.Label(shell, text="Поточний курс (опціонально)", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=study_year_var, width=12).pack(fill=tk.X, pady=(6, 12))

        footer = ttk.Frame(shell, style="Card.TFrame")
        footer.pack(fill=tk.X)

        def on_submit_stream() -> None:
            stream_name = name_var.get().strip()
            if not stream_name:
                messagebox.showerror("Некоректні дані", "Назва потоку обов'язкова.", parent=modal)
                return
            course_id = parse_selected_prefixed_id(course_var.get())
            if course_id is None:
                messagebox.showerror("Некоректні дані", "Оберіть курс зі списку.", parent=modal)
                return
            try:
                admission_year = parse_optional_positive_int(admission_year_var.get(), field_name="Рік набору")
                graduation_year = parse_optional_positive_int(graduation_year_var.get(), field_name="Рік випуску")
                study_year = parse_optional_positive_int(study_year_var.get(), field_name="Поточний курс")
                with session_scope() as session:
                    created = AcademicController(session=session).create_stream(
                        course_id=course_id,
                        name=stream_name,
                        admission_year=admission_year,
                        expected_graduation_year=graduation_year,
                        study_year=study_year,
                        company_id=company_id,
                    )
            except IntegrityError:
                messagebox.showerror("Не вдалося створити потік", "Потік з такою назвою вже існує для цього курсу.", parent=modal)
                return
            except Exception as exc:
                messagebox.showerror("Не вдалося створити потік", str(exc), parent=modal)
                return

            modal.destroy()
            load_structure_state()
            stream_filter_var.set(f"{created.id} | {created.name}")
            render_main_cards()

        self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
        self._motion_button(footer, text="Створити", command=on_submit_stream, primary=True, width=130).pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )
        name_entry.focus_set()

    def open_main_view() -> None:
        group_state["id"] = None
        group_state["name"] = None
        detail_view.pack_forget()
        main_view.pack(fill=tk.BOTH, expand=True)
        render_main_cards()

    def open_group_view(group_id: int, group_name: str) -> None:
        group_state["id"] = group_id
        group_state["name"] = group_name
        detail_title_var.set(group_name)
        main_view.pack_forget()
        detail_view.pack(fill=tk.BOTH, expand=True)
        load_group_detail()

    def delete_group(group_id: int, group_name: str) -> None:
        if not messagebox.askyesno("Підтвердження", f"Видалити групу '{group_name}' разом із підгрупами?"):
            return
        try:
            with session_scope() as session:
                auth_controller = AuthController(session=session)
                resource_controller = ResourceController(session=session)
                subgroups = resource_controller.list_subgroups(group_id=group_id, company_id=company_id)
                subgroup_ids = [item.id for item in subgroups]
                users = auth_controller.list_group_users(
                    company_id=company_id,
                    group_id=group_id,
                    subgroup_ids=subgroup_ids,
                )
                for user in users:
                    auth_controller.update_user_membership(user.id, resource_id=None, subgroup_id=None)
                deleted = resource_controller.delete_group_with_subgroups(group_id)
                if not deleted:
                    raise ValueError("Групу не знайдено.")
        except Exception as exc:
            messagebox.showerror("Не вдалося видалити групу", str(exc))
            return
        if group_state["id"] == group_id:
            open_main_view()
        else:
            render_main_cards()

    cards_layout_state = {"columns": 1, "card_width": 260}

    def refresh_cards_layout() -> bool:
        viewport_width = cards_canvas.winfo_width()
        if viewport_width <= 1:
            viewport_width = cards_scroll_wrap.winfo_width()
        if viewport_width <= 1:
            viewport_width = max(1, main_view.winfo_width() - 24)
        columns = compute_main_columns(viewport_width)
        card_width = compute_main_card_width(viewport_width, columns)
        if cards_layout_state["columns"] == columns and cards_layout_state["card_width"] == card_width:
            return False
        cards_layout_state["columns"] = columns
        cards_layout_state["card_width"] = card_width
        return True

    def clear_cards_container() -> None:
        for child in cards_container.winfo_children():
            child.destroy()

    def apply_card_grid_columns(columns: int) -> None:
        for col in range(4):
            cards_container.grid_columnconfigure(col, weight=1 if col < columns else 0, uniform="group-card-col")

    def card_wrap_width() -> int:
        return max(160, int(cards_layout_state["card_width"]) - 34)

    def render_empty_main(text: str) -> None:
        clear_cards_container()
        empty = ttk.Frame(cards_container, style="Card.TFrame")
        empty.grid(row=0, column=0, sticky="w", padx=8, pady=8)
        ttk.Label(
            empty,
            text=text,
            style="CardSubtle.TLabel",
            wraplength=max(260, cards_canvas.winfo_width() - 36),
            justify=tk.LEFT,
        ).pack(anchor="w")

    def render_department_cards() -> None:
        departments = sorted(structure_state["departments"], key=lambda item: (item.name.lower(), item.id))
        if not departments:
            render_empty_main("Поки що немає кафедр. Створи першу кафедру.")
            return

        specialties = structure_state["specialties"]
        courses = structure_state["courses"]
        streams = structure_state["streams"]
        dep_id_by_spec_id = {item.id: item.department_id for item in specialties}
        spec_id_by_course_id = {item.id: item.specialty_id for item in courses}
        course_id_by_stream_id = {item.id: item.course_id for item in streams}

        specialty_count_by_dep: dict[int, int] = {}
        course_count_by_dep: dict[int, int] = {}
        stream_count_by_dep: dict[int, int] = {}
        for specialty in specialties:
            specialty_count_by_dep[specialty.department_id] = specialty_count_by_dep.get(specialty.department_id, 0) + 1
        for course in courses:
            dep_id = dep_id_by_spec_id.get(course.specialty_id)
            if dep_id is None:
                continue
            course_count_by_dep[dep_id] = course_count_by_dep.get(dep_id, 0) + 1
        for stream in streams:
            if stream.course_id is None:
                continue
            spec_id = spec_id_by_course_id.get(stream.course_id)
            dep_id = dep_id_by_spec_id.get(spec_id) if spec_id is not None else None
            if dep_id is None:
                continue
            stream_count_by_dep[dep_id] = stream_count_by_dep.get(dep_id, 0) + 1

        clear_cards_container()
        columns = cards_layout_state["columns"]
        card_width = cards_layout_state["card_width"]
        wrap = card_wrap_width()
        apply_card_grid_columns(columns)
        for index, department in enumerate(departments):
            row = index // columns
            column = index % columns
            card = RoundedMotionCard(
                cards_container,
                bg_color=self.theme.SURFACE,
                card_color=self.theme.SURFACE_ALT,
                shadow_color=self.theme.SHADOW_SOFT,
                radius=16,
                padding=4,
                shadow_offset=4,
                motion_enabled=True,
                width=card_width,
                height=188,
            )
            card.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
            title = ttk.Label(
                card.content,
                text=department.name,
                style="CardAltTitle.TLabel",
                wraplength=wrap,
                justify=tk.LEFT,
            )
            title.pack(anchor="w", pady=(4, 2))
            subtitle = ttk.Label(
                card.content,
                text=(
                    f"Спеціальностей: {specialty_count_by_dep.get(department.id, 0)} | "
                    f"Курсів: {course_count_by_dep.get(department.id, 0)} | "
                    f"Потоків: {stream_count_by_dep.get(department.id, 0)}"
                ),
                style="CardAltSubtle.TLabel",
                wraplength=wrap,
                justify=tk.LEFT,
            )
            subtitle.pack(anchor="w")
            short_name = department.short_name or "Без скорочення"
            hint = ttk.Label(
                card.content,
                text=f"Скорочення: {short_name}",
                style="CardAltSubtle.TLabel",
                wraplength=wrap,
                justify=tk.LEFT,
            )
            hint.pack(anchor="w", pady=(3, 0))

            def on_card_resize(event: tk.Event, labels: tuple[ttk.Label, ...] = (title, subtitle, hint)) -> None:
                line_wrap = max(120, event.width - 24)
                for label in labels:
                    label.configure(wraplength=line_wrap)

            card.content.bind("<Configure>", on_card_resize, add="+")
            for widget in (card, card.canvas, card.content, title, subtitle, hint):
                widget.bind(
                    "<Button-1>",
                    lambda _e, dep_id=department.id: (
                        set_hierarchy_level("specialties", department_id=dep_id, specialty_id=None),
                        render_main_cards(),
                    ),
                )

    def render_specialty_cards() -> None:
        department_id = selected_department_id()
        if department_id is None:
            set_hierarchy_level("departments", department_id=None, specialty_id=None)
            render_main_cards()
            return
        specialties = [
            item
            for item in structure_state["specialties"]
            if item.department_id == department_id
        ]
        specialties.sort(key=lambda item: (item.name.lower(), item.id))
        if not specialties:
            render_empty_main("У цій кафедрі ще немає спеціальностей.")
            return

        courses = structure_state["courses"]
        streams = structure_state["streams"]
        course_count_by_spec: dict[int, int] = {}
        stream_count_by_spec: dict[int, int] = {}
        for course in courses:
            course_count_by_spec[course.specialty_id] = course_count_by_spec.get(course.specialty_id, 0) + 1
        for stream in streams:
            if stream.course_id is None:
                continue
            course = structure_state["course_by_id"].get(stream.course_id)
            if course is None:
                continue
            stream_count_by_spec[course.specialty_id] = stream_count_by_spec.get(course.specialty_id, 0) + 1

        clear_cards_container()
        columns = cards_layout_state["columns"]
        card_width = cards_layout_state["card_width"]
        wrap = card_wrap_width()
        apply_card_grid_columns(columns)
        for index, specialty in enumerate(specialties):
            row = index // columns
            column = index % columns
            card = RoundedMotionCard(
                cards_container,
                bg_color=self.theme.SURFACE,
                card_color=self.theme.SURFACE_ALT,
                shadow_color=self.theme.SHADOW_SOFT,
                radius=16,
                padding=4,
                shadow_offset=4,
                motion_enabled=True,
                width=card_width,
                height=180,
            )
            card.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
            title_text = f"{specialty.code} • {specialty.name}" if specialty.code else specialty.name
            title = ttk.Label(
                card.content,
                text=title_text,
                style="CardAltTitle.TLabel",
                wraplength=wrap,
                justify=tk.LEFT,
            )
            title.pack(anchor="w", pady=(4, 2))
            stats = ttk.Label(
                card.content,
                text=f"Курсів: {course_count_by_spec.get(specialty.id, 0)} • Потоків: {stream_count_by_spec.get(specialty.id, 0)}",
                style="CardAltSubtle.TLabel",
                wraplength=wrap,
                justify=tk.LEFT,
            )
            stats.pack(anchor="w")
            degree = specialty.degree_level or "OTHER"
            detail = ttk.Label(
                card.content,
                text=f"Рівень: {degree}",
                style="CardAltSubtle.TLabel",
                wraplength=wrap,
                justify=tk.LEFT,
            )
            detail.pack(anchor="w", pady=(3, 0))

            def on_card_resize(event: tk.Event, labels: tuple[ttk.Label, ...] = (title, stats, detail)) -> None:
                line_wrap = max(120, event.width - 24)
                for label in labels:
                    label.configure(wraplength=line_wrap)

            card.content.bind("<Configure>", on_card_resize, add="+")
            for widget in (card, card.canvas, card.content, title, stats, detail):
                widget.bind(
                    "<Button-1>",
                    lambda _e, spec_id=specialty.id: (
                        set_hierarchy_level("groups", department_id=department_id, specialty_id=spec_id),
                        course_filter_var.set("Усі курси"),
                        stream_filter_var.set("Усі потоки"),
                        render_main_cards(),
                    ),
                )

    def load_group_cards_data() -> list[tuple[int, str, int, str]]:
        specialty_id = selected_specialty_id()
        if specialty_id is None:
            return []
        course_id_filter = selected_course_id()
        stream_id_filter = selected_stream_id()

        all_streams = [item for item in structure_state["streams"] if item.specialty_id == specialty_id]
        if course_id_filter is not None:
            all_streams = [item for item in all_streams if item.course_id == course_id_filter]
        allowed_stream_ids = {item.id for item in all_streams}
        if stream_id_filter is not None:
            allowed_stream_ids = {stream_id_filter} if stream_id_filter in allowed_stream_ids else set()

        with session_scope() as session:
            auth_controller = AuthController(session=session)
            resource_controller = ResourceController(session=session)
            groups = resource_controller.list_resources(
                resource_type=ResourceType.GROUP,
                company_id=company_id,
            )
            groups = [item for item in groups if item.stream_id in allowed_stream_ids]

            result: list[tuple[int, str, int, str]] = []
            for group in groups:
                subgroups = resource_controller.list_subgroups(group_id=group.id, company_id=company_id)
                users = auth_controller.list_group_users(
                    company_id=company_id,
                    group_id=group.id,
                    subgroup_ids=[item.id for item in subgroups],
                )
                stream_label = "Без потоку"
                stream = structure_state["stream_by_id"].get(group.stream_id)
                if stream is not None:
                    course = structure_state["course_by_id"].get(stream.course_id) if stream.course_id is not None else None
                    course_name = course.code or course.name if course is not None else "Курс?"
                    stream_label = f"{course_name} • {stream.name}"
                result.append((group.id, group.name, len(users), stream_label))
        result.sort(key=lambda item: (item[1].lower(), item[0]))
        return result

    def render_group_cards() -> None:
        try:
            groups = load_group_cards_data()
        except Exception as exc:
            messagebox.showerror("Помилка завантаження груп", str(exc))
            return

        if not groups:
            render_empty_main("У цій спеціальності ще немає груп за обраними фільтрами.")
            return

        def on_card_context(event: tk.Event, group_id: int, group_name: str) -> None:
            menu = tk.Menu(
                self.root,
                tearoff=0,
                bg=self.theme.SURFACE,
                fg=self.theme.TEXT_PRIMARY,
                activebackground=self.theme.DANGER_HOVER,
                activeforeground=self.theme.TEXT_LIGHT,
                bd=0,
                borderwidth=0,
                relief=tk.FLAT,
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
            )
            menu.add_command(
                label="Видалити",
                command=lambda: delete_group(group_id, group_name),
                foreground=self.theme.DANGER,
                activebackground=self.theme.DANGER_HOVER,
                activeforeground=self.theme.TEXT_LIGHT,
            )
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        clear_cards_container()
        columns = cards_layout_state["columns"]
        card_width = cards_layout_state["card_width"]
        wrap = card_wrap_width()
        apply_card_grid_columns(columns)
        for index, (group_id, group_name, user_count, stream_label) in enumerate(groups):
            row = index // columns
            column = index % columns
            card = RoundedMotionCard(
                cards_container,
                bg_color=self.theme.SURFACE,
                card_color=self.theme.SURFACE_ALT,
                shadow_color=self.theme.SHADOW_SOFT,
                radius=16,
                padding=4,
                shadow_offset=4,
                motion_enabled=True,
                width=card_width,
                height=176,
            )
            card.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
            title = ttk.Label(
                card.content,
                text=group_name,
                style="CardAltTitle.TLabel",
                wraplength=wrap,
                justify=tk.LEFT,
            )
            title.pack(anchor="w", pady=(4, 2))
            meta = ttk.Label(
                card.content,
                text=stream_label,
                style="CardAltSubtle.TLabel",
                wraplength=wrap,
                justify=tk.LEFT,
            )
            meta.pack(anchor="w")
            count = ttk.Label(
                card.content,
                text=f"Учасників: {user_count}",
                style="CardAltSubtle.TLabel",
                wraplength=wrap,
                justify=tk.LEFT,
            )
            count.pack(anchor="w", pady=(2, 0))

            def on_card_resize(event: tk.Event, labels: tuple[ttk.Label, ...] = (title, meta, count)) -> None:
                line_wrap = max(120, event.width - 24)
                for label in labels:
                    label.configure(wraplength=line_wrap)

            card.content.bind("<Configure>", on_card_resize, add="+")
            for widget in (card, card.canvas, card.content, title, meta, count):
                widget.bind("<Button-1>", lambda _e, gid=group_id, gname=group_name: open_group_view(gid, gname))
                widget.bind("<Button-3>", lambda e, gid=group_id, gname=group_name: on_card_context(e, gid, gname))

    def render_main_cards(_event=None, *, reload_structure: bool = True) -> None:
        if reload_structure:
            load_structure_state()
        refresh_cards_layout()
        refresh_header_actions()
        refresh_hierarchy_nav()

        level = str(browse_state["level"])
        if level == "groups":
            group_filters.pack(fill=tk.X, pady=(0, 8))
            refresh_group_filter_options()
            render_group_cards()
        else:
            group_filters.pack_forget()
            if level == "specialties":
                render_specialty_cards()
            else:
                render_department_cards()
        _sync_cards_scroll()

    def on_cards_resize(_event=None) -> None:
        _sync_cards_scroll()
        if not refresh_cards_layout():
            return
        render_main_cards(reload_structure=False)

    def render_participant_cards(users: list[User]) -> None:
        for child in participants_cards_frame.winfo_children():
            child.destroy()

        if not users:
            empty_label = ttk.Label(
                participants_cards_frame,
                text="У групі поки немає учасників.",
                style="CardSubtle.TLabel",
            )
            empty_label.pack(anchor="w", pady=(2, 0))
            _bind_wheel_recursive(
                empty_label,
                participants_wheel_f,
                participants_wheel_up_f,
                participants_wheel_down_f,
            )
            _sync_participants_scroll()
            return

        for user in users:
            subgroup_label = "Без підгрупи"
            if user.subgroup_id and user.subgroup_id in current_subgroups_by_id:
                subgroup_label = subgroup_short_name(current_subgroups_by_id[user.subgroup_id].name)

            card = RoundedMotionCard(
                participants_cards_frame,
                bg_color=self.theme.SURFACE,
                card_color=self.theme.SURFACE_ALT,
                shadow_color=self.theme.SHADOW_SOFT,
                radius=14,
                padding=3,
                shadow_offset=3,
                motion_enabled=True,
                height=104,
            )
            card.pack(fill=tk.X, pady=(0, 8))
            card.content.grid_columnconfigure(0, weight=1)
            username_label = ttk.Label(card.content, text=user.username, style="CardAltTitle.TLabel")
            username_label.grid(row=0, column=0, sticky="w")
            badge_color = self.theme.SECONDARY_HOVER if user.subgroup_id is not None else self.theme.SURFACE
            badge_fg = self.theme.ACCENT if user.subgroup_id is not None else self.theme.TEXT_MUTED
            badge_label = tk.Label(
                card.content,
                text=subgroup_label,
                bg=badge_color,
                fg=badge_fg,
                font=("Segoe UI", 9, "bold"),
                padx=10,
                pady=4,
                bd=0,
                relief=tk.FLAT,
            )
            badge_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
            _bind_wheel_recursive(
                card,
                participants_wheel_f,
                participants_wheel_up_f,
                participants_wheel_down_f,
            )

        _sync_participants_scroll()

    def render_subgroup_tree(users: list[User]) -> None:
        subgroup_tree.delete(*subgroup_tree.get_children())
        tree_subgroup_id_by_iid.clear()

        counts_by_subgroup_id: dict[int | None, int] = {None: 0}
        for subgroup_id in current_subgroups_by_id:
            counts_by_subgroup_id[subgroup_id] = 0
        for user in users:
            subgroup_id = user.subgroup_id if user.subgroup_id in current_subgroups_by_id else None
            counts_by_subgroup_id[subgroup_id] = counts_by_subgroup_id.get(subgroup_id, 0) + 1

        unassigned_iid = "sg_none"
        subgroup_tree.insert(
            "",
            tk.END,
            iid=unassigned_iid,
            text=f"Без підгрупи [{counts_by_subgroup_id.get(None, 0)}]",
            open=True,
            tags=("bucket",),
        )
        tree_subgroup_id_by_iid[unassigned_iid] = None

        for subgroup in current_subgroups_by_id.values():
            iid = f"sg_{subgroup.id}"
            subgroup_tree.insert(
                "",
                tk.END,
                iid=iid,
                text=f"Підгрупа: {subgroup_short_name(subgroup.name)} [{counts_by_subgroup_id.get(subgroup.id, 0)}]",
                open=True,
                tags=("bucket",),
            )
            tree_subgroup_id_by_iid[iid] = subgroup.id

        for user in users:
            parent_iid = unassigned_iid
            if user.subgroup_id is not None and user.subgroup_id in current_subgroups_by_id:
                parent_iid = f"sg_{user.subgroup_id}"
            subgroup_tree.insert(
                parent_iid,
                tk.END,
                iid=f"user_{user.id}",
                text=f"Учасник: {user.username}",
                tags=("participant",),
            )

    def load_group_detail() -> None:
        nonlocal current_users_by_id, current_subgroups_by_id

        group_id = group_state["id"]
        if group_id is None:
            return
        with session_scope() as session:
            auth_controller = AuthController(session=session)
            resource_controller = ResourceController(session=session)
            academic_controller = AcademicController(session=session)
            group = resource_controller.get_resource(group_id)
            if group is None or group.type != ResourceType.GROUP:
                messagebox.showerror("Помилка", "Групу не знайдено.")
                open_main_view()
                return
            subgroups = resource_controller.list_subgroups(group_id=group_id, company_id=company_id)
            subgroup_ids = [item.id for item in subgroups]
            users = auth_controller.list_group_users(
                company_id=company_id,
                group_id=group_id,
                subgroup_ids=subgroup_ids,
            )
            available_users = auth_controller.list_available_personal_users_for_company(company_id=company_id)
            stream = academic_controller.get_stream(group.stream_id) if getattr(group, "stream_id", None) is not None else None
            course = (
                academic_controller.get_course(stream.course_id)
                if stream is not None and getattr(stream, "course_id", None) is not None
                else None
            )
            specialty = (
                academic_controller.get_specialty(course.specialty_id if course is not None else stream.specialty_id)
                if stream is not None
                else None
            )
            department = (
                academic_controller.get_department(specialty.department_id)
                if specialty is not None
                else None
            )

        current_subgroups_by_id = {item.id: item for item in subgroups}
        current_users_by_id = {item.id: item for item in users}

        structure_parts: list[str] = []
        if department is not None:
            structure_parts.append(department.short_name or department.name)
        if specialty is not None:
            structure_parts.append(specialty.code or specialty.name)
        if course is not None:
            structure_parts.append(course.code or course.name)
        if stream is not None:
            structure_parts.append(stream.name)
        structure_prefix = " → ".join(structure_parts) if structure_parts else "Без структури потоку"
        detail_meta_var.set(
            f"{structure_prefix}. Додавай учасників за логіном і перетягуй їх між підгрупами."
        )

        render_participant_cards(users)
        render_subgroup_tree(users)

        available_usernames = [item.username for item in available_users if item.id not in current_users_by_id]
        participant_input_box["values"] = available_usernames
        if participant_username_var.get().strip() not in available_usernames:
            participant_username_var.set("")

    def open_reassign_group_stream_modal() -> None:
        group_id = group_state["id"]
        if group_id is None:
            return

        with session_scope() as session:
            resource_controller = ResourceController(session=session)
            academic_controller = AcademicController(session=session)
            group = resource_controller.get_resource(int(group_id))
            if group is None or group.type != ResourceType.GROUP:
                messagebox.showerror("Помилка", "Групу не знайдено.")
                open_main_view()
                return
            streams = academic_controller.list_streams(company_id=company_id, include_archived=True)
            courses = academic_controller.list_courses(company_id=company_id, include_archived=True)
            specialties = academic_controller.list_specialties(company_id=company_id, include_archived=True)

        if not streams:
            messagebox.showerror("Курс/потік", "Немає доступних потоків для переназначення.", parent=self.root)
            return

        course_by_id = {item.id: item for item in courses}
        specialty_by_id = {item.id: item for item in specialties}
        stream_by_id = {item.id: item for item in streams}

        stream_labels_by_course_id: dict[int | None, list[str]] = {}
        stream_id_by_label: dict[str, int] = {}
        for stream in streams:
            course = course_by_id.get(stream.course_id) if stream.course_id is not None else None
            course_name = (course.code or course.name) if course is not None else "Без курсу"
            year_suffix = f" • набір {stream.admission_year}" if stream.admission_year is not None else ""
            label = f"{stream.id} | {course_name} • {stream.name}{year_suffix}"
            stream_id_by_label[label] = stream.id
            stream_labels_by_course_id.setdefault(stream.course_id, []).append(label)

        course_values: list[str] = []
        course_id_by_label: dict[str, int | None] = {}
        for course_id in sorted(stream_labels_by_course_id.keys(), key=lambda value: (value is None, value or 0)):
            if course_id is None:
                label = "Без курсу"
            else:
                course = course_by_id.get(course_id)
                if course is None:
                    label = f"{course_id} | Курс"
                else:
                    specialty = specialty_by_id.get(course.specialty_id)
                    specialty_prefix = f"{specialty.code} / " if specialty is not None and specialty.code else ""
                    course_label = f"{course.code} — {course.name}" if course.code else course.name
                    label = f"{course.id} | {specialty_prefix}{course_label}"
            course_values.append(label)
            course_id_by_label[label] = course_id

        if not course_values:
            messagebox.showerror("Курс/потік", "Немає доступних курсів для переназначення.", parent=self.root)
            return

        current_stream = stream_by_id.get(group.stream_id) if group.stream_id is not None else None
        current_course_id = current_stream.course_id if current_stream is not None else None
        current_stream_label = None
        if current_stream is not None:
            for label, stream_id in stream_id_by_label.items():
                if stream_id == current_stream.id:
                    current_stream_label = label
                    break

        modal = tk.Toplevel(self.root)
        modal.title("Переназначення курсу та потоку")
        modal.transient(self.root)
        modal.resizable(False, False)
        modal.grab_set()

        shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        ttk.Label(shell, text="Переназначення групи", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            shell,
            text=f"Група: {group.name}",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        course_var = tk.StringVar()
        stream_var = tk.StringVar()

        ttk.Label(shell, text="Курс", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
        course_box = ttk.Combobox(
            shell,
            textvariable=course_var,
            values=course_values,
            state="readonly",
            width=58,
        )
        course_box.pack(fill=tk.X, pady=(6, 8))

        ttk.Label(shell, text="Потік", style="Card.TLabel").pack(anchor="w")
        stream_box = ttk.Combobox(
            shell,
            textvariable=stream_var,
            values=[],
            state="readonly",
            width=58,
        )
        stream_box.pack(fill=tk.X, pady=(6, 10))

        stream_hint_var = tk.StringVar(value="")
        ttk.Label(shell, textvariable=stream_hint_var, style="CardSubtle.TLabel").pack(anchor="w")

        def _refresh_stream_values(*_args) -> None:
            selected_course_id = course_id_by_label.get(course_var.get().strip())
            values = stream_labels_by_course_id.get(selected_course_id, [])
            stream_box["values"] = values
            if stream_var.get().strip() not in values:
                if current_stream_label is not None and current_stream_label in values:
                    stream_var.set(current_stream_label)
                elif values:
                    stream_var.set(values[0])
                else:
                    stream_var.set("")
            stream_hint_var.set(f"Доступно потоків: {len(values)}")

        initial_course_label = None
        for label, course_id in course_id_by_label.items():
            if course_id == current_course_id:
                initial_course_label = label
                break
        course_var.set(initial_course_label or course_values[0])
        _refresh_stream_values()
        course_box.bind("<<ComboboxSelected>>", _refresh_stream_values, add="+")

        footer = ttk.Frame(shell, style="Card.TFrame")
        footer.pack(fill=tk.X, pady=(10, 0))

        def on_submit_reassign_stream() -> None:
            selected_stream_id = stream_id_by_label.get(stream_var.get().strip())
            if selected_stream_id is None:
                messagebox.showerror("Некоректні дані", "Оберіть потік зі списку.", parent=modal)
                return
            try:
                with session_scope() as session:
                    ResourceController(session=session).update_resource(
                        int(group_id),
                        stream_id=int(selected_stream_id),
                    )
            except Exception as exc:
                messagebox.showerror("Не вдалося переназначити потік", str(exc), parent=modal)
                return

            modal.destroy()
            load_group_detail()
            render_group_cards()

        self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
        self._motion_button(footer, text="Зберегти", command=on_submit_reassign_stream, primary=True, width=130).pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )

        modal.update_idletasks()
        modal.geometry(f"+{self.root.winfo_rootx() + 230}+{self.root.winfo_rooty() + 130}")

    def on_add_participant() -> None:
        group_id = group_state["id"]
        if group_id is None:
            return

        username = participant_username_var.get().strip()
        if not username:
            messagebox.showerror("Некоректні дані", "Вкажи логін учасника.")
            return

        if any(user.username == username for user in current_users_by_id.values()):
            messagebox.showerror("Помилка", "Цей учасник уже в групі.")
            return

        try:
            with session_scope() as session:
                auth_controller = AuthController(session=session)
                company_users = auth_controller.list_company_users(company_id=company_id)
                company_personals = {item.username: item for item in company_users if item.role == UserRole.PERSONAL}
                available_personals = {
                    item.username: item
                    for item in auth_controller.list_available_personal_users_for_company(company_id=company_id)
                }

                user = company_personals.get(username) or available_personals.get(username)
                if user is None:
                    raise ValueError("Особистий акаунт із таким логіном не знайдено.")

                if user.company_id != company_id:
                    auth_controller.reassign_personal_user_company(user_id=user.id, company_id=company_id)

                auth_controller.update_user_membership(
                    user.id,
                    resource_id=int(group_id),
                    subgroup_id=None,
                )
        except Exception as exc:
            messagebox.showerror("Не вдалося додати учасника", str(exc))
            return

        participant_username_var.set("")
        load_group_detail()
        render_group_cards()

    def on_create_subgroup() -> None:
        group_id = group_state["id"]
        group_name = group_state["name"]
        if group_id is None or not isinstance(group_name, str):
            return
        raw_name = subgroup_name_var.get().strip()
        if not raw_name:
            messagebox.showerror("Некоректні дані", "Введи назву підгрупи.")
            return
        stored_name = f"{group_name}::{raw_name}"
        try:
            with session_scope() as session:
                ResourceController(session=session).create_resource(
                    name=stored_name,
                    resource_type=ResourceType.SUBGROUP,
                    company_id=company_id,
                    parent_group_id=int(group_id),
                )
        except Exception as exc:
            messagebox.showerror("Не вдалося створити підгрупу", str(exc))
            return
        subgroup_name_var.set("")
        load_group_detail()

    def on_delete_subgroup() -> None:
        group_id = group_state["id"]
        if group_id is None:
            return
        selection = subgroup_tree.selection()
        if not selection:
            messagebox.showerror("Помилка", "Обери підгрупу для видалення.")
            return
        selected_iid = selection[0]
        subgroup_id = tree_subgroup_id_by_iid.get(selected_iid)
        if subgroup_id is None:
            messagebox.showerror("Помилка", "Обери саме підгрупу, а не учасника.")
            return

        subgroup_resource = current_subgroups_by_id.get(subgroup_id)
        subgroup_name = subgroup_short_name(subgroup_resource.name) if subgroup_resource is not None else f"#{subgroup_id}"
        if not messagebox.askyesno("Підтвердження", f"Видалити підгрупу '{subgroup_name}'?"):
            return
        try:
            with session_scope() as session:
                auth_controller = AuthController(session=session)
                users = auth_controller.list_group_users(
                    company_id=company_id,
                    group_id=int(group_id),
                    subgroup_ids=[subgroup_id],
                )
                for user in users:
                    if user.subgroup_id == subgroup_id:
                        auth_controller.update_user_membership(user.id, resource_id=int(group_id), subgroup_id=None)
                ResourceController(session=session).delete_resource(subgroup_id)
        except Exception as exc:
            messagebox.showerror("Не вдалося видалити підгрупу", str(exc))
            return
        load_group_detail()

    def on_detail_tree_press(event: tk.Event) -> None:
        item = subgroup_tree.identify_row(event.y)
        if item.startswith("user_"):
            tree_drag_state["item"] = item
            tree_drag_state["active"] = False
        else:
            tree_drag_state["item"] = None
            tree_drag_state["active"] = False

    def on_detail_tree_motion(event: tk.Event) -> None:
        item = tree_drag_state["item"]
        if item is None:
            return
        tree_drag_state["active"] = True
        target = subgroup_tree.identify_row(event.y)
        if target:
            subgroup_tree.selection_set(target)

    def on_detail_tree_release(event: tk.Event) -> None:
        item = tree_drag_state["item"]
        if item is None:
            return

        target = subgroup_tree.identify_row(event.y)
        if not target:
            selected = subgroup_tree.selection()
            target = selected[0] if selected else "sg_none"
        if target.startswith("user_"):
            target = subgroup_tree.parent(target)
        if target not in tree_subgroup_id_by_iid:
            target = "sg_none"

        user_id = int(item.split("_", maxsplit=1)[1])
        subgroup_id = tree_subgroup_id_by_iid.get(target)
        group_id = group_state["id"]

        tree_drag_state["item"] = None
        was_drag = bool(tree_drag_state["active"])
        tree_drag_state["active"] = False
        if not was_drag or group_id is None:
            return

        try:
            with session_scope() as session:
                AuthController(session=session).update_user_membership(
                    user_id,
                    resource_id=int(group_id),
                    subgroup_id=subgroup_id,
                )
        except Exception as exc:
            messagebox.showerror("Не вдалося оновити підгрупу", str(exc))
            return

        load_group_detail()

    subgroup_tree.bind("<ButtonPress-1>", on_detail_tree_press)
    subgroup_tree.bind("<B1-Motion>", on_detail_tree_motion)
    subgroup_tree.bind("<ButtonRelease-1>", on_detail_tree_release)

    def open_create_group_modal() -> None:
        with session_scope() as session:
            auth_controller = AuthController(session=session)
            academic_controller = AcademicController(session=session)
            personal_users = auth_controller.list_available_personal_users_for_company(
                company_id=company_id
            )
            streams = academic_controller.list_streams(company_id=company_id, include_archived=False)
            courses = academic_controller.list_courses(company_id=company_id, include_archived=True)
            specialties = academic_controller.list_specialties(company_id=company_id, include_archived=True)
        if not streams:
            messagebox.showerror("Створення групи", "Спочатку створіть потік (кафедра → спеціальність → курс → потік).")
            return
        user_by_username = {item.username: item for item in personal_users}
        user_by_id = {item.id: item for item in personal_users}

        modal = tk.Toplevel(self.root)
        modal.title("Створення групи")
        modal.geometry("900x640")
        modal.minsize(840, 560)
        modal.transient(self.root)
        modal.grab_set()
        modal.configure(bg=self.theme.APP_BG)

        root = ttk.Frame(modal, padding=14, style="Card.TFrame")
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, text="Нова група", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            root,
            text="Вкажи назву, додай учасників за логіном, створи підгрупи і розподіли перетягуванням.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(2, 10))

        course_by_id = {item.id: item for item in courses}
        specialty_by_id = {item.id: item for item in specialties}
        stream_values = []
        for item in streams:
            course = course_by_id.get(getattr(item, "course_id", None))
            specialty = specialty_by_id.get(course.specialty_id) if course is not None else specialty_by_id.get(item.specialty_id)
            spec_label = f"{specialty.code} — " if specialty is not None and specialty.code else ""
            course_label = f"{(course.code or course.name)} • " if course is not None else ""
            year_suffix = f" • набір {item.admission_year}" if item.admission_year is not None else ""
            stream_values.append(f"{item.id} | {spec_label}{course_label}{item.name}{year_suffix}")
        stream_var = tk.StringVar(value=stream_values[0])

        stream_row = ttk.Frame(root, style="Card.TFrame")
        stream_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(stream_row, text="Потік", style="Card.TLabel").pack(side=tk.LEFT)
        ttk.Combobox(stream_row, textvariable=stream_var, values=stream_values, width=34, state="readonly").pack(
            side=tk.LEFT,
            padx=(8, 0),
        )

        group_name_var = tk.StringVar()
        group_row = ttk.Frame(root, style="Card.TFrame")
        group_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(group_row, text="Назва групи", style="Card.TLabel").pack(side=tk.LEFT)
        group_name_entry = ttk.Entry(group_row, textvariable=group_name_var, width=34)
        group_name_entry.pack(side=tk.LEFT, padx=(8, 0))

        participant_var = tk.StringVar()
        add_row = ttk.Frame(root, style="Card.TFrame")
        add_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(add_row, text="Учасник (логін)", style="Card.TLabel").pack(side=tk.LEFT)
        participant_box = ttk.Combobox(add_row, textvariable=participant_var, width=26, state="normal")
        participant_box.pack(side=tk.LEFT, padx=(8, 8))

        subgroup_var = tk.StringVar()
        subgroup_row = ttk.Frame(root, style="Card.TFrame")
        subgroup_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(subgroup_row, text="Підгрупа", style="Card.TLabel").pack(side=tk.LEFT)
        subgroup_entry = ttk.Entry(subgroup_row, textvariable=subgroup_var, width=22)
        subgroup_entry.pack(side=tk.LEFT, padx=(8, 8))

        footer = ttk.Frame(root, style="Card.TFrame")
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        tree_container = ttk.Frame(root, style="Card.TFrame")
        tree_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        tree = ttk.Treeview(
            tree_container,
            show="tree headings",
            height=10,
            selectmode="browse",
        )
        tree.heading("#0", text="Підгрупи та учасники", anchor="w")
        tree.column("#0", anchor="w", minwidth=240, width=360, stretch=True)
        tree.tag_configure(
            "bucket",
            font=("Segoe UI", 10, "bold"),
            background=self.theme.SURFACE_ALT,
            foreground=self.theme.TEXT_PRIMARY,
        )
        tree.tag_configure(
            "participant",
            font=("Segoe UI", 10),
            foreground=self.theme.TEXT_PRIMARY,
        )
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll = ttk.Scrollbar(
            tree_container,
            orient=tk.VERTICAL,
            command=tree.yview,
            style="App.Vertical.TScrollbar",
        )
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=tree_scroll.set)

        unassigned_iid = "group_none"
        tree.insert("", tk.END, iid=unassigned_iid, text="Без підгрупи [0]", open=True, tags=("bucket",))
        subgroup_iid_by_name: dict[str, str] = {}
        subgroup_name_by_iid: dict[str, str] = {}
        added_users: dict[int, str] = {}
        assignment_by_user_id: dict[int, str | None] = {}
        drag_state: dict[str, str | bool | None] = {"item": None, "active": False}

        def refresh_tree_bucket_labels() -> None:
            tree.item(unassigned_iid, text=f"Без підгрупи [{len(tree.get_children(unassigned_iid))}]")
            for subgroup_name, subgroup_iid in subgroup_iid_by_name.items():
                tree.item(subgroup_iid, text=f"Підгрупа: {subgroup_name} [{len(tree.get_children(subgroup_iid))}]")

        def refresh_suggestions() -> None:
            available = [item.username for item in personal_users if item.id not in added_users]
            participant_box["values"] = available
            if participant_var.get().strip() not in available:
                participant_var.set("")

        def add_participant_from_input() -> None:
            username = participant_var.get().strip()
            if not username:
                messagebox.showerror("Помилка", "Вкажи логін учасника.", parent=modal)
                return
            user = user_by_username.get(username)
            if user is None:
                messagebox.showerror("Помилка", "Користувача з таким логіном не знайдено.", parent=modal)
                return
            if user.id in added_users:
                return
            item_iid = f"user_{user.id}"
            tree.insert(unassigned_iid, tk.END, iid=item_iid, text=f"Учасник: {user.username}", tags=("participant",))
            added_users[user.id] = user.username
            assignment_by_user_id[user.id] = None
            participant_var.set("")
            refresh_suggestions()
            refresh_tree_bucket_labels()

        def remove_selected_participant() -> None:
            selected = tree.selection()
            if not selected:
                return
            item = selected[0]
            if not item.startswith("user_"):
                return
            user_id = int(item.split("_", maxsplit=1)[1])
            tree.delete(item)
            added_users.pop(user_id, None)
            assignment_by_user_id.pop(user_id, None)
            refresh_suggestions()
            refresh_tree_bucket_labels()

        def add_subgroup() -> None:
            name = subgroup_var.get().strip()
            if not name:
                messagebox.showerror("Помилка", "Вкажи назву підгрупи.", parent=modal)
                return
            if name in subgroup_iid_by_name:
                return
            iid = f"sg_{len(subgroup_iid_by_name) + 1}_{uuid4().hex[:4]}"
            tree.insert("", tk.END, iid=iid, text=f"Підгрупа: {name} [0]", open=True, tags=("bucket",))
            subgroup_iid_by_name[name] = iid
            subgroup_name_by_iid[iid] = name
            subgroup_var.set("")
            refresh_tree_bucket_labels()

        def remove_selected_subgroup() -> None:
            selected = tree.selection()
            if not selected:
                return
            iid = selected[0]
            if iid not in subgroup_name_by_iid:
                return
            for child in tree.get_children(iid):
                tree.move(child, unassigned_iid, tk.END)
                user_id = int(child.split("_", maxsplit=1)[1])
                assignment_by_user_id[user_id] = None
            name = subgroup_name_by_iid.pop(iid)
            subgroup_iid_by_name.pop(name, None)
            tree.delete(iid)
            refresh_tree_bucket_labels()

        def on_tree_press(event: tk.Event) -> None:
            item = tree.identify_row(event.y)
            if item.startswith("user_"):
                drag_state["item"] = item
                drag_state["active"] = False
            else:
                drag_state["item"] = None
                drag_state["active"] = False

        def on_tree_motion(event: tk.Event) -> None:
            item = drag_state["item"]
            if item is None:
                return
            drag_state["active"] = True
            target = tree.identify_row(event.y)
            if target:
                tree.selection_set(target)

        def on_tree_release(event: tk.Event) -> None:
            item = drag_state["item"]
            if item is None:
                return

            target = tree.identify_row(event.y)
            if not target:
                selected = tree.selection()
                target = selected[0] if selected else unassigned_iid
            if target.startswith("user_"):
                target = tree.parent(target)
            if target != unassigned_iid and target not in subgroup_name_by_iid:
                target = unassigned_iid
            if drag_state["active"] and tree.parent(item) != target:
                tree.move(item, target, tk.END)
            user_id = int(item.split("_", maxsplit=1)[1])
            assignment_by_user_id[user_id] = subgroup_name_by_iid.get(target)
            drag_state["item"] = None
            drag_state["active"] = False
            refresh_tree_bucket_labels()

        def save_group() -> None:
            group_name = group_name_var.get().strip()
            if not group_name:
                messagebox.showerror("Некоректні дані", "Введи назву групи.", parent=modal)
                return
            stream_id = parse_selected_prefixed_id(stream_var.get())
            if stream_id is None:
                messagebox.showerror("Некоректні дані", "Обери потік зі списку.", parent=modal)
                return
            try:
                with session_scope() as session:
                    resource_controller = ResourceController(session=session)
                    auth_controller = AuthController(session=session)
                    group = resource_controller.create_resource(
                        name=group_name,
                        resource_type=ResourceType.GROUP,
                        company_id=company_id,
                        stream_id=stream_id,
                    )
                    subgroup_id_by_name: dict[str, int] = {}
                    for subgroup_name in subgroup_iid_by_name:
                        created = resource_controller.create_resource(
                            name=f"{group_name}::{subgroup_name}",
                            resource_type=ResourceType.SUBGROUP,
                            company_id=company_id,
                            parent_group_id=group.id,
                        )
                        subgroup_id_by_name[subgroup_name] = created.id

                    for user_id, subgroup_name in assignment_by_user_id.items():
                        user = user_by_id.get(user_id)
                        if user is not None and user.company_id != company_id:
                            auth_controller.reassign_personal_user_company(user_id=user_id, company_id=company_id)
                            user.company_id = company_id
                        auth_controller.update_user_membership(
                            user_id,
                            resource_id=group.id,
                            subgroup_id=subgroup_id_by_name.get(subgroup_name) if subgroup_name else None,
                        )
            except IntegrityError:
                messagebox.showerror(
                    "Не вдалося створити групу",
                    "Група або підгрупа з такою назвою вже існує.",
                    parent=modal,
                )
                return
            except Exception as exc:
                messagebox.showerror("Не вдалося створити групу", str(exc), parent=modal)
                return
            modal.destroy()
            render_group_cards()

        self._motion_button(add_row, text="Додати", command=add_participant_from_input, primary=True, width=110).pack(
            side=tk.LEFT,
            padx=(0, 8),
        )
        self._motion_button(add_row, text="Прибрати", command=remove_selected_participant, primary=False, width=120).pack(
            side=tk.LEFT
        )

        self._motion_button(subgroup_row, text="Додати підгрупу", command=add_subgroup, primary=False, width=150).pack(
            side=tk.LEFT,
            padx=(0, 8),
        )
        self._motion_button(
            subgroup_row,
            text="Видалити підгрупу",
            command=remove_selected_subgroup,
            primary=False,
            width=170,
        ).pack(side=tk.LEFT)

        self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=140).pack(side=tk.RIGHT)
        self._motion_button(footer, text="Зберегти", command=save_group, primary=True, width=140).pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )

        tree.bind("<ButtonPress-1>", on_tree_press)
        tree.bind("<B1-Motion>", on_tree_motion)
        tree.bind("<ButtonRelease-1>", on_tree_release)
        group_name_entry.focus_set()
        refresh_suggestions()
        refresh_tree_bucket_labels()

    course_filter_box.bind("<<ComboboxSelected>>", on_course_filter_change, add="+")
    stream_filter_box.bind("<<ComboboxSelected>>", on_stream_filter_change, add="+")
    cards_canvas.bind("<Configure>", on_cards_resize, add="+")
    main_view.bind("<Map>", lambda _event: on_cards_resize(), add="+")

    hierarchy_back_button.command = on_hierarchy_back
    back_button.command = open_main_view
    set_hierarchy_level("departments", department_id=None, specialty_id=None)
    open_main_view()
