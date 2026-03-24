# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.main_window import *  # noqa: F401,F403

def _build_company_settings_profile_tab__impl(self, parent: ttk.Frame, *, company_id: int, username: str) -> None:
    with session_scope() as session:
        controller = AuthController(session=session)
        company = controller.get_company(company_id)
        profile = controller.get_company_profile(company_id)

    company_name_default = company.name if company is not None else f"Компанія #{company_id}"
    timezone_default = (profile.timezone or DEFAULT_TIMEZONE).strip()
    language_default_code = (profile.language or DEFAULT_LANGUAGE_CODE).strip().lower()
    theme_default = (profile.theme or UiTheme.DEFAULT_VARIANT).strip().lower()
    logo_default = profile.logo_path

    company_name_var = tk.StringVar(value=company_name_default)
    timezone_var = tk.StringVar(value=timezone_default)
    avatar_storage = AvatarStorageService()
    avatar_state = {
        "current_logo_path": logo_default,
        "pending_source_path": None,
        "remove_current": False,
        "hover": False,
        "image": None,
    }

    theme_label_by_key = {
        "ocean": "Океан",
        "graphite": "Графіт",
        "sunrise": "Світанок",
        "aurora": "Аврора",
        "sand": "Пісок",
        "berry": "Ягідна",
    }
    theme_key_by_label = {label: key for key, label in theme_label_by_key.items()}
    theme_var = tk.StringVar(value=theme_label_by_key.get(theme_default, theme_label_by_key["ocean"]))

    timezone_options = all_timezones()
    if timezone_default not in timezone_options:
        timezone_options.append(timezone_default)
        timezone_options = sorted(timezone_options)

    language_label_by_code = {code: f"{label} ({code})" for code, label in LANGUAGE_OPTIONS}
    language_code_by_label = {value: key for key, value in language_label_by_code.items()}
    language_var = tk.StringVar(
        value=language_label_by_code.get(
            language_default_code,
            language_label_by_code[DEFAULT_LANGUAGE_CODE],
        )
    )

    header_shell = RoundedMotionCard(
        parent,
        bg_color=self.theme.SURFACE,
        card_color=self.theme.SURFACE,
        shadow_color=self.theme.SHADOW_SOFT,
        radius=18,
        padding=4,
        shadow_offset=4,
        motion_enabled=True,
        height=170,
    )
    header_shell.pack(fill=tk.X, pady=(0, 10))
    header_shell.pack_propagate(False)
    header = ttk.Frame(header_shell.content, style="Card.TFrame", padding=8)
    header.pack(fill=tk.BOTH, expand=True)
    header.grid_columnconfigure(1, weight=1)

    avatar_canvas = tk.Canvas(
        header,
        width=132,
        height=132,
        bg=self.theme.SURFACE,
        bd=0,
        highlightthickness=0,
        relief=tk.FLAT,
        cursor="hand2",
    )
    avatar_canvas.grid(row=0, column=0, rowspan=4, sticky="nw", padx=(0, 16))

    ttk.Label(header, text="Назва компанії", style="Card.TLabel").grid(row=0, column=1, sticky="w")
    ttk.Entry(header, textvariable=company_name_var).grid(row=1, column=1, sticky="ew", pady=(6, 8))
    ttk.Label(header, text=f"Акаунт: {username}", style="CardSubtle.TLabel").grid(row=2, column=1, sticky="w", pady=(0, 2))

    avatar_actions = ttk.Frame(header, style="Card.TFrame")
    avatar_actions.grid(row=3, column=1, sticky="w", pady=(2, 0))
    self._motion_button(
        avatar_actions,
        text="Скинути фото",
        command=lambda: on_remove_avatar(),
        primary=False,
        width=140,
        height=38,
    ).pack(side=tk.LEFT)

    details_shell = RoundedMotionCard(
        parent,
        bg_color=self.theme.SURFACE,
        card_color=self.theme.SURFACE,
        shadow_color=self.theme.SHADOW_SOFT,
        radius=16,
        padding=4,
        shadow_offset=4,
        motion_enabled=True,
        height=128,
    )
    details_shell.pack(fill=tk.X)
    details_shell.pack_propagate(False)
    details = ttk.Frame(details_shell.content, style="Card.TFrame", padding=4)
    details.pack(fill=tk.BOTH, expand=True)
    details.grid_columnconfigure(0, weight=1)
    details.grid_columnconfigure(1, weight=1)
    details.grid_columnconfigure(2, weight=1)

    timezone_col = ttk.Frame(details, style="Card.TFrame")
    timezone_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    ttk.Label(timezone_col, text="Часовий пояс", style="Card.TLabel").pack(anchor="w", pady=(0, 4))
    timezone_box = ttk.Combobox(timezone_col, textvariable=timezone_var, values=timezone_options, state="readonly")
    timezone_box.pack(fill=tk.X)

    language_col = ttk.Frame(details, style="Card.TFrame")
    language_col.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
    ttk.Label(language_col, text="Мова", style="Card.TLabel").pack(anchor="w", pady=(0, 4))
    language_box = ttk.Combobox(
        language_col,
        textvariable=language_var,
        values=[language_label_by_code[code] for code, _ in LANGUAGE_OPTIONS],
        state="readonly",
    )
    language_box.pack(fill=tk.X)

    theme_col = ttk.Frame(details, style="Card.TFrame")
    theme_col.grid(row=0, column=2, sticky="nsew")
    ttk.Label(theme_col, text="Тема", style="Card.TLabel").pack(anchor="w", pady=(0, 4))
    theme_box = ttk.Combobox(
        theme_col,
        textvariable=theme_var,
        values=[theme_label_by_key[key] for key in ("ocean", "graphite", "sunrise", "aurora", "sand", "berry")],
        state="readonly",
    )
    theme_box.pack(fill=tk.X)

    def _resolve_preview_path() -> str | None:
        pending_source = avatar_state["pending_source_path"]
        if pending_source:
            return str(pending_source)
        if avatar_state["remove_current"]:
            return None
        current_logo_path = avatar_state["current_logo_path"]
        if not current_logo_path:
            return None
        return str(current_logo_path)

    def _draw_avatar() -> None:
        avatar_canvas.delete("all")
        center_x = 66
        center_y = 66
        size = 110
        image_path = _resolve_preview_path()
        photo = self._build_rounded_avatar_photo(image_path, size) if image_path else None
        avatar_state["image"] = photo

        if photo is None:
            draw_default_company_avatar(
                avatar_canvas,
                x=center_x,
                y=center_y,
                size=size,
                circle_fill=self.theme.AVATAR_CIRCLE_BG,
                building_fill=self.theme.AVATAR_BUILDING,
                window_fill=self.theme.AVATAR_WINDOW,
                outline=self.theme.AVATAR_CIRCLE_BORDER,
            )
        else:
            avatar_canvas.create_oval(
                center_x - size // 2 - 2,
                center_y - size // 2 - 2,
                center_x + size // 2 + 2,
                center_y + size // 2 + 2,
                fill=self.theme.AVATAR_CIRCLE_BG,
                outline=self.theme.AVATAR_CIRCLE_BORDER,
                width=2,
            )
            avatar_canvas.create_image(center_x, center_y, image=photo)

        if avatar_state["hover"]:
            avatar_canvas.create_oval(
                center_x - size // 2,
                center_y - size // 2,
                center_x + size // 2,
                center_y + size // 2,
                fill=self.theme.AVATAR_OVERLAY,
                outline="",
                stipple="gray50",
            )
            avatar_canvas.create_text(
                center_x,
                center_y,
                text="Змінити фото",
                fill=self.theme.TEXT_LIGHT,
                font=("Segoe UI", 10, "bold"),
            )

    def on_pick_avatar() -> None:
        selected = filedialog.askopenfilename(
            title="Оберіть фото профілю",
            filetypes=[
                ("Зображення", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"),
                ("Усі файли", "*.*"),
            ],
        )
        if not selected:
            return
        avatar_state["pending_source_path"] = selected
        avatar_state["remove_current"] = False
        _draw_avatar()

    def on_remove_avatar() -> None:
        avatar_state["pending_source_path"] = None
        avatar_state["remove_current"] = True
        _draw_avatar()

    def on_avatar_enter(_event=None) -> None:
        avatar_state["hover"] = True
        _draw_avatar()

    def on_avatar_leave(_event=None) -> None:
        avatar_state["hover"] = False
        _draw_avatar()

    avatar_canvas.bind("<Enter>", on_avatar_enter, add="+")
    avatar_canvas.bind("<Leave>", on_avatar_leave, add="+")
    avatar_canvas.bind("<Button-1>", lambda _e: on_pick_avatar(), add="+")

    _draw_avatar()

    def on_reset() -> None:
        company_name_var.set(company_name_default)
        timezone_var.set(timezone_default)
        language_var.set(
            language_label_by_code.get(
                language_default_code,
                language_label_by_code[DEFAULT_LANGUAGE_CODE],
            )
        )
        theme_var.set(theme_label_by_key.get(theme_default, theme_label_by_key["ocean"]))
        avatar_state["pending_source_path"] = None
        avatar_state["remove_current"] = False
        avatar_state["current_logo_path"] = logo_default
        _draw_avatar()

    def on_save_profile() -> None:
        selected_theme = theme_key_by_label.get(theme_var.get().strip(), UiTheme.DEFAULT_VARIANT)
        selected_language = language_code_by_label.get(language_var.get().strip(), DEFAULT_LANGUAGE_CODE)
        existing_logo_path = str(avatar_state["current_logo_path"]) if avatar_state["current_logo_path"] else None
        pending_source = str(avatar_state["pending_source_path"]) if avatar_state["pending_source_path"] else None
        remove_current = bool(avatar_state["remove_current"])
        new_logo_path: str | None = existing_logo_path
        update_logo = False
        generated_logo_path: str | None = None

        try:
            if pending_source:
                generated_logo_path = avatar_storage.save_company_avatar(
                    company_id=company_id,
                    source_path=pending_source,
                )
                new_logo_path = generated_logo_path
                update_logo = True
            elif remove_current:
                new_logo_path = None
                update_logo = True

            with session_scope() as session:
                controller = AuthController(session=session)
                controller.update_company_profile(
                    company_id=company_id,
                    company_name=company_name_var.get().strip(),
                    timezone=timezone_var.get().strip(),
                    theme=selected_theme,
                    language=selected_language,
                    logo_path=new_logo_path,
                    update_logo_path=update_logo,
                )
        except IntegrityError:
            if generated_logo_path:
                avatar_storage.delete_avatar(generated_logo_path)
            messagebox.showerror("Не вдалося зберегти", "Компанія з такою назвою вже існує.")
            return
        except Exception as exc:
            if generated_logo_path:
                avatar_storage.delete_avatar(generated_logo_path)
            messagebox.showerror("Не вдалося зберегти", str(exc))
            return

        if update_logo and existing_logo_path and existing_logo_path != new_logo_path:
            avatar_storage.delete_avatar(existing_logo_path)

        self._show_company_dashboard(initial_view="settings")

    controls = ttk.Frame(parent, style="Card.TFrame")
    controls.pack(fill=tk.X, pady=(10, 0))
    self._motion_button(
        controls,
        text="Зберегти зміни",
        command=on_save_profile,
        primary=True,
        width=200,
    ).pack(side=tk.LEFT)
    self._motion_button(
        controls,
        text="Скинути",
        command=on_reset,
        primary=False,
        width=140,
    ).pack(side=tk.LEFT, padx=(8, 0))
