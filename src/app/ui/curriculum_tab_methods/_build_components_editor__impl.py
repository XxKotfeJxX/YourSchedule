def _build_components_editor__impl(self, parent: ttk.Frame) -> None:
    components = ttk.Frame(parent, style="Card.TFrame")
    components.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
    components.grid_columnconfigure(0, weight=1)
    components.grid_rowconfigure(1, weight=1)

    ttk.Label(components, text="Компоненти", style="Card.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

    self.component_tree = ttk.Treeview(
        components,
        columns=("id", "subject", "type", "duration", "sessions", "max"),
        show="headings",
        height=7,
    )
    for cid, title, width in (
        ("id", "ID", 46),
        ("subject", "Предмет", 170),
        ("type", "Тип", 90),
        ("duration", "Трив.", 56),
        ("sessions", "Занять", 70),
        ("max", "Макс/тиж", 70),
    ):
        self.component_tree.heading(cid, text=title)
        self.component_tree.column(cid, width=width, anchor="center")
    self.component_tree.grid(row=1, column=0, sticky="nsew")
    scroll = ttk.Scrollbar(components, orient=tk.VERTICAL, command=self.component_tree.yview, style="App.Vertical.TScrollbar")
    self._setup_autohide_tree_scrollbar(
        tree=self.component_tree,
        scrollbar=scroll,
        layout_kwargs={"row": 1, "column": 1, "sticky": "ns", "padx": (4, 0)},
    )
    self.component_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_component_select(), add="+")

    form = ttk.Frame(components, style="Card.TFrame")
    form.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
    form.grid_columnconfigure(0, weight=1)
    form.grid_columnconfigure(1, weight=1)
    form.grid_columnconfigure(2, weight=1)

    ttk.Label(form, text="Предмет").grid(row=0, column=0, sticky="w")
    ttk.Label(form, text="Тип").grid(row=0, column=1, sticky="w")
    ttk.Label(form, text="Тривалість").grid(row=0, column=2, sticky="w")

    self.component_subject_box = ttk.Combobox(form, textvariable=self.component_subject_var, state="readonly")
    self.component_subject_box.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
    ttk.Combobox(
        form,
        textvariable=self.component_type_var,
        values=[item.value for item in PlanComponentType],
        state="readonly",
    ).grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))
    ttk.Entry(form, textvariable=self.component_duration_var).grid(row=1, column=2, sticky="ew", pady=(2, 4))

    ttk.Label(form, text="Занять").grid(row=2, column=0, sticky="w")
    ttk.Label(form, text="Макс/тижд").grid(row=2, column=1, sticky="w")
    ttk.Label(form, text="Нотатки").grid(row=2, column=2, sticky="w")
    ttk.Entry(form, textvariable=self.component_sessions_var).grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
    ttk.Entry(form, textvariable=self.component_max_per_week_var).grid(row=3, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))
    ttk.Entry(form, textvariable=self.component_notes_var).grid(row=3, column=2, sticky="ew", pady=(2, 4))

    buttons = ttk.Frame(form, style="Card.TFrame")
    buttons.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(2, 0))
    self._grid_action_buttons(
        parent=buttons,
        items=[
            ("Додати", self._create_component, True),
            ("Змінити", self._update_component, False),
            ("Видалити", self._delete_component, False),
        ],
        columns=3,
        width=108,
        height=32,
    )
