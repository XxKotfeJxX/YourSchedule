# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.main_window import *  # noqa: F401,F403

def _build_company_settings_view__impl(self, parent: ttk.Frame, company_id: int, username: str) -> None:
    settings_shell = ttk.Frame(parent, style="Card.TFrame")
    settings_shell.pack(fill=tk.BOTH, expand=True)

    settings_canvas = tk.Canvas(
        settings_shell,
        bg=self.theme.SURFACE,
        bd=0,
        highlightthickness=0,
        relief=tk.FLAT,
    )
    settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    settings_scroll = ttk.Scrollbar(
        settings_shell,
        orient=tk.VERTICAL,
        command=settings_canvas.yview,
        style="App.Vertical.TScrollbar",
    )
    settings_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    settings_canvas.configure(yscrollcommand=settings_scroll.set)

    body = ttk.Frame(settings_canvas, style="Card.TFrame")
    body_window = settings_canvas.create_window((0, 0), anchor="nw", window=body)

    def _sync_settings_scroll(_event=None) -> None:
        viewport_width = max(1, settings_canvas.winfo_width())
        viewport_height = max(1, settings_canvas.winfo_height())
        requested_height = max(1, body.winfo_reqheight())
        settings_canvas.itemconfigure(
            body_window,
            width=viewport_width,
            height=max(viewport_height, requested_height),
        )
        bbox = settings_canvas.bbox("all")
        if bbox is not None:
            settings_canvas.configure(scrollregion=bbox)

    def _scroll_settings(step_units: int) -> str:
        self._dismiss_combobox_popdowns(body)
        first, last = settings_canvas.yview()
        visible = float(last) - float(first)
        if visible >= 0.999:
            return "break"
        if step_units < 0 and float(first) <= 0.0001:
            return "break"
        if step_units > 0 and float(last) >= 0.9999:
            return "break"
        settings_canvas.yview_scroll(step_units, "units")
        return "break"

    body.bind("<Configure>", _sync_settings_scroll)
    settings_canvas.bind("<Configure>", _sync_settings_scroll)

    def _on_settings_wheel(event: tk.Event) -> str:
        delta = getattr(event, "delta", 0)
        if not delta:
            return "break"
        direction = -1 if delta > 0 else 1
        steps = max(1, int(abs(delta) / 120))
        for _ in range(steps):
            _scroll_settings(direction)
        return "break"

    def _on_settings_up(_event: tk.Event) -> str:
        return _scroll_settings(-1)

    def _on_settings_down(_event: tk.Event) -> str:
        return _scroll_settings(1)

    for widget in (settings_canvas, body):
        widget.bind("<MouseWheel>", _on_settings_wheel, add="+")
        widget.bind("<Button-4>", _on_settings_up, add="+")
        widget.bind("<Button-5>", _on_settings_down, add="+")

    tabs_bar = ttk.Frame(body, style="Card.TFrame")
    tabs_bar.pack(fill=tk.X, pady=(0, 8))

    content = ttk.Frame(body, style="Card.TFrame")
    content.pack(fill=tk.BOTH, expand=True)

    views: dict[str, ttk.Frame] = {
        "profile": ttk.Frame(content, style="Card.TFrame"),
        "templates": ttk.Frame(content, style="Card.TFrame"),
        "system": ttk.Frame(content, style="Card.TFrame"),
    }
    nav_buttons: dict[str, RoundedMotionButton] = {}

    def _set_nav_button_state(button: RoundedMotionButton, *, active: bool) -> None:
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
        button._draw()

    def open_tab(name: str) -> None:
        for frame in views.values():
            frame.pack_forget()
        views[name].pack(fill=tk.BOTH, expand=True)
        for key, button in nav_buttons.items():
            _set_nav_button_state(button, active=key == name)

    tab_specs = (
        ("profile", "Профіль"),
        ("templates", "Шаблони"),
        ("system", "Система"),
    )
    for key, label in tab_specs:
        button = self._motion_button(
            tabs_bar,
            text=label,
            command=lambda selected=key: open_tab(selected),
            primary=False,
            width=150,
            height=40,
        )
        button.pack(side=tk.LEFT, padx=(0, 8))
        nav_buttons[key] = button

    self._build_company_settings_profile_tab(
        views["profile"],
        company_id=company_id,
        username=username,
    )
    self._build_company_settings_templates_tab(views["templates"], company_id=company_id)
    self._build_company_settings_system_tab(views["system"], company_id=company_id, username=username)

    open_tab("profile")
