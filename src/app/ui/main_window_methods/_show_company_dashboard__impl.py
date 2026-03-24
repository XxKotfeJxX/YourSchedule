def _show_company_dashboard__impl(self, initial_view: str = "schedule") -> None:
    user = self.current_user
    if user is None:
        self._show_login_screen()
        return

    self._apply_company_theme(user.company_id)
    self._clear_root()

    root_frame = ttk.Frame(self.root)
    root_frame.pack(fill=tk.BOTH, expand=True)

    sidebar = ttk.Frame(root_frame, style="Sidebar.TFrame", padding=16, width=260)
    sidebar.pack(side=tk.LEFT, fill=tk.Y)
    sidebar.pack_propagate(False)

    content = ttk.Frame(root_frame, padding=20)
    content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    hero = tk.Canvas(
        content,
        height=88,
        bg=self.theme.SURFACE,
        highlightthickness=0,
        relief=tk.FLAT,
    )
    hero.pack(fill=tk.X, pady=(0, 12))
    hero.create_oval(-60, -120, 220, 120, fill=self.theme.HERO_BLOB_1, outline="")
    hero.create_oval(200, -60, 520, 180, fill=self.theme.HERO_BLOB_2, outline="")
    hero.create_oval(500, -100, 900, 180, fill=self.theme.HERO_BLOB_3, outline="")
    hero.create_text(
        22,
        18,
        text="Компанійний простір",
        fill=self.theme.HERO_TITLE,
        anchor="nw",
        font=("Segoe UI", 16, "bold"),
    )
    hero.create_text(
        22,
        48,
        text="Керуйте групами, підгрупами та розкладом в одному місці.",
        fill=self.theme.HERO_SUBTITLE,
        anchor="nw",
        font=("Segoe UI", 10),
    )

    content_card_shell = RoundedMotionCard(
        content,
        bg_color=self.theme.APP_BG,
        card_color=self.theme.SURFACE,
        shadow_color=self.theme.SHADOW_SOFT,
        radius=18,
        padding=4,
        shadow_offset=5,
        motion_enabled=True,
    )
    content_card_shell.pack(fill=tk.BOTH, expand=True)
    views_container = ttk.Frame(content_card_shell.content, style="Card.TFrame", padding=14)
    views_container.pack(fill=tk.BOTH, expand=True)

    with session_scope() as session:
        company = AuthController(session=session).get_company(user.company_id)
    company_name = company.name if company else f"Компанія #{user.company_id}"

    ttk.Label(sidebar, text="Розклад", style="SidebarTitle.TLabel").pack(anchor="w", pady=(0, 4))
    ttk.Label(sidebar, text=company_name, style="SidebarMeta.TLabel").pack(anchor="w", pady=(0, 16))

    views: dict[str, ttk.Frame] = {}
    for key in ("schedule", "groups", "rooms", "curriculum", "settings"):
        frame = ttk.Frame(views_container, style="Card.TFrame", padding=18)
        views[key] = frame

    nav_buttons: dict[str, RoundedMotionButton] = {}

    def _set_nav_button_active(button: RoundedMotionButton, *, active: bool) -> None:
        if active:
            button.fill = self.theme.ACCENT
            button.hover_fill = self.theme.ACCENT_HOVER
            button.pressed_fill = self.theme.ACCENT_PRESSED
            button.text_color = self.theme.TEXT_LIGHT
            button.shadow_color = self.theme.SIDEBAR_BUTTON_SHADOW
        else:
            button.fill = self.theme.SIDEBAR_BUTTON_FILL
            button.hover_fill = self.theme.SIDEBAR_BUTTON_HOVER
            button.pressed_fill = self.theme.SIDEBAR_BUTTON_PRESSED
            button.text_color = self.theme.SIDEBAR_BUTTON_TEXT
            button.shadow_color = self.theme.SIDEBAR_BUTTON_SHADOW
        button._state = "normal"
        button._lift = 0
        button._draw()

    def _refresh_nav_buttons(active_name: str) -> None:
        for key, button in nav_buttons.items():
            _set_nav_button_active(button, active=(key == active_name))

    def open_view(name: str) -> None:
        for frame in views.values():
            frame.pack_forget()
        views[name].pack(fill=tk.BOTH, expand=True)
        _refresh_nav_buttons(name)

    def _add_nav_button(*, key: str, label: str) -> None:
        button = self._motion_button(
            sidebar,
            text=label,
            command=lambda tab=key: open_view(tab),
            primary=True,
            width=224,
            height=44,
            canvas_bg=self.theme.SIDEBAR_BG,
            fill=self.theme.SIDEBAR_BUTTON_FILL,
            hover_fill=self.theme.SIDEBAR_BUTTON_HOVER,
            pressed_fill=self.theme.SIDEBAR_BUTTON_PRESSED,
            text_color=self.theme.SIDEBAR_BUTTON_TEXT,
            shadow_color=self.theme.SIDEBAR_BUTTON_SHADOW,
        )
        button.pack(pady=(0, 6), anchor="w")
        nav_buttons[key] = button

    _add_nav_button(key="schedule", label="Розклад")
    _add_nav_button(key="groups", label="Групи")
    _add_nav_button(key="rooms", label="Приміщення")
    _add_nav_button(key="curriculum", label="Навчальні плани")
    _add_nav_button(key="settings", label="Налаштування")

    ttk.Frame(sidebar, style="Sidebar.TFrame").pack(fill=tk.BOTH, expand=True)
    self._motion_button(
        sidebar,
        text="Вийти",
        command=self._logout,
        primary=True,
        width=224,
        height=44,
        canvas_bg=self.theme.SIDEBAR_BG,
        fill=self.theme.DANGER,
        hover_fill=self.theme.DANGER_HOVER,
        pressed_fill=self.theme.DANGER_HOVER,
        text_color=self.theme.TEXT_LIGHT,
        shadow_color=self.theme.SIDEBAR_BUTTON_SHADOW,
    ).pack(anchor="w")

    self._build_company_schedule_view(views["schedule"], user.company_id)
    self._build_company_groups_view(views["groups"], user.company_id)
    self._build_company_rooms_view(views["rooms"], user.company_id)
    self._build_company_curriculum_view(views["curriculum"], user.company_id)
    self._build_company_settings_view(views["settings"], user.company_id, user.username)

    selected_view = initial_view if initial_view in views else "schedule"
    open_view(selected_view)
