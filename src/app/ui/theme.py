from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk


class UiTheme:
    PALETTES = {
        "ocean": {
            "APP_BG": "#edf2f7",
            "SURFACE": "#ffffff",
            "SURFACE_ALT": "#f5f8fc",
            "SIDEBAR_BG": "#17324a",
            "TEXT_PRIMARY": "#1f2937",
            "TEXT_MUTED": "#607084",
            "TEXT_LIGHT": "#f8fbff",
            "ACCENT": "#0f766e",
            "ACCENT_HOVER": "#115e59",
            "DANGER": "#be123c",
            "DANGER_HOVER": "#9f1239",
            "BORDER": "#d5deea",
        },
        "graphite": {
            "APP_BG": "#ecf1f5",
            "SURFACE": "#ffffff",
            "SURFACE_ALT": "#f3f6fa",
            "SIDEBAR_BG": "#253849",
            "TEXT_PRIMARY": "#1f2937",
            "TEXT_MUTED": "#5f7187",
            "TEXT_LIGHT": "#f8fbff",
            "ACCENT": "#2563eb",
            "ACCENT_HOVER": "#1d4ed8",
            "DANGER": "#be123c",
            "DANGER_HOVER": "#9f1239",
            "BORDER": "#cfd9e6",
        },
        "sunrise": {
            "APP_BG": "#f8f1e8",
            "SURFACE": "#fffdf9",
            "SURFACE_ALT": "#f6eee3",
            "SIDEBAR_BG": "#3f2f2c",
            "TEXT_PRIMARY": "#2c2623",
            "TEXT_MUTED": "#7b675d",
            "TEXT_LIGHT": "#fffaf5",
            "ACCENT": "#c65d3a",
            "ACCENT_HOVER": "#a84b2d",
            "DANGER": "#b02045",
            "DANGER_HOVER": "#901538",
            "BORDER": "#dfd1c4",
        },
    }
    DEFAULT_VARIANT = "ocean"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.current_variant = self.DEFAULT_VARIANT
        self.set_variant(self.DEFAULT_VARIANT)

    def set_variant(self, variant: str) -> str:
        chosen = variant if variant in self.PALETTES else self.DEFAULT_VARIANT
        self.current_variant = chosen
        palette = self.PALETTES[chosen]
        for key, value in palette.items():
            setattr(self, key, value)
        return chosen

    def _pick_font_family(self, candidates: tuple[str, ...]) -> str:
        available = set(tkfont.families(self.root))
        for candidate in candidates:
            if candidate in available:
                return candidate
        return "TkDefaultFont"

    def apply(self) -> None:
        self.root.configure(bg=self.APP_BG)

        heading_font = self._pick_font_family(("Bahnschrift", "Trebuchet MS", "Segoe UI"))
        body_font = self._pick_font_family(("Calibri", "Segoe UI", "Verdana"))

        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(".", font=(body_font, 10), foreground=self.TEXT_PRIMARY)
        style.configure("TFrame", background=self.APP_BG)
        style.configure("Card.TFrame", background=self.SURFACE)
        style.configure("Sidebar.TFrame", background=self.SIDEBAR_BG)
        style.configure("Shadow.TFrame", background="#d6dee8")

        style.configure(
            "TLabel",
            background=self.APP_BG,
            foreground=self.TEXT_PRIMARY,
        )
        style.configure(
            "Title.TLabel",
            background=self.APP_BG,
            foreground=self.TEXT_PRIMARY,
            font=(heading_font, 24, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=self.APP_BG,
            foreground=self.TEXT_MUTED,
            font=(body_font, 11),
        )
        style.configure(
            "SectionTitle.TLabel",
            background=self.APP_BG,
            foreground=self.TEXT_PRIMARY,
            font=(heading_font, 15, "bold"),
        )
        style.configure(
            "Card.TLabel",
            background=self.SURFACE,
            foreground=self.TEXT_PRIMARY,
        )
        style.configure(
            "CardTitle.TLabel",
            background=self.SURFACE,
            foreground=self.TEXT_PRIMARY,
            font=(heading_font, 14, "bold"),
        )
        style.configure(
            "CardSubtle.TLabel",
            background=self.SURFACE,
            foreground=self.TEXT_MUTED,
        )
        style.configure(
            "SidebarTitle.TLabel",
            background=self.SIDEBAR_BG,
            foreground=self.TEXT_LIGHT,
            font=(heading_font, 17, "bold"),
        )
        style.configure(
            "SidebarMeta.TLabel",
            background=self.SIDEBAR_BG,
            foreground="#c3d3e4",
            font=(body_font, 10),
        )

        style.configure(
            "Primary.TButton",
            font=(body_font, 10, "bold"),
            padding=(14, 9),
            background=self.ACCENT,
            foreground=self.TEXT_LIGHT,
            borderwidth=0,
            focusthickness=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.ACCENT_HOVER), ("pressed", self.ACCENT_HOVER)],
            foreground=[("disabled", "#cfe8e5")],
            padding=[("active", (14, 8)), ("!active", (14, 9))],
        )

        style.configure(
            "Secondary.TButton",
            font=(body_font, 10),
            padding=(12, 8),
            background=self.SURFACE_ALT,
            foreground=self.TEXT_PRIMARY,
            borderwidth=1,
            relief="solid",
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#e9f0f9"), ("pressed", "#e0e9f3")],
            bordercolor=[("focus", self.ACCENT)],
            padding=[("active", (12, 7)), ("!active", (12, 8))],
        )

        style.configure(
            "SidebarNav.TButton",
            font=(body_font, 10, "bold"),
            padding=(12, 10),
            background=self.SIDEBAR_BG,
            foreground="#e4eef8",
            anchor="w",
            borderwidth=0,
            focusthickness=0,
        )
        style.map(
            "SidebarNav.TButton",
            background=[("active", "#244966"), ("pressed", "#1e415c")],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")],
            padding=[("active", (12, 9)), ("!active", (12, 10))],
        )
        style.configure(
            "SidebarDanger.TButton",
            font=(body_font, 10, "bold"),
            padding=(12, 10),
            background=self.DANGER,
            foreground=self.TEXT_LIGHT,
            anchor="center",
            borderwidth=0,
            focusthickness=0,
        )
        style.map(
            "SidebarDanger.TButton",
            background=[("active", self.DANGER_HOVER), ("pressed", self.DANGER_HOVER)],
            padding=[("active", (12, 9)), ("!active", (12, 10))],
        )

        style.configure(
            "TEntry",
            fieldbackground=self.SURFACE,
            background=self.SURFACE,
            bordercolor=self.BORDER,
            lightcolor=self.BORDER,
            darkcolor=self.BORDER,
            padding=7,
        )
        style.map("TEntry", bordercolor=[("focus", self.ACCENT)])

        style.configure(
            "TCombobox",
            fieldbackground=self.SURFACE,
            background=self.SURFACE,
            bordercolor=self.BORDER,
            lightcolor=self.BORDER,
            darkcolor=self.BORDER,
            padding=6,
        )
        style.map("TCombobox", bordercolor=[("focus", self.ACCENT)])

        style.configure(
            "TLabelframe",
            background=self.APP_BG,
            bordercolor=self.BORDER,
            relief="solid",
            borderwidth=1,
            padding=8,
        )
        style.configure(
            "TLabelframe.Label",
            background=self.APP_BG,
            foreground=self.TEXT_PRIMARY,
            font=(body_font, 10, "bold"),
        )

        style.configure(
            "Treeview",
            rowheight=32,
            background=self.SURFACE,
            fieldbackground=self.SURFACE,
            bordercolor=self.BORDER,
            relief="solid",
        )
        style.configure(
            "Treeview.Heading",
            background="#dde7f2",
            foreground=self.TEXT_PRIMARY,
            bordercolor=self.BORDER,
            font=(body_font, 10, "bold"),
            padding=(6, 8),
        )

        style.configure(
            "App.Vertical.TScrollbar",
            background="#c8d4e4",
            troughcolor="#eef3f9",
            bordercolor="#d3deeb",
            darkcolor="#c8d4e4",
            lightcolor="#c8d4e4",
            arrowcolor="#5e6f84",
            relief="flat",
            borderwidth=0,
            arrowsize=14,
            width=12,
        )
        style.map(
            "App.Vertical.TScrollbar",
            background=[("active", "#a8bacf"), ("pressed", "#8fa5bf")],
            arrowcolor=[("active", "#203d5a"), ("pressed", "#203d5a")],
        )

    def style_listbox(self, box: tk.Listbox) -> None:
        box.configure(
            bg=self.SURFACE,
            fg=self.TEXT_PRIMARY,
            selectbackground="#d5e7fb",
            selectforeground=self.TEXT_PRIMARY,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            borderwidth=0,
            relief=tk.FLAT,
        )
