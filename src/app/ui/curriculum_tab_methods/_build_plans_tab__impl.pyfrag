def _build_plans_tab__impl(self, parent: ttk.Frame) -> None:
    content = ttk.Frame(parent, style="Card.TFrame")
    content.pack(fill=tk.BOTH, expand=True)

    left = ttk.Frame(content, style="Card.TFrame")
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    left.grid_columnconfigure(0, weight=1)
    left.grid_rowconfigure(1, weight=1)
    ttk.Label(left, text="Плани", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
    self.plan_listbox = tk.Listbox(
        left,
        activestyle="none",
        bg=self.theme.SURFACE,
        fg=self.theme.TEXT_PRIMARY,
        selectbackground=self.theme.LISTBOX_SELECTED_BG,
        selectforeground=self.theme.TEXT_PRIMARY,
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=self.theme.BORDER,
        relief=tk.FLAT,
        font=("Segoe UI", 11),
        exportselection=False,
    )
    self.plan_listbox.grid(row=1, column=0, sticky="nsew", padx=(2, 0), pady=(4, 6))
    plan_scroll = ttk.Scrollbar(
        left,
        orient=tk.VERTICAL,
        command=self.plan_listbox.yview,
        style="App.Vertical.TScrollbar",
    )
    self._setup_autohide_scrollbar(
        listbox=self.plan_listbox,
        scrollbar=plan_scroll,
        manager="grid",
        layout_kwargs={"row": 1, "column": 1, "sticky": "ns", "padx": (4, 0), "pady": (4, 6)},
    )
    self.plan_listbox.bind("<<ListboxSelect>>", lambda _e: self._on_plan_select(), add="+")
    self._motion_button(
        left,
        text="Оновити",
        command=self._load_plans,
        primary=False,
        width=120,
        height=34,
    ).grid(row=2, column=0, sticky="w")

    right_shell = ttk.Frame(content, style="Card.TFrame")
    right_canvas = tk.Canvas(
        right_shell,
        bg=self.theme.SURFACE,
        bd=0,
        highlightthickness=0,
        relief=tk.FLAT,
    )
    right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    right_scroll = ttk.Scrollbar(
        right_shell,
        orient=tk.VERTICAL,
        command=right_canvas.yview,
        style="App.Vertical.TScrollbar",
    )
    right_canvas.configure(yscrollcommand=right_scroll.set)
    plans_scroll_state = {"visible": False}

    right = ttk.Frame(right_canvas, style="Card.TFrame")
    right_window = right_canvas.create_window((0, 0), anchor="nw", window=right)
    right.grid_columnconfigure(0, weight=1)

    self._build_plan_editor(right)
    self._build_components_editor(right)
    self._build_assignments_editor(right)

    def _sync_plans_scroll(_event=None) -> None:
        viewport_width = max(1, right_canvas.winfo_width())
        right_canvas.itemconfigure(right_window, width=viewport_width)
        requested_height = max(1, right.winfo_reqheight())
        viewport_height = max(1, right_canvas.winfo_height())
        needs_scroll = requested_height > (viewport_height + 1)

        if needs_scroll and not plans_scroll_state["visible"]:
            right_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0), pady=2)
            plans_scroll_state["visible"] = True
            right_canvas.after_idle(_sync_plans_scroll)
        elif (not needs_scroll) and plans_scroll_state["visible"]:
            right_scroll.pack_forget()
            plans_scroll_state["visible"] = False
            right_canvas.yview_moveto(0.0)
            right_canvas.after_idle(_sync_plans_scroll)

        bbox = right_canvas.bbox("all")
        if bbox is not None:
            right_canvas.configure(scrollregion=bbox)

    def _create_smooth_wheel_handlers(get_view, set_view, *, gain: float = 0.15):
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

    _on_plans_wheel, _on_plans_up, _on_plans_down = _create_smooth_wheel_handlers(
        right_canvas.yview,
        right_canvas.yview_moveto,
        gain=0.15,
    )

    def _create_tree_wheel_handlers(tree: ttk.Treeview):
        def _wheel_step(step_units: int) -> str:
            tree.yview_scroll(step_units, "units")
            return "break"

        def _on_wheel(event: tk.Event) -> str:
            delta = int(getattr(event, "delta", 0))
            if delta == 0:
                return "break"
            direction = -1 if delta > 0 else 1
            steps = max(1, int(abs(delta) / 120))
            for _ in range(steps):
                _wheel_step(direction)
            return "break"

        def _on_button4(_event: tk.Event) -> str:
            return _wheel_step(-1)

        def _on_button5(_event: tk.Event) -> str:
            return _wheel_step(1)

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

    def _bind_plans_wheel_recursive(widget: tk.Widget) -> None:
        if not isinstance(widget, (ttk.Treeview, tk.Listbox)):
            widget.bind("<MouseWheel>", _on_plans_wheel, add="+")
            widget.bind("<Button-4>", _on_plans_up, add="+")
            widget.bind("<Button-5>", _on_plans_down, add="+")
        for child in widget.winfo_children():
            _bind_plans_wheel_recursive(child)

    right.bind("<Configure>", _sync_plans_scroll, add="+")
    right_canvas.bind("<Configure>", _sync_plans_scroll, add="+")
    right_canvas.bind("<MouseWheel>", _on_plans_wheel, add="+")
    right_canvas.bind("<Button-4>", _on_plans_up, add="+")
    right_canvas.bind("<Button-5>", _on_plans_down, add="+")
    _bind_plans_wheel_recursive(right)

    if self.component_tree is not None:
        comp_wheel, comp_up, comp_down = _create_tree_wheel_handlers(self.component_tree)
        self.component_tree.bind(
            "<MouseWheel>",
            _with_fallback(comp_wheel, self.component_tree.yview, _on_plans_wheel),
            add="+",
        )
        self.component_tree.bind(
            "<Button-4>",
            _with_fallback(comp_up, self.component_tree.yview, _on_plans_up),
            add="+",
        )
        self.component_tree.bind(
            "<Button-5>",
            _with_fallback(comp_down, self.component_tree.yview, _on_plans_down),
            add="+",
        )

    if self.assignment_tree is not None:
        ass_wheel, ass_up, ass_down = _create_tree_wheel_handlers(self.assignment_tree)
        self.assignment_tree.bind(
            "<MouseWheel>",
            _with_fallback(ass_wheel, self.assignment_tree.yview, _on_plans_wheel),
            add="+",
        )
        self.assignment_tree.bind(
            "<Button-4>",
            _with_fallback(ass_up, self.assignment_tree.yview, _on_plans_up),
            add="+",
        )
        self.assignment_tree.bind(
            "<Button-5>",
            _with_fallback(ass_down, self.assignment_tree.yview, _on_plans_down),
            add="+",
        )

    right.after_idle(_sync_plans_scroll)

    self._bind_responsive_split(
        container=content,
        left=left,
        right=right_shell,
        breakpoint=980,
        wide_left_weight=2,
        wide_right_weight=5,
        stacked_top_weight=1,
        stacked_bottom_weight=1,
    )
