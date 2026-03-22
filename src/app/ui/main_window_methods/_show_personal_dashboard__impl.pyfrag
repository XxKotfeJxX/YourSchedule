def _show_personal_dashboard__impl(self) -> None:
    user = self.current_user
    if user is None:
        self._show_login_screen()
        return

    self._clear_root()

    container = ttk.Frame(self.root, padding=18)
    container.pack(fill=tk.BOTH, expand=True)

    header = ttk.Frame(container)
    header.pack(fill=tk.X, pady=(0, 12))
    ttk.Label(header, text="Розклад", style="SectionTitle.TLabel").pack(anchor="w")
    ttk.Label(header, text="Особистий акаунт", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

    content = ttk.Frame(container, style="Card.TFrame", padding=16)
    content.pack(fill=tk.BOTH, expand=True)

    status_var = tk.StringVar(value="Готово.")
    period_var = tk.StringVar()
    week_var = tk.StringVar()

    nav_frame = ttk.Frame(container)
    nav_frame.pack(fill=tk.X, pady=(10, 0))

    home_frame = ttk.Frame(content, style="Card.TFrame")
    notes_frame = ttk.Frame(content, style="Card.TFrame")
    settings_frame = ttk.Frame(content, style="Card.TFrame")

    tree = ttk.Treeview(
        home_frame,
        columns=("slot", "mon", "tue", "wed", "thu", "fri", "sat", "sun"),
        show="headings",
        height=19,
    )
    tree.heading("slot", text="Пара")
    tree.column("slot", width=120, anchor="center", stretch=False)
    for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun"):
        tree.heading(day, text=day.upper())
        tree.column(day, width=140, anchor="center", stretch=True)

    controls = ttk.Frame(home_frame, style="Card.TFrame")
    controls.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(controls, text="Період", style="Card.TLabel").pack(side=tk.LEFT)
    period_box = ttk.Combobox(controls, textvariable=period_var, width=24, state="readonly")
    period_box.pack(side=tk.LEFT, padx=(6, 10))
    ttk.Label(controls, text="Початок тижня", style="Card.TLabel").pack(side=tk.LEFT)
    ttk.Entry(controls, textvariable=week_var, width=12).pack(side=tk.LEFT, padx=(6, 10))

    def parse_period() -> int:
        raw = period_var.get().strip()
        if not raw:
            raise ValueError("Оберіть період.")
        return int(raw.split("|", maxsplit=1)[0].strip())

    def parse_week() -> date | None:
        raw = week_var.get().strip()
        if not raw:
            return None
        return date.fromisoformat(raw)

    def load_periods() -> None:
        with session_scope() as session:
            periods = CalendarController(session=session).list_calendar_periods(company_id=user.company_id)
        values = [f"{item.id} | {item.start_date}..{item.end_date}" for item in periods]
        period_box["values"] = values
        if values and not period_var.get():
            period_var.set(values[0])
        if not values:
            status_var.set("Поки що немає періоду. Звернись до адміністратора компанії.")

    def render_grid(grid) -> None:
        for item in tree.get_children():
            tree.delete(item)
        for weekday, day_date in enumerate(grid.weekdays):
            cid = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")[weekday]
            tree.heading(cid, text=f"{WEEKDAY_LABELS[weekday]}\n{day_date.isoformat()}")
        for row in grid.rows:
            values = [row.slot_label] + [row.cells.get(i, "") for i in range(7)]
            tree.insert("", tk.END, values=values)

    def load_personal_schedule() -> None:
        try:
            if user.resource_id is None:
                raise ValueError("Ваш акаунт ще не прив'язаний до групи.")
            period_id = parse_period()
            week_start = parse_week()
            with session_scope() as session:
                grid = ScheduleViewController(session=session).get_weekly_grid(
                    calendar_period_id=period_id,
                    week_start=week_start,
                    resource_id=user.resource_id,
                )
        except Exception as exc:
            messagebox.showerror("Не вдалося завантажити розклад", str(exc))
            return
        render_grid(grid)
        status_var.set(f"Завантажено тиждень {grid.week_start}.")

    self._motion_button(
        controls,
        text="Завантажити",
        command=load_personal_schedule,
        primary=True,
        width=140,
    ).pack(side=tk.LEFT)

    tree.pack(fill=tk.BOTH, expand=True)
    ttk.Label(home_frame, textvariable=status_var, anchor="w", style="CardSubtle.TLabel").pack(fill=tk.X, pady=(8, 0))

    ttk.Label(notes_frame, text="Нагадування (скоро буде)", style="CardTitle.TLabel").pack(anchor="w", pady=(8, 0))
    ttk.Label(
        notes_frame,
        text="Тут з'являться персональні нотатки та нагадування.",
        style="CardSubtle.TLabel",
    ).pack(anchor="w", pady=(4, 0))
    ttk.Label(settings_frame, text=f"Користувач: {user.username}", style="CardTitle.TLabel").pack(anchor="w", pady=(8, 0))
    ttk.Label(settings_frame, text="Редагування профілю з'явиться в наступних фазах.", style="CardSubtle.TLabel").pack(
        anchor="w"
    )
    self._motion_button(
        settings_frame,
        text="Вийти",
        command=self._logout,
        primary=True,
        width=120,
    ).pack(anchor="w", pady=(10, 0))

    frames = {
        "home": home_frame,
        "notes": notes_frame,
        "settings": settings_frame,
    }

    def open_tab(tab: str) -> None:
        for frame in frames.values():
            frame.pack_forget()
        frames[tab].pack(fill=tk.BOTH, expand=True)

    self._motion_button(
        nav_frame,
        text="Головна",
        command=lambda: open_tab("home"),
        primary=False,
        width=130,
    ).pack(side=tk.LEFT, padx=(0, 6))
    self._motion_button(
        nav_frame,
        text="Нагадування",
        command=lambda: open_tab("notes"),
        primary=False,
        width=150,
    ).pack(side=tk.LEFT, padx=(0, 6))
    self._motion_button(
        nav_frame,
        text="Налаштування",
        command=lambda: open_tab("settings"),
        primary=False,
        width=150,
    ).pack(side=tk.LEFT)

    load_periods()
    open_tab("home")
    if period_var.get():
        load_personal_schedule()
