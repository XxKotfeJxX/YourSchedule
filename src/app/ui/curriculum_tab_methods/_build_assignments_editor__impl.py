def _build_assignments_editor__impl(self, parent: ttk.Frame) -> None:
    assignments = ttk.Frame(parent, style="Card.TFrame")
    assignments.grid(row=2, column=0, sticky="nsew")
    assignments.grid_columnconfigure(0, weight=1)
    assignments.grid_rowconfigure(1, weight=1)

    ttk.Label(assignments, text="Призначення", style="Card.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

    self.assignment_tree = ttk.Treeview(
        assignments,
        columns=("id", "teacher", "target", "sessions", "max", "req"),
        show="headings",
        height=7,
    )
    for cid, title, width in (
        ("id", "ID", 46),
        ("teacher", "Викладач", 150),
        ("target", "Ціль", 180),
        ("sessions", "Занять", 70),
        ("max", "Макс/тиж", 70),
        ("req", "Вим.", 60),
    ):
        self.assignment_tree.heading(cid, text=title)
        self.assignment_tree.column(cid, width=width, anchor="center")
    self.assignment_tree.grid(row=1, column=0, sticky="nsew")
    scroll = ttk.Scrollbar(assignments, orient=tk.VERTICAL, command=self.assignment_tree.yview, style="App.Vertical.TScrollbar")
    self._setup_autohide_tree_scrollbar(
        tree=self.assignment_tree,
        scrollbar=scroll,
        layout_kwargs={"row": 1, "column": 1, "sticky": "ns", "padx": (4, 0)},
    )
    self.assignment_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_assignment_select(), add="+")

    form = ttk.Frame(assignments, style="Card.TFrame")
    form.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
    form.grid_columnconfigure(0, weight=1)
    form.grid_columnconfigure(1, weight=1)
    form.grid_columnconfigure(2, weight=1)

    ttk.Label(form, text="Викладач").grid(row=0, column=0, sticky="w")
    ttk.Label(form, text="Тип цілі").grid(row=0, column=1, sticky="w")
    ttk.Label(form, text="Потік").grid(row=0, column=2, sticky="w")

    self.assignment_teacher_box = ttk.Combobox(form, textvariable=self.assignment_teacher_var, state="readonly")
    self.assignment_teacher_box.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
    self.assignment_target_type_box = ttk.Combobox(
        form,
        textvariable=self.assignment_target_type_var,
        values=[item.value for item in PlanTargetType],
        state="readonly",
    )
    self.assignment_target_type_box.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))
    self.assignment_target_type_box.bind("<<ComboboxSelected>>", lambda _e: self._refresh_assignment_target_controls(), add="+")
    self.assignment_stream_box = ttk.Combobox(form, textvariable=self.assignment_stream_var, state="readonly")
    self.assignment_stream_box.grid(row=1, column=2, sticky="ew", pady=(2, 4))

    ttk.Label(form, text="Група").grid(row=2, column=0, sticky="w")
    ttk.Label(form, text="Підгрупа").grid(row=2, column=1, sticky="w")
    ttk.Label(form, text="Занять (порожньо = авто)").grid(row=2, column=2, sticky="w")

    self.assignment_group_box = ttk.Combobox(form, textvariable=self.assignment_group_var, state="readonly")
    self.assignment_group_box.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
    self.assignment_subgroup_box = ttk.Combobox(form, textvariable=self.assignment_subgroup_var, state="readonly")
    self.assignment_subgroup_box.grid(row=3, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))
    ttk.Entry(form, textvariable=self.assignment_sessions_var).grid(row=3, column=2, sticky="ew", pady=(2, 4))

    ttk.Label(form, text="Макс/тиж (порожньо = авто)").grid(row=4, column=0, sticky="w")
    ttk.Entry(form, textvariable=self.assignment_max_per_week_var).grid(row=5, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))

    buttons = ttk.Frame(form, style="Card.TFrame")
    buttons.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(2, 0))
    self._grid_action_buttons(
        parent=buttons,
        items=[
            ("Додати", self._create_assignment, True),
            ("Змінити", self._update_assignment, False),
            ("Видалити", self._delete_assignment, False),
            ("Синхр.", self._sync_assignment, False),
        ],
        columns=2,
        width=108,
        height=32,
    )
