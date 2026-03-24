def _build_company_schedule_view__impl(self, parent: ttk.Frame, company_id: int) -> None:
    period_var = tk.StringVar()
    week_start_var = tk.StringVar()
    group_filter_var = tk.StringVar(value="Не обрано")
    scenario_var = tk.StringVar(value="Опублікований")
    scenario_compare_var = tk.StringVar(value="Опублікований")
    status_var = tk.StringVar(value="Готово.")
    plan_sync_var = tk.StringVar()
    plan_sync_hint_var = tk.StringVar(value="Синхронізуйте вимоги з навчальних планів.")

    blackout_scope_var = tk.StringVar(value="Викладач")
    blackout_resource_var = tk.StringVar()
    blackout_start_date_var = tk.StringVar()
    blackout_start_time_var = tk.StringVar(value="08:30")
    blackout_end_date_var = tk.StringVar()
    blackout_end_time_var = tk.StringVar(value="18:00")
    blackout_title_var = tk.StringVar()
    blackout_batch_start_date_var = tk.StringVar()
    blackout_batch_end_date_var = tk.StringVar()
    blackout_batch_start_time_var = tk.StringVar(value="08:30")
    blackout_batch_end_time_var = tk.StringVar(value="18:00")
    blackout_weekday_labels: list[tuple[int, str]] = [
        (1, "Пн"),
        (2, "Вт"),
        (3, "Ср"),
        (4, "Чт"),
        (5, "Пт"),
        (6, "Сб"),
        (7, "Нд"),
    ]
    blackout_batch_weekday_vars: dict[int, tk.BooleanVar] = {
        day: tk.BooleanVar(value=(day <= 5))
        for day, _ in blackout_weekday_labels
    }
    blackout_time_values = [f"{hour:02d}:{minute:02d}" for hour in range(7, 23) for minute in (0, 15, 30, 45)]
    coverage_summary_var = tk.StringVar(value="Coverage: —")

    room_type_options: list[tuple[str, RoomType | None]] = [
        ("Не важливо", None),
        ("Лекційна", RoomType.LECTURE_HALL),
        ("Клас", RoomType.CLASSROOM),
        ("Лабораторія", RoomType.LAB),
        ("Комп'ютерна", RoomType.COMPUTER_LAB),
        ("Інше", RoomType.OTHER),
    ]
    room_type_by_label = {label: room_type for label, room_type in room_type_options}
    room_type_labels = [label for label, _ in room_type_options]

    blackout_scope_options: list[tuple[str, ResourceType]] = [
        ("Викладач", ResourceType.TEACHER),
        ("Група", ResourceType.GROUP),
        ("Аудиторія", ResourceType.ROOM),
    ]
    blackout_scope_type_by_label = {label: resource_type for label, resource_type in blackout_scope_options}
    blackout_scope_labels = [label for label, _ in blackout_scope_options]
    blackout_resource_values_by_scope: dict[str, list[str]] = {label: [] for label in blackout_scope_labels}
    blackout_resource_name_by_id: dict[int, str] = {}
    blackout_resource_scope_by_id: dict[int, str] = {}
    blackout_table_columns = ("resource", "start", "end", "title")
    blackout_heading_titles = {
        "resource": "Ресурс",
        "start": "Початок",
        "end": "Кінець",
        "title": "Причина",
    }
    blackout_filter_state: dict[str, object] = {
        "rows": [],
        "search_by_column": {},
        "value_filter_by_column": {},
        "sort_column": None,
        "sort_desc": False,
        "menu": None,
    }
    room_type_label_by_enum = {room_type: label for label, room_type in room_type_options if room_type is not None}
    requirements_state: dict[str, list[dict[str, object]]] = {"items": []}
    plan_sync_state: dict[str, object] = {"items": [], "selected_ids": [], "selection_touched": False}
    schedule_entries_state: dict[int, dict[str, object]] = {}
    scenario_values_state: dict[str, list[str]] = {"values": ["Опублікований"]}
    period_state: dict[str, object] = {
        "items": [],
        "by_id": {},
        "menu": None,
    }
    week_start_state: dict[str, object] = {
        "labels": [],
        "start_by_label": {},
        "label_by_iso": {},
    }
    week_selector_state: dict[str, object] = {"menu": None, "values": []}
    group_selector_state: dict[str, object] = {
        "menu": None,
        "values": [],
        "all_values": [],
        "meta_by_value": {},
        "specialty_values": ["Усі спеціальності"],
        "course_values": ["Усі курси"],
        "specialty_filter": "Усі спеціальності",
        "course_filter": "Усі курси",
    }
    scenario_selector_state: dict[str, object] = {"menu": None, "values": []}
    scenario_compare_selector_state: dict[str, object] = {"menu": None, "values": []}

    policy_max_sessions_var = tk.StringVar(value="4")
    policy_max_consecutive_var = tk.StringVar(value="3")
    policy_no_gaps_var = tk.BooleanVar(value=False)
    policy_time_pref_var = tk.StringVar(value="Баланс")
    policy_weight_time_var = tk.StringVar(value="2")
    policy_weight_compact_var = tk.StringVar(value="3")
    policy_weight_building_var = tk.StringVar(value="2")
    policy_time_pref_options = {
        "Баланс": TimePreference.BALANCED,
        "Ранок": TimePreference.MORNING,
        "Вечір": TimePreference.EVENING,
    }

    manual_requirement_var = tk.StringVar()
    manual_date_var = tk.StringVar()
    manual_order_var = tk.StringVar(value="1")
    manual_room_var = tk.StringVar(value="Авто")
    manual_lock_var = tk.BooleanVar(value=True)

    schedule_shell = ttk.Frame(parent, style="Card.TFrame")
    schedule_shell.pack(fill=tk.BOTH, expand=True)

    schedule_canvas = tk.Canvas(
        schedule_shell,
        bg=self.theme.SURFACE,
        bd=0,
        highlightthickness=0,
        relief=tk.FLAT,
    )
    schedule_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    schedule_scroll = ttk.Scrollbar(
        schedule_shell,
        orient=tk.VERTICAL,
        command=schedule_canvas.yview,
        style="App.Vertical.TScrollbar",
    )
    schedule_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    schedule_canvas.configure(yscrollcommand=schedule_scroll.set)

    schedule_body = ttk.Frame(schedule_canvas, style="Card.TFrame")
    schedule_window = schedule_canvas.create_window((0, 0), anchor="nw", window=schedule_body)
    schedule_scroll_state = {"visible": True}

    def _sync_schedule_scroll(_event=None) -> None:
        viewport_width = max(1, schedule_canvas.winfo_width())
        viewport_height = max(1, schedule_canvas.winfo_height())
        requested_height = max(1, schedule_body.winfo_reqheight())
        schedule_canvas.itemconfigure(
            schedule_window,
            width=viewport_width,
            height=max(viewport_height, requested_height),
        )
        bbox = schedule_canvas.bbox("all")
        if bbox is not None:
            schedule_canvas.configure(scrollregion=bbox)

        need_scroll = requested_height > (viewport_height + 1)
        if need_scroll and not schedule_scroll_state["visible"]:
            schedule_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            schedule_scroll_state["visible"] = True
        elif not need_scroll and schedule_scroll_state["visible"]:
            schedule_scroll.pack_forget()
            schedule_scroll_state["visible"] = False

    def _create_smooth_wheel_handlers(get_view, set_view, *, gain: float = 0.14):
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

    def _bind_wheel_recursive(
        widget: tk.Widget,
        on_wheel,
        on_up,
        on_down,
        *,
        skip_widgets: set[tk.Widget] | None = None,
    ) -> None:
        if skip_widgets is not None and widget in skip_widgets:
            return
        widget.bind("<MouseWheel>", on_wheel, add="+")
        widget.bind("<Button-4>", on_up, add="+")
        widget.bind("<Button-5>", on_down, add="+")
        for child in widget.winfo_children():
            _bind_wheel_recursive(
                child,
                on_wheel,
                on_up,
                on_down,
                skip_widgets=skip_widgets,
            )

    schedule_body.bind("<Configure>", _sync_schedule_scroll, add="+")
    schedule_canvas.bind("<Configure>", _sync_schedule_scroll, add="+")
    schedule_wheel_raw, schedule_wheel_up_raw, schedule_wheel_down_raw = _create_smooth_wheel_handlers(
        schedule_canvas.yview,
        schedule_canvas.yview_moveto,
        gain=0.14,
    )

    def dismiss_schedule_popdowns() -> None:
        self._dismiss_combobox_popdowns(schedule_body)
        close_blackout_filter_menu()

    def schedule_wheel(event: tk.Event) -> str:
        dismiss_schedule_popdowns()
        return schedule_wheel_raw(event)

    def schedule_wheel_up(event: tk.Event) -> str:
        dismiss_schedule_popdowns()
        return schedule_wheel_up_raw(event)

    def schedule_wheel_down(event: tk.Event) -> str:
        dismiss_schedule_popdowns()
        return schedule_wheel_down_raw(event)

    schedule_canvas.bind("<MouseWheel>", schedule_wheel, add="+")
    schedule_canvas.bind("<Button-4>", schedule_wheel_up, add="+")
    schedule_canvas.bind("<Button-5>", schedule_wheel_down, add="+")

    parent = schedule_body
    tabs_bar = ttk.Frame(parent, style="Card.TFrame")
    tabs_bar.pack(fill=tk.X, pady=(0, 8))
    schedule_views: dict[str, ttk.Frame] = {
        "view": ttk.Frame(parent, style="Card.TFrame"),
        "setup": ttk.Frame(parent, style="Card.TFrame"),
    }
    for frame in schedule_views.values():
        frame.pack(fill=tk.BOTH, expand=True)
        frame.pack_forget()
    schedule_tab_buttons: dict[str, RoundedMotionButton] = {}

    def _set_schedule_tab_state(button: RoundedMotionButton, *, active: bool) -> None:
        if active:
            button.fill = self.theme.ACCENT
            button.hover_fill = self.theme.ACCENT_HOVER
            button.pressed_fill = self.theme.ACCENT_PRESSED
            button.text_color = self.theme.TEXT_LIGHT
            button.shadow_color = self.theme.SHADOW_SOFT
        else:
            button.fill = self.theme.SURFACE_ALT
            button.hover_fill = self.theme.SECONDARY_HOVER
            button.pressed_fill = self.theme.SECONDARY_PRESSED
            button.text_color = self.theme.TEXT_PRIMARY
            button.shadow_color = self.theme.SHADOW_SOFT
        button._state = "normal"
        button._lift = 0
        button._draw()

    def open_schedule_tab(name: str) -> None:
        for frame in schedule_views.values():
            frame.pack_forget()
        schedule_views[name].pack(fill=tk.BOTH, expand=True)
        for key, button in schedule_tab_buttons.items():
            _set_schedule_tab_state(button, active=(key == name))
        self.root.after_idle(_sync_schedule_scroll)

    tab_specs = (
        ("view", "Візуалізація"),
        ("setup", "Налаштування"),
    )
    for key, label in tab_specs:
        tab_button = self._motion_button(
            tabs_bar,
            text=label,
            command=lambda selected=key: open_schedule_tab(selected),
            primary=False,
            width=170,
            height=40,
        )
        tab_button.pack(side=tk.LEFT, padx=(0, 8))
        schedule_tab_buttons[key] = tab_button

    parent = schedule_views["view"]

    header = ttk.Frame(parent, style="Card.TFrame")
    header.pack(fill=tk.X, pady=(0, 8))

    ttk.Label(header, text="Розклад", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(header, text="Період", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))

    period_selector_shell = ttk.Frame(header, style="Card.TFrame")
    period_selector_shell.grid(row=1, column=1, sticky="w", padx=(6, 10), pady=(8, 0))
    period_selector_main = tk.Frame(
        period_selector_shell,
        bg=self.theme.SURFACE,
        bd=0,
        highlightthickness=1,
        highlightbackground=self.theme.BORDER,
        highlightcolor=self.theme.ACCENT,
    )
    period_selector_main.pack(fill=tk.X)
    period_display = tk.Label(
        period_selector_main,
        textvariable=period_var,
        bg=self.theme.SURFACE,
        fg=self.theme.TEXT_PRIMARY,
        anchor="w",
        padx=10,
        pady=8,
        font=("Segoe UI", 10),
        cursor="hand2",
    )
    period_display.pack(side=tk.LEFT, fill=tk.X, expand=True)
    period_toggle_button = tk.Button(
        period_selector_main,
        text="▾",
        width=3,
        relief=tk.FLAT,
        bd=0,
        bg=self.theme.SURFACE_ALT,
        fg=self.theme.TEXT_PRIMARY,
        activebackground=self.theme.SECONDARY_HOVER,
        activeforeground=self.theme.TEXT_PRIMARY,
        cursor="hand2",
    )
    period_toggle_button.pack(side=tk.LEFT, fill=tk.Y)
    period_empty_create_button = self._motion_button(
        period_selector_shell,
        text="+ Створити період",
        command=lambda: None,
        primary=True,
        width=210,
        height=34,
    )
    period_selector_main.pack_forget()
    period_empty_create_button.pack(fill=tk.X)

    def build_header_selector(
        parent_widget: tk.Widget,
        *,
        text_var: tk.StringVar,
        width_px: int,
    ) -> tuple[tk.Frame, tk.Label, tk.Button]:
        selector_main = tk.Frame(
            parent_widget,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            highlightcolor=self.theme.ACCENT,
            width=width_px,
            height=36,
        )
        selector_main.grid_propagate(False)
        selector_label = tk.Label(
            selector_main,
            textvariable=text_var,
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            anchor="w",
            padx=10,
            pady=8,
            font=("Segoe UI", 10),
            cursor="hand2",
        )
        selector_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        selector_button = tk.Button(
            selector_main,
            text="▾",
            width=3,
            relief=tk.FLAT,
            bd=0,
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.TEXT_PRIMARY,
            activebackground=self.theme.SECONDARY_HOVER,
            activeforeground=self.theme.TEXT_PRIMARY,
            cursor="hand2",
        )
        selector_button.pack(side=tk.LEFT, fill=tk.Y)
        return selector_main, selector_label, selector_button

    ttk.Label(header, text="Тиждень", style="Card.TLabel").grid(row=1, column=2, sticky="w", pady=(8, 0))
    week_selector_main, week_selector_label, week_selector_button = build_header_selector(
        header,
        text_var=week_start_var,
        width_px=250,
    )
    week_selector_main.grid(row=1, column=3, sticky="w", padx=(6, 4), pady=(8, 0))

    group_selector_shell = ttk.Frame(header, style="Card.TFrame")
    group_selector_shell.grid(row=1, column=4, columnspan=2, sticky="w", pady=(8, 0))
    ttk.Label(group_selector_shell, text="Група", style="Card.TLabel").pack(side=tk.LEFT, padx=(0, 6))
    group_selector_main, group_selector_label, group_selector_button = build_header_selector(
        group_selector_shell,
        text_var=group_filter_var,
        width_px=168,
    )
    group_selector_main.pack(side=tk.LEFT)

    ttk.Label(header, text="Сценарій", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 0))
    scenario_selector_main, scenario_selector_label, scenario_selector_button = build_header_selector(
        header,
        text_var=scenario_var,
        width_px=250,
    )
    scenario_selector_main.grid(row=2, column=1, sticky="w", padx=(6, 10), pady=(8, 0))

    ttk.Label(header, text="Порівняти з", style="Card.TLabel").grid(row=2, column=2, sticky="w", pady=(8, 0))
    scenario_compare_selector_main, scenario_compare_selector_label, scenario_compare_selector_button = build_header_selector(
        header,
        text_var=scenario_compare_var,
        width_px=250,
    )
    scenario_compare_selector_main.grid(row=2, column=3, sticky="w", padx=(6, 10), pady=(8, 0))
    scenario_compare_button = self._motion_button(
        header,
        text="Порівняти",
        command=lambda: None,
        primary=False,
        width=122,
        height=36,
        canvas_bg=self.theme.SURFACE,
    )
    scenario_compare_button.grid(row=2, column=4, sticky="w", pady=(8, 0))
    scenario_publish_button = self._motion_button(
        header,
        text="Опублікувати",
        command=lambda: None,
        primary=True,
        width=140,
        height=36,
        canvas_bg=self.theme.SURFACE,
    )
    scenario_publish_button.grid(row=2, column=5, sticky="w", padx=(6, 0), pady=(8, 0))

    tree = ttk.Treeview(
        parent,
        columns=("slot", "mon", "tue", "wed", "thu", "fri", "sat", "sun"),
        show="headings",
        height=16,
    )
    tree.heading("slot", text="Пара")
    tree.column("slot", width=120, anchor="center", stretch=False)
    for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun"):
        tree.heading(day, text=day.upper())
        tree.column(day, width=145, anchor="center", stretch=True)
    tree.pack(fill=tk.BOTH, expand=True, pady=(8, 10))

    parent = schedule_views["setup"]

    setup_tabs_bar = ttk.Frame(parent, style="Card.TFrame")
    setup_tabs_bar.pack(fill=tk.X, pady=(0, 8))
    setup_tabs_body = ttk.Frame(parent, style="Card.TFrame")
    setup_tabs_body.pack(fill=tk.BOTH, expand=True)
    setup_tab_views: dict[str, ttk.Frame] = {
        "hard": ttk.Frame(setup_tabs_body, style="Card.TFrame"),
        "soft": ttk.Frame(setup_tabs_body, style="Card.TFrame"),
        "manual": ttk.Frame(setup_tabs_body, style="Card.TFrame"),
    }
    for frame in setup_tab_views.values():
        frame.pack(fill=tk.BOTH, expand=True)
        frame.pack_forget()
    setup_tab_buttons: dict[str, RoundedMotionButton] = {}

    def _set_setup_tab_state(button: RoundedMotionButton, *, active: bool) -> None:
        if active:
            button.fill = self.theme.ACCENT
            button.hover_fill = self.theme.ACCENT_HOVER
            button.pressed_fill = self.theme.ACCENT_PRESSED
            button.text_color = self.theme.TEXT_LIGHT
            button.shadow_color = self.theme.SHADOW_SOFT
        else:
            button.fill = self.theme.SURFACE_ALT
            button.hover_fill = self.theme.SECONDARY_HOVER
            button.pressed_fill = self.theme.SECONDARY_PRESSED
            button.text_color = self.theme.TEXT_PRIMARY
            button.shadow_color = self.theme.SHADOW_SOFT
        button._state = "normal"
        button._lift = 0
        button._draw()

    def open_setup_tab(name: str) -> None:
        for frame in setup_tab_views.values():
            frame.pack_forget()
        setup_tab_views[name].pack(fill=tk.BOTH, expand=True)
        for key, button in setup_tab_buttons.items():
            _set_setup_tab_state(button, active=(key == name))
        self.root.after_idle(_sync_schedule_scroll)

    for key, label in (("hard", "Hard"), ("soft", "Soft"), ("manual", "Manual/CRUD")):
        tab_button = self._motion_button(
            setup_tabs_bar,
            text=label,
            command=lambda selected=key: open_setup_tab(selected),
            primary=False,
            width=156,
            height=36,
        )
        tab_button.pack(side=tk.LEFT, padx=(0, 8))
        setup_tab_buttons[key] = tab_button

    open_setup_tab("hard")

    parent = setup_tab_views["hard"]

    plan_sync_box = ttk.LabelFrame(parent, text="Навчальні плани", padding=(12, 10), style="CardSection.TLabelframe")
    plan_sync_box.pack(fill=tk.X)
    plan_sync_box.columnconfigure(1, weight=1)

    ttk.Label(plan_sync_box, text="Додати план", style="CardSubtle.TLabel").grid(row=0, column=0, sticky="w")
    plan_selector_box = ttk.Combobox(
        plan_sync_box,
        textvariable=plan_sync_var,
        state="readonly",
    )
    plan_selector_box.grid(row=0, column=1, sticky="ew", padx=(8, 8))
    plan_add_button = ttk.Button(plan_sync_box, text="Додати", style="Secondary.TButton")
    plan_add_button.grid(row=0, column=2, sticky="w", padx=(0, 8))
    plan_remove_button = ttk.Button(plan_sync_box, text="Прибрати", style="Secondary.TButton")
    plan_remove_button.grid(row=0, column=3, sticky="w", padx=(0, 8))
    plan_clear_button = ttk.Button(plan_sync_box, text="Очистити", style="Secondary.TButton")
    plan_clear_button.grid(row=0, column=4, sticky="w")

    ttk.Label(plan_sync_box, text="Обрані", style="CardSubtle.TLabel").grid(row=1, column=0, sticky="nw", pady=(8, 0))
    plan_selected_wrap = ttk.Frame(plan_sync_box, style="Card.TFrame")
    plan_selected_wrap.grid(row=1, column=1, columnspan=4, sticky="ew", pady=(8, 0))
    plan_selected_wrap.columnconfigure(0, weight=1)
    plan_selected_listbox = tk.Listbox(
        plan_selected_wrap,
        height=4,
        activestyle="none",
        exportselection=False,
        selectmode=tk.BROWSE,
        relief=tk.FLAT,
        borderwidth=0,
    )
    self.theme.style_listbox(plan_selected_listbox)
    plan_selected_listbox.grid(row=0, column=0, sticky="ew")
    plan_selected_scroll = ttk.Scrollbar(
        plan_selected_wrap,
        orient=tk.VERTICAL,
        command=plan_selected_listbox.yview,
        style="App.Vertical.TScrollbar",
    )
    plan_selected_scroll.grid(row=0, column=1, sticky="ns")
    plan_selected_listbox.configure(yscrollcommand=plan_selected_scroll.set)

    plan_sync_actions = ttk.Frame(plan_sync_box, style="Card.TFrame")
    plan_sync_actions.grid(row=2, column=1, columnspan=4, sticky="w", pady=(8, 0))
    plan_sync_selected_button = ttk.Button(plan_sync_actions, text="Синхр. обрані", style="Primary.TButton")
    plan_sync_selected_button.pack(side=tk.LEFT)
    plan_sync_all_button = ttk.Button(plan_sync_actions, text="Синхр. усі плани", style="Secondary.TButton")
    plan_sync_all_button.pack(side=tk.LEFT, padx=(8, 0))
    plan_sync_refresh_button = ttk.Button(plan_sync_actions, text="Оновити список", style="Secondary.TButton")
    plan_sync_refresh_button.pack(side=tk.LEFT, padx=(8, 0))

    ttk.Label(
        plan_sync_box,
        textvariable=plan_sync_hint_var,
        style="CardSubtle.TLabel",
    ).grid(row=3, column=0, columnspan=5, sticky="w", pady=(8, 0))

    blackout_box = ttk.LabelFrame(
        parent,
        text="Недоступності ресурсів",
        padding=(12, 10),
        style="CardSection.TLabelframe",
    )
    blackout_box.pack(fill=tk.X, pady=(8, 0))
    blackout_box.columnconfigure(1, weight=1)
    blackout_box.columnconfigure(2, weight=1)
    blackout_box.columnconfigure(3, weight=1)
    blackout_box.columnconfigure(5, weight=1)
    blackout_box.columnconfigure(7, weight=1)

    ttk.Label(
        blackout_box,
        text="Blackout = один інтервал. Пакет = серія інтервалів у діапазоні дат за вибраними днями тижня.",
        style="CardSubtle.TLabel",
    ).grid(row=0, column=0, columnspan=8, sticky="w", pady=(0, 8))

    ttk.Label(blackout_box, text="Ресурс", style="CardSubtle.TLabel").grid(row=1, column=0, sticky="w")
    blackout_scope_box = ttk.Combobox(
        blackout_box,
        textvariable=blackout_scope_var,
        values=blackout_scope_labels,
        width=11,
        state="readonly",
    )
    blackout_scope_box.grid(row=1, column=1, sticky="w", padx=(6, 12))
    blackout_resource_box = ttk.Combobox(
        blackout_box,
        textvariable=blackout_resource_var,
        width=34,
        state="readonly",
    )
    blackout_resource_box.grid(row=1, column=2, columnspan=2, sticky="ew", padx=(0, 12))
    ttk.Label(blackout_box, text="Початок", style="CardSubtle.TLabel").grid(row=1, column=4, sticky="w")
    blackout_start_wrap = ttk.Frame(blackout_box, style="Card.TFrame")
    blackout_start_wrap.grid(row=1, column=5, sticky="ew", padx=(6, 12))
    blackout_start_wrap.columnconfigure(0, weight=1)
    blackout_start_date_box = ttk.Combobox(
        blackout_start_wrap,
        textvariable=blackout_start_date_var,
        state="readonly",
        width=12,
    )
    blackout_start_date_box.grid(row=0, column=0, sticky="ew")
    blackout_start_time_box = ttk.Combobox(
        blackout_start_wrap,
        textvariable=blackout_start_time_var,
        values=blackout_time_values,
        state="readonly",
        width=7,
    )
    blackout_start_time_box.grid(row=0, column=1, sticky="w", padx=(6, 0))
    ttk.Label(blackout_box, text="Кінець", style="CardSubtle.TLabel").grid(row=1, column=6, sticky="w")
    blackout_end_wrap = ttk.Frame(blackout_box, style="Card.TFrame")
    blackout_end_wrap.grid(row=1, column=7, sticky="ew", padx=(6, 0))
    blackout_end_wrap.columnconfigure(0, weight=1)
    blackout_end_date_box = ttk.Combobox(
        blackout_end_wrap,
        textvariable=blackout_end_date_var,
        state="readonly",
        width=12,
    )
    blackout_end_date_box.grid(row=0, column=0, sticky="ew")
    blackout_end_time_box = ttk.Combobox(
        blackout_end_wrap,
        textvariable=blackout_end_time_var,
        values=blackout_time_values,
        state="readonly",
        width=7,
    )
    blackout_end_time_box.grid(row=0, column=1, sticky="w", padx=(6, 0))

    ttk.Label(blackout_box, text="Причина", style="CardSubtle.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 0))
    ttk.Entry(blackout_box, textvariable=blackout_title_var).grid(
        row=2,
        column=1,
        columnspan=3,
        sticky="ew",
        padx=(6, 12),
        pady=(8, 0),
    )
    blackout_add_button = ttk.Button(blackout_box, text="Додати blackout", style="Primary.TButton")
    blackout_add_button.grid(row=2, column=5, sticky="w", padx=(6, 8), pady=(8, 0))
    blackout_delete_button = ttk.Button(blackout_box, text="Видалити", style="Secondary.TButton")
    blackout_delete_button.grid(row=2, column=6, sticky="w", padx=(0, 8), pady=(8, 0))
    blackout_reload_button = ttk.Button(blackout_box, text="Оновити", style="Secondary.TButton")
    blackout_reload_button.grid(row=2, column=7, sticky="w", pady=(8, 0))

    ttk.Label(blackout_box, text="Пакет: з дати", style="CardSubtle.TLabel").grid(row=3, column=0, sticky="w", pady=(8, 0))
    blackout_batch_start_date_box = ttk.Combobox(
        blackout_box,
        textvariable=blackout_batch_start_date_var,
        state="readonly",
        width=12,
    )
    blackout_batch_start_date_box.grid(row=3, column=1, sticky="w", padx=(6, 12), pady=(8, 0))
    ttk.Label(blackout_box, text="по дату", style="CardSubtle.TLabel").grid(row=3, column=2, sticky="w", pady=(8, 0))
    blackout_batch_end_date_box = ttk.Combobox(
        blackout_box,
        textvariable=blackout_batch_end_date_var,
        state="readonly",
        width=12,
    )
    blackout_batch_end_date_box.grid(row=3, column=3, sticky="w", padx=(6, 12), pady=(8, 0))
    ttk.Label(blackout_box, text="час", style="CardSubtle.TLabel").grid(row=3, column=4, sticky="w", pady=(8, 0))
    blackout_batch_start_time_box = ttk.Combobox(
        blackout_box,
        textvariable=blackout_batch_start_time_var,
        values=blackout_time_values,
        state="readonly",
        width=8,
    )
    blackout_batch_start_time_box.grid(row=3, column=5, sticky="w", padx=(6, 6), pady=(8, 0))
    blackout_batch_end_time_box = ttk.Combobox(
        blackout_box,
        textvariable=blackout_batch_end_time_var,
        values=blackout_time_values,
        state="readonly",
        width=8,
    )
    blackout_batch_end_time_box.grid(row=3, column=6, sticky="w", padx=(0, 12), pady=(8, 0))
    blackout_batch_button = ttk.Button(blackout_box, text="Додати пакет", style="Primary.TButton")
    blackout_batch_button.grid(row=3, column=7, sticky="w", pady=(8, 0))

    ttk.Label(blackout_box, text="Дні тижня", style="CardSubtle.TLabel").grid(
        row=4, column=0, sticky="w", pady=(8, 0)
    )
    blackout_weekdays_wrap = ttk.Frame(blackout_box, style="Card.TFrame")
    blackout_weekdays_wrap.grid(row=4, column=1, columnspan=3, sticky="w", padx=(6, 12), pady=(8, 0))
    blackout_weekday_buttons: dict[int, tk.Button] = {}

    def refresh_blackout_weekday_button(weekday: int) -> None:
        button = blackout_weekday_buttons.get(weekday)
        if button is None:
            return
        selected = bool(blackout_batch_weekday_vars[weekday].get())
        if selected:
            button.configure(
                bg=self.theme.ACCENT,
                fg=self.theme.TEXT_LIGHT,
                activebackground=self.theme.ACCENT_HOVER,
                activeforeground=self.theme.TEXT_LIGHT,
            )
        else:
            button.configure(
                bg=self.theme.SURFACE_ALT,
                fg=self.theme.TEXT_PRIMARY,
                activebackground=self.theme.SECONDARY_HOVER,
                activeforeground=self.theme.TEXT_PRIMARY,
            )

    def toggle_blackout_weekday(weekday: int) -> None:
        current = bool(blackout_batch_weekday_vars[weekday].get())
        blackout_batch_weekday_vars[weekday].set(not current)
        refresh_blackout_weekday_button(weekday)

    for idx, (weekday, label) in enumerate(blackout_weekday_labels):
        toggle_button = tk.Button(
            blackout_weekdays_wrap,
            text=label,
            width=4,
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            command=lambda day=weekday: toggle_blackout_weekday(day),
        )
        toggle_button.pack(side=tk.LEFT, padx=(0 if idx == 0 else 8, 0))
        blackout_weekday_buttons[weekday] = toggle_button
        refresh_blackout_weekday_button(weekday)

    blackout_table_wrap = ttk.Frame(blackout_box, style="Card.TFrame")
    blackout_table_wrap.grid(row=5, column=0, columnspan=8, sticky="ew", pady=(10, 0))
    blackout_table_style = "BlackoutFilters.Treeview"
    blackout_style = ttk.Style(self.root)
    try:
        blackout_style.layout(
            f"{blackout_table_style}.Heading",
            [
                ("Treeheading.cell", {"sticky": "nswe"}),
                (
                    "Treeheading.border",
                    {
                        "sticky": "nswe",
                        "children": [
                            (
                                "Treeheading.padding",
                                {
                                    "sticky": "nswe",
                                    "children": [
                                        ("Treeheading.image", {"side": "right", "sticky": "se"}),
                                        ("Treeheading.text", {"sticky": "we"}),
                                    ],
                                },
                            )
                        ],
                    },
                ),
            ],
        )
    except tk.TclError:
        pass
    blackout_table = ttk.Treeview(
        blackout_table_wrap,
        columns=blackout_table_columns,
        show="headings",
        height=5,
        style=blackout_table_style,
    )
    for column_id in blackout_table_columns:
        blackout_table.heading(column_id, text=blackout_heading_titles[column_id])
    blackout_table.column("resource", width=280, anchor="w")
    blackout_table.column("start", width=160, anchor="center")
    blackout_table.column("end", width=160, anchor="center")
    blackout_table.column("title", width=300, anchor="w")
    blackout_table.pack(side=tk.LEFT, fill=tk.X, expand=True)
    blackout_scroll = ttk.Scrollbar(
        blackout_table_wrap,
        orient=tk.VERTICAL,
        command=blackout_table.yview,
        style="App.Vertical.TScrollbar",
    )
    blackout_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    blackout_table.configure(yscrollcommand=blackout_scroll.set)
    blackout_filter_icon_image_source = Image.new("RGBA", (18, 18), (0, 0, 0, 0))
    blackout_filter_icon_draw = ImageDraw.Draw(blackout_filter_icon_image_source)
    blackout_filter_icon_draw.polygon(
        [(7, 6), (16, 6), (12, 10), (12, 15), (10, 15), (10, 10)],
        fill=self.theme.ACCENT,
    )
    blackout_filter_icon = ImageTk.PhotoImage(blackout_filter_icon_image_source)

    requirements_box = ttk.LabelFrame(parent, text="Вимоги", padding=10)
    requirements_box.pack(fill=tk.X, pady=(8, 0))
    requirements_actions = ttk.Frame(requirements_box, style="Card.TFrame")
    requirements_actions.pack(fill=tk.X, pady=(0, 6))
    requirements_refresh_button = ttk.Button(requirements_actions, text="Оновити")
    requirements_refresh_button.pack(side=tk.LEFT, padx=(0, 8))
    requirements_edit_button = ttk.Button(requirements_actions, text="Редагувати")
    requirements_edit_button.pack(side=tk.LEFT, padx=(0, 8))
    requirements_delete_button = ttk.Button(requirements_actions, text="Видалити")
    requirements_delete_button.pack(side=tk.LEFT)

    requirements_table_wrap = ttk.Frame(requirements_box, style="Card.TFrame")
    requirements_table_wrap.pack(fill=tk.X)
    requirements_table = ttk.Treeview(
        requirements_table_wrap,
        columns=("name", "params", "teacher", "target", "room"),
        show="headings",
        height=6,
    )
    requirements_table.heading("name", text="Назва")
    requirements_table.heading("params", text="Параметри")
    requirements_table.heading("teacher", text="Викладачі")
    requirements_table.heading("target", text="Цілі")
    requirements_table.heading("room", text="Аудиторія")
    requirements_table.column("name", width=220, anchor="w")
    requirements_table.column("params", width=180, anchor="center")
    requirements_table.column("teacher", width=190, anchor="w")
    requirements_table.column("target", width=190, anchor="w")
    requirements_table.column("room", width=290, anchor="w")
    requirements_table.pack(side=tk.LEFT, fill=tk.X, expand=True)
    requirements_scroll = ttk.Scrollbar(
        requirements_table_wrap,
        orient=tk.VERTICAL,
        command=requirements_table.yview,
        style="App.Vertical.TScrollbar",
    )
    requirements_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    requirements_table.configure(yscrollcommand=requirements_scroll.set)

    parent = setup_tab_views["soft"]

    policy_box = ttk.LabelFrame(parent, text="Політика генерації", padding=10)
    policy_box.pack(fill=tk.X, pady=(8, 0))
    ttk.Label(policy_box, text="Макс пар/день").grid(row=0, column=0, sticky="w")
    ttk.Entry(policy_box, textvariable=policy_max_sessions_var, width=8).grid(row=0, column=1, sticky="w", padx=(6, 12))
    ttk.Label(policy_box, text="Макс підряд блоків").grid(row=0, column=2, sticky="w")
    ttk.Entry(policy_box, textvariable=policy_max_consecutive_var, width=8).grid(row=0, column=3, sticky="w", padx=(6, 12))
    ttk.Checkbutton(policy_box, text="Заборонити вікна", variable=policy_no_gaps_var).grid(
        row=0, column=4, sticky="w", padx=(0, 12)
    )
    ttk.Label(policy_box, text="Перевага часу").grid(row=0, column=5, sticky="w")
    ttk.Combobox(
        policy_box,
        textvariable=policy_time_pref_var,
        values=list(policy_time_pref_options.keys()),
        state="readonly",
        width=10,
    ).grid(row=0, column=6, sticky="w", padx=(6, 12))
    ttk.Label(policy_box, text="W час").grid(row=1, column=0, sticky="w", pady=(8, 0))
    ttk.Entry(policy_box, textvariable=policy_weight_time_var, width=8).grid(row=1, column=1, sticky="w", padx=(6, 12), pady=(8, 0))
    ttk.Label(policy_box, text="W компактність").grid(row=1, column=2, sticky="w", pady=(8, 0))
    ttk.Entry(policy_box, textvariable=policy_weight_compact_var, width=8).grid(
        row=1, column=3, sticky="w", padx=(6, 12), pady=(8, 0)
    )
    ttk.Label(policy_box, text="W переходи").grid(row=1, column=4, sticky="w", pady=(8, 0))
    ttk.Entry(policy_box, textvariable=policy_weight_building_var, width=8).grid(
        row=1, column=5, sticky="w", padx=(6, 12), pady=(8, 0)
    )
    policy_save_button = ttk.Button(policy_box, text="Зберегти політику")
    policy_save_button.grid(row=1, column=6, sticky="w", pady=(8, 0))

    parent = setup_tab_views["manual"]
    manual_crud_box = ttk.LabelFrame(parent, text="Ручне керування (Manual/CRUD)", padding=10)
    manual_crud_box.pack(fill=tk.X)
    manual_crud_body = ttk.Frame(manual_crud_box, style="Card.TFrame")
    manual_crud_body.pack(fill=tk.X)
    parent = manual_crud_body

    manual_box = ttk.LabelFrame(parent, text="Ручний слот", padding=10)
    manual_box.pack(fill=tk.X, pady=(8, 0))
    ttk.Label(manual_box, text="Вимога").grid(row=0, column=0, sticky="w")
    manual_requirement_box = ttk.Combobox(
        manual_box,
        textvariable=manual_requirement_var,
        width=34,
        state="readonly",
    )
    manual_requirement_box.grid(row=0, column=1, sticky="w", padx=(6, 12))
    ttk.Label(manual_box, text="Дата").grid(row=0, column=2, sticky="w")
    ttk.Entry(manual_box, textvariable=manual_date_var, width=12).grid(row=0, column=3, sticky="w", padx=(6, 12))
    ttk.Label(manual_box, text="Номер блоку").grid(row=0, column=4, sticky="w")
    ttk.Entry(manual_box, textvariable=manual_order_var, width=8).grid(row=0, column=5, sticky="w", padx=(6, 12))
    ttk.Label(manual_box, text="Аудиторія").grid(row=0, column=6, sticky="w")
    manual_room_box = ttk.Combobox(manual_box, textvariable=manual_room_var, width=24, state="readonly")
    manual_room_box.grid(row=0, column=7, sticky="w", padx=(6, 12))
    ttk.Checkbutton(manual_box, text="Закріпити (LOCK)", variable=manual_lock_var).grid(row=1, column=0, sticky="w", pady=(8, 0))
    manual_add_button = ttk.Button(manual_box, text="Додати ручний слот")
    manual_add_button.grid(row=1, column=1, sticky="w", pady=(8, 0))
    manual_update_button = ttk.Button(manual_box, text="Оновити вибране")
    manual_update_button.grid(row=1, column=2, sticky="w", padx=(8, 0), pady=(8, 0))

    entries_box = ttk.LabelFrame(parent, text="Заняття (CRUD)", padding=10)
    entries_box.pack(fill=tk.X, pady=(8, 0))
    entries_actions = ttk.Frame(entries_box, style="Card.TFrame")
    entries_actions.pack(fill=tk.X, pady=(0, 6))
    entries_refresh_button = ttk.Button(entries_actions, text="Оновити")
    entries_refresh_button.pack(side=tk.LEFT, padx=(0, 8))
    entries_prefill_button = ttk.Button(entries_actions, text="У поля ручного слота")
    entries_prefill_button.pack(side=tk.LEFT, padx=(0, 8))
    entries_lock_button = ttk.Button(entries_actions, text="LOCK")
    entries_lock_button.pack(side=tk.LEFT, padx=(0, 8))
    entries_unlock_button = ttk.Button(entries_actions, text="UNLOCK")
    entries_unlock_button.pack(side=tk.LEFT, padx=(0, 8))
    entries_delete_button = ttk.Button(entries_actions, text="Видалити")
    entries_delete_button.pack(side=tk.LEFT)

    entries_table_wrap = ttk.Frame(entries_box, style="Card.TFrame")
    entries_table_wrap.pack(fill=tk.X)
    entries_table = ttk.Treeview(
        entries_table_wrap,
        columns=("id", "requirement", "slot", "room", "flags"),
        show="headings",
        height=6,
    )
    entries_table.heading("id", text="ID")
    entries_table.heading("requirement", text="Вимога")
    entries_table.heading("slot", text="Слот")
    entries_table.heading("room", text="Аудиторія")
    entries_table.heading("flags", text="Ознаки")
    entries_table.column("id", width=70, anchor="center")
    entries_table.column("requirement", width=280, anchor="w")
    entries_table.column("slot", width=230, anchor="center")
    entries_table.column("room", width=240, anchor="w")
    entries_table.column("flags", width=160, anchor="center")
    entries_table.pack(side=tk.LEFT, fill=tk.X, expand=True)
    entries_scroll = ttk.Scrollbar(
        entries_table_wrap,
        orient=tk.VERTICAL,
        command=entries_table.yview,
        style="App.Vertical.TScrollbar",
    )
    entries_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    entries_table.configure(yscrollcommand=entries_scroll.set)

    parent = setup_tab_views["manual"]

    coverage_box = ttk.LabelFrame(parent, text="Coverage dashboard", padding=10)
    coverage_box.pack(fill=tk.X, pady=(8, 0))
    coverage_actions = ttk.Frame(coverage_box, style="Card.TFrame")
    coverage_actions.pack(fill=tk.X, pady=(0, 6))
    ttk.Label(coverage_actions, textvariable=coverage_summary_var, style="CardSubtle.TLabel").pack(side=tk.LEFT)
    coverage_refresh_button = ttk.Button(coverage_actions, text="Оновити coverage")
    coverage_refresh_button.pack(side=tk.RIGHT)
    coverage_table_wrap = ttk.Frame(coverage_box, style="Card.TFrame")
    coverage_table_wrap.pack(fill=tk.X)
    coverage_table = ttk.Treeview(
        coverage_table_wrap,
        columns=("reason", "requirements", "missing", "message"),
        show="headings",
        height=4,
    )
    coverage_table.heading("reason", text="Причина")
    coverage_table.heading("requirements", text="Вимог")
    coverage_table.heading("missing", text="Не закрито занять")
    coverage_table.heading("message", text="Приклад")
    coverage_table.column("reason", width=170, anchor="center")
    coverage_table.column("requirements", width=90, anchor="center")
    coverage_table.column("missing", width=150, anchor="center")
    coverage_table.column("message", width=520, anchor="w")
    coverage_table.pack(side=tk.LEFT, fill=tk.X, expand=True)
    coverage_scroll = ttk.Scrollbar(
        coverage_table_wrap,
        orient=tk.VERTICAL,
        command=coverage_table.yview,
        style="App.Vertical.TScrollbar",
    )
    coverage_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    coverage_table.configure(yscrollcommand=coverage_scroll.set)

    def _bind_table_wheel(widget: tk.Widget, view_get, view_set) -> None:
        table_wheel, table_wheel_up, table_wheel_down = _create_smooth_wheel_handlers(
            view_get,
            view_set,
            gain=0.14,
        )
        wheel_f_raw = _with_fallback(table_wheel, view_get, schedule_wheel)
        up_f_raw = _with_fallback(table_wheel_up, view_get, schedule_wheel_up)
        down_f_raw = _with_fallback(table_wheel_down, view_get, schedule_wheel_down)

        def wheel_f(event: tk.Event) -> str:
            dismiss_schedule_popdowns()
            return wheel_f_raw(event)

        def up_f(event: tk.Event) -> str:
            dismiss_schedule_popdowns()
            return up_f_raw(event)

        def down_f(event: tk.Event) -> str:
            dismiss_schedule_popdowns()
            return down_f_raw(event)

        widget.bind("<MouseWheel>", wheel_f, add="+")
        widget.bind("<Button-4>", up_f, add="+")
        widget.bind("<Button-5>", down_f, add="+")

    _bind_table_wheel(blackout_table, blackout_table.yview, blackout_table.yview_moveto)
    _bind_table_wheel(requirements_table, requirements_table.yview, requirements_table.yview_moveto)
    _bind_table_wheel(entries_table, entries_table.yview, entries_table.yview_moveto)
    _bind_table_wheel(coverage_table, coverage_table.yview, coverage_table.yview_moveto)

    _bind_wheel_recursive(
        schedule_body,
        schedule_wheel,
        schedule_wheel_up,
        schedule_wheel_down,
        skip_widgets={blackout_table, requirements_table, entries_table, coverage_table},
    )

    parent = schedule_views["setup"]
    buttons = ttk.Frame(parent, style="Card.TFrame")
    buttons.pack(fill=tk.X, pady=(8, 8))

    status = ttk.Label(parent, textvariable=status_var, anchor="w", style="CardSubtle.TLabel")
    status.pack(fill=tk.X)

    def parse_period_id() -> int:
        raw = period_var.get().strip()
        if not raw:
            raise ValueError("Оберіть період.")
        return int(raw.split("|", maxsplit=1)[0].strip())

    def parse_scenario_id(raw: str) -> int | None:
        value = raw.strip()
        if not value or value == "Опублікований":
            return None
        return int(value.split("|", maxsplit=1)[0].strip())

    def selected_scenario_id() -> int | None:
        return parse_scenario_id(scenario_var.get())

    def selected_plan_id() -> int:
        raw = plan_sync_var.get().strip()
        if not raw:
            raise ValueError("Оберіть навчальний план.")
        return parse_prefixed_id(raw, field_name="навчальний план")

    def parse_week_start() -> date | None:
        raw = week_start_var.get().strip()
        if not raw:
            return None
        start_by_label = week_start_state.get("start_by_label", {})
        if isinstance(start_by_label, dict):
            resolved = start_by_label.get(raw)
            if isinstance(resolved, date):
                return resolved
        if "|" in raw:
            tail = raw.split("|", maxsplit=1)[1].strip()
            start_part = tail.split("..", maxsplit=1)[0].strip()
            return date.fromisoformat(start_part)
        if "•" in raw and "—" in raw:
            right = raw.split("•", maxsplit=1)[1].strip()
            start_part = right.split("—", maxsplit=1)[0].strip()
            return date.fromisoformat(start_part)
        return date.fromisoformat(raw)

    def parse_prefixed_id(raw: str, *, field_name: str) -> int:
        value = raw.strip()
        if not value or "|" not in value:
            raise ValueError(f"Оберіть '{field_name}'.")
        return int(value.split("|", maxsplit=1)[0].strip())

    def selected_plan_ids() -> list[int]:
        raw_ids = plan_sync_state.get("selected_ids", [])
        if not isinstance(raw_ids, list):
            return []
        resolved: list[int] = []
        for value in raw_ids:
            try:
                resolved.append(int(value))
            except (TypeError, ValueError):
                continue
        return resolved

    def refresh_plan_selection_controls(*, plans_count: int | None = None) -> None:
        total_plans = plans_count
        if total_plans is None:
            raw_items = plan_sync_state.get("items", [])
            if isinstance(raw_items, list):
                total_plans = len(raw_items)
            else:
                total_plans = 0
        selected_ids = selected_plan_ids()
        has_plans = total_plans > 0
        has_selected = bool(selected_ids)
        has_list_selection = bool(plan_selected_listbox.curselection())
        can_add = has_plans and bool(plan_sync_var.get().strip())

        plan_add_button.configure(state=("normal" if can_add else "disabled"))
        plan_remove_button.configure(state=("normal" if has_list_selection else "disabled"))
        plan_clear_button.configure(state=("normal" if has_selected else "disabled"))
        plan_sync_selected_button.configure(state=("normal" if has_selected else "disabled"))
        plan_sync_all_button.configure(state=("normal" if has_plans else "disabled"))

        plan_sync_hint_var.set(
            f"Активних планів: {total_plans}. "
            f"У виборі для синхронізації: {len(selected_ids)}."
        )

    def render_plan_selection() -> None:
        raw_items = plan_sync_state.get("items", [])
        items = raw_items if isinstance(raw_items, list) else []
        plan_by_id: dict[int, dict[str, object]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                plan_by_id[int(item["id"])] = item
            except (KeyError, TypeError, ValueError):
                continue

        normalized_selected = [plan_id for plan_id in selected_plan_ids() if plan_id in plan_by_id]
        plan_sync_state["selected_ids"] = normalized_selected

        selected_index = plan_selected_listbox.curselection()
        selected_offset = int(selected_index[0]) if selected_index else None
        plan_selected_listbox.delete(0, tk.END)
        for plan_id in normalized_selected:
            plan_name = str(plan_by_id[plan_id].get("name", "")).strip()
            plan_selected_listbox.insert(tk.END, f"{plan_id} | {plan_name}")
        if selected_offset is not None and 0 <= selected_offset < len(normalized_selected):
            plan_selected_listbox.selection_set(selected_offset)
        refresh_plan_selection_controls(plans_count=len(plan_by_id))

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

    def parse_non_negative_int(raw: str, *, field_name: str) -> int:
        value = raw.strip()
        if not value:
            raise ValueError(f"Заповніть поле '{field_name}'.")
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"Поле '{field_name}' має бути цілим числом.") from exc
        if parsed < 0:
            raise ValueError(f"Поле '{field_name}' має бути невід'ємним.")
        return parsed

    def parse_datetime_input(raw: str, *, field_name: str) -> datetime:
        value = raw.strip()
        if not value:
            raise ValueError(f"Заповніть поле '{field_name}'.")
        normalized = value.replace("T", " ")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"Поле '{field_name}' має формат YYYY-MM-DD HH:MM.") from exc

    def parse_date_input(raw: str, *, field_name: str) -> date:
        value = raw.strip()
        if not value:
            raise ValueError(f"Заповніть поле '{field_name}'.")
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Поле '{field_name}' має формат YYYY-MM-DD.") from exc

    def parse_time_input(raw: str, *, field_name: str) -> time:
        value = raw.strip()
        if not value:
            raise ValueError(f"Заповніть поле '{field_name}'.")
        try:
            return time.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Поле '{field_name}' має формат HH:MM.") from exc

    def period_weeks_count(start_date: date, end_date: date) -> int:
        days_count = (end_date - start_date).days + 1
        return max(1, (days_count + 6) // 7)

    def period_label(item: dict[str, object]) -> str:
        period_id = int(item["id"])
        name = str(item.get("name") or "").strip()
        if name:
            return f"{period_id} | {name}"
        return f"{period_id} | Період #{period_id}"

    def close_period_menu() -> None:
        popup = period_state.get("menu")
        if popup is None:
            return
        try:
            if isinstance(popup, tk.Toplevel) and popup.winfo_exists():
                try:
                    popup.grab_release()
                except tk.TclError:
                    pass
                popup.destroy()
        except tk.TclError:
            pass
        period_state["menu"] = None

    def close_selector_menu(selector_state: dict[str, object]) -> None:
        popup = selector_state.get("menu")
        if popup is None:
            return
        try:
            if isinstance(popup, tk.Toplevel) and popup.winfo_exists():
                try:
                    popup.grab_release()
                except tk.TclError:
                    pass
                popup.destroy()
        except tk.TclError:
            pass
        selector_state["menu"] = None

    def close_all_header_menus(*, keep: dict[str, object] | None = None) -> None:
        close_period_menu()
        close_blackout_filter_menu()
        for state in (
            week_selector_state,
            group_selector_state,
            scenario_selector_state,
            scenario_compare_selector_state,
        ):
            if keep is state:
                continue
            close_selector_menu(state)

    def track_popup_geometry(
        *,
        popup: tk.Toplevel,
        anchor_widget: tk.Widget,
        width: int,
        height: int,
        close_callback,
        clip_widget: tk.Widget | None = None,
        poll_ms: int = 90,
    ) -> None:
        def _apply() -> None:
            if not popup.winfo_exists():
                return
            try:
                if not anchor_widget.winfo_exists() or not anchor_widget.winfo_ismapped():
                    close_callback()
                    return

                anchor_left = anchor_widget.winfo_rootx()
                anchor_top = anchor_widget.winfo_rooty()
                anchor_right = anchor_left + anchor_widget.winfo_width()
                anchor_bottom = anchor_top + anchor_widget.winfo_height()

                if clip_widget is not None:
                    if not clip_widget.winfo_exists() or not clip_widget.winfo_ismapped():
                        close_callback()
                        return
                    clip_left = clip_widget.winfo_rootx()
                    clip_top = clip_widget.winfo_rooty()
                    clip_right = clip_left + clip_widget.winfo_width()
                    clip_bottom = clip_top + clip_widget.winfo_height()
                    inside_clip = not (
                        anchor_right <= clip_left
                        or anchor_left >= clip_right
                        or anchor_bottom <= clip_top
                        or anchor_top >= clip_bottom
                    )
                    if not inside_clip:
                        close_callback()
                        return

                self.root.update_idletasks()
                anchor_widget.update_idletasks()
                x_pos = anchor_left
                y_pos = anchor_top + anchor_widget.winfo_height()
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                x_pos = max(0, min(x_pos, screen_width - width - 4))
                if y_pos + height > screen_height:
                    y_pos = max(0, anchor_top - height - 2)
                popup.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
                popup.lift()
                popup.after(poll_ms, _apply)
            except tk.TclError:
                close_callback()

        _apply()

    def open_selector_popup(
        *,
        selector_state: dict[str, object],
        anchor_widget: tk.Widget,
        values: list[str],
        selected_value: str,
        on_pick,
        searchable: bool = False,
    ) -> None:
        if not values:
            return
        popup = selector_state.get("menu")
        if isinstance(popup, tk.Toplevel) and popup.winfo_exists():
            close_selector_menu(selector_state)
            return

        close_all_header_menus(keep=selector_state)
        popup = tk.Toplevel(self.root)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.configure(bg=self.theme.BORDER)
        selector_state["menu"] = popup
        popup.bind("<Escape>", lambda _e: close_selector_menu(selector_state), add="+")

        shell = tk.Frame(popup, bg=self.theme.SURFACE, bd=0, highlightthickness=0)
        shell.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        search_var = tk.StringVar(value="")
        filtered_values: list[str] = list(values)
        search_entry: tk.Entry | None = None

        if searchable:
            search_row = tk.Frame(shell, bg=self.theme.SURFACE_ALT, bd=0, highlightthickness=0)
            search_row.pack(fill=tk.X, padx=6, pady=(6, 4))
            search_entry = tk.Entry(
                search_row,
                textvariable=search_var,
                relief=tk.FLAT,
                bd=0,
                highlightthickness=1,
                highlightbackground=self.theme.BORDER,
                highlightcolor=self.theme.ACCENT,
                bg=self.theme.SURFACE,
                fg=self.theme.TEXT_PRIMARY,
                insertbackground=self.theme.TEXT_PRIMARY,
                font=("Segoe UI", 10),
            )
            search_entry.pack(fill=tk.X, ipady=6)

        list_wrap = tk.Frame(shell, bg=self.theme.SURFACE, bd=0, highlightthickness=0)
        list_wrap.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        listbox = tk.Listbox(
            list_wrap,
            activestyle="none",
            exportselection=False,
            selectmode=tk.SINGLE,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            highlightcolor=self.theme.ACCENT,
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            selectbackground=self.theme.ACCENT,
            selectforeground=self.theme.TEXT_LIGHT,
            font=("Segoe UI", 10),
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll = ttk.Scrollbar(
            list_wrap,
            orient=tk.VERTICAL,
            command=listbox.yview,
            style="App.Vertical.TScrollbar",
        )
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=list_scroll.set)

        def render_values() -> None:
            nonlocal filtered_values
            query = search_var.get().strip().casefold()
            if query:
                filtered_values = [value for value in values if query in value.casefold()]
            else:
                filtered_values = list(values)
            listbox.delete(0, tk.END)
            for value in filtered_values:
                listbox.insert(tk.END, value)
            if selected_value in filtered_values:
                selected_index = filtered_values.index(selected_value)
                listbox.selection_set(selected_index)
                listbox.see(selected_index)
            elif filtered_values:
                listbox.selection_set(0)
                listbox.see(0)

        def commit_selection(_event=None) -> str:
            selected = listbox.curselection()
            if not selected:
                return "break"
            picked_value = str(listbox.get(selected[0]))
            close_selector_menu(selector_state)
            on_pick(picked_value)
            return "break"

        def close_on_outside_click(event: tk.Event) -> str | None:
            if not popup.winfo_exists():
                return None
            x_root = int(getattr(event, "x_root", 0))
            y_root = int(getattr(event, "y_root", 0))
            left = popup.winfo_rootx()
            top = popup.winfo_rooty()
            right = left + popup.winfo_width()
            bottom = top + popup.winfo_height()
            if left <= x_root < right and top <= y_root < bottom:
                return None
            close_selector_menu(selector_state)
            return "break"

        listbox.bind("<Return>", commit_selection, add="+")
        listbox.bind("<Double-Button-1>", commit_selection, add="+")
        listbox.bind("<ButtonRelease-1>", commit_selection, add="+")
        popup.bind("<ButtonPress-1>", close_on_outside_click, add="+")
        if searchable and search_entry is not None:
            search_var.trace_add("write", lambda *_args: render_values())
            search_entry.bind("<Down>", lambda _e: (listbox.focus_set(), "break")[1], add="+")

        render_values()
        popup.update_idletasks()
        self.root.update_idletasks()
        anchor_widget.update_idletasks()
        base_width = max(anchor_widget.winfo_width(), 320 if searchable else 260)
        rows_count = max(1, min(9, len(filtered_values)))
        base_height = rows_count * 24 + (52 if searchable else 10)

        popup.deiconify()
        track_popup_geometry(
            popup=popup,
            anchor_widget=anchor_widget,
            width=base_width,
            height=base_height,
            close_callback=lambda: close_selector_menu(selector_state),
            clip_widget=schedule_canvas,
        )
        popup.grab_set()
        if searchable and search_entry is not None:
            search_entry.focus_set()
        else:
            listbox.focus_set()

    def selected_period_item() -> dict[str, object] | None:
        raw = period_var.get().strip()
        if not raw or "|" not in raw:
            return None
        try:
            period_id = int(raw.split("|", maxsplit=1)[0].strip())
        except ValueError:
            return None
        period_by_id = period_state.get("by_id", {})
        if isinstance(period_by_id, dict):
            item = period_by_id.get(period_id)
            if isinstance(item, dict):
                return item
        return None

    def refresh_week_start_selector(*, keep_selection: bool = True) -> None:
        selected_period = selected_period_item()
        previous_raw = week_start_var.get().strip()
        labels: list[str] = []
        start_by_label: dict[str, date] = {}
        label_by_iso: dict[str, str] = {}
        current_label: str | None = None
        if isinstance(selected_period, dict):
            period_start = selected_period["start_date"]
            period_end = selected_period["end_date"]
            weeks_count = int(selected_period["weeks_count"])
            today = date.today()
            for week_index in range(1, weeks_count + 1):
                week_start = period_start + timedelta(days=(week_index - 1) * 7)
                week_end = min(period_end, week_start + timedelta(days=6))
                is_current_week = week_start <= today <= week_end
                label = f"Тиждень {week_index} • {week_start.isoformat()} — {week_end.isoformat()}"
                if is_current_week:
                    label += " • поточний"
                    current_label = label
                labels.append(label)
                start_by_label[label] = week_start
                label_by_iso[week_start.isoformat()] = label

        week_start_state["labels"] = labels
        week_start_state["start_by_label"] = start_by_label
        week_start_state["label_by_iso"] = label_by_iso
        week_selector_state["values"] = labels
        is_enabled = bool(labels)
        week_selector_button.configure(state=("normal" if is_enabled else "disabled"))
        week_selector_label.configure(fg=self.theme.TEXT_PRIMARY if is_enabled else self.theme.TEXT_MUTED)

        selected_label: str = ""
        if keep_selection and previous_raw in start_by_label:
            selected_label = previous_raw
        elif keep_selection and previous_raw in label_by_iso:
            selected_label = label_by_iso[previous_raw]
        elif current_label is not None:
            selected_label = current_label
        elif labels:
            selected_label = labels[0]
        week_start_var.set(selected_label)

    def select_period(period_id: int | None, *, trigger_reload: bool) -> None:
        period_by_id = period_state.get("by_id", {})
        if period_id is None or not isinstance(period_by_id, dict) or period_id not in period_by_id:
            period_var.set("")
            refresh_week_start_selector(keep_selection=False)
            if trigger_reload:
                on_period_changed()
            return
        item = period_by_id[period_id]
        if isinstance(item, dict):
            period_var.set(period_label(item))
        refresh_week_start_selector(keep_selection=True)
        if trigger_reload:
            on_period_changed()

    def refresh_period_selector_state() -> None:
        items = period_state.get("items", [])
        has_periods = isinstance(items, list) and bool(items)
        close_period_menu()
        period_selector_main.pack_forget()
        period_empty_create_button.pack_forget()
        if has_periods:
            period_selector_main.pack(fill=tk.X)
            period_toggle_button.configure(state="normal")
            period_display.bind("<Button-1>", lambda _e: open_period_menu())
        else:
            period_var.set("")
            period_empty_create_button.pack(fill=tk.X)

    def list_week_template_choices(*, include_ids: set[int] | None = None) -> tuple[list[str], dict[str, int], dict[int, str]]:
        include_ids = include_ids or set()
        with session_scope() as session:
            overview = TemplateController(session=session).load_templates_overview(company_id)
        templates = sorted(
            list(overview.week_templates),
            key=lambda item: (bool(item.is_archived), str(item.name).lower(), int(item.id)),
        )
        visible = [item for item in templates if (not bool(item.is_archived)) or (int(item.id) in include_ids)]
        if not visible:
            raise ValueError("Немає доступних шаблонів тижня. Створіть їх у вкладці шаблонів.")

        labels: list[str] = []
        by_label: dict[str, int] = {}
        by_id: dict[int, str] = {}
        for item in visible:
            archived_suffix = " [архів]" if bool(item.is_archived) else ""
            label = f"{int(item.id)} | {item.name}{archived_suffix}"
            labels.append(label)
            by_label[label] = int(item.id)
            by_id[int(item.id)] = label
        return labels, by_label, by_id

    def open_period_modal(*, period_id: int | None = None) -> None:
        existing = period_state.get("by_id", {}).get(period_id) if period_id is not None else None
        is_edit = isinstance(existing, dict)
        period_data = existing if is_edit else None
        include_template_ids: set[int] = set()
        if period_data is not None:
            week_map = period_data.get("week_pattern_by_week_index", {})
            if isinstance(week_map, dict):
                include_template_ids = {int(value) for value in week_map.values()}
        try:
            template_labels, template_id_by_label, template_label_by_id = list_week_template_choices(
                include_ids=include_template_ids
            )
        except Exception as exc:
            messagebox.showerror("Період", str(exc), parent=self.root)
            return

        if is_edit and period_data is not None:
            start_date = period_data["start_date"]
            weeks_default = int(period_data["weeks_count"])
            period_name_default = str(period_data.get("name") or "")
            existing_week_map = dict(period_data.get("week_pattern_by_week_index", {}))
        else:
            items = period_state.get("items", [])
            if isinstance(items, list) and items:
                last_period = items[-1]
                start_date = last_period["end_date"] + timedelta(days=1)
            else:
                start_date = date.today()
            weeks_default = 16
            period_name_default = ""
            default_template_id = template_id_by_label[template_labels[0]]
            existing_week_map = {index: default_template_id for index in range(1, weeks_default + 1)}

        modal = tk.Toplevel(self.root)
        modal.title("Редагувати період" if is_edit else "Створити період")
        modal.transient(self.root)
        modal.grab_set()
        modal.resizable(False, False)

        shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        ttk.Label(shell, text="Редагування періоду" if is_edit else "Створення періоду", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            shell,
            text="Оберіть назву, дату старту та кількість тижнів.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(2, 10))

        form = ttk.Frame(shell, style="Card.TFrame")
        form.pack(fill=tk.X)
        ttk.Label(form, text="Назва", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        period_name_var = tk.StringVar(value=period_name_default)
        ttk.Entry(form, textvariable=period_name_var, width=34).grid(row=0, column=1, sticky="w", padx=(8, 12))
        ttk.Label(form, text="Кількість тижнів", style="Card.TLabel").grid(row=0, column=2, sticky="w")
        weeks_count_var = tk.StringVar(value=str(weeks_default))
        ttk.Entry(form, textvariable=weeks_count_var, width=8).grid(row=0, column=3, sticky="w", padx=(8, 0))
        ttk.Label(form, text="Початок", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))

        start_year_var = tk.StringVar(value=str(start_date.year))
        start_month_var = tk.StringVar(value=f"{start_date.month:02d}")
        start_day_var = tk.StringVar(value=f"{start_date.day:02d}")

        years_pool = {start_date.year, date.today().year}
        items = period_state.get("items", [])
        if isinstance(items, list):
            for period_item in items:
                if not isinstance(period_item, dict):
                    continue
                item_start = period_item.get("start_date")
                if isinstance(item_start, date):
                    years_pool.add(item_start.year)
        year_values = [str(year) for year in range(min(years_pool) - 2, max(years_pool) + 5)]
        month_values = [f"{month:02d}" for month in range(1, 13)]

        start_date_row = ttk.Frame(form, style="Card.TFrame")
        start_date_row.grid(row=1, column=1, sticky="w", padx=(8, 12), pady=(8, 0))
        start_year_box = ttk.Combobox(
            start_date_row,
            textvariable=start_year_var,
            values=year_values,
            state="readonly",
            width=7,
        )
        start_year_box.pack(side=tk.LEFT)
        ttk.Label(start_date_row, text="-", style="CardSubtle.TLabel").pack(side=tk.LEFT, padx=4)
        start_month_box = ttk.Combobox(
            start_date_row,
            textvariable=start_month_var,
            values=month_values,
            state="readonly",
            width=4,
        )
        start_month_box.pack(side=tk.LEFT)
        ttk.Label(start_date_row, text="-", style="CardSubtle.TLabel").pack(side=tk.LEFT, padx=4)
        start_day_box = ttk.Combobox(
            start_date_row,
            textvariable=start_day_var,
            values=[],
            state="readonly",
            width=4,
        )
        start_day_box.pack(side=tk.LEFT)

        period_range_var = tk.StringVar(value="")
        ttk.Label(form, textvariable=period_range_var, style="CardSubtle.TLabel").grid(
            row=1,
            column=2,
            columnspan=2,
            sticky="w",
            padx=(0, 0),
            pady=(8, 0),
        )

        quick_row = ttk.Frame(shell, style="Card.TFrame")
        quick_row.pack(fill=tk.X, pady=(10, 8))
        ttk.Label(quick_row, text="Швидке призначення", style="Card.TLabel").pack(side=tk.LEFT)
        quick_template_var = tk.StringVar(value=template_labels[0])
        ttk.Combobox(
            quick_row,
            textvariable=quick_template_var,
            values=template_labels,
            state="readonly",
            width=38,
        ).pack(side=tk.LEFT, padx=(8, 8))

        weeks_shell = ttk.Frame(shell, style="Card.TFrame")
        weeks_shell.pack(fill=tk.BOTH, expand=True)
        weeks_canvas = tk.Canvas(
            weeks_shell,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            height=260,
        )
        weeks_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        weeks_scroll = ttk.Scrollbar(
            weeks_shell,
            orient=tk.VERTICAL,
            command=weeks_canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        weeks_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        weeks_canvas.configure(yscrollcommand=weeks_scroll.set)
        weeks_body = ttk.Frame(weeks_canvas, style="Card.TFrame")
        weeks_window = weeks_canvas.create_window((0, 0), anchor="nw", window=weeks_body)

        week_choice_vars: list[tk.StringVar] = []

        def sync_weeks_canvas(_event=None) -> None:
            weeks_canvas.itemconfigure(weeks_window, width=max(1, weeks_canvas.winfo_width()))
            bbox = weeks_canvas.bbox("all")
            if bbox is not None:
                weeks_canvas.configure(scrollregion=bbox)

        weeks_body.bind("<Configure>", sync_weeks_canvas, add="+")
        weeks_canvas.bind("<Configure>", sync_weeks_canvas, add="+")

        def selected_period_start_date() -> date:
            year_raw = start_year_var.get().strip()
            month_raw = start_month_var.get().strip()
            day_raw = start_day_var.get().strip()
            if not year_raw or not month_raw or not day_raw:
                raise ValueError("Оберіть дату початку періоду.")
            try:
                return date(int(year_raw), int(month_raw), int(day_raw))
            except ValueError as exc:
                raise ValueError("Оберіть коректну дату початку періоду.") from exc

        def refresh_start_day_choices() -> None:
            try:
                year_num = int(start_year_var.get().strip())
                month_num = int(start_month_var.get().strip())
                if month_num < 1 or month_num > 12:
                    return
            except ValueError:
                return
            days_in_month = monthrange(year_num, month_num)[1]
            day_values = [f"{day:02d}" for day in range(1, days_in_month + 1)]
            start_day_box.configure(values=day_values)
            current_day = start_day_var.get().strip()
            if current_day not in day_values:
                start_day_var.set(f"{min(start_date.day, days_in_month):02d}")

        def refresh_period_range_preview() -> None:
            try:
                preview_start = selected_period_start_date()
            except ValueError:
                period_range_var.set("Період: —")
                return
            raw_weeks = weeks_count_var.get().strip()
            if not raw_weeks:
                period_range_var.set(f"Період: {preview_start.isoformat()}..—")
                return
            try:
                parsed_weeks = int(raw_weeks)
                if parsed_weeks <= 0:
                    raise ValueError
            except ValueError:
                period_range_var.set(f"Період: {preview_start.isoformat()}..—")
                return
            preview_end = preview_start + timedelta(days=parsed_weeks * 7 - 1)
            period_range_var.set(f"Період: {preview_start.isoformat()}..{preview_end.isoformat()}")

        def on_start_date_selection_changed(_event=None) -> None:
            refresh_start_day_choices()
            refresh_period_range_preview()

        start_year_box.bind("<<ComboboxSelected>>", on_start_date_selection_changed, add="+")
        start_month_box.bind("<<ComboboxSelected>>", on_start_date_selection_changed, add="+")
        start_day_box.bind("<<ComboboxSelected>>", lambda _event: refresh_period_range_preview(), add="+")
        weeks_count_var.trace_add("write", lambda *_args: refresh_period_range_preview())
        refresh_start_day_choices()
        refresh_period_range_preview()

        def rebuild_week_rows() -> None:
            for child in weeks_body.winfo_children():
                child.destroy()
            previous_values = [var.get().strip() for var in week_choice_vars]
            week_choice_vars.clear()

            weeks_count = parse_optional_positive_int(weeks_count_var.get(), field_name="Кількість тижнів")
            if weeks_count is None:
                raise ValueError("Вкажіть кількість тижнів.")
            default_template_id = template_id_by_label.get(quick_template_var.get().strip(), template_id_by_label[template_labels[0]])
            for week_index in range(1, weeks_count + 1):
                row = ttk.Frame(weeks_body, style="Card.TFrame")
                row.pack(fill=tk.X, pady=(0, 6))
                ttk.Label(row, text=f"Тиждень {week_index}", style="Card.TLabel").pack(side=tk.LEFT)
                if week_index <= len(previous_values) and previous_values[week_index - 1] in template_id_by_label:
                    selected_label = previous_values[week_index - 1]
                else:
                    mapped_template_id = int(existing_week_map.get(week_index, default_template_id))
                    selected_label = template_label_by_id.get(mapped_template_id, template_labels[0])
                var = tk.StringVar(value=selected_label)
                week_choice_vars.append(var)
                ttk.Combobox(
                    row,
                    textvariable=var,
                    values=template_labels,
                    state="readonly",
                    width=38,
                ).pack(side=tk.LEFT, padx=(8, 0))
            modal.after_idle(sync_weeks_canvas)

        def apply_quick_template() -> None:
            quick_label = quick_template_var.get().strip()
            if quick_label not in template_id_by_label:
                raise ValueError("Оберіть шаблон для швидкого призначення.")
            for var in week_choice_vars:
                var.set(quick_label)

        def on_rebuild_weeks() -> None:
            try:
                rebuild_week_rows()
            except Exception as exc:
                messagebox.showerror("Період", str(exc), parent=modal)

        def on_apply_quick_template() -> None:
            try:
                apply_quick_template()
            except Exception as exc:
                messagebox.showerror("Період", str(exc), parent=modal)

        def on_save_period() -> None:
            try:
                resolved_start_date = selected_period_start_date()
                weeks_count = parse_optional_positive_int(weeks_count_var.get(), field_name="Кількість тижнів")
                if weeks_count is None:
                    raise ValueError("Вкажіть кількість тижнів.")
                if weeks_count != len(week_choice_vars):
                    rebuild_week_rows()
                    weeks_count = len(week_choice_vars)
                week_pattern_by_week_index: dict[int, int] = {}
                for week_index, value_var in enumerate(week_choice_vars, start=1):
                    label = value_var.get().strip()
                    if label not in template_id_by_label:
                        raise ValueError(f"Оберіть шаблон для тижня {week_index}.")
                    week_pattern_by_week_index[week_index] = int(template_id_by_label[label])

                with session_scope() as session:
                    calendar_controller = CalendarController(session=session)
                    if is_edit and period_data is not None:
                        if not messagebox.askyesno(
                            "Редагування періоду",
                            "Підтвердити збереження? Поточні заняття цього періоду буде перебудовано.",
                            parent=modal,
                        ):
                            return
                        updated = calendar_controller.update_calendar_period_with_templates(
                            period_id=int(period_data["id"]),
                            name=period_name_var.get().strip(),
                            start_date=resolved_start_date,
                            weeks_count=weeks_count,
                            week_pattern_by_week_index=week_pattern_by_week_index,
                        )
                        resulting_id = int(updated.id)
                    else:
                        created = calendar_controller.create_calendar_period_with_templates(
                            company_id=company_id,
                            name=period_name_var.get().strip(),
                            start_date=resolved_start_date,
                            weeks_count=weeks_count,
                            week_pattern_by_week_index=week_pattern_by_week_index,
                        )
                        resulting_id = int(created.id)
            except Exception as exc:
                messagebox.showerror("Період", str(exc), parent=modal)
                return

            modal.destroy()
            close_period_menu()
            load_reference_data(select_period_id=resulting_id)
            on_period_changed()
            status_var.set("Період збережено.")

        self._motion_button(
            quick_row,
            text="Застосувати до всіх",
            command=on_apply_quick_template,
            primary=False,
            width=180,
            height=36,
        ).pack(side=tk.LEFT)

        actions = ttk.Frame(shell, style="Card.TFrame")
        actions.pack(fill=tk.X, pady=(10, 0))
        self._motion_button(
            actions,
            text="Оновити тижні",
            command=on_rebuild_weeks,
            primary=False,
            width=150,
            height=36,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self._motion_button(
            actions,
            text="Зберегти",
            command=on_save_period,
            primary=True,
            width=130,
            height=36,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self._motion_button(
            actions,
            text="Скасувати",
            command=modal.destroy,
            primary=False,
            width=130,
            height=36,
        ).pack(side=tk.LEFT)

        on_rebuild_weeks()

    def on_delete_period(period_id: int) -> None:
        period_by_id = period_state.get("by_id", {})
        if not isinstance(period_by_id, dict) or period_id not in period_by_id:
            return
        items = period_state.get("items", [])
        if not isinstance(items, list):
            return
        period_index = next((idx for idx, item in enumerate(items) if int(item["id"]) == int(period_id)), -1)
        if period_index < 0:
            return
        current_item = items[period_index]
        current_label = str(current_item.get("name") or "").strip() or f"Період #{period_id}"
        if not messagebox.askyesno(
            "Видалення періоду",
            f"Видалити '{current_label}'? Це також очистить заняття й сценарії цього періоду.",
            parent=self.root,
        ):
            return
        try:
            with session_scope() as session:
                deleted = CalendarController(session=session).delete_calendar_period(period_id=period_id)
                if not deleted:
                    raise ValueError("Період не знайдено або вже видалено.")
        except Exception as exc:
            messagebox.showerror("Видалення періоду", str(exc), parent=self.root)
            return

        selected_item = selected_period_item()
        selected_id = int(selected_item["id"]) if isinstance(selected_item, dict) else None
        next_period_id: int | None = None
        remaining = [item for item in items if int(item["id"]) != int(period_id)]
        if selected_id == int(period_id):
            if period_index < len(remaining):
                next_period_id = int(remaining[period_index]["id"])
            elif remaining:
                next_period_id = int(remaining[-1]["id"])
        else:
            next_period_id = selected_id

        close_period_menu()
        load_reference_data(select_period_id=next_period_id)
        on_period_changed()
        status_var.set("Період видалено.")

    def open_period_menu() -> None:
        items = period_state.get("items", [])
        if not isinstance(items, list) or not items:
            return
        popup = period_state.get("menu")
        if isinstance(popup, tk.Toplevel) and popup.winfo_exists():
            close_period_menu()
            return

        close_selector_menu(week_selector_state)
        close_selector_menu(group_selector_state)
        close_selector_menu(scenario_selector_state)
        close_selector_menu(scenario_compare_selector_state)
        close_period_menu()
        popup = tk.Toplevel(self.root)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.configure(bg=self.theme.BORDER)
        period_state["menu"] = popup
        popup.bind("<Escape>", lambda _e: close_period_menu(), add="+")

        shell = tk.Frame(popup, bg=self.theme.SURFACE, bd=0, highlightthickness=0)
        shell.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        selected_item = selected_period_item()
        selected_id = int(selected_item["id"]) if isinstance(selected_item, dict) else None

        for item in items:
            item_id = int(item["id"])
            is_selected = selected_id == item_id
            row_bg = self.theme.SECONDARY_HOVER if is_selected else self.theme.SURFACE
            row = tk.Frame(shell, bg=row_bg, bd=0, highlightthickness=0)
            row.pack(fill=tk.X)

            select_button = tk.Button(
                row,
                text=period_label(item),
                anchor="w",
                relief=tk.FLAT,
                bd=0,
                padx=8,
                pady=7,
                bg=row_bg,
                fg=self.theme.TEXT_PRIMARY,
                activebackground=self.theme.SECONDARY_HOVER,
                activeforeground=self.theme.TEXT_PRIMARY,
                command=lambda pid=item_id: (
                    close_period_menu(),
                    select_period(pid, trigger_reload=True),
                ),
            )
            select_button.pack(side=tk.LEFT, fill=tk.X, expand=True)

            HoverCircleIconButton(
                row,
                text="✎",
                command=lambda pid=item_id: (
                    close_period_menu(),
                    open_period_modal(period_id=pid),
                ),
                diameter=32,
                canvas_bg=row_bg,
                icon_color=self.theme.TEXT_MUTED,
                hover_bg=self.theme.SECONDARY_HOVER,
                hover_icon_color=self.theme.TEXT_PRIMARY,
                pressed_bg=self.theme.SECONDARY_PRESSED,
            ).pack(side=tk.LEFT, padx=(4, 2), pady=2)
            HoverCircleIconButton(
                row,
                text="🗑",
                command=lambda pid=item_id: on_delete_period(pid),
                diameter=32,
                canvas_bg=row_bg,
                icon_color=self.theme.DANGER,
                hover_bg=self.theme.SECONDARY_HOVER,
                hover_icon_color=self.theme.DANGER_HOVER,
                pressed_bg=self.theme.SECONDARY_PRESSED,
            ).pack(side=tk.LEFT, padx=(2, 6), pady=2)

        create_row = tk.Frame(shell, bg=self.theme.SURFACE_ALT, bd=0, highlightthickness=0)
        create_row.pack(fill=tk.X, pady=(4, 0))
        create_button = tk.Button(
            create_row,
            text="+ Створити період",
            anchor="w",
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=8,
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.ACCENT,
            activebackground=self.theme.SECONDARY_HOVER,
            activeforeground=self.theme.ACCENT_HOVER,
            command=lambda: (
                close_period_menu(),
                open_period_modal(period_id=None),
            ),
        )
        create_button.pack(fill=tk.X)

        popup.update_idletasks()
        self.root.update_idletasks()
        menu_width = max(220, period_selector_main.winfo_width(), shell.winfo_reqwidth())
        menu_height = max(40, shell.winfo_reqheight() + 2)

        def close_on_outside_click(event: tk.Event) -> str | None:
            if not popup.winfo_exists():
                return None
            x_root = int(getattr(event, "x_root", 0))
            y_root = int(getattr(event, "y_root", 0))
            left = popup.winfo_rootx()
            top = popup.winfo_rooty()
            right = left + popup.winfo_width()
            bottom = top + popup.winfo_height()
            inside = left <= x_root < right and top <= y_root < bottom
            if inside:
                return None
            close_period_menu()
            return "break"

        popup.bind("<ButtonPress-1>", close_on_outside_click, add="+")
        popup.deiconify()
        track_popup_geometry(
            popup=popup,
            anchor_widget=period_selector_main,
            width=menu_width,
            height=menu_height,
            close_callback=close_period_menu,
            clip_widget=schedule_canvas,
        )
        popup.grab_set()

    period_toggle_button.configure(command=open_period_menu)
    period_display.bind("<Button-1>", lambda _e: open_period_menu())
    period_empty_create_button.command = lambda: open_period_modal(period_id=None)

    def open_week_start_menu() -> None:
        values = week_selector_state.get("values", [])
        if not isinstance(values, list):
            values = []
        open_selector_popup(
            selector_state=week_selector_state,
            anchor_widget=week_selector_main,
            values=values,
            selected_value=week_start_var.get().strip(),
            on_pick=lambda selected: (
                week_start_var.set(selected),
                on_load_week(),
            ),
            searchable=False,
        )

    def open_group_filter_menu() -> None:
        values = group_selector_state.get("all_values", [])
        if not isinstance(values, list) or not values:
            return
        popup = group_selector_state.get("menu")
        if isinstance(popup, tk.Toplevel) and popup.winfo_exists():
            close_selector_menu(group_selector_state)
            return

        close_all_header_menus(keep=group_selector_state)
        popup = tk.Toplevel(self.root)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.configure(bg=self.theme.BORDER)
        group_selector_state["menu"] = popup
        popup.bind("<Escape>", lambda _e: close_selector_menu(group_selector_state), add="+")

        shell = tk.Frame(popup, bg=self.theme.SURFACE, bd=0, highlightthickness=0)
        shell.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        filters_row = tk.Frame(shell, bg=self.theme.SURFACE_ALT, bd=0, highlightthickness=0)
        filters_row.pack(fill=tk.X, padx=6, pady=(6, 4))
        ttk.Label(filters_row, text="Спеціальність", style="CardSubtle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(filters_row, text="Курс", style="CardSubtle.TLabel").grid(row=0, column=1, sticky="w", padx=(8, 0))

        specialty_values = group_selector_state.get("specialty_values", ["Усі спеціальності"])
        if not isinstance(specialty_values, list) or not specialty_values:
            specialty_values = ["Усі спеціальності"]
        course_values = group_selector_state.get("course_values", ["Усі курси"])
        if not isinstance(course_values, list) or not course_values:
            course_values = ["Усі курси"]

        specialty_filter_var = tk.StringVar(value=str(group_selector_state.get("specialty_filter", "Усі спеціальності")))
        if specialty_filter_var.get() not in specialty_values:
            specialty_filter_var.set("Усі спеціальності")
        course_filter_var = tk.StringVar(value=str(group_selector_state.get("course_filter", "Усі курси")))
        if course_filter_var.get() not in course_values:
            course_filter_var.set("Усі курси")

        specialty_box = ttk.Combobox(
            filters_row,
            textvariable=specialty_filter_var,
            values=specialty_values,
            state="readonly",
            width=24,
            style="PopupFilter.TCombobox",
        )
        specialty_box.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        course_box = ttk.Combobox(
            filters_row,
            textvariable=course_filter_var,
            values=course_values,
            state="readonly",
            width=14,
            style="PopupFilter.TCombobox",
        )
        course_box.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(2, 0))
        filters_row.columnconfigure(0, weight=1)
        filters_row.columnconfigure(1, weight=0)

        search_row = tk.Frame(shell, bg=self.theme.SURFACE_ALT, bd=0, highlightthickness=0)
        search_row.pack(fill=tk.X, padx=6, pady=(0, 4))
        search_var = tk.StringVar(value="")
        search_entry = tk.Entry(
            search_row,
            textvariable=search_var,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            highlightcolor=self.theme.ACCENT,
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            insertbackground=self.theme.TEXT_PRIMARY,
            font=("Segoe UI", 10),
        )
        search_entry.pack(fill=tk.X, ipady=6)

        list_wrap = tk.Frame(shell, bg=self.theme.SURFACE, bd=0, highlightthickness=0)
        list_wrap.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        listbox = tk.Listbox(
            list_wrap,
            activestyle="none",
            exportselection=False,
            selectmode=tk.SINGLE,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            highlightcolor=self.theme.ACCENT,
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            selectbackground=self.theme.ACCENT,
            selectforeground=self.theme.TEXT_LIGHT,
            font=("Segoe UI", 10),
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll = ttk.Scrollbar(
            list_wrap,
            orient=tk.VERTICAL,
            command=listbox.yview,
            style="App.Vertical.TScrollbar",
        )
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=list_scroll.set)

        meta_by_value = group_selector_state.get("meta_by_value", {})
        if not isinstance(meta_by_value, dict):
            meta_by_value = {}
        filtered_values: list[str] = []

        def render_filtered_values() -> None:
            nonlocal filtered_values
            selected_specialty = specialty_filter_var.get().strip() or "Усі спеціальності"
            selected_course = course_filter_var.get().strip() or "Усі курси"
            query = search_var.get().strip().casefold()
            group_selector_state["specialty_filter"] = selected_specialty
            group_selector_state["course_filter"] = selected_course

            filtered_values = []
            for value in values:
                if value == "Не обрано":
                    if query and query not in "не обрано":
                        continue
                    filtered_values.append(value)
                    continue
                meta = meta_by_value.get(value, {})
                specialty_label = str(meta.get("specialty_label", "Без спеціальності"))
                course_label = str(meta.get("course_label", "Без курсу"))
                if selected_specialty != "Усі спеціальності" and specialty_label != selected_specialty:
                    continue
                if selected_course != "Усі курси" and course_label != selected_course:
                    continue
                if query:
                    haystack = f"{value} {specialty_label} {course_label}".casefold()
                    if query not in haystack:
                        continue
                filtered_values.append(value)

            listbox.delete(0, tk.END)
            for item in filtered_values:
                listbox.insert(tk.END, item)
            selected_value = group_filter_var.get().strip()
            if selected_value in filtered_values:
                selected_index = filtered_values.index(selected_value)
                listbox.selection_set(selected_index)
                listbox.see(selected_index)
            elif filtered_values:
                listbox.selection_set(0)
                listbox.see(0)

        def commit_selection(_event=None) -> str:
            selected = listbox.curselection()
            if not selected:
                return "break"
            picked_value = str(listbox.get(selected[0]))
            close_selector_menu(group_selector_state)
            group_filter_var.set(picked_value)
            on_load_week()
            return "break"

        def close_on_outside_click(event: tk.Event) -> str | None:
            if not popup.winfo_exists():
                return None
            x_root = int(getattr(event, "x_root", 0))
            y_root = int(getattr(event, "y_root", 0))
            left = popup.winfo_rootx()
            top = popup.winfo_rooty()
            right = left + popup.winfo_width()
            bottom = top + popup.winfo_height()
            if left <= x_root < right and top <= y_root < bottom:
                return None
            close_selector_menu(group_selector_state)
            return "break"

        specialty_box.bind("<<ComboboxSelected>>", lambda _e: render_filtered_values(), add="+")
        course_box.bind("<<ComboboxSelected>>", lambda _e: render_filtered_values(), add="+")
        search_var.trace_add("write", lambda *_args: render_filtered_values())
        search_entry.bind("<Down>", lambda _e: (listbox.focus_set(), "break")[1], add="+")
        listbox.bind("<Return>", commit_selection, add="+")
        listbox.bind("<Double-Button-1>", commit_selection, add="+")
        listbox.bind("<ButtonRelease-1>", commit_selection, add="+")
        popup.bind("<ButtonPress-1>", close_on_outside_click, add="+")

        render_filtered_values()
        popup.update_idletasks()
        self.root.update_idletasks()
        group_selector_main.update_idletasks()
        menu_width = max(320, group_selector_main.winfo_width() + 120)
        rows_count = max(1, min(10, len(filtered_values)))
        menu_height = 110 + rows_count * 24

        popup.deiconify()
        track_popup_geometry(
            popup=popup,
            anchor_widget=group_selector_main,
            width=menu_width,
            height=menu_height,
            close_callback=lambda: close_selector_menu(group_selector_state),
            clip_widget=schedule_canvas,
        )
        popup.grab_set()
        search_entry.focus_set()

    def open_scenario_menu() -> None:
        values = scenario_selector_state.get("values", [])
        if not isinstance(values, list):
            values = []
        open_selector_popup(
            selector_state=scenario_selector_state,
            anchor_widget=scenario_selector_main,
            values=values,
            selected_value=scenario_var.get().strip(),
            on_pick=lambda selected: (
                scenario_var.set(selected),
                on_load_week(),
            ),
            searchable=False,
        )

    def open_scenario_compare_menu() -> None:
        values = scenario_compare_selector_state.get("values", [])
        if not isinstance(values, list):
            values = []
        open_selector_popup(
            selector_state=scenario_compare_selector_state,
            anchor_widget=scenario_compare_selector_main,
            values=values,
            selected_value=scenario_compare_var.get().strip(),
            on_pick=lambda selected: scenario_compare_var.set(selected),
            searchable=False,
        )

    week_selector_button.configure(command=open_week_start_menu)
    week_selector_label.bind("<Button-1>", lambda _e: open_week_start_menu(), add="+")
    group_selector_button.configure(command=open_group_filter_menu)
    group_selector_label.bind("<Button-1>", lambda _e: open_group_filter_menu(), add="+")
    scenario_selector_button.configure(command=open_scenario_menu)
    scenario_selector_label.bind("<Button-1>", lambda _e: open_scenario_menu(), add="+")
    scenario_compare_selector_button.configure(command=open_scenario_compare_menu)
    scenario_compare_selector_label.bind("<Button-1>", lambda _e: open_scenario_compare_menu(), add="+")

    def selected_group_resource_id() -> int | None:
        raw = group_filter_var.get().strip()
        if not raw or raw == "Не обрано":
            # Special sentinel: render only an empty grid shell without schedule entries.
            return -1
        return parse_prefixed_id(raw, field_name="група")

    def selected_blackout_scope() -> str:
        scope = blackout_scope_var.get().strip()
        if scope not in blackout_scope_type_by_label:
            raise ValueError("Оберіть тип ресурсу для blackout.")
        return scope

    def selected_blackout_resource_id() -> int:
        raw = blackout_resource_var.get().strip()
        if not raw:
            raise ValueError("Оберіть ресурс для blackout.")
        return parse_prefixed_id(raw, field_name="ресурс blackout")

    def selected_manual_requirement_id() -> int:
        raw = manual_requirement_var.get().strip()
        if not raw:
            raise ValueError("Оберіть вимогу для ручного слота.")
        return parse_prefixed_id(raw, field_name="вимога")

    def selected_manual_room_resource_id() -> int | None:
        raw = manual_room_var.get().strip()
        if not raw or raw == "Авто":
            return None
        return parse_prefixed_id(raw, field_name="аудиторія")

    def refresh_blackout_resource_choices() -> None:
        scope = selected_blackout_scope()
        values = blackout_resource_values_by_scope.get(scope, [])
        blackout_resource_box["values"] = values
        if values and blackout_resource_var.get() not in values:
            blackout_resource_var.set(values[0])
        if not values:
            blackout_resource_var.set("")

    def refresh_blackout_date_choices() -> None:
        selected_period = selected_period_item()
        if selected_period is not None:
            start_day = selected_period["start_date"]
            end_day = selected_period["end_date"]
        else:
            start_day = date.today()
            end_day = start_day + timedelta(days=120)

        if end_day < start_day:
            start_day, end_day = end_day, start_day

        dates_values = [
            (start_day + timedelta(days=offset)).isoformat()
            for offset in range((end_day - start_day).days + 1)
        ]
        if not dates_values:
            dates_values = [date.today().isoformat()]

        for box in (
            blackout_start_date_box,
            blackout_end_date_box,
            blackout_batch_start_date_box,
            blackout_batch_end_date_box,
        ):
            box["values"] = dates_values

        if blackout_start_date_var.get() not in dates_values:
            blackout_start_date_var.set(dates_values[0])
        if blackout_end_date_var.get() not in dates_values:
            blackout_end_date_var.set(dates_values[min(1, len(dates_values) - 1)])
        if blackout_batch_start_date_var.get() not in dates_values:
            blackout_batch_start_date_var.set(dates_values[0])
        if blackout_batch_end_date_var.get() not in dates_values:
            blackout_batch_end_date_var.set(dates_values[-1])

        if blackout_start_time_var.get() not in blackout_time_values:
            blackout_start_time_var.set("08:30")
        if blackout_end_time_var.get() not in blackout_time_values:
            blackout_end_time_var.set("18:00")
        if blackout_batch_start_time_var.get() not in blackout_time_values:
            blackout_batch_start_time_var.set("08:30")
        if blackout_batch_end_time_var.get() not in blackout_time_values:
            blackout_batch_end_time_var.set("18:00")

    def selected_blackout_batch_weekdays() -> set[int]:
        selected_days = {
            weekday
            for weekday, var in blackout_batch_weekday_vars.items()
            if bool(var.get())
        }
        if not selected_days:
            raise ValueError("Оберіть хоча б один день тижня для пакетного blackout.")
        return selected_days

    def close_blackout_filter_menu() -> None:
        popup = blackout_filter_state.get("menu")
        if popup is None:
            return
        try:
            if isinstance(popup, tk.Toplevel) and popup.winfo_exists():
                try:
                    popup.grab_release()
                except tk.TclError:
                    pass
                popup.destroy()
        except tk.TclError:
            pass
        blackout_filter_state["menu"] = None

    def blackout_is_column_filtered(column_id: str) -> bool:
        search_by = blackout_filter_state.get("search_by_column", {})
        value_filter_by = blackout_filter_state.get("value_filter_by_column", {})
        if isinstance(search_by, dict) and str(search_by.get(column_id, "")).strip():
            return True
        if isinstance(value_filter_by, dict):
            selected_values = value_filter_by.get(column_id)
            if isinstance(selected_values, set) and selected_values:
                return True
        return False

    def refresh_blackout_table_headings() -> None:
        sort_column = blackout_filter_state.get("sort_column")
        sort_desc = bool(blackout_filter_state.get("sort_desc", False))
        for column_id in blackout_table_columns:
            title = blackout_heading_titles[column_id]
            if blackout_is_column_filtered(column_id):
                heading_image = blackout_filter_icon
            else:
                heading_image = ""
            if sort_column == column_id:
                title += " ↓" if sort_desc else " ↑"
            blackout_table.heading(column_id, text=title, image=heading_image)

    def render_blackouts_table() -> None:
        raw_rows = blackout_filter_state.get("rows", [])
        rows = list(raw_rows) if isinstance(raw_rows, list) else []
        search_by = blackout_filter_state.get("search_by_column", {})
        value_filter_by = blackout_filter_state.get("value_filter_by_column", {})
        if not isinstance(search_by, dict):
            search_by = {}
        if not isinstance(value_filter_by, dict):
            value_filter_by = {}

        filtered_rows: list[dict[str, str]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            passes = True
            for column_id, query in search_by.items():
                query_text = str(query).strip().casefold()
                if not query_text:
                    continue
                value_text = str(row.get(column_id, "")).casefold()
                if query_text not in value_text:
                    passes = False
                    break
            if not passes:
                continue
            for column_id, selected_values in value_filter_by.items():
                if not isinstance(selected_values, set) or not selected_values:
                    continue
                value_text = str(row.get(column_id, ""))
                if value_text not in selected_values:
                    passes = False
                    break
            if passes:
                filtered_rows.append(row)

        sort_column = blackout_filter_state.get("sort_column")
        sort_desc = bool(blackout_filter_state.get("sort_desc", False))
        if isinstance(sort_column, str) and sort_column in blackout_table_columns:
            filtered_rows.sort(
                key=lambda item: str(item.get(sort_column, "")).casefold(),
                reverse=sort_desc,
            )

        for item_id in blackout_table.get_children():
            blackout_table.delete(item_id)
        for row in filtered_rows:
            blackout_table.insert(
                "",
                tk.END,
                iid=str(row["id"]),
                values=(row["resource"], row["start"], row["end"], row["title"]),
            )
        refresh_blackout_table_headings()

    def clear_blackout_filters_and_sort() -> None:
        blackout_filter_state["search_by_column"] = {}
        blackout_filter_state["value_filter_by_column"] = {}
        blackout_filter_state["sort_column"] = None
        blackout_filter_state["sort_desc"] = False
        render_blackouts_table()

    def open_blackout_column_menu(column_id: str, x_root: int, y_root: int) -> None:
        if column_id not in blackout_table_columns:
            return
        close_blackout_filter_menu()
        popup = tk.Toplevel(self.root)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.configure(bg=self.theme.BORDER)
        blackout_filter_state["menu"] = popup
        popup.bind("<Escape>", lambda _e: close_blackout_filter_menu(), add="+")

        shell = tk.Frame(popup, bg=self.theme.SURFACE, bd=0, highlightthickness=0)
        shell.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        header = tk.Frame(shell, bg=self.theme.SURFACE_ALT, bd=0, highlightthickness=0)
        header.pack(fill=tk.X, padx=8, pady=(8, 6))
        tk.Label(
            header,
            text=f"{blackout_heading_titles[column_id]}: фільтр / сортування",
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill=tk.X)

        search_by = blackout_filter_state.get("search_by_column", {})
        if not isinstance(search_by, dict):
            search_by = {}
        value_filter_by = blackout_filter_state.get("value_filter_by_column", {})
        if not isinstance(value_filter_by, dict):
            value_filter_by = {}

        search_var = tk.StringVar(value=str(search_by.get(column_id, "")))
        tk.Label(
            shell,
            text="Пошук у колонці",
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_MUTED,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill=tk.X, padx=8)
        search_entry = tk.Entry(
            shell,
            textvariable=search_var,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            highlightcolor=self.theme.ACCENT,
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            insertbackground=self.theme.TEXT_PRIMARY,
            font=("Segoe UI", 10),
        )
        search_entry.pack(fill=tk.X, padx=8, pady=(2, 8), ipady=5)

        rows = blackout_filter_state.get("rows", [])
        if not isinstance(rows, list):
            rows = []
        unique_values = sorted({str(row.get(column_id, "")) for row in rows if isinstance(row, dict)})
        selected_values_existing = value_filter_by.get(column_id)
        if not isinstance(selected_values_existing, set):
            selected_values_existing = set(unique_values)

        values_wrap = tk.Frame(shell, bg=self.theme.SURFACE, bd=0, highlightthickness=0)
        values_wrap.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        value_listbox = tk.Listbox(
            values_wrap,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            activestyle="none",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            highlightcolor=self.theme.ACCENT,
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            selectbackground=self.theme.LISTBOX_SELECTED_BG,
            selectforeground=self.theme.TEXT_PRIMARY,
            font=("Segoe UI", 9),
            height=8,
        )
        value_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        value_scroll = ttk.Scrollbar(
            values_wrap,
            orient=tk.VERTICAL,
            command=value_listbox.yview,
            style="App.Vertical.TScrollbar",
        )
        value_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        value_listbox.configure(yscrollcommand=value_scroll.set)

        for index, value in enumerate(unique_values):
            value_listbox.insert(tk.END, value)
            if value in selected_values_existing:
                value_listbox.selection_set(index)

        controls = tk.Frame(shell, bg=self.theme.SURFACE, bd=0, highlightthickness=0)
        controls.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Button(
            controls,
            text="Усі",
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=4,
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.TEXT_PRIMARY,
            activebackground=self.theme.SECONDARY_HOVER,
            activeforeground=self.theme.TEXT_PRIMARY,
            cursor="hand2",
            command=lambda: value_listbox.select_set(0, tk.END),
        ).pack(side=tk.LEFT)
        tk.Button(
            controls,
            text="Жоден",
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=4,
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.TEXT_PRIMARY,
            activebackground=self.theme.SECONDARY_HOVER,
            activeforeground=self.theme.TEXT_PRIMARY,
            cursor="hand2",
            command=lambda: value_listbox.selection_clear(0, tk.END),
        ).pack(side=tk.LEFT, padx=(8, 0))

        actions = tk.Frame(shell, bg=self.theme.SURFACE, bd=0, highlightthickness=0)
        actions.pack(fill=tk.X, padx=8, pady=(0, 8))

        def apply_filter() -> None:
            next_search = dict(search_by)
            query = search_var.get().strip()
            if query:
                next_search[column_id] = query
            else:
                next_search.pop(column_id, None)

            next_value_filter = dict(value_filter_by)
            selected_indices = value_listbox.curselection()
            selected_values = {str(value_listbox.get(idx)) for idx in selected_indices}
            if not selected_values or len(selected_values) == len(unique_values):
                next_value_filter.pop(column_id, None)
            else:
                next_value_filter[column_id] = selected_values

            blackout_filter_state["search_by_column"] = next_search
            blackout_filter_state["value_filter_by_column"] = next_value_filter
            render_blackouts_table()
            close_blackout_filter_menu()

        def set_sort(desc: bool) -> None:
            blackout_filter_state["sort_column"] = column_id
            blackout_filter_state["sort_desc"] = desc
            render_blackouts_table()
            close_blackout_filter_menu()

        tk.Button(
            actions,
            text="Сортувати ↑",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=5,
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.TEXT_PRIMARY,
            activebackground=self.theme.SECONDARY_HOVER,
            activeforeground=self.theme.TEXT_PRIMARY,
            cursor="hand2",
            command=lambda: set_sort(False),
        ).pack(side=tk.LEFT)
        tk.Button(
            actions,
            text="Сортувати ↓",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=5,
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.TEXT_PRIMARY,
            activebackground=self.theme.SECONDARY_HOVER,
            activeforeground=self.theme.TEXT_PRIMARY,
            cursor="hand2",
            command=lambda: set_sort(True),
        ).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(
            actions,
            text="Застосувати",
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=5,
            bg=self.theme.ACCENT,
            fg=self.theme.TEXT_LIGHT,
            activebackground=self.theme.ACCENT_HOVER,
            activeforeground=self.theme.TEXT_LIGHT,
            cursor="hand2",
            command=apply_filter,
        ).pack(side=tk.RIGHT)

        footer = tk.Frame(shell, bg=self.theme.SURFACE, bd=0, highlightthickness=0)
        footer.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Button(
            footer,
            text="Очистити все",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.TEXT_PRIMARY,
            activebackground=self.theme.SECONDARY_HOVER,
            activeforeground=self.theme.TEXT_PRIMARY,
            cursor="hand2",
            command=lambda: (
                clear_blackout_filters_and_sort(),
                close_blackout_filter_menu(),
            ),
        ).pack(side=tk.LEFT)
        tk.Button(
            footer,
            text="Закрити",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.TEXT_PRIMARY,
            activebackground=self.theme.SECONDARY_HOVER,
            activeforeground=self.theme.TEXT_PRIMARY,
            cursor="hand2",
            command=close_blackout_filter_menu,
        ).pack(side=tk.RIGHT)

        def close_on_outside_click(event: tk.Event) -> str | None:
            if not popup.winfo_exists():
                return None
            px = popup.winfo_rootx()
            py = popup.winfo_rooty()
            pr = px + popup.winfo_width()
            pb = py + popup.winfo_height()
            ex = int(getattr(event, "x_root", 0))
            ey = int(getattr(event, "y_root", 0))
            if px <= ex < pr and py <= ey < pb:
                return None
            close_blackout_filter_menu()
            return "break"

        popup.bind("<ButtonPress-1>", close_on_outside_click, add="+")
        popup.update_idletasks()
        width = 360
        height = 350
        x_pos = max(0, min(int(x_root), self.root.winfo_screenwidth() - width - 4))
        y_pos = max(0, min(int(y_root) + 4, self.root.winfo_screenheight() - height - 4))
        popup.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        popup.deiconify()
        popup.lift()
        popup.grab_set()
        search_entry.focus_set()

    def on_blackout_heading_click(event: tk.Event) -> str | None:
        region = blackout_table.identify_region(event.x, event.y)
        if region != "heading":
            close_blackout_filter_menu()
            return None
        raw_column = blackout_table.identify_column(event.x)
        if not raw_column.startswith("#"):
            return "break"
        try:
            column_index = int(raw_column[1:]) - 1
        except ValueError:
            return "break"
        if column_index < 0 or column_index >= len(blackout_table_columns):
            return "break"
        column_id = blackout_table_columns[column_index]
        open_blackout_column_menu(
            column_id=column_id,
            x_root=blackout_table.winfo_rootx() + int(event.x),
            y_root=blackout_table.winfo_rooty() + int(event.y),
        )
        return "break"

    def load_blackouts() -> None:
        close_blackout_filter_menu()
        with session_scope() as session:
            controller = ResourceController(session=session)
            blackouts = controller.list_blackouts(company_id=company_id)

        rows: list[dict[str, str]] = []
        for blackout in blackouts:
            resource_id = int(blackout.resource_id)
            scope_label = blackout_resource_scope_by_id.get(resource_id, "Ресурс")
            resource_name = blackout_resource_name_by_id.get(resource_id, f"#{resource_id}")
            resource_label = f"{scope_label}: {resource_name}"
            rows.append(
                {
                    "id": str(blackout.id),
                    "resource": resource_label,
                    "start": blackout.starts_at.strftime("%Y-%m-%d %H:%M"),
                    "end": blackout.ends_at.strftime("%Y-%m-%d %H:%M"),
                    "title": blackout.title or "—",
                }
            )
        blackout_filter_state["rows"] = rows
        render_blackouts_table()

    def load_coverage_dashboard() -> None:
        try:
            period_id = parse_period_id()
            scenario_id = selected_scenario_id()
        except Exception:
            coverage_summary_var.set("Coverage: —")
            for item_id in coverage_table.get_children():
                coverage_table.delete(item_id)
            return

        try:
            with session_scope() as session:
                dashboard = SchedulerController(session=session).get_coverage_dashboard(
                    calendar_period_id=period_id,
                    scenario_id=scenario_id,
                )
        except Exception as exc:
            coverage_summary_var.set(f"Coverage: помилка ({exc})")
            return

        coverage_summary_var.set(
            "Coverage: "
            f"вимог {dashboard.covered_requirements}/{dashboard.total_requirements}, "
            f"сесій {dashboard.total_sessions_scheduled}/{dashboard.total_sessions_required}, "
            f"не закрито вимог {dashboard.uncovered_requirements}"
        )
        for item_id in coverage_table.get_children():
            coverage_table.delete(item_id)
        for index, reason in enumerate(dashboard.reasons[:12], start=1):
            coverage_table.insert(
                "",
                tk.END,
                iid=f"coverage_{index}",
                values=(
                    reason.code,
                    str(reason.requirements_count),
                    str(reason.sessions_missing),
                    reason.sample_message,
                ),
            )

    def selected_schedule_entry_id() -> int | None:
        selected = entries_table.selection()
        if not selected:
            return None
        return int(selected[0])

    def clear_schedule_entries() -> None:
        schedule_entries_state.clear()
        for item_id in entries_table.get_children():
            entries_table.delete(item_id)

    def load_schedule_entries() -> None:
        try:
            period_id = parse_period_id()
            scenario_id = selected_scenario_id()
        except Exception:
            clear_schedule_entries()
            return

        with session_scope() as session:
            rows = SchedulerController(session=session).list_schedule_entries(
                calendar_period_id=period_id,
                scenario_id=scenario_id,
            )

        clear_schedule_entries()
        for row in rows:
            flags: list[str] = []
            if row.is_locked:
                flags.append("LOCK")
            if row.is_manual:
                flags.append("MAN")
            slot_label = (
                f"{row.day.isoformat()} | "
                f"{row.order_in_day}-{row.order_in_day + row.blocks_count - 1}"
            )
            entries_table.insert(
                "",
                tk.END,
                iid=str(row.entry_id),
                values=(
                    str(row.entry_id),
                    f"{row.requirement_id} | {row.requirement_name}",
                    slot_label,
                    row.room_name or "—",
                    " ".join(flags) if flags else "—",
                ),
            )
            schedule_entries_state[int(row.entry_id)] = {
                "entry_id": int(row.entry_id),
                "requirement_id": int(row.requirement_id),
                "day": row.day,
                "order_in_day": int(row.order_in_day),
                "blocks_count": int(row.blocks_count),
                "room_resource_id": None if row.room_resource_id is None else int(row.room_resource_id),
                "is_locked": bool(row.is_locked),
            }

    def load_selected_entry_into_manual() -> bool:
        entry_id = selected_schedule_entry_id()
        if entry_id is None:
            messagebox.showwarning("Заняття", "Оберіть запис у списку занять.")
            return False
        entry_state = schedule_entries_state.get(entry_id)
        if entry_state is None:
            messagebox.showwarning("Заняття", "Стан вибраного запису не знайдено.")
            return False

        requirement_id = int(entry_state["requirement_id"])
        requirement_label = ""
        for item in requirements_state["items"]:
            if int(item["id"]) == requirement_id:
                requirement_label = str(item["label"])
                break
        if requirement_label:
            manual_requirement_var.set(requirement_label)

        day_value = entry_state.get("day")
        if isinstance(day_value, date):
            manual_date_var.set(day_value.isoformat())
        manual_order_var.set(str(entry_state["order_in_day"]))

        room_resource_id = entry_state.get("room_resource_id")
        if room_resource_id is None:
            manual_room_var.set("Авто")
        else:
            match = next(
                (
                    value
                    for value in manual_room_box["values"]
                    if str(value).startswith(f"{int(room_resource_id)} |")
                ),
                None,
            )
            manual_room_var.set(str(match) if match is not None else "Авто")
        manual_lock_var.set(bool(entry_state["is_locked"]))
        return True

    def selected_requirement_id() -> int | None:
        selected = requirements_table.selection()
        if not selected:
            return None
        return int(selected[0])

    def _compact_names(values: list[str], *, limit: int = 2) -> str:
        if not values:
            return "—"
        if len(values) <= limit:
            return ", ".join(values)
        return f"{', '.join(values[:limit])} +{len(values) - limit}"

    def _format_room_constraints(requirement, room_name_by_profile_id: dict[int, str]) -> str:
        parts: list[str] = []
        if requirement.room_type is not None:
            parts.append(room_type_label_by_enum.get(requirement.room_type, requirement.room_type.value))
        if requirement.min_capacity is not None:
            parts.append(f"≥ {requirement.min_capacity} місць")
        if requirement.needs_projector:
            parts.append("проєктор")
        if requirement.fixed_room_id is not None:
            room_label = room_name_by_profile_id.get(int(requirement.fixed_room_id), f"#{requirement.fixed_room_id}")
            parts.append(f"фікс: {room_label}")
        if not parts:
            return "без обмежень"
        return ", ".join(parts)

    def render_requirements() -> None:
        for item_id in requirements_table.get_children():
            requirements_table.delete(item_id)
        for item in requirements_state["items"]:
            requirements_table.insert(
                "",
                tk.END,
                iid=str(item["id"]),
                values=(
                    str(item["name"]),
                    str(item["params"]),
                    str(item["teachers"]),
                    str(item["targets"]),
                    str(item["room_constraints"]),
                ),
            )

    def load_requirements() -> None:
        with session_scope() as session:
            req_controller = RequirementController(session=session)
            resource_controller = ResourceController(session=session)
            room_controller = RoomController(session=session)

            requirements = req_controller.list_requirements(company_id=company_id)
            resources = resource_controller.list_resources(company_id=company_id)
            room_profiles = room_controller.list_rooms(company_id=company_id, include_archived=True)

            resource_by_id = {int(resource.id): resource for resource in resources}
            room_name_by_profile_id = {int(room.id): str(room.name) for room in room_profiles}
            rows: list[dict[str, object]] = []

            for requirement in requirements:
                links = req_controller.list_requirement_resources(requirement_id=int(requirement.id))
                teachers: list[str] = []
                targets: list[str] = []

                for link in links:
                    resource = resource_by_id.get(int(link.resource_id))
                    if resource is None:
                        continue
                    if resource.type == ResourceType.TEACHER:
                        teachers.append(str(resource.name))
                    elif resource.type in {ResourceType.GROUP, ResourceType.SUBGROUP}:
                        targets.append(str(resource.name))

                rows.append(
                    {
                        "id": int(requirement.id),
                        "label": f"{int(requirement.id)} | {str(requirement.name)}",
                        "name": str(requirement.name),
                        "params": (
                            f"{int(requirement.duration_blocks)} бл. | "
                            f"{int(requirement.sessions_total)} зан. | "
                            f"{int(requirement.max_per_week)} / тиж."
                        ),
                        "teachers": _compact_names(teachers),
                        "targets": _compact_names(targets),
                        "room_constraints": _format_room_constraints(requirement, room_name_by_profile_id),
                    }
                )

        requirements_state["items"] = rows
        render_requirements()
        manual_values = [str(item["label"]) for item in rows]
        manual_requirement_box["values"] = manual_values
        if manual_values and manual_requirement_var.get() not in manual_values:
            manual_requirement_var.set(manual_values[0])
        if not manual_values:
            manual_requirement_var.set("")

    def open_requirement_edit_modal() -> None:
        requirement_id = selected_requirement_id()
        if requirement_id is None:
            messagebox.showwarning("Редагування вимоги", "Оберіть вимогу у списку.")
            return

        with session_scope() as session:
            req_controller = RequirementController(session=session)
            resource_controller = ResourceController(session=session)
            room_controller = RoomController(session=session)
            requirement = req_controller.get_requirement(requirement_id=requirement_id)
            requirement_links = (
                req_controller.list_requirement_resources(requirement_id=requirement_id)
                if requirement is not None
                else []
            )
            room_profiles = room_controller.list_rooms(company_id=company_id, include_archived=True)
            teacher_resources = resource_controller.list_resources(
                resource_type=ResourceType.TEACHER,
                company_id=company_id,
            )
            group_resources = resource_controller.list_resources(
                resource_type=ResourceType.GROUP,
                company_id=company_id,
            )
            subgroup_resources = resource_controller.list_resources(
                resource_type=ResourceType.SUBGROUP,
                company_id=company_id,
            )
        if requirement is None:
            messagebox.showerror("Редагування вимоги", "Вимогу не знайдено.")
            load_requirements()
            return

        teacher_resource_ids = {int(resource.id) for resource in teacher_resources}
        group_resource_ids = {int(resource.id) for resource in group_resources}
        subgroup_resource_ids = {int(resource.id) for resource in subgroup_resources}
        assigned_teacher_ids: set[int] = set()
        assigned_group_ids: set[int] = set()
        assigned_subgroup_ids: set[int] = set()

        for link in requirement_links:
            resource_id = int(link.resource_id)
            if resource_id in teacher_resource_ids:
                assigned_teacher_ids.add(resource_id)
            elif resource_id in group_resource_ids:
                assigned_group_ids.add(resource_id)
            elif resource_id in subgroup_resource_ids:
                assigned_subgroup_ids.add(resource_id)

        modal = tk.Toplevel(self.root)
        modal.title(f"Вимога #{requirement.id}")
        modal.transient(self.root)
        modal.grab_set()
        modal.resizable(False, False)
        body = ttk.Frame(modal, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        name_var = tk.StringVar(value=str(requirement.name))
        duration_var = tk.StringVar(value=str(requirement.duration_blocks))
        sessions_var = tk.StringVar(value=str(requirement.sessions_total))
        max_week_var = tk.StringVar(value=str(requirement.max_per_week))
        room_type_var = tk.StringVar(
            value=room_type_label_by_enum.get(requirement.room_type, "Не важливо")
            if requirement.room_type is not None
            else "Не важливо"
        )
        min_capacity_var = tk.StringVar(value="" if requirement.min_capacity is None else str(requirement.min_capacity))
        needs_projector_var = tk.BooleanVar(value=bool(requirement.needs_projector))

        fixed_room_values = ["Авто"] + [f"{room.id} | {room.name}" for room in room_profiles]
        fixed_room_var = tk.StringVar(value="Авто")
        if requirement.fixed_room_id is not None:
            for value in fixed_room_values:
                if value.startswith(f"{int(requirement.fixed_room_id)} |"):
                    fixed_room_var.set(value)
                    break

        ttk.Label(body, text="Назва").grid(row=0, column=0, sticky="w")
        ttk.Entry(body, textvariable=name_var, width=44).grid(row=0, column=1, columnspan=3, sticky="w", padx=(8, 0))
        ttk.Label(body, text="Тривалість (блоків)").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(body, textvariable=duration_var, width=8).grid(row=1, column=1, sticky="w", padx=(8, 12), pady=(8, 0))
        ttk.Label(body, text="Кількість занять").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(body, textvariable=sessions_var, width=8).grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(8, 0))
        ttk.Label(body, text="Макс/тиждень").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(body, textvariable=max_week_var, width=8).grid(row=2, column=1, sticky="w", padx=(8, 12), pady=(8, 0))
        ttk.Label(body, text="Тип аудиторії").grid(row=2, column=2, sticky="w", pady=(8, 0))
        ttk.Combobox(
            body,
            textvariable=room_type_var,
            values=room_type_labels,
            state="readonly",
            width=18,
        ).grid(row=2, column=3, sticky="w", padx=(8, 0), pady=(8, 0))
        ttk.Label(body, text="Мін. місткість").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(body, textvariable=min_capacity_var, width=8).grid(row=3, column=1, sticky="w", padx=(8, 12), pady=(8, 0))
        ttk.Checkbutton(body, text="Потрібен проєктор", variable=needs_projector_var).grid(
            row=3, column=2, columnspan=2, sticky="w", pady=(8, 0)
        )
        ttk.Label(body, text="Фікс. аудиторія").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(
            body,
            textvariable=fixed_room_var,
            values=fixed_room_values,
            state="readonly",
            width=30,
        ).grid(row=4, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=(8, 0))

        resources_shell = ttk.LabelFrame(body, text="Прив'язки ресурсів", padding=8)
        resources_shell.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        resources_shell.columnconfigure(0, weight=1)
        resources_shell.columnconfigure(1, weight=1)
        resources_shell.columnconfigure(2, weight=1)

        teacher_values = [f"{resource.id} | {resource.name}" for resource in teacher_resources]
        group_values = [f"{resource.id} | {resource.name}" for resource in group_resources]
        subgroup_values = [f"{resource.id} | {resource.name}" for resource in subgroup_resources]

        teacher_wrap = ttk.Frame(resources_shell, style="Card.TFrame")
        teacher_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(teacher_wrap, text="Викладачі").pack(anchor="w")
        teacher_list_wrap = ttk.Frame(teacher_wrap, style="Card.TFrame")
        teacher_list_wrap.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        teacher_listbox = tk.Listbox(
            teacher_list_wrap,
            selectmode=tk.EXTENDED,
            exportselection=False,
            height=7,
            width=26,
        )
        teacher_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        teacher_scroll = ttk.Scrollbar(teacher_list_wrap, orient=tk.VERTICAL, command=teacher_listbox.yview)
        teacher_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        teacher_listbox.configure(yscrollcommand=teacher_scroll.set)

        group_wrap = ttk.Frame(resources_shell, style="Card.TFrame")
        group_wrap.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        ttk.Label(group_wrap, text="Групи").pack(anchor="w")
        group_list_wrap = ttk.Frame(group_wrap, style="Card.TFrame")
        group_list_wrap.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        group_listbox = tk.Listbox(
            group_list_wrap,
            selectmode=tk.EXTENDED,
            exportselection=False,
            height=7,
            width=26,
        )
        group_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        group_scroll = ttk.Scrollbar(group_list_wrap, orient=tk.VERTICAL, command=group_listbox.yview)
        group_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        group_listbox.configure(yscrollcommand=group_scroll.set)

        subgroup_wrap = ttk.Frame(resources_shell, style="Card.TFrame")
        subgroup_wrap.grid(row=0, column=2, sticky="nsew")
        ttk.Label(subgroup_wrap, text="Підгрупи").pack(anchor="w")
        subgroup_list_wrap = ttk.Frame(subgroup_wrap, style="Card.TFrame")
        subgroup_list_wrap.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        subgroup_listbox = tk.Listbox(
            subgroup_list_wrap,
            selectmode=tk.EXTENDED,
            exportselection=False,
            height=7,
            width=26,
        )
        subgroup_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        subgroup_scroll = ttk.Scrollbar(subgroup_list_wrap, orient=tk.VERTICAL, command=subgroup_listbox.yview)
        subgroup_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        subgroup_listbox.configure(yscrollcommand=subgroup_scroll.set)

        for row in teacher_values:
            teacher_listbox.insert(tk.END, row)
        for index, row in enumerate(teacher_values):
            if parse_prefixed_id(row, field_name="викладач") in assigned_teacher_ids:
                teacher_listbox.selection_set(index)

        for row in group_values:
            group_listbox.insert(tk.END, row)
        for index, row in enumerate(group_values):
            if parse_prefixed_id(row, field_name="група") in assigned_group_ids:
                group_listbox.selection_set(index)

        for row in subgroup_values:
            subgroup_listbox.insert(tk.END, row)
        for index, row in enumerate(subgroup_values):
            if parse_prefixed_id(row, field_name="підгрупа") in assigned_subgroup_ids:
                subgroup_listbox.selection_set(index)

        actions = ttk.Frame(body, style="Card.TFrame")
        actions.grid(row=6, column=0, columnspan=4, sticky="e", pady=(12, 0))

        def selected_ids_from_listbox(listbox: tk.Listbox, *, field_name: str) -> set[int]:
            result: set[int] = set()
            for selected_index in listbox.curselection():
                result.add(parse_prefixed_id(str(listbox.get(selected_index)), field_name=field_name))
            return result

        def save_requirement() -> None:
            try:
                name = name_var.get().strip()
                if not name:
                    raise ValueError("Назва вимоги не може бути порожньою.")
                duration = int(duration_var.get().strip())
                sessions_total = int(sessions_var.get().strip())
                max_per_week = int(max_week_var.get().strip())
                room_type_label = room_type_var.get().strip() or "Не важливо"
                if room_type_label not in room_type_by_label:
                    raise ValueError("Оберіть тип аудиторії.")
                room_type = room_type_by_label[room_type_label]
                min_capacity = parse_optional_positive_int(min_capacity_var.get(), field_name="Мін. місткість")
                fixed_room_id = None if fixed_room_var.get().strip() == "Авто" else parse_prefixed_id(
                    fixed_room_var.get(), field_name="фіксована аудиторія"
                )
                selected_teacher_ids = selected_ids_from_listbox(teacher_listbox, field_name="викладач")
                selected_group_ids = selected_ids_from_listbox(group_listbox, field_name="група")
                selected_subgroup_ids = selected_ids_from_listbox(subgroup_listbox, field_name="підгрупа")
                if not selected_teacher_ids:
                    raise ValueError("Оберіть хоча б одного викладача.")
                if not selected_group_ids and not selected_subgroup_ids:
                    raise ValueError("Оберіть хоча б одну групу або підгрупу.")
                with session_scope() as session:
                    req_controller = RequirementController(session=session)
                    resource_controller = ResourceController(session=session)
                    req_controller.update_requirement(
                        requirement_id=requirement_id,
                        name=name,
                        duration_blocks=duration,
                        sessions_total=sessions_total,
                        max_per_week=max_per_week,
                        room_type=room_type,
                        min_capacity=min_capacity,
                        needs_projector=bool(needs_projector_var.get()),
                        fixed_room_id=fixed_room_id,
                    )
                    resources = resource_controller.list_resources(company_id=company_id)
                    resource_type_by_id = {int(resource.id): resource.type for resource in resources}
                    current_links = req_controller.list_requirement_resources(requirement_id=requirement_id)
                    for link in current_links:
                        resource_type = resource_type_by_id.get(int(link.resource_id))
                        if resource_type in {ResourceType.TEACHER, ResourceType.GROUP, ResourceType.SUBGROUP}:
                            req_controller.unassign_resource(
                                requirement_id=requirement_id,
                                resource_id=int(link.resource_id),
                                role=str(link.role),
                            )

                    for resource_id in sorted(selected_teacher_ids):
                        req_controller.assign_resource(
                            requirement_id=requirement_id,
                            resource_id=resource_id,
                            role="TEACHER",
                        )
                    for resource_id in sorted(selected_group_ids):
                        req_controller.assign_resource(
                            requirement_id=requirement_id,
                            resource_id=resource_id,
                            role="GROUP",
                        )
                    for resource_id in sorted(selected_subgroup_ids):
                        req_controller.assign_resource(
                            requirement_id=requirement_id,
                            resource_id=resource_id,
                            role="SUBGROUP",
                        )
            except Exception as exc:
                messagebox.showerror("Редагування вимоги", str(exc), parent=modal)
                return
            modal.destroy()
            load_requirements()
            status_var.set(f"Вимогу #{requirement_id} оновлено.")

        self._motion_button(actions, text="Зберегти", command=save_requirement, primary=True, width=120).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        self._motion_button(actions, text="Скасувати", command=modal.destroy, primary=False, width=120).pack(
            side=tk.LEFT
        )

    def on_delete_requirement() -> None:
        requirement_id = selected_requirement_id()
        if requirement_id is None:
            messagebox.showwarning("Видалення вимоги", "Оберіть вимогу у списку.")
            return
        if not messagebox.askyesno("Видалення вимоги", f"Видалити вимогу #{requirement_id}?", parent=self.root):
            return
        try:
            with session_scope() as session:
                deleted = RequirementController(session=session).delete_requirement(requirement_id=requirement_id)
                if not deleted:
                    raise ValueError("Вимогу не знайдено або вже видалено.")
        except Exception as exc:
            messagebox.showerror("Видалення вимоги", str(exc))
            return
        load_requirements()
        on_load_week()
        status_var.set(f"Вимогу #{requirement_id} видалено.")

    def load_scenarios(*, period_id: int | None = None) -> None:
        resolved_period_id = period_id
        if resolved_period_id is None:
            try:
                resolved_period_id = parse_period_id()
            except Exception:
                resolved_period_id = None

        values = ["Опублікований"]
        if resolved_period_id is not None:
            with session_scope() as session:
                scenarios = SchedulerController(session=session).list_scenarios(
                    calendar_period_id=resolved_period_id
                )
            for scenario in scenarios:
                published_suffix = " [опублік.]" if scenario.is_published else ""
                values.append(
                    f"{scenario.id} | {scenario.name}{published_suffix} ({scenario.entries_count})"
                )

        scenario_values_state["values"] = values
        scenario_selector_state["values"] = list(values)
        scenario_compare_selector_state["values"] = list(values)
        if scenario_var.get() not in values:
            scenario_var.set(values[0])
        if scenario_compare_var.get() not in values:
            scenario_compare_var.set(values[0])
        scenario_enabled = bool(values)
        scenario_selector_button.configure(state=("normal" if scenario_enabled else "disabled"))
        scenario_selector_label.configure(fg=self.theme.TEXT_PRIMARY if scenario_enabled else self.theme.TEXT_MUTED)
        scenario_compare_selector_button.configure(state=("normal" if scenario_enabled else "disabled"))
        scenario_compare_selector_label.configure(
            fg=self.theme.TEXT_PRIMARY if scenario_enabled else self.theme.TEXT_MUTED
        )

    def on_create_scenarios_ab() -> None:
        try:
            period_id = parse_period_id()
            created_names: list[str] = []
            with session_scope() as session:
                controller = SchedulerController(session=session)
                existing = controller.list_scenarios(calendar_period_id=period_id)
                existing_names = {str(item.name).strip().lower() for item in existing}
                for name in ("Чернетка A", "Чернетка B"):
                    if name.lower() in existing_names:
                        continue
                    controller.create_scenario(
                        calendar_period_id=period_id,
                        name=name,
                        copy_from_published=True,
                    )
                    created_names.append(name)
        except Exception as exc:
            messagebox.showerror("Сценарії", str(exc))
            return
        load_scenarios(period_id=period_id)
        if created_names:
            status_var.set(f"Створено сценарії: {', '.join(created_names)}.")
        else:
            status_var.set("Чернетки A/B вже існують.")

    def on_publish_scenario() -> None:
        try:
            period_id = parse_period_id()
            scenario_id = selected_scenario_id()
            if scenario_id is None:
                raise ValueError("Оберіть чернетку для публікації.")
            with session_scope() as session:
                published_entries = SchedulerController(session=session).publish_scenario(
                    scenario_id=scenario_id
                )
        except Exception as exc:
            messagebox.showerror("Публікація сценарію", str(exc))
            return
        load_scenarios(period_id=period_id)
        on_load_week()
        status_var.set(f"Опубліковано сценарій #{scenario_id}. Занять: {published_entries}.")

    def on_compare_scenarios() -> None:
        try:
            period_id = parse_period_id()
            left_id = selected_scenario_id()
            right_id = parse_scenario_id(scenario_compare_var.get())
            with session_scope() as session:
                comparison = SchedulerController(session=session).compare_scenarios(
                    calendar_period_id=period_id,
                    left_scenario_id=left_id,
                    right_scenario_id=right_id,
                )
        except Exception as exc:
            messagebox.showerror("Порівняння сценаріїв", str(exc))
            return
        lines = [
            f"{comparison.left_label} vs {comparison.right_label}",
            f"Тільки ліворуч: {comparison.only_left_count}",
            f"Тільки праворуч: {comparison.only_right_count}",
            f"Змінені вимоги: {comparison.changed_count}",
        ]
        if comparison.items:
            lines.append("")
            lines.append("Приклади різниці:")
            lines.extend(f"[{item.code}] {item.message}" for item in comparison.items[:8])
        messagebox.showinfo("Порівняння сценаріїв", "\n".join(lines))
        status_var.set(
            f"Порівняння: left={comparison.only_left_count}, "
            f"right={comparison.only_right_count}, changed={comparison.changed_count}."
        )

    def on_period_changed() -> None:
        try:
            period_id = parse_period_id()
        except Exception:
            refresh_blackout_date_choices()
            load_scenarios(period_id=None)
            load_coverage_dashboard()
            clear_schedule_entries()
            return
        refresh_blackout_date_choices()
        load_scenarios(period_id=period_id)
        on_load_week()

    def load_reference_data(*, select_period_id: int | None = None) -> None:
        with session_scope() as session:
            calendar = CalendarController(session=session)
            periods = calendar.list_calendar_periods(company_id=company_id)
            resources = ResourceController(session=session)
            groups = resources.list_resources(resource_type=ResourceType.GROUP, company_id=company_id)
            teachers = resources.list_resources(resource_type=ResourceType.TEACHER, company_id=company_id)
            rooms = resources.list_resources(resource_type=ResourceType.ROOM, company_id=company_id)
            room_profiles = RoomController(session=session).list_rooms(company_id=company_id, include_archived=False)
            academic = AcademicController(session=session)
            streams = academic.list_streams(company_id=company_id, include_archived=False)
            streams_all = academic.list_streams(company_id=company_id, include_archived=True)
            courses_all = academic.list_courses(company_id=company_id, include_archived=True)
            specialties_all = academic.list_specialties(company_id=company_id, include_archived=True)
            plans = CurriculumController(session=session).list_plans(company_id=company_id, include_archived=False)
            period_items: list[dict[str, object]] = []
            for item in periods:
                weeks_count = period_weeks_count(item.start_date, item.end_date)
                week_pattern_by_week_index: dict[int, int] = {
                    week_index: int(item.week_pattern_id)
                    for week_index in range(1, weeks_count + 1)
                }
                for override in list(item.week_template_overrides):
                    week_idx = int(override.week_index)
                    if 1 <= week_idx <= weeks_count:
                        week_pattern_by_week_index[week_idx] = int(override.week_pattern_id)
                period_items.append(
                    {
                        "id": int(item.id),
                        "name": str(item.name or "").strip(),
                        "start_date": item.start_date,
                        "end_date": item.end_date,
                        "weeks_count": weeks_count,
                        "week_pattern_id": int(item.week_pattern_id),
                        "week_pattern_by_week_index": week_pattern_by_week_index,
                    }
                )

        period_state["items"] = period_items
        period_state["by_id"] = {int(item["id"]): item for item in period_items}
        existing_selected = selected_period_item()
        fallback_selected_id = int(existing_selected["id"]) if isinstance(existing_selected, dict) else None
        target_period_id = select_period_id if select_period_id is not None else fallback_selected_id
        if period_items:
            if target_period_id is None or target_period_id not in period_state["by_id"]:
                target_period_id = int(period_items[0]["id"])
            select_period(target_period_id, trigger_reload=False)
        else:
            period_var.set("")
            refresh_week_start_selector(keep_selection=False)
            status_var.set("Періоди відсутні. Створіть період через дропдаун.")
        refresh_period_selector_state()
        try:
            load_scenarios(period_id=parse_period_id())
        except Exception:
            load_scenarios(period_id=None)

        plan_sync_state["items"] = [{"id": int(item.id), "name": str(item.name)} for item in plans]
        plan_values = [f"{item['id']} | {item['name']}" for item in plan_sync_state["items"]]
        existing_selected_ids = selected_plan_ids()
        selection_touched = bool(plan_sync_state.get("selection_touched", False))
        available_ids = [int(item["id"]) for item in plan_sync_state["items"]]
        if existing_selected_ids:
            plan_sync_state["selected_ids"] = [plan_id for plan_id in existing_selected_ids if plan_id in available_ids]
        elif selection_touched:
            plan_sync_state["selected_ids"] = []
        else:
            plan_sync_state["selected_ids"] = list(available_ids)
        plan_selector_box["values"] = plan_values
        if plan_values and plan_sync_var.get() not in plan_values:
            plan_sync_var.set(plan_values[0])
        if not plan_values:
            plan_sync_var.set("")
        render_plan_selection()

        group_values = [f"{item.id} | {item.name}" for item in groups]
        group_selector_values = ["Не обрано"] + group_values
        group_selector_state["values"] = list(group_selector_values)
        group_selector_state["all_values"] = list(group_selector_values)

        stream_by_id = {int(item.id): item for item in streams_all}
        course_by_id = {int(item.id): item for item in courses_all}
        specialty_by_id = {int(item.id): item for item in specialties_all}

        group_meta_by_value: dict[str, dict[str, object]] = {}
        specialty_filters: set[str] = set()
        course_filters: set[str] = set()
        for resource in groups:
            value = f"{resource.id} | {resource.name}"
            stream = stream_by_id.get(int(resource.stream_id)) if resource.stream_id is not None else None
            course = (
                course_by_id.get(int(stream.course_id))
                if stream is not None and stream.course_id is not None
                else None
            )
            specialty = (
                specialty_by_id.get(int(stream.specialty_id))
                if stream is not None and stream.specialty_id is not None
                else None
            )
            specialty_label = "Без спеціальності"
            if specialty is not None:
                specialty_label = (
                    f"{specialty.code} — {specialty.name}"
                    if specialty.code
                    else str(specialty.name)
                )
            study_year = (
                int(course.study_year)
                if course is not None and course.study_year is not None
                else int(stream.study_year)
                if stream is not None and stream.study_year is not None
                else None
            )
            course_label = f"{study_year} курс" if study_year is not None else "Без курсу"
            specialty_filters.add(specialty_label)
            course_filters.add(course_label)
            group_meta_by_value[value] = {
                "specialty_label": specialty_label,
                "course_label": course_label,
            }

        group_selector_state["meta_by_value"] = group_meta_by_value
        group_selector_state["specialty_values"] = ["Усі спеціальності"] + sorted(specialty_filters)
        group_selector_state["course_values"] = ["Усі курси"] + sorted(
            course_filters,
            key=lambda raw: (
                1,
                int(raw.split(" ", maxsplit=1)[0]),
            )
            if raw.endswith("курс") and raw.split(" ", maxsplit=1)[0].isdigit()
            else (2, raw),
        )
        if str(group_selector_state.get("specialty_filter", "")) not in group_selector_state["specialty_values"]:
            group_selector_state["specialty_filter"] = "Усі спеціальності"
        if str(group_selector_state.get("course_filter", "")) not in group_selector_state["course_values"]:
            group_selector_state["course_filter"] = "Усі курси"
        if group_filter_var.get() not in group_selector_values:
            group_filter_var.set("Не обрано")
        group_selector_button.configure(state=("normal" if group_selector_values else "disabled"))
        group_selector_label.configure(
            fg=self.theme.TEXT_PRIMARY if group_selector_values else self.theme.TEXT_MUTED
        )

        teacher_values = [f"{item.id} | {item.name}" for item in teachers]
        room_values = [f"{item.id} | {item.name}" for item in rooms]
        manual_room_box["values"] = ["Авто"] + room_values
        if manual_room_var.get() not in manual_room_box["values"]:
            manual_room_var.set("Авто")
        selected_period = selected_period_item()
        if selected_period is not None and not manual_date_var.get():
            manual_date_var.set(selected_period["start_date"].isoformat())
        refresh_blackout_date_choices()

        blackout_resource_values_by_scope["Викладач"] = teacher_values
        blackout_resource_values_by_scope["Група"] = group_values
        blackout_resource_values_by_scope["Аудиторія"] = room_values

        blackout_resource_name_by_id.clear()
        blackout_resource_scope_by_id.clear()
        for resource in teachers:
            blackout_resource_name_by_id[int(resource.id)] = str(resource.name)
            blackout_resource_scope_by_id[int(resource.id)] = "Викладач"
        for resource in groups:
            blackout_resource_name_by_id[int(resource.id)] = str(resource.name)
            blackout_resource_scope_by_id[int(resource.id)] = "Група"
        for resource in rooms:
            blackout_resource_name_by_id[int(resource.id)] = str(resource.name)
            blackout_resource_scope_by_id[int(resource.id)] = "Аудиторія"

        try:
            refresh_blackout_resource_choices()
        except ValueError:
            blackout_scope_var.set("Викладач")
            refresh_blackout_resource_choices()

    def render_grid(grid) -> None:
        for item in tree.get_children():
            tree.delete(item)
        for weekday, day_date in enumerate(grid.weekdays):
            cid = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")[weekday]
            tree.heading(cid, text=f"{WEEKDAY_LABELS[weekday]}\n{day_date.isoformat()}")
        for row in grid.rows:
            values = [row.slot_label] + [row.cells.get(i, "") for i in range(7)]
            tree.insert("", tk.END, values=values)

    def on_load_week() -> None:
        try:
            period_id = parse_period_id()
            week_start = parse_week_start()
            resource_id = selected_group_resource_id()
            scenario_id = selected_scenario_id()
            with session_scope() as session:
                grid = ScheduleViewController(session=session).get_weekly_grid(
                    calendar_period_id=period_id,
                    week_start=week_start,
                    resource_id=resource_id,
                    scenario_id=scenario_id,
                )
        except Exception as exc:
            messagebox.showerror("Не вдалося завантажити розклад", str(exc))
            return
        render_grid(grid)
        scope_label = "опублікований" if selected_scenario_id() is None else "чернетка"
        if resource_id == -1:
            status_var.set(
                f"Завантажено тиждень {grid.week_start}. "
                f"Групу не обрано: показано сітку без занять. Режим: {scope_label}."
            )
        else:
            status_var.set(f"Завантажено тиждень {grid.week_start}. Рядків: {len(grid.rows)}. Режим: {scope_label}.")
        load_coverage_dashboard()
        load_schedule_entries()

    def on_build_schedule() -> None:
        try:
            period_id = parse_period_id()
            scenario_id = selected_scenario_id()
            with session_scope() as session:
                result = SchedulerController(session=session).build_schedule(
                    period_id,
                    replace_existing=True,
                    scenario_id=scenario_id,
                )
        except Exception as exc:
            messagebox.showerror("Не вдалося згенерувати розклад", str(exc))
            return
        status_var.set(
            f"Генерацію завершено. Створено: {len(result.created_entries)} | "
            f"Нерозміщено занять: {sum(result.unscheduled_sessions.values())}"
        )
        if result.diagnostics:
            details = "\n".join(f"[{item.code}] {item.message}" for item in result.diagnostics[:12])
            messagebox.showwarning("Діагностика конфліктів", details)
        on_load_week()

    def on_validate() -> None:
        try:
            period_id = parse_period_id()
            scenario_id = selected_scenario_id()
            with session_scope() as session:
                report = ScheduleValidationController(session=session).validate_schedule(
                    period_id,
                    scenario_id=scenario_id,
                )
        except Exception as exc:
            messagebox.showerror("Не вдалося перевірити розклад", str(exc))
            return
        if report.is_valid:
            messagebox.showinfo("Перевірка", "Проблем не знайдено.")
            status_var.set("Перевірка успішна.")
            return
        details = "\n".join(f"[{item.code}] {item.message}" for item in report.issues[:10])
        messagebox.showwarning("Проблеми перевірки", details)
        status_var.set(f"Знайдено проблем: {len(report.issues)}")

    def load_policy() -> None:
        try:
            with session_scope() as session:
                policy = SchedulerController(session=session).get_policy(company_id=company_id)
        except Exception as exc:
            messagebox.showerror("Політика генерації", str(exc))
            return
        policy_max_sessions_var.set("" if policy.max_sessions_per_day is None else str(policy.max_sessions_per_day))
        policy_max_consecutive_var.set("" if policy.max_consecutive_blocks is None else str(policy.max_consecutive_blocks))
        policy_no_gaps_var.set(bool(policy.enforce_no_gaps))
        reverse_map = {value: label for label, value in policy_time_pref_options.items()}
        normalized_pref = policy.time_preference if isinstance(policy.time_preference, TimePreference) else TimePreference.BALANCED
        policy_time_pref_var.set(reverse_map.get(normalized_pref, "Баланс"))
        policy_weight_time_var.set(str(policy.weight_time_preference))
        policy_weight_compact_var.set(str(policy.weight_compactness))
        policy_weight_building_var.set(str(policy.weight_building_transition))

    def on_save_policy() -> None:
        try:
            max_sessions = parse_optional_positive_int(policy_max_sessions_var.get(), field_name="Макс пар/день")
            max_consecutive = parse_optional_positive_int(policy_max_consecutive_var.get(), field_name="Макс підряд блоків")
            pref_label = policy_time_pref_var.get().strip() or "Баланс"
            if pref_label not in policy_time_pref_options:
                raise ValueError("Оберіть коректну часову перевагу.")
            weight_time = parse_non_negative_int(policy_weight_time_var.get(), field_name="W час")
            weight_compact = parse_non_negative_int(policy_weight_compact_var.get(), field_name="W компактність")
            weight_building = parse_non_negative_int(policy_weight_building_var.get(), field_name="W переходи")
            with session_scope() as session:
                SchedulerController(session=session).update_policy(
                    company_id=company_id,
                    max_sessions_per_day=max_sessions,
                    max_consecutive_blocks=max_consecutive,
                    enforce_no_gaps=bool(policy_no_gaps_var.get()),
                    time_preference=policy_time_pref_options[pref_label].value,
                    weight_time_preference=weight_time,
                    weight_compactness=weight_compact,
                    weight_building_transition=weight_building,
                )
        except Exception as exc:
            messagebox.showerror("Політика генерації", str(exc))
            return
        status_var.set("Політику генерації збережено.")

    def on_check_feasibility() -> None:
        try:
            period_id = parse_period_id()
            scenario_id = selected_scenario_id()
            with session_scope() as session:
                report = SchedulerController(session=session).analyze_feasibility(
                    calendar_period_id=period_id,
                    replace_existing=True,
                    scenario_id=scenario_id,
                )
        except Exception as exc:
            messagebox.showerror("Перевірка здійсненності", str(exc))
            return
        if report.is_feasible:
            messagebox.showinfo("Перевірка здійсненності", "Ознак нерозв'язності не знайдено.")
            status_var.set("Перевірка здійсненності успішна.")
            return
        details = "\n".join(f"[{issue.code}] {issue.message}" for issue in report.issues[:10])
        messagebox.showwarning("Перевірка здійсненності", details)
        status_var.set(f"Знайдено ризиків: {len(report.issues)}")

    def on_add_plan_to_selection() -> None:
        try:
            plan_id = selected_plan_id()
        except Exception as exc:
            messagebox.showerror("Вибір планів", str(exc))
            return
        selected_ids = selected_plan_ids()
        if plan_id in selected_ids:
            status_var.set(f"План #{plan_id} вже додано у вибір.")
            return
        selected_ids.append(plan_id)
        plan_sync_state["selected_ids"] = selected_ids
        plan_sync_state["selection_touched"] = True
        render_plan_selection()
        status_var.set(f"План #{plan_id} додано у вибір синхронізації.")

    def on_remove_plan_from_selection() -> None:
        selected = plan_selected_listbox.curselection()
        if not selected:
            messagebox.showwarning("Вибір планів", "Оберіть план у списку 'Обрані'.")
            return
        selected_ids = selected_plan_ids()
        index = int(selected[0])
        if index < 0 or index >= len(selected_ids):
            return
        removed_id = int(selected_ids[index])
        del selected_ids[index]
        plan_sync_state["selected_ids"] = selected_ids
        plan_sync_state["selection_touched"] = True
        render_plan_selection()
        status_var.set(f"План #{removed_id} прибрано з вибору синхронізації.")

    def on_clear_plan_selection() -> None:
        plan_sync_state["selected_ids"] = []
        plan_sync_state["selection_touched"] = True
        render_plan_selection()
        status_var.set("Список обраних планів очищено.")

    def on_sync_selected_plan() -> None:
        try:
            plan_ids = selected_plan_ids()
            if not plan_ids:
                raise ValueError("Додайте хоча б один план у список 'Обрані'.")
            total_synced = 0
            with session_scope() as session:
                controller = CurriculumController(session=session)
                for plan_id in plan_ids:
                    synced = controller.sync_plan_requirements(plan_id=plan_id)
                    total_synced += len(synced)
        except Exception as exc:
            messagebox.showerror("Синхронізація плану", str(exc))
            return
        load_requirements()
        load_coverage_dashboard()
        if period_var.get().strip():
            on_load_week()
        else:
            load_schedule_entries()
        status_var.set(
            f"Синхронізовано обрані плани: {len(plan_ids)}. "
            f"Оновлено вимог: {total_synced}."
        )

    def on_sync_all_plans() -> None:
        try:
            total_synced = 0
            synced_plans = 0
            with session_scope() as session:
                controller = CurriculumController(session=session)
                plans = controller.list_plans(company_id=company_id, include_archived=False)
                if not plans:
                    raise ValueError("Немає активних навчальних планів для синхронізації.")
                for plan in plans:
                    synced_requirements = controller.sync_plan_requirements(plan_id=int(plan.id))
                    total_synced += len(synced_requirements)
                    synced_plans += 1
        except Exception as exc:
            messagebox.showerror("Синхронізація планів", str(exc))
            return
        load_requirements()
        load_coverage_dashboard()
        if period_var.get().strip():
            on_load_week()
        else:
            load_schedule_entries()
        status_var.set(f"Синхронізовано планів: {synced_plans}. Оновлено вимог: {total_synced}.")

    def on_add_blackout() -> None:
        try:
            selected_blackout_scope()
            resource_id = selected_blackout_resource_id()
            start_day = parse_date_input(blackout_start_date_var.get(), field_name="Дата початку")
            end_day = parse_date_input(blackout_end_date_var.get(), field_name="Дата кінця")
            start_clock = parse_time_input(blackout_start_time_var.get(), field_name="Час початку")
            end_clock = parse_time_input(blackout_end_time_var.get(), field_name="Час кінця")
            starts_at = datetime.combine(start_day, start_clock)
            ends_at = datetime.combine(end_day, end_clock)
            if ends_at <= starts_at:
                raise ValueError("Кінець blackout має бути пізніше за початок.")
            title = blackout_title_var.get().strip() or None
            with session_scope() as session:
                ResourceController(session=session).create_blackout(
                    resource_id=resource_id,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    title=title,
                )
        except Exception as exc:
            messagebox.showerror("Не вдалося додати blackout", str(exc))
            return
        load_blackouts()
        load_coverage_dashboard()
        status_var.set("Blackout додано.")

    def on_add_blackout_batch() -> None:
        try:
            selected_blackout_scope()
            resource_id = selected_blackout_resource_id()
            start_day = parse_date_input(blackout_batch_start_date_var.get(), field_name="Початок пакета")
            end_day = parse_date_input(blackout_batch_end_date_var.get(), field_name="Кінець пакета")
            if end_day < start_day:
                raise ValueError("Кінець пакета має бути не раніше початку.")
            start_clock = parse_time_input(blackout_batch_start_time_var.get(), field_name="Час початку")
            end_clock = parse_time_input(blackout_batch_end_time_var.get(), field_name="Час кінця")
            weekdays = selected_blackout_batch_weekdays()
            title = blackout_title_var.get().strip() or None

            intervals: list[tuple[datetime, datetime, str | None]] = []
            current_day = start_day
            while current_day <= end_day:
                if current_day.isoweekday() in weekdays:
                    starts_at = datetime.combine(current_day, start_clock)
                    ends_at = datetime.combine(current_day, end_clock)
                    if ends_at <= starts_at:
                        raise ValueError("Час кінця blackout має бути пізніше за початок.")
                    intervals.append((starts_at, ends_at, title))
                current_day += timedelta(days=1)
            if not intervals:
                raise ValueError("За обраним діапазоном і днями тижня не згенеровано жодного blackout.")

            with session_scope() as session:
                created = ResourceController(session=session).create_blackouts_batch(
                    resource_id=resource_id,
                    intervals=intervals,
                )
        except Exception as exc:
            messagebox.showerror("Batch blackout", str(exc))
            return
        load_blackouts()
        load_coverage_dashboard()
        status_var.set(f"Додано blackout пакет: {len(created)} записів.")

    def on_delete_blackout() -> None:
        selected = blackout_table.selection()
        if not selected:
            messagebox.showwarning("Видалення blackout", "Оберіть blackout у списку.")
            return
        blackout_id = int(selected[0])
        try:
            with session_scope() as session:
                deleted = ResourceController(session=session).delete_blackout(blackout_id=blackout_id)
                if not deleted:
                    raise ValueError("Blackout не знайдено або вже видалено.")
        except Exception as exc:
            messagebox.showerror("Не вдалося видалити blackout", str(exc))
            return
        load_blackouts()
        load_coverage_dashboard()
        status_var.set("Blackout видалено.")

    def on_add_manual_entry() -> None:
        try:
            period_id = parse_period_id()
            scenario_id = selected_scenario_id()
            requirement_id = selected_manual_requirement_id()
            day = date.fromisoformat(manual_date_var.get().strip())
            order_in_day = int(manual_order_var.get().strip())
            if order_in_day <= 0:
                raise ValueError("Номер блоку має бути більшим за 0.")
            room_resource_id = selected_manual_room_resource_id()
            with session_scope() as session:
                SchedulerController(session=session).create_manual_entry(
                    calendar_period_id=period_id,
                    scenario_id=scenario_id,
                    requirement_id=requirement_id,
                    day=day,
                    order_in_day=order_in_day,
                    room_resource_id=room_resource_id,
                    is_locked=bool(manual_lock_var.get()),
                )
        except Exception as exc:
            messagebox.showerror("Ручний слот", str(exc))
            return
        on_load_week()
        status_var.set("Ручний слот додано.")

    def on_update_manual_entry() -> None:
        entry_id = selected_schedule_entry_id()
        if entry_id is None:
            messagebox.showwarning("Заняття", "Оберіть запис у списку занять.")
            return
        try:
            period_id = parse_period_id()
            scenario_id = selected_scenario_id()
            day = date.fromisoformat(manual_date_var.get().strip())
            order_in_day = int(manual_order_var.get().strip())
            if order_in_day <= 0:
                raise ValueError("Номер блоку має бути більшим за 0.")
            room_resource_id = selected_manual_room_resource_id()
            with session_scope() as session:
                SchedulerController(session=session).update_manual_entry(
                    calendar_period_id=period_id,
                    scenario_id=scenario_id,
                    entry_id=entry_id,
                    day=day,
                    order_in_day=order_in_day,
                    room_resource_id=room_resource_id,
                    is_locked=bool(manual_lock_var.get()),
                )
        except Exception as exc:
            messagebox.showerror("Оновлення заняття", str(exc))
            return
        on_load_week()
        status_var.set(f"Заняття #{entry_id} оновлено.")

    def on_set_schedule_entry_lock(is_locked: bool) -> None:
        entry_id = selected_schedule_entry_id()
        if entry_id is None:
            messagebox.showwarning("Заняття", "Оберіть запис у списку занять.")
            return
        try:
            period_id = parse_period_id()
            scenario_id = selected_scenario_id()
            with session_scope() as session:
                SchedulerController(session=session).set_schedule_entry_lock(
                    calendar_period_id=period_id,
                    scenario_id=scenario_id,
                    entry_id=entry_id,
                    is_locked=is_locked,
                )
        except Exception as exc:
            messagebox.showerror("LOCK/UNLOCK", str(exc))
            return
        on_load_week()
        status_var.set(f"Заняття #{entry_id}: {'LOCK' if is_locked else 'UNLOCK'}.")

    def on_delete_schedule_entry() -> None:
        entry_id = selected_schedule_entry_id()
        if entry_id is None:
            messagebox.showwarning("Заняття", "Оберіть запис у списку занять.")
            return
        if not messagebox.askyesno("Видалення заняття", f"Видалити заняття #{entry_id}?", parent=self.root):
            return
        try:
            period_id = parse_period_id()
            scenario_id = selected_scenario_id()
            with session_scope() as session:
                deleted = SchedulerController(session=session).delete_schedule_entry(
                    calendar_period_id=period_id,
                    scenario_id=scenario_id,
                    entry_id=entry_id,
                    allow_locked=True,
                )
                if not deleted:
                    raise ValueError("Запис не знайдено або вже видалено.")
        except Exception as exc:
            messagebox.showerror("Видалення заняття", str(exc))
            return
        on_load_week()
        status_var.set(f"Заняття #{entry_id} видалено.")

    def on_create_default_period() -> None:
        try:
            start = date.today()
            end = start + timedelta(days=120)
            period_id = self._create_default_template_period(
                company_id=company_id,
                start=start,
                end=end,
            )
        except Exception as exc:
            messagebox.showerror("Не вдалося створити період", str(exc))
            return

        load_reference_data(select_period_id=period_id)
        status_var.set(
            f"Створено період #{period_id}: {start.isoformat()}..{end.isoformat()}."
        )
        on_load_week()

    self._motion_button(
        buttons,
        text="Завантажити тиждень",
        command=on_load_week,
        primary=False,
        width=180,
    ).pack(side=tk.LEFT, padx=(0, 6))
    self._motion_button(
        buttons,
        text="Згенерувати",
        command=on_build_schedule,
        primary=True,
        width=140,
    ).pack(side=tk.LEFT, padx=(0, 6))
    self._motion_button(
        buttons,
        text="Перевірити",
        command=on_validate,
        primary=False,
        width=130,
    ).pack(side=tk.LEFT, padx=(0, 6))
    self._motion_button(
        buttons,
        text="Здійсненність",
        command=on_check_feasibility,
        primary=False,
        width=140,
    ).pack(side=tk.LEFT, padx=(0, 6))
    self._motion_button(
        buttons,
        text="Створити A/B",
        command=on_create_scenarios_ab,
        primary=False,
        width=140,
    ).pack(side=tk.LEFT, padx=(0, 6))
    self._motion_button(
        buttons,
        text="Швидко створити період",
        command=on_create_default_period,
        primary=True,
        width=220,
    ).pack(side=tk.LEFT)

    blackout_add_button.configure(command=on_add_blackout)
    blackout_batch_button.configure(command=on_add_blackout_batch)
    blackout_delete_button.configure(command=on_delete_blackout)
    blackout_reload_button.configure(command=load_blackouts)
    coverage_refresh_button.configure(command=load_coverage_dashboard)
    scenario_compare_button.command = on_compare_scenarios
    scenario_publish_button.command = on_publish_scenario
    policy_save_button.configure(command=on_save_policy)
    manual_add_button.configure(command=on_add_manual_entry)
    manual_update_button.configure(command=on_update_manual_entry)
    entries_refresh_button.configure(command=load_schedule_entries)
    entries_prefill_button.configure(command=load_selected_entry_into_manual)
    entries_lock_button.configure(command=lambda: on_set_schedule_entry_lock(True))
    entries_unlock_button.configure(command=lambda: on_set_schedule_entry_lock(False))
    entries_delete_button.configure(command=on_delete_schedule_entry)
    requirements_refresh_button.configure(command=load_requirements)
    requirements_edit_button.configure(command=open_requirement_edit_modal)
    requirements_delete_button.configure(command=on_delete_requirement)
    plan_add_button.configure(command=on_add_plan_to_selection)
    plan_remove_button.configure(command=on_remove_plan_from_selection)
    plan_clear_button.configure(command=on_clear_plan_selection)
    plan_sync_selected_button.configure(command=on_sync_selected_plan)
    plan_sync_all_button.configure(command=on_sync_all_plans)
    plan_sync_refresh_button.configure(command=lambda: load_reference_data())

    load_reference_data()
    load_policy()
    load_blackouts()
    load_requirements()
    load_coverage_dashboard()
    plan_selector_box.bind("<<ComboboxSelected>>", lambda _e: refresh_plan_selection_controls(), add="+")
    plan_selected_listbox.bind("<<ListboxSelect>>", lambda _e: refresh_plan_selection_controls(), add="+")
    blackout_scope_box.bind("<<ComboboxSelected>>", lambda _e: refresh_blackout_resource_choices(), add="+")
    blackout_table.bind("<Button-1>", on_blackout_heading_click, add="+")
    entries_table.bind("<Double-1>", lambda _e: load_selected_entry_into_manual(), add="+")
    requirements_table.bind("<Double-1>", lambda _e: open_requirement_edit_modal(), add="+")
    open_schedule_tab("view")
    if period_var.get():
        on_load_week()
    self.root.after_idle(_sync_schedule_scroll)
