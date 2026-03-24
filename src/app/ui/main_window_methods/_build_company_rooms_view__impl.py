# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.main_window import *  # noqa: F401,F403

def _build_company_rooms_view__impl(self, parent: ttk.Frame, company_id: int) -> None:
    buildings_state: dict[str, list[object]] = {"items": []}
    columns_state = {"value": 4}
    selected_building = {"item": None}
    rooms_state: dict[str, list[object]] = {"items": []}
    room_booking_state: dict[int, object] = {}
    room_type_options: list[tuple[str, RoomType | None]] = [
        ("Усі", None),
        ("Лекційна аудиторія", RoomType.LECTURE_HALL),
        ("Клас", RoomType.CLASSROOM),
        ("Лабораторія", RoomType.LAB),
        ("Комп'ютерна лабораторія", RoomType.COMPUTER_LAB),
        ("Викладацька", RoomType.TEACHERS_OFFICE),
        ("Технічне", RoomType.TECHNICAL),
        ("Інше", RoomType.OTHER),
    ]
    room_type_by_label = {label: room_type for label, room_type in room_type_options if room_type is not None}
    room_type_label_by_enum = {room_type: label for label, room_type in room_type_options if room_type is not None}
    room_type_choices = [label for label, room_type in room_type_options if room_type is not None]

    list_view = ttk.Frame(parent, style="Card.TFrame")
    list_view.pack(fill=tk.BOTH, expand=True)

    detail_view = ttk.Frame(parent, style="Card.TFrame")
    detail_view.pack(fill=tk.BOTH, expand=True)
    detail_view.pack_forget()

    header = ttk.Frame(list_view, style="Card.TFrame")
    header.pack(fill=tk.X, pady=(0, 10))
    titles = ttk.Frame(header, style="Card.TFrame")
    titles.pack(side=tk.LEFT, fill=tk.X, expand=True)
    ttk.Label(titles, text="Приміщення", style="CardTitle.TLabel").pack(anchor="w")
    ttk.Label(
        titles,
        text="Керуйте корпусами й аудиторіями. Натисніть картку корпусу, щоб відкрити деталі.",
        style="CardSubtle.TLabel",
    ).pack(anchor="w", pady=(2, 0))

    cards_shell = ttk.Frame(list_view, style="Card.TFrame")
    cards_shell.pack(fill=tk.BOTH, expand=True)
    cards_canvas = tk.Canvas(
        cards_shell,
        bg=self.theme.SURFACE,
        bd=0,
        highlightthickness=0,
        relief=tk.FLAT,
    )
    cards_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    cards_scroll = ttk.Scrollbar(
        cards_shell,
        orient=tk.VERTICAL,
        command=cards_canvas.yview,
        style="App.Vertical.TScrollbar",
    )
    cards_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    cards_canvas.configure(yscrollcommand=cards_scroll.set)

    cards_grid = ttk.Frame(cards_canvas, style="Card.TFrame")
    cards_window = cards_canvas.create_window((0, 0), anchor="nw", window=cards_grid)

    detail_header = ttk.Frame(detail_view, style="Card.TFrame")
    detail_header.pack(fill=tk.X, pady=(0, 6))
    back_button = HoverCircleIconButton(
        detail_header,
        text="←",
        command=lambda: open_list_view(),
        diameter=42,
        canvas_bg=self.theme.SURFACE,
        icon_color=self.theme.TEXT_PRIMARY,
        hover_bg=self.theme.SECONDARY_HOVER,
        hover_icon_color=self.theme.TEXT_PRIMARY,
        pressed_bg=self.theme.SECONDARY_PRESSED,
    )
    back_button.pack(side=tk.LEFT)

    detail_title_var = tk.StringVar(value="")
    detail_address_var = tk.StringVar(value="")
    detail_titles = ttk.Frame(detail_header, style="Card.TFrame")
    detail_titles.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
    ttk.Label(detail_titles, textvariable=detail_title_var, style="CardTitle.TLabel").pack(anchor="w")
    ttk.Label(detail_titles, textvariable=detail_address_var, style="CardSubtle.TLabel").pack(anchor="w", pady=(2, 0))

    detail_actions = ttk.Frame(detail_view, style="Card.TFrame")
    detail_actions.pack(fill=tk.X, pady=(0, 8))

    room_search_var = tk.StringVar(value="")
    room_type_filter_var = tk.StringVar(value="Усі")
    room_min_capacity_var = tk.StringVar(value="")
    room_department_filter_var = tk.StringVar(value="Усі кафедри")
    room_projector_filter_var = tk.StringVar(value="Усі")
    room_projector_filter_options: list[tuple[str, bool | None]] = [
        ("Усі", None),
        ("Є проєктор", True),
        ("Немає проєктора", False),
    ]
    room_projector_filter_by_label = {label: value for label, value in room_projector_filter_options}
    room_department_label_by_id: dict[int, str] = {}
    room_department_id_by_label: dict[str, int] = {}
    room_status_all_var = tk.BooleanVar(value=True)
    room_status_active_var = tk.BooleanVar(value=True)
    room_status_archived_var = tk.BooleanVar(value=True)
    room_status_booked_var = tk.BooleanVar(value=True)
    room_filter_sync_state = {"busy": False}
    room_filter_reload_job = {"id": None}
    rooms_count_var = tk.StringVar(value="Аудиторій: 0")

    detail_body = ttk.Frame(detail_view, style="Card.TFrame")
    detail_body.pack(fill=tk.BOTH, expand=True)

    rooms_header = ttk.Frame(detail_body, style="Card.TFrame")
    rooms_header.pack(fill=tk.X, pady=(0, 4))
    ttk.Label(rooms_header, text="Аудиторії", style="CardTitle.TLabel").pack(side=tk.LEFT)
    ttk.Label(rooms_header, textvariable=rooms_count_var, style="CardSubtle.TLabel").pack(side=tk.LEFT, padx=(12, 0), pady=(4, 0))

    filters_shell = ttk.Frame(detail_body, style="Card.TFrame", padding=(2, 2, 2, 2))
    filters_shell.pack(fill=tk.X, pady=(0, 8))
    filters_shell.grid_columnconfigure(1, weight=1)

    ttk.Label(filters_shell, text="Пошук", style="Card.TLabel").grid(row=0, column=0, sticky="w")
    room_search_entry = ttk.Entry(filters_shell, textvariable=room_search_var)
    room_search_entry.grid(row=0, column=1, sticky="ew", padx=(8, 12))

    ttk.Label(filters_shell, text="Тип", style="Card.TLabel").grid(row=0, column=2, sticky="w")
    room_type_box = ttk.Combobox(
        filters_shell,
        textvariable=room_type_filter_var,
        values=[label for label, _ in room_type_options],
        state="readonly",
        width=16,
    )
    room_type_box.grid(row=0, column=3, sticky="w", padx=(8, 12))
    ttk.Label(filters_shell, text="Мін. місткість", style="Card.TLabel").grid(row=0, column=4, sticky="w")
    room_capacity_entry = ttk.Entry(filters_shell, textvariable=room_min_capacity_var, width=8)
    room_capacity_entry.grid(row=0, column=5, sticky="w", padx=(8, 12))
    ttk.Label(filters_shell, text="Кафедра", style="Card.TLabel").grid(row=0, column=6, sticky="w")
    room_department_box = ttk.Combobox(
        filters_shell,
        textvariable=room_department_filter_var,
        state="readonly",
        width=24,
    )
    room_department_box.grid(row=0, column=7, sticky="w", padx=(8, 12))
    ttk.Label(filters_shell, text="Проєктор", style="Card.TLabel").grid(row=0, column=8, sticky="w")
    room_projector_box = ttk.Combobox(
        filters_shell,
        textvariable=room_projector_filter_var,
        values=[label for label, _ in room_projector_filter_options],
        state="readonly",
        width=18,
    )
    room_projector_box.grid(row=0, column=9, sticky="w", padx=(8, 12))

    status_wrap = ttk.Frame(filters_shell, style="Card.TFrame")
    status_wrap.grid(row=1, column=0, columnspan=11, sticky="ew", pady=(12, 0))
    ttk.Label(status_wrap, text="Статус:", style="CardSubtle.TLabel").pack(side=tk.LEFT, padx=(0, 8))
    status_buttons_wrap = ttk.Frame(status_wrap, style="Card.TFrame")
    status_buttons_wrap.pack(side=tk.LEFT, fill=tk.X, expand=True)
    status_chip_specs: list[tuple[str, str, tk.BooleanVar, int]] = [
        ("all", "Усі", room_status_all_var, 74),
        ("active", "Активні", room_status_active_var, 94),
        ("archived", "Архівні", room_status_archived_var, 90),
        ("booked", "Бронь", room_status_booked_var, 82),
    ]
    status_chip_buttons: dict[str, RoundedMotionButton] = {}
    for key, label, variable, width in status_chip_specs:
        chip_button = self._motion_button(
            status_buttons_wrap,
            text=label,
            command=lambda var=variable: var.set(not bool(var.get())),
            primary=False,
            width=width,
            height=30,
        )
        chip_button.pack(side=tk.LEFT, padx=(0, 6))
        status_chip_buttons[key] = chip_button

    def refresh_status_chips() -> None:
        for key, label, variable, _width in status_chip_specs:
            chip_button = status_chip_buttons[key]
            active = bool(variable.get())
            if active:
                chip_button.fill = self.theme.ACCENT
                chip_button.hover_fill = self.theme.ACCENT_HOVER
                chip_button.pressed_fill = self.theme.ACCENT_PRESSED
                chip_button.text_color = self.theme.TEXT_LIGHT
                chip_button.shadow_color = self.theme.SHADOW_SOFT
                chip_button.set_text(f"✓ {label}")
            else:
                chip_button.fill = self.theme.SURFACE_ALT
                chip_button.hover_fill = self.theme.SECONDARY_HOVER
                chip_button.pressed_fill = self.theme.SECONDARY_PRESSED
                chip_button.text_color = self.theme.TEXT_PRIMARY
                chip_button.shadow_color = self.theme.SHADOW_SOFT
                chip_button.set_text(label)

    def on_filter_panel_resize(_event=None) -> None:
        width = max(1, filters_shell.winfo_width())
        compact = width < 1240
        if compact:
            filters_shell.grid_columnconfigure(1, weight=0)
            room_search_entry.grid_configure(columnspan=1)
            room_search_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 12), pady=(6, 0))
            room_type_box.grid(row=1, column=2, sticky="w", padx=(8, 12), pady=(6, 0))
            room_capacity_entry.grid(row=1, column=4, sticky="w", padx=(8, 12), pady=(6, 0))
            room_department_box.grid_configure(row=1, column=6, sticky="w", padx=(8, 12), pady=(6, 0))
            room_projector_box.grid_configure(row=1, column=8, sticky="w", padx=(8, 12), pady=(6, 0))
            reset_filters_button.grid_configure(row=1, column=10, sticky="e", padx=(0, 0), pady=(6, 0))
            status_wrap.grid_configure(row=2, column=0, columnspan=11, pady=(10, 0))
        else:
            filters_shell.grid_columnconfigure(1, weight=1)
            room_search_entry.grid_configure(row=0, column=1, columnspan=1, sticky="ew", padx=(8, 12), pady=(0, 0))
            room_type_box.grid_configure(row=0, column=3, sticky="w", padx=(8, 12), pady=(0, 0))
            room_capacity_entry.grid_configure(row=0, column=5, sticky="w", padx=(8, 12), pady=(0, 0))
            room_department_box.grid_configure(row=0, column=7, sticky="w", padx=(8, 12), pady=(0, 0))
            room_projector_box.grid_configure(row=0, column=9, sticky="w", padx=(8, 12), pady=(0, 0))
            reset_filters_button.grid_configure(row=0, column=10, sticky="e", padx=(0, 0), pady=(0, 0))
            status_wrap.grid_configure(row=1, column=0, columnspan=11, pady=(12, 0))

    rooms_table_wrap = ttk.Frame(detail_body, style="Card.TFrame")
    rooms_table_wrap.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
    rooms_table = ttk.Treeview(
        rooms_table_wrap,
        columns=("name", "type", "capacity", "floor", "department", "projector", "status"),
        show="headings",
        height=18,
    )
    rooms_table.heading("name", text="Назва")
    rooms_table.heading("type", text="Тип")
    rooms_table.heading("capacity", text="Місткість")
    rooms_table.heading("floor", text="Поверх")
    rooms_table.heading("department", text="Кафедра")
    rooms_table.heading("projector", text="Проєктор")
    rooms_table.heading("status", text="Статус")
    rooms_table.column("name", width=280, anchor="w")
    rooms_table.column("type", width=150, anchor="center")
    rooms_table.column("capacity", width=110, anchor="center")
    rooms_table.column("floor", width=110, anchor="center")
    rooms_table.column("department", width=170, anchor="center")
    rooms_table.column("projector", width=110, anchor="center")
    rooms_table.column("status", width=200, anchor="center")
    rooms_table.tag_configure("room_archived", background="#f4e8ef")
    rooms_table.tag_configure("room_booked", background="#e8f0ff")
    rooms_table.tag_configure("room_archived_booked", background="#efe6f8")
    rooms_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    rooms_table_scroll = ttk.Scrollbar(
        rooms_table_wrap,
        orient=tk.VERTICAL,
        command=rooms_table.yview,
        style="App.Vertical.TScrollbar",
    )
    rooms_table_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    rooms_table.configure(yscrollcommand=rooms_table_scroll.set)

    def open_list_view() -> None:
        detail_view.pack_forget()
        list_view.pack(fill=tk.BOTH, expand=True)

    def open_building_view(building) -> None:
        selected_building["item"] = building
        detail_title_var.set(str(building.name))
        detail_address_var.set(str(building.address or "Адресу не вказано"))
        room_filter_sync_state["busy"] = True
        room_search_var.set("")
        room_type_filter_var.set("Усі")
        room_min_capacity_var.set("")
        room_department_filter_var.set("Усі кафедри")
        room_projector_filter_var.set("Усі")
        room_status_all_var.set(True)
        room_status_active_var.set(True)
        room_status_archived_var.set(True)
        room_status_booked_var.set(True)
        room_filter_sync_state["busy"] = False
        load_room_departments()
        refresh_status_chips()
        load_rooms()
        list_view.pack_forget()
        detail_view.pack(fill=tk.BOTH, expand=True)

    def parse_optional_int(raw: str, *, field_name: str, allow_negative: bool = False) -> int | None:
        text = raw.strip()
        if not text:
            return None
        try:
            value = int(text)
        except ValueError as exc:
            raise ValueError(f"Поле '{field_name}' має бути цілим числом.") from exc
        if not allow_negative and value < 0:
            raise ValueError(f"Поле '{field_name}' не може бути від'ємним.")
        return value

    def parse_datetime_input(raw: str, *, field_name: str) -> datetime:
        value = raw.strip()
        if not value:
            raise ValueError(f"Поле '{field_name}' обов'язкове.")
        for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"Поле '{field_name}' має бути у форматі YYYY-MM-DD HH:MM або DD.MM.YYYY HH:MM."
            ) from exc

    def load_room_departments() -> None:
        with session_scope() as session:
            departments = AcademicController(session=session).list_departments(
                company_id=company_id,
                include_archived=False,
            )
        room_department_label_by_id.clear()
        room_department_id_by_label.clear()
        values = ["Усі кафедри"]
        for department in departments:
            label_name = department.short_name or department.name
            label = f"{department.id} | {label_name}"
            room_department_label_by_id[department.id] = label_name
            room_department_id_by_label[label] = department.id
            values.append(label)
        room_department_box["values"] = values
        if room_department_filter_var.get() not in values:
            room_department_filter_var.set("Усі кафедри")

    def selected_room_department_id() -> int | None:
        return room_department_id_by_label.get(room_department_filter_var.get().strip())

    def room_department_display_value(department_id: int | None) -> str:
        if department_id is None:
            return "Не вказано"
        name = room_department_label_by_id.get(department_id)
        if not name:
            return "Не вказано"
        return f"{department_id} | {name}"

    def parse_room_department_selection(raw: str) -> int | None:
        value = raw.strip()
        if not value or value == "Не вказано":
            return None
        department_id = room_department_id_by_label.get(value)
        if department_id is None:
            raise ValueError("Оберіть кафедру зі списку або 'Не вказано'.")
        return department_id

    def schedule_room_filter_reload(delay_ms: int = 220) -> None:
        if room_filter_sync_state["busy"]:
            return
        job_id = room_filter_reload_job["id"]
        if job_id is not None:
            try:
                self.root.after_cancel(job_id)
            except ValueError:
                pass
            room_filter_reload_job["id"] = None

        def _execute_reload() -> None:
            room_filter_reload_job["id"] = None
            load_rooms()

        room_filter_reload_job["id"] = self.root.after(delay_ms, _execute_reload)

    def on_room_status_all_changed(*_args) -> None:
        if room_filter_sync_state["busy"]:
            return
        value = bool(room_status_all_var.get())
        room_filter_sync_state["busy"] = True
        room_status_active_var.set(value)
        room_status_archived_var.set(value)
        room_status_booked_var.set(value)
        room_filter_sync_state["busy"] = False
        refresh_status_chips()
        schedule_room_filter_reload(delay_ms=0)

    def on_room_status_partial_changed(*_args) -> None:
        if room_filter_sync_state["busy"]:
            return
        all_selected = bool(room_status_active_var.get()) and bool(room_status_archived_var.get()) and bool(
            room_status_booked_var.get()
        )
        room_filter_sync_state["busy"] = True
        room_status_all_var.set(all_selected)
        room_filter_sync_state["busy"] = False
        refresh_status_chips()
        schedule_room_filter_reload(delay_ms=0)

    def get_selected_room() -> object | None:
        selected = rooms_table.selection()
        if not selected:
            return None
        item_id = selected[0]
        for room in rooms_state["items"]:
            if str(room.id) == str(item_id):
                return room
        return None

    def render_rooms() -> None:
        for item in rooms_table.get_children():
            rooms_table.delete(item)

        items = rooms_state["items"]
        rooms_count_var.set(f"Аудиторій: {len(items)}")
        now = datetime.utcnow()
        for room in items:
            booking = room_booking_state.get(int(room.id))
            is_booked = booking is not None
            if is_booked:
                starts_at = booking.starts_at
                ends_at = booking.ends_at
                if starts_at <= now <= ends_at:
                    status_text = f"Заброньована до {ends_at.strftime('%d.%m %H:%M')}"
                else:
                    status_text = f"Бронь з {starts_at.strftime('%d.%m %H:%M')}"
            else:
                status_text = "Активна"
            if bool(room.is_archived):
                status_text = "Архівна" if not is_booked else f"Архівна • {status_text}"

            row_tags: tuple[str, ...] = ()
            if bool(room.is_archived) and is_booked:
                row_tags = ("room_archived_booked",)
            elif bool(room.is_archived):
                row_tags = ("room_archived",)
            elif is_booked:
                row_tags = ("room_booked",)

            rooms_table.insert(
                "",
                tk.END,
                iid=str(room.id),
                values=(
                    str(room.name),
                    room_type_label_by_enum.get(room.room_type, "Інше"),
                    "" if room.capacity is None else str(room.capacity),
                    "" if room.floor is None else str(room.floor),
                    room_department_label_by_id.get(room.home_department_id, "—") if room.home_department_id is not None else "—",
                    "Так" if bool(room.has_projector) else "Ні",
                    status_text,
                ),
                tags=row_tags,
            )

    def load_rooms() -> None:
        building = selected_building["item"]
        if building is None:
            rooms_state["items"] = []
            render_rooms()
            return

        selected_type_label = room_type_filter_var.get().strip() or "Усі"
        room_type_filter = None
        if selected_type_label != "Усі":
            room_type_filter = room_type_by_label.get(selected_type_label)
            if room_type_filter is None:
                messagebox.showerror("Некоректний фільтр", "Невідомий тип аудиторії.", parent=self.root)
                return

        min_capacity = None
        raw_capacity = room_min_capacity_var.get().strip()
        if raw_capacity:
            if not raw_capacity.isdigit():
                return
            min_capacity = int(raw_capacity)
        home_department_id = selected_room_department_id()
        selected_projector_label = room_projector_filter_var.get().strip() or "Усі"
        if selected_projector_label not in room_projector_filter_by_label:
            messagebox.showerror("Некоректний фільтр", "Невідомий стан фільтра проєктора.", parent=self.root)
            return
        has_projector_filter = room_projector_filter_by_label[selected_projector_label]

        with session_scope() as session:
            controller = RoomController(session=session)
            rooms = controller.list_rooms(
                building_id=building.id,
                include_archived=True,
                search=room_search_var.get().strip() or None,
                room_type=room_type_filter,
                min_capacity=min_capacity,
                has_projector=has_projector_filter,
                home_department_id=home_department_id,
            )
            room_booking_state.clear()
            room_booking_state.update(
                controller.upcoming_booking_map([int(room.id) for room in rooms])
            )

        show_active = bool(room_status_active_var.get())
        show_archived = bool(room_status_archived_var.get())
        show_booked = bool(room_status_booked_var.get())

        filtered_rooms: list[object] = []
        for room in rooms:
            room_id = int(room.id)
            is_archived = bool(room.is_archived)
            is_booked = room_id in room_booking_state
            include_room = (
                (show_active and (not is_archived and not is_booked))
                or (show_archived and is_archived)
                or (show_booked and is_booked)
            )
            if include_room:
                filtered_rooms.append(room)

        rooms_state["items"] = filtered_rooms
        render_rooms()
        refresh_room_action_state()

    def open_room_modal(room=None) -> None:
        building = selected_building["item"]
        if building is None:
            messagebox.showerror("Аудиторія", "Спочатку виберіть корпус.", parent=self.root)
            return
        load_room_departments()

        is_edit = room is not None
        modal = tk.Toplevel(self.root)
        modal.title("Редагування аудиторії" if is_edit else "Створення аудиторії")
        modal.transient(self.root)
        modal.resizable(False, False)
        modal.grab_set()

        shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        ttk.Label(shell, text="Редагування аудиторії" if is_edit else "Створення аудиторії", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(shell, text=f"Корпус: {building.name}", style="CardSubtle.TLabel").pack(anchor="w", pady=(2, 10))

        name_var = tk.StringVar(value=str(room.name) if is_edit else "")
        type_var = tk.StringVar(value=room_type_label_by_enum.get(room.room_type, "Клас") if is_edit else "Клас")
        capacity_var = tk.StringVar(value="" if (not is_edit or room.capacity is None) else str(room.capacity))
        floor_var = tk.StringVar(value="" if (not is_edit or room.floor is None) else str(room.floor))
        has_projector_var = tk.BooleanVar(value=bool(room.has_projector) if is_edit else False)
        department_values = ["Не вказано"] + list(room_department_id_by_label.keys())
        department_var = tk.StringVar(value=room_department_display_value(room.home_department_id) if is_edit else "Не вказано")

        ttk.Label(shell, text="Назва", style="Card.TLabel").pack(anchor="w")
        name_entry = ttk.Entry(shell, textvariable=name_var, width=38)
        name_entry.pack(fill=tk.X, pady=(6, 10))

        ttk.Label(shell, text="Тип", style="Card.TLabel").pack(anchor="w")
        ttk.Combobox(
            shell,
            textvariable=type_var,
            values=room_type_choices,
            state="readonly",
            width=24,
        ).pack(fill=tk.X, pady=(6, 10))

        row = ttk.Frame(shell, style="Card.TFrame")
        row.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(row, text="Місткість", style="Card.TLabel").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=capacity_var, width=10).pack(side=tk.LEFT, padx=(6, 14))
        ttk.Label(row, text="Поверх", style="Card.TLabel").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=floor_var, width=10).pack(side=tk.LEFT, padx=(6, 0))

        dep_row = ttk.Frame(shell, style="Card.TFrame")
        dep_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(dep_row, text="Кафедра", style="Card.TLabel").pack(side=tk.LEFT)
        ttk.Combobox(
            dep_row,
            textvariable=department_var,
            values=department_values,
            state="readonly",
            width=32,
        ).pack(side=tk.LEFT, padx=(8, 0))

        projector_row = ttk.Frame(shell, style="Card.TFrame")
        projector_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Checkbutton(
            projector_row,
            text="Є проєктор",
            variable=has_projector_var,
        ).pack(anchor="w")

        actions = ttk.Frame(shell, style="Card.TFrame")
        actions.pack(fill=tk.X)

        def on_submit() -> None:
            clean_name = name_var.get().strip()
            if not clean_name:
                messagebox.showerror("Некоректні дані", "Назва аудиторії обов'язкова.", parent=modal)
                return

            selected_type = room_type_by_label.get(type_var.get().strip())
            if selected_type is None:
                messagebox.showerror("Некоректні дані", "Оберіть тип аудиторії зі списку.", parent=modal)
                return

            try:
                capacity = parse_optional_int(capacity_var.get(), field_name="Місткість", allow_negative=False)
                floor = parse_optional_int(floor_var.get(), field_name="Поверх", allow_negative=True)
                department_id = parse_room_department_selection(department_var.get())
            except ValueError as exc:
                messagebox.showerror("Некоректні дані", str(exc), parent=modal)
                return

            try:
                with session_scope() as session:
                    controller = RoomController(session=session)
                    if is_edit:
                        controller.update_room(
                            room.id,
                            name=clean_name,
                            room_type=selected_type,
                            capacity=capacity,
                            floor=floor,
                            has_projector=bool(has_projector_var.get()),
                            home_department_id=department_id,
                            is_archived=False,
                        )
                    else:
                        controller.create_room(
                            building_id=building.id,
                            name=clean_name,
                            room_type=selected_type,
                            capacity=capacity,
                            floor=floor,
                            has_projector=bool(has_projector_var.get()),
                            home_department_id=department_id,
                            company_id=company_id,
                        )
            except IntegrityError:
                messagebox.showerror(
                    "Не вдалося зберегти аудиторію",
                    "Аудиторія з такою назвою вже існує в цьому корпусі.",
                    parent=modal,
                )
                return
            except Exception as exc:
                messagebox.showerror("Не вдалося зберегти аудиторію", str(exc), parent=modal)
                return

            modal.destroy()
            load_rooms()

        self._motion_button(actions, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
        self._motion_button(actions, text="Зберегти", command=on_submit, primary=True, width=130).pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )

        name_entry.focus_set()
        modal.update_idletasks()
        modal.geometry(f"+{self.root.winfo_rootx() + 220}+{self.root.winfo_rooty() + 120}")

    def toggle_archive_selected_room() -> None:
        room = get_selected_room()
        if room is None:
            messagebox.showerror("Статус аудиторії", "Оберіть аудиторію у списку.", parent=self.root)
            return

        is_archived = bool(room.is_archived)
        action_title = "Розархівування аудиторії" if is_archived else "Архівація аудиторії"
        question = (
            f"Розархівувати аудиторію '{room.name}'?"
            if is_archived
            else f"Архівувати аудиторію '{room.name}'?"
        )
        if not messagebox.askyesno(action_title, question, parent=self.root):
            return

        with session_scope() as session:
            controller = RoomController(session=session)
            if is_archived:
                controller.unarchive_room(room.id)
            else:
                controller.archive_room(room.id)
        load_rooms()

    def open_book_room_modal(room=None) -> None:
        target = room if room is not None else get_selected_room()
        if target is None:
            messagebox.showerror("Бронювання аудиторії", "Оберіть аудиторію у списку.", parent=self.root)
            return
        if bool(target.is_archived):
            messagebox.showerror(
                "Бронювання аудиторії",
                "Архівовану аудиторію не можна забронювати. Спочатку розархівуйте її.",
                parent=self.root,
            )
            return

        now = datetime.now().replace(second=0, microsecond=0)
        default_start = now + timedelta(minutes=30 - (now.minute % 30 or 30))
        default_end = default_start + timedelta(hours=1)

        modal = tk.Toplevel(self.root)
        modal.title("Бронювання аудиторії")
        modal.transient(self.root)
        modal.resizable(False, False)
        modal.grab_set()

        shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        ttk.Label(shell, text="Бронювання аудиторії", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(shell, text=f"Аудиторія: {target.name}", style="CardSubtle.TLabel").pack(anchor="w", pady=(2, 10))

        title_var = tk.StringVar(value="")
        starts_var = tk.StringVar(value=default_start.strftime("%Y-%m-%d %H:%M"))
        ends_var = tk.StringVar(value=default_end.strftime("%Y-%m-%d %H:%M"))

        ttk.Label(shell, text="Назва / примітка", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=title_var, width=42).pack(fill=tk.X, pady=(6, 10))
        ttk.Label(shell, text="Початок", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=starts_var, width=24).pack(fill=tk.X, pady=(6, 10))
        ttk.Label(shell, text="Кінець", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=ends_var, width=24).pack(fill=tk.X, pady=(6, 4))
        ttk.Label(
            shell,
            text="Формат: YYYY-MM-DD HH:MM або DD.MM.YYYY HH:MM",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        actions = ttk.Frame(shell, style="Card.TFrame")
        actions.pack(fill=tk.X)

        def on_submit_booking() -> None:
            try:
                starts_at = parse_datetime_input(starts_var.get(), field_name="Початок")
                ends_at = parse_datetime_input(ends_var.get(), field_name="Кінець")
            except ValueError as exc:
                messagebox.showerror("Некоректні дані", str(exc), parent=modal)
                return

            try:
                with session_scope() as session:
                    controller = RoomController(session=session)
                    controller.create_room_booking(
                        room_id=int(target.id),
                        starts_at=starts_at,
                        ends_at=ends_at,
                        title=title_var.get().strip() or None,
                    )
            except Exception as exc:
                messagebox.showerror("Бронювання аудиторії", str(exc), parent=modal)
                return

            modal.destroy()
            load_rooms()

        self._motion_button(actions, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
        self._motion_button(actions, text="Забронювати", command=on_submit_booking, primary=True, width=130).pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )

        modal.update_idletasks()
        modal.geometry(f"+{self.root.winfo_rootx() + 250}+{self.root.winfo_rooty() + 130}")

    def delete_selected_room() -> None:
        room = get_selected_room()
        if room is None:
            messagebox.showerror("Видалення аудиторії", "Оберіть аудиторію у списку.", parent=self.root)
            return
        if not messagebox.askyesno("Видалення аудиторії", f"Видалити аудиторію '{room.name}' назавжди?", parent=self.root):
            return
        try:
            with session_scope() as session:
                controller = RoomController(session=session)
                was_deleted = controller.delete_room(room.id)
            if not was_deleted:
                messagebox.showerror("Видалення аудиторії", "Аудиторію не знайдено.", parent=self.root)
                return
        except IntegrityError:
            messagebox.showerror(
                "Видалення аудиторії",
                "Аудиторію використано в пов'язаних даних і її не можна видалити.",
                parent=self.root,
            )
            return
        except Exception as exc:
            messagebox.showerror("Видалення аудиторії", str(exc), parent=self.root)
            return
        load_rooms()

    def open_bulk_create_rooms_modal() -> None:
        building = selected_building["item"]
        if building is None:
            messagebox.showerror("Масове створення", "Спочатку виберіть корпус.", parent=self.root)
            return
        load_room_departments()

        modal = tk.Toplevel(self.root)
        modal.title("Масове створення аудиторій")
        modal.transient(self.root)
        modal.resizable(False, False)
        modal.grab_set()

        shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        ttk.Label(shell, text="Масове створення аудиторій", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(shell, text=f"Корпус: {building.name}", style="CardSubtle.TLabel").pack(anchor="w", pady=(2, 10))

        mode_var = tk.StringVar(value="range")
        mode_buttons: dict[str, tk.Button] = {}

        tabs_shell = ttk.Frame(shell, style="Card.TFrame")
        tabs_shell.pack(fill=tk.X, pady=(0, 8))
        tabs_shell.grid_columnconfigure(0, weight=1)
        tabs_shell.grid_columnconfigure(1, weight=1)

        def set_bulk_mode(mode: str) -> None:
            mode_var.set(mode)
            refresh_mode_tabs()
            render_mode_panel()

        def refresh_mode_tabs() -> None:
            active_mode = mode_var.get()
            for mode_name, button in mode_buttons.items():
                is_active = mode_name == active_mode
                button.configure(
                    bg=self.theme.ACCENT if is_active else self.theme.SURFACE_ALT,
                    fg=self.theme.TEXT_LIGHT if is_active else self.theme.TEXT_PRIMARY,
                    activebackground=self.theme.ACCENT_HOVER if is_active else self.theme.SECONDARY_HOVER,
                    activeforeground=self.theme.TEXT_LIGHT if is_active else self.theme.TEXT_PRIMARY,
                    relief=tk.FLAT,
                    bd=0,
                    cursor="hand2",
                )

        def make_tab_button(*, label: str, mode: str, column: int) -> None:
            button = tk.Button(
                tabs_shell,
                text=label,
                font=("Segoe UI", 10, "bold"),
                padx=12,
                pady=8,
                command=lambda m=mode: set_bulk_mode(m),
            )
            button.grid(row=0, column=column, sticky="ew", padx=(0, 6) if column == 0 else (6, 0))
            mode_buttons[mode] = button

        make_tab_button(label="Діапазон", mode="range", column=0)
        make_tab_button(label="Список", mode="list", column=1)

        prefix_var = tk.StringVar(value=f"{building.name}-")
        start_var = tk.StringVar(value="101")
        end_var = tk.StringVar(value="120")
        step_var = tk.StringVar(value="1")
        exclude_var = tk.StringVar(value="")

        mode_panel = ttk.Frame(shell, style="Card.TFrame")
        mode_panel.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        range_panel = ttk.Frame(mode_panel, style="Card.TFrame")
        list_panel = ttk.Frame(mode_panel, style="Card.TFrame")

        list_text = tk.Text(
            list_panel,
            height=8,
            width=48,
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.TEXT_PRIMARY,
            insertbackground=self.theme.TEXT_PRIMARY,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            highlightcolor=self.theme.ACCENT,
        )

        grid = ttk.Frame(range_panel, style="Card.TFrame")
        grid.pack(fill=tk.X)
        ttk.Label(grid, text="Префікс", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(grid, textvariable=prefix_var, width=14).grid(row=1, column=0, sticky="w", pady=(4, 8))
        ttk.Label(grid, text="Початок", style="Card.TLabel").grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Entry(grid, textvariable=start_var, width=8).grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(4, 8))
        ttk.Label(grid, text="Кінець", style="Card.TLabel").grid(row=0, column=2, sticky="w", padx=(10, 0))
        ttk.Entry(grid, textvariable=end_var, width=8).grid(row=1, column=2, sticky="w", padx=(10, 0), pady=(4, 8))
        ttk.Label(grid, text="Крок", style="Card.TLabel").grid(row=0, column=3, sticky="w", padx=(10, 0))
        ttk.Entry(grid, textvariable=step_var, width=8).grid(row=1, column=3, sticky="w", padx=(10, 0), pady=(4, 8))
        ttk.Label(grid, text="Виключити (через кому)", style="CardSubtle.TLabel").grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="w",
        )
        ttk.Entry(grid, textvariable=exclude_var, width=40).grid(row=3, column=0, columnspan=4, sticky="ew", pady=(4, 0))

        ttk.Label(list_panel, text="Список назв: одна назва аудиторії на рядок", style="CardSubtle.TLabel").pack(anchor="w")
        list_text.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        def render_mode_panel() -> None:
            range_panel.pack_forget()
            list_panel.pack_forget()
            if mode_var.get() == "list":
                list_panel.pack(fill=tk.BOTH, expand=True)
            else:
                range_panel.pack(fill=tk.X)

        refresh_mode_tabs()
        render_mode_panel()

        settings_row = ttk.Frame(shell, style="Card.TFrame")
        settings_row.pack(fill=tk.X, pady=(0, 10))
        type_var = tk.StringVar(value="Клас")
        capacity_var = tk.StringVar(value="")
        floor_var = tk.StringVar(value="")
        bulk_has_projector_var = tk.BooleanVar(value=False)
        bulk_department_values = ["Не вказано"] + list(room_department_id_by_label.keys())
        bulk_department_var = tk.StringVar(value="Не вказано")
        policy_var = tk.StringVar(value="Пропустити дублікати")

        ttk.Label(settings_row, text="Тип", style="Card.TLabel").pack(side=tk.LEFT)
        ttk.Combobox(settings_row, textvariable=type_var, values=room_type_choices, state="readonly", width=16).pack(
            side=tk.LEFT,
            padx=(6, 10),
        )
        ttk.Label(settings_row, text="Місткість", style="Card.TLabel").pack(side=tk.LEFT)
        ttk.Entry(settings_row, textvariable=capacity_var, width=8).pack(side=tk.LEFT, padx=(6, 10))
        ttk.Label(settings_row, text="Поверх", style="Card.TLabel").pack(side=tk.LEFT)
        ttk.Entry(settings_row, textvariable=floor_var, width=8).pack(side=tk.LEFT, padx=(6, 10))
        ttk.Checkbutton(
            settings_row,
            text="Проєктор",
            variable=bulk_has_projector_var,
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(settings_row, text="Кафедра", style="Card.TLabel").pack(side=tk.LEFT)
        ttk.Combobox(
            settings_row,
            textvariable=bulk_department_var,
            values=bulk_department_values,
            state="readonly",
            width=22,
        ).pack(side=tk.LEFT, padx=(6, 10))
        ttk.Label(settings_row, text="Дублікати", style="Card.TLabel").pack(side=tk.LEFT)
        ttk.Combobox(
            settings_row,
            textvariable=policy_var,
            values=["Пропустити дублікати", "Зупинити при дублікаті", "Оновити наявні"],
            state="readonly",
            width=17,
        ).pack(side=tk.LEFT, padx=(6, 0))

        footer = ttk.Frame(shell, style="Card.TFrame")
        footer.pack(fill=tk.X)

        def on_submit_bulk() -> None:
            selected_type = room_type_by_label.get(type_var.get().strip())
            if selected_type is None:
                messagebox.showerror("Некоректні дані", "Оберіть тип аудиторії зі списку.", parent=modal)
                return

            policy = {
                "Пропустити дублікати": "skip",
                "Зупинити при дублікаті": "fail",
                "Оновити наявні": "update",
            }.get(policy_var.get().strip())
            if policy is None:
                messagebox.showerror("Некоректні дані", "Оберіть коректну політику дублікатів.", parent=modal)
                return

            try:
                capacity = parse_optional_int(capacity_var.get(), field_name="Місткість", allow_negative=False)
                floor = parse_optional_int(floor_var.get(), field_name="Поверх", allow_negative=True)
                home_department_id = parse_room_department_selection(bulk_department_var.get())
            except ValueError as exc:
                messagebox.showerror("Некоректні дані", str(exc), parent=modal)
                return

            if mode_var.get() == "list":
                names = [line.strip() for line in list_text.get("1.0", "end").splitlines() if line.strip()]
            else:
                try:
                    start = int(start_var.get().strip())
                    end = int(end_var.get().strip())
                    step = int(step_var.get().strip())
                except ValueError:
                    messagebox.showerror("Некоректні дані", "Початок, кінець і крок мають бути цілими числами.", parent=modal)
                    return
                if step <= 0 or end < start:
                    messagebox.showerror("Некоректні дані", "Діапазон номерів некоректний.", parent=modal)
                    return
                excluded = set()
                raw_excluded = exclude_var.get().strip()
                if raw_excluded:
                    try:
                        excluded = {
                            int(token.strip())
                            for token in raw_excluded.replace(";", ",").split(",")
                            if token.strip()
                        }
                    except ValueError:
                        messagebox.showerror("Некоректні дані", "Список виключень має містити лише числа.", parent=modal)
                        return
                prefix = prefix_var.get().strip()
                names = [f"{prefix}{number}" for number in range(start, end + 1, step) if number not in excluded]

            if not names:
                messagebox.showerror("Некоректні дані", "Немає назв аудиторій для створення.", parent=modal)
                return

            try:
                with session_scope() as session:
                    controller = RoomController(session=session)
                    result = controller.bulk_create_rooms(
                        building_id=building.id,
                        names=names,
                        room_type=selected_type,
                        capacity=capacity,
                        floor=floor,
                        has_projector=bool(bulk_has_projector_var.get()),
                        home_department_id=home_department_id,
                        company_id=company_id,
                        duplicate_policy=policy,
                    )
            except IntegrityError:
                messagebox.showerror("Не вдалося створити аудиторії", "Сталася помилка цілісності даних.", parent=modal)
                return
            except Exception as exc:
                messagebox.showerror("Не вдалося створити аудиторії", str(exc), parent=modal)
                return

            modal.destroy()
            load_rooms()
            messagebox.showinfo(
                "Масове створення",
                f"Створено: {result['created']}\nОновлено: {result['updated']}\nПропущено: {result['skipped']}",
                parent=self.root,
            )

        self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
        self._motion_button(footer, text="Створити", command=on_submit_bulk, primary=True, width=130).pack(
            side=tk.RIGHT,
            padx=(0, 8),
        )

        modal.update_idletasks()
        modal.geometry(f"+{self.root.winfo_rootx() + 210}+{self.root.winfo_rooty() + 90}")

    def sync_cards_scroll(_event=None) -> None:
        viewport_width = max(1, cards_canvas.winfo_width())
        cards_canvas.itemconfigure(cards_window, width=viewport_width)
        bbox = cards_canvas.bbox("all")
        if bbox is not None:
            cards_canvas.configure(scrollregion=bbox)

    def compute_columns(width: int) -> int:
        if width >= 1280:
            return 4
        if width >= 980:
            return 3
        if width >= 680:
            return 2
        return 1

    def render_buildings() -> None:
        for child in cards_grid.winfo_children():
            child.destroy()

        items = buildings_state["items"]
        if not items:
            empty = ttk.Label(
                cards_grid,
                text="Ще немає корпусів. Додайте перший корпус.",
                style="CardSubtle.TLabel",
            )
            empty.grid(row=0, column=0, sticky="w", padx=8, pady=8)
            sync_cards_scroll()
            return

        columns = max(1, int(columns_state["value"]))
        for col in range(columns):
            cards_grid.grid_columnconfigure(col, weight=1, uniform="building-col")

        for index, building in enumerate(items):
            row = index // columns
            col = index % columns
            card = RoundedMotionCard(
                cards_grid,
                bg_color=self.theme.SURFACE,
                card_color=self.theme.SURFACE_ALT,
                shadow_color=self.theme.SHADOW_SOFT,
                radius=16,
                padding=4,
                shadow_offset=4,
                motion_enabled=True,
                height=150,
            )
            card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
            card.content.grid_columnconfigure(0, weight=1)

            title_label = tk.Label(
                card.content,
                text=str(building.name),
                bg=self.theme.SURFACE_ALT,
                fg=self.theme.TEXT_PRIMARY,
                font=("Segoe UI", 12, "bold"),
                anchor="w",
                justify=tk.LEFT,
                wraplength=220,
            )
            title_label.grid(row=0, column=0, sticky="ew", pady=(2, 2))
            address_label = tk.Label(
                card.content,
                text=str(building.address or "Адресу не вказано"),
                bg=self.theme.SURFACE_ALT,
                fg=self.theme.TEXT_MUTED,
                font=("Segoe UI", 10),
                anchor="w",
                justify=tk.LEFT,
                wraplength=220,
            )
            address_label.grid(row=1, column=0, sticky="ew", pady=(2, 0))
            meta_label = tk.Label(
                card.content,
                text=f"ID корпусу: {building.id}",
                bg=self.theme.SURFACE_ALT,
                fg=self.theme.TEXT_MUTED,
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            )
            meta_label.grid(row=2, column=0, sticky="w", pady=(8, 0))

            def on_card_resize(
                event: tk.Event,
                name_ref: tk.Label = title_label,
                addr_ref: tk.Label = address_label,
            ) -> None:
                wrap = max(120, event.width - 28)
                name_ref.configure(wraplength=wrap)
                addr_ref.configure(wraplength=wrap)

            card.content.bind("<Configure>", on_card_resize, add="+")

            for widget in (card, card.canvas, card.content, title_label, address_label, meta_label):
                widget.bind("<Button-1>", lambda _e, b=building: open_building_view(b), add="+")

        sync_cards_scroll()

    def load_buildings() -> None:
        with session_scope() as session:
            controller = BuildingController(session=session)
            buildings = controller.list_buildings(company_id=company_id, include_archived=False)
        buildings_state["items"] = buildings

    def on_cards_resize(_event=None) -> None:
        sync_cards_scroll()
        new_columns = compute_columns(cards_canvas.winfo_width())
        if new_columns == columns_state["value"]:
            return
        columns_state["value"] = new_columns
        render_buildings()

    cards_grid.bind("<Configure>", sync_cards_scroll, add="+")
    cards_canvas.bind("<Configure>", on_cards_resize, add="+")

    def on_reset_room_filters() -> None:
        room_filter_sync_state["busy"] = True
        room_search_var.set("")
        room_type_filter_var.set("Усі")
        room_min_capacity_var.set("")
        room_department_filter_var.set("Усі кафедри")
        room_projector_filter_var.set("Усі")
        room_status_all_var.set(True)
        room_status_active_var.set(True)
        room_status_archived_var.set(True)
        room_status_booked_var.set(True)
        room_filter_sync_state["busy"] = False
        refresh_status_chips()
        load_rooms()

    room_action_buttons: list[object] = []

    button_new_room = self._motion_button(
        detail_actions,
        text="+ Нова аудиторія",
        command=lambda: open_room_modal(room=None),
        primary=True,
        width=138,
        height=38,
    )
    room_action_buttons.append(button_new_room)
    button_bulk_create = self._motion_button(
        detail_actions,
        text="+ Масове додавання",
        command=open_bulk_create_rooms_modal,
        primary=False,
        width=152,
        height=38,
    )
    room_action_buttons.append(button_bulk_create)
    button_edit_room = self._motion_button(
        detail_actions,
        text="Редагувати",
        command=lambda: open_room_modal(room=get_selected_room()) if get_selected_room() is not None else messagebox.showerror(
            "Редагування аудиторії",
            "Оберіть аудиторію у списку.",
            parent=self.root,
        ),
        primary=False,
        width=112,
        height=38,
    )
    room_action_buttons.append(button_edit_room)
    archive_toggle_button = self._motion_button(
        detail_actions,
        text="Архівувати",
        command=toggle_archive_selected_room,
        primary=False,
        width=124,
        height=38,
    )
    room_action_buttons.append(archive_toggle_button)
    button_book_room = self._motion_button(
        detail_actions,
        text="Забронювати",
        command=lambda: open_book_room_modal(room=None),
        primary=False,
        width=124,
        height=38,
    )
    room_action_buttons.append(button_book_room)
    button_delete_room = self._motion_button(
        detail_actions,
        text="Видалити",
        command=delete_selected_room,
        primary=False,
        width=108,
        height=38,
        fill="#e11d48",
        hover_fill="#be123c",
        pressed_fill="#9f1239",
        text_color=self.theme.TEXT_LIGHT,
    )
    room_action_buttons.append(button_delete_room)

    def relayout_room_actions(_event=None) -> None:
        width = max(1, detail_actions.winfo_width())
        if width >= 860:
            columns = 6
        elif width >= 740:
            columns = 5
        elif width >= 610:
            columns = 4
        elif width >= 470:
            columns = 3
        elif width >= 340:
            columns = 2
        else:
            columns = 1
        max_columns = 6
        for col in range(max_columns):
            if col < columns:
                detail_actions.grid_columnconfigure(col, weight=1, uniform="room-action-col")
            else:
                detail_actions.grid_columnconfigure(col, weight=0, uniform="")
        for index, button in enumerate(room_action_buttons):
            row = index // columns
            col = index % columns
            button.grid(row=row, column=col, sticky="ew", padx=4, pady=4)

    def refresh_room_action_state(_event=None) -> None:
        room = get_selected_room()
        if room is not None and bool(room.is_archived):
            archive_toggle_button.set_text("Розархівувати")
        else:
            archive_toggle_button.set_text("Архівувати")

    room_context_menu = tk.Menu(self.root, tearoff=0)

    def on_rooms_table_context_menu(event: tk.Event) -> str:
        row_id = rooms_table.identify_row(event.y)
        if not row_id:
            return "break"
        rooms_table.selection_set(row_id)
        refresh_room_action_state()

        room = get_selected_room()
        if room is None:
            return "break"

        room_context_menu.delete(0, tk.END)
        room_context_menu.add_command(label="Редагувати", command=lambda: open_room_modal(room=room))
        room_context_menu.add_command(
            label="Розархівувати" if bool(room.is_archived) else "Архівувати",
            command=toggle_archive_selected_room,
        )
        room_context_menu.add_command(label="Забронювати", command=lambda: open_book_room_modal(room=room))
        room_context_menu.add_separator()
        room_context_menu.add_command(label="Видалити", command=delete_selected_room)
        room_context_menu.tk_popup(event.x_root, event.y_root)
        room_context_menu.grab_release()
        return "break"

    reset_filters_button = self._motion_button(
        filters_shell,
        text="Скинути",
        command=on_reset_room_filters,
        primary=False,
        width=108,
        height=34,
    )
    on_filter_panel_resize()
    refresh_status_chips()

    room_search_var.trace_add("write", lambda *_args: schedule_room_filter_reload())
    room_min_capacity_var.trace_add("write", lambda *_args: schedule_room_filter_reload())
    room_status_all_var.trace_add("write", on_room_status_all_changed)
    room_status_active_var.trace_add("write", on_room_status_partial_changed)
    room_status_archived_var.trace_add("write", on_room_status_partial_changed)
    room_status_booked_var.trace_add("write", on_room_status_partial_changed)
    room_type_box.bind("<<ComboboxSelected>>", lambda _e: load_rooms(), add="+")
    room_department_box.bind("<<ComboboxSelected>>", lambda _e: load_rooms(), add="+")
    room_projector_box.bind("<<ComboboxSelected>>", lambda _e: load_rooms(), add="+")
    filters_shell.bind("<Configure>", on_filter_panel_resize, add="+")
    detail_actions.bind("<Configure>", relayout_room_actions, add="+")
    relayout_room_actions()

    rooms_table.bind("<<TreeviewSelect>>", refresh_room_action_state, add="+")
    rooms_table.bind("<Button-3>", on_rooms_table_context_menu, add="+")

    def open_create_building_modal() -> None:
        modal = tk.Toplevel(self.root)
        modal.title("Новий корпус")
        modal.transient(self.root)
        modal.resizable(False, False)
        modal.grab_set()

        shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
        shell.pack(fill=tk.BOTH, expand=True)
        ttk.Label(shell, text="Створення корпусу", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            shell,
            text="Назва обов'язкова. Адреса необов'язкова.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(2, 10))

        name_var = tk.StringVar()
        address_var = tk.StringVar()

        ttk.Label(shell, text="Назва", style="Card.TLabel").pack(anchor="w")
        name_entry = ttk.Entry(shell, textvariable=name_var, width=44)
        name_entry.pack(fill=tk.X, pady=(6, 10))
        ttk.Label(shell, text="Адреса", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(shell, textvariable=address_var, width=44).pack(fill=tk.X, pady=(6, 12))

        buttons = ttk.Frame(shell, style="Card.TFrame")
        buttons.pack(fill=tk.X, pady=(2, 0))

        def on_submit() -> None:
            clean_name = name_var.get().strip()
            clean_address = address_var.get().strip()
            if not clean_name:
                messagebox.showerror("Некоректні дані", "Назва корпусу обов'язкова.", parent=modal)
                return
            try:
                with session_scope() as session:
                    controller = BuildingController(session=session)
                    controller.create_building(
                        name=clean_name,
                        address=clean_address or None,
                        company_id=company_id,
                    )
            except IntegrityError:
                messagebox.showerror(
                    "Не вдалося створити корпус",
                    "Корпус з такою назвою вже існує.",
                    parent=modal,
                )
                return
            except Exception as exc:
                messagebox.showerror("Не вдалося створити корпус", str(exc), parent=modal)
                return

            modal.destroy()
            load_buildings()
            render_buildings()

        self._motion_button(
            buttons,
            text="Скасувати",
            command=modal.destroy,
            primary=False,
            width=140,
        ).pack(side=tk.RIGHT)
        self._motion_button(
            buttons,
            text="Створити",
            command=on_submit,
            primary=True,
            width=140,
        ).pack(side=tk.RIGHT, padx=(0, 8))

        name_entry.focus_set()
        modal.update_idletasks()
        modal.geometry(
            f"+{self.root.winfo_rootx() + 180}+{self.root.winfo_rooty() + 110}"
        )

    self._motion_button(
        header,
        text="+ Створити корпус",
        command=open_create_building_modal,
        primary=True,
        width=190,
    ).pack(side=tk.RIGHT)

    load_buildings()
    columns_state["value"] = compute_columns(max(1, cards_canvas.winfo_width()))
    render_buildings()
    render_rooms()
