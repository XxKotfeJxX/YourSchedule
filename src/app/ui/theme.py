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
            "ACCENT_PRESSED": "#0d5f58",
            "DANGER": "#be123c",
            "DANGER_HOVER": "#9f1239",
            "BORDER": "#d5deea",
            "SHADOW_SOFT": "#d6dee8",
            "SECONDARY_HOVER": "#e9f0f9",
            "SECONDARY_PRESSED": "#e0e9f3",
            "SIDEBAR_META": "#c3d3e4",
            "SIDEBAR_BUTTON_FILL": "#1f4563",
            "SIDEBAR_BUTTON_HOVER": "#295676",
            "SIDEBAR_BUTTON_PRESSED": "#173b56",
            "SIDEBAR_BUTTON_TEXT": "#edf5ff",
            "SIDEBAR_BUTTON_SHADOW": "#11263a",
            "TREE_HEADING_BG": "#dde7f2",
            "SCROLLBAR_BG": "#c8d4e4",
            "SCROLLBAR_BG_ACTIVE": "#a8bacf",
            "SCROLLBAR_BG_PRESSED": "#8fa5bf",
            "SCROLLBAR_TROUGH": "#eef3f9",
            "SCROLLBAR_BORDER": "#d3deeb",
            "SCROLLBAR_ARROW": "#5e6f84",
            "SCROLLBAR_ARROW_ACTIVE": "#203d5a",
            "LISTBOX_SELECTED_BG": "#d5e7fb",
            "HERO_BLOB_1": "#d7f2ee",
            "HERO_BLOB_2": "#dfeaf8",
            "HERO_BLOB_3": "#e9e2fb",
            "HERO_TITLE": "#1f2937",
            "HERO_SUBTITLE": "#57657a",
            "AVATAR_CIRCLE_BG": "#e6eef8",
            "AVATAR_CIRCLE_BORDER": "#bfd0e5",
            "AVATAR_BUILDING": "#4e6b8a",
            "AVATAR_WINDOW": "#eaf3ff",
            "AVATAR_OVERLAY": "#10243a",
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
            "ACCENT_PRESSED": "#1e40af",
            "DANGER": "#be123c",
            "DANGER_HOVER": "#9f1239",
            "BORDER": "#cfd9e6",
            "SHADOW_SOFT": "#cfd8e3",
            "SECONDARY_HOVER": "#e5edf7",
            "SECONDARY_PRESSED": "#dbe5f2",
            "SIDEBAR_META": "#bed1e4",
            "SIDEBAR_BUTTON_FILL": "#2b445a",
            "SIDEBAR_BUTTON_HOVER": "#33516d",
            "SIDEBAR_BUTTON_PRESSED": "#263f54",
            "SIDEBAR_BUTTON_TEXT": "#edf5ff",
            "SIDEBAR_BUTTON_SHADOW": "#182838",
            "TREE_HEADING_BG": "#dae6f3",
            "SCROLLBAR_BG": "#c5d3e2",
            "SCROLLBAR_BG_ACTIVE": "#a7bbd0",
            "SCROLLBAR_BG_PRESSED": "#90a7c0",
            "SCROLLBAR_TROUGH": "#ebf1f8",
            "SCROLLBAR_BORDER": "#d1dceb",
            "SCROLLBAR_ARROW": "#54697f",
            "SCROLLBAR_ARROW_ACTIVE": "#1c3852",
            "LISTBOX_SELECTED_BG": "#d4e3fb",
            "HERO_BLOB_1": "#dfe9f5",
            "HERO_BLOB_2": "#dde6f7",
            "HERO_BLOB_3": "#e7e5f7",
            "HERO_TITLE": "#1d2d3a",
            "HERO_SUBTITLE": "#506175",
            "AVATAR_CIRCLE_BG": "#e4ecf5",
            "AVATAR_CIRCLE_BORDER": "#becddf",
            "AVATAR_BUILDING": "#4a6278",
            "AVATAR_WINDOW": "#eef5ff",
            "AVATAR_OVERLAY": "#182634",
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
            "ACCENT_PRESSED": "#923f25",
            "DANGER": "#b02045",
            "DANGER_HOVER": "#901538",
            "BORDER": "#dfd1c4",
            "SHADOW_SOFT": "#d9cabd",
            "SECONDARY_HOVER": "#f1e5d8",
            "SECONDARY_PRESSED": "#e8d9ca",
            "SIDEBAR_META": "#e8d7cd",
            "SIDEBAR_BUTTON_FILL": "#5c433d",
            "SIDEBAR_BUTTON_HOVER": "#704f47",
            "SIDEBAR_BUTTON_PRESSED": "#4e3833",
            "SIDEBAR_BUTTON_TEXT": "#fff4ea",
            "SIDEBAR_BUTTON_SHADOW": "#2a1d1a",
            "TREE_HEADING_BG": "#f0e2d4",
            "SCROLLBAR_BG": "#d8c5b2",
            "SCROLLBAR_BG_ACTIVE": "#c7ad94",
            "SCROLLBAR_BG_PRESSED": "#b89778",
            "SCROLLBAR_TROUGH": "#f2e8de",
            "SCROLLBAR_BORDER": "#decfbe",
            "SCROLLBAR_ARROW": "#745d49",
            "SCROLLBAR_ARROW_ACTIVE": "#4a352a",
            "LISTBOX_SELECTED_BG": "#f1dcc8",
            "HERO_BLOB_1": "#f8dbc9",
            "HERO_BLOB_2": "#f2e0cc",
            "HERO_BLOB_3": "#f0d8df",
            "HERO_TITLE": "#402d28",
            "HERO_SUBTITLE": "#755e54",
            "AVATAR_CIRCLE_BG": "#f1e1d3",
            "AVATAR_CIRCLE_BORDER": "#dfc7b3",
            "AVATAR_BUILDING": "#8d5f4f",
            "AVATAR_WINDOW": "#fff4ea",
            "AVATAR_OVERLAY": "#402b24",
        },
        "aurora": {
            "APP_BG": "#eef8f5",
            "SURFACE": "#ffffff",
            "SURFACE_ALT": "#f1faf7",
            "SIDEBAR_BG": "#153c3a",
            "TEXT_PRIMARY": "#183133",
            "TEXT_MUTED": "#547274",
            "TEXT_LIGHT": "#f5fffd",
            "ACCENT": "#0ea5a2",
            "ACCENT_HOVER": "#0b8f8d",
            "ACCENT_PRESSED": "#0a7877",
            "DANGER": "#be123c",
            "DANGER_HOVER": "#9f1239",
            "BORDER": "#cbe1df",
            "SHADOW_SOFT": "#cde1e0",
            "SECONDARY_HOVER": "#e6f5f2",
            "SECONDARY_PRESSED": "#dceeea",
            "SIDEBAR_META": "#b5ddd8",
            "SIDEBAR_BUTTON_FILL": "#1e5450",
            "SIDEBAR_BUTTON_HOVER": "#266560",
            "SIDEBAR_BUTTON_PRESSED": "#184a46",
            "SIDEBAR_BUTTON_TEXT": "#ebfffb",
            "SIDEBAR_BUTTON_SHADOW": "#0f2928",
            "TREE_HEADING_BG": "#d8efec",
            "SCROLLBAR_BG": "#b8d9d7",
            "SCROLLBAR_BG_ACTIVE": "#9fc7c4",
            "SCROLLBAR_BG_PRESSED": "#88b4b1",
            "SCROLLBAR_TROUGH": "#e8f5f4",
            "SCROLLBAR_BORDER": "#c6e0de",
            "SCROLLBAR_ARROW": "#477170",
            "SCROLLBAR_ARROW_ACTIVE": "#1f4544",
            "LISTBOX_SELECTED_BG": "#caece8",
            "HERO_BLOB_1": "#cff5ec",
            "HERO_BLOB_2": "#d6f2f8",
            "HERO_BLOB_3": "#e0e9fb",
            "HERO_TITLE": "#183133",
            "HERO_SUBTITLE": "#4f696c",
            "AVATAR_CIRCLE_BG": "#d9efec",
            "AVATAR_CIRCLE_BORDER": "#b9ddd8",
            "AVATAR_BUILDING": "#3f6f6b",
            "AVATAR_WINDOW": "#f0fffd",
            "AVATAR_OVERLAY": "#123231",
        },
        "sand": {
            "APP_BG": "#f7f3ea",
            "SURFACE": "#fffefb",
            "SURFACE_ALT": "#f5f0e6",
            "SIDEBAR_BG": "#5c4731",
            "TEXT_PRIMARY": "#342a22",
            "TEXT_MUTED": "#736354",
            "TEXT_LIGHT": "#fffaf1",
            "ACCENT": "#b9822f",
            "ACCENT_HOVER": "#9f6f24",
            "ACCENT_PRESSED": "#875d1e",
            "DANGER": "#b02045",
            "DANGER_HOVER": "#901538",
            "BORDER": "#dfd4c4",
            "SHADOW_SOFT": "#d8cfbf",
            "SECONDARY_HOVER": "#efe7da",
            "SECONDARY_PRESSED": "#e5dccd",
            "SIDEBAR_META": "#e5d7c3",
            "SIDEBAR_BUTTON_FILL": "#765a3d",
            "SIDEBAR_BUTTON_HOVER": "#8a6b48",
            "SIDEBAR_BUTTON_PRESSED": "#684f36",
            "SIDEBAR_BUTTON_TEXT": "#fff6ea",
            "SIDEBAR_BUTTON_SHADOW": "#3b2b1e",
            "TREE_HEADING_BG": "#efe2cf",
            "SCROLLBAR_BG": "#d7c5ac",
            "SCROLLBAR_BG_ACTIVE": "#c6ad8f",
            "SCROLLBAR_BG_PRESSED": "#b49573",
            "SCROLLBAR_TROUGH": "#f2eadf",
            "SCROLLBAR_BORDER": "#deceba",
            "SCROLLBAR_ARROW": "#6f5a44",
            "SCROLLBAR_ARROW_ACTIVE": "#443324",
            "LISTBOX_SELECTED_BG": "#efdfc7",
            "HERO_BLOB_1": "#f4dfc2",
            "HERO_BLOB_2": "#efe4cf",
            "HERO_BLOB_3": "#ebdde4",
            "HERO_TITLE": "#3f3024",
            "HERO_SUBTITLE": "#715f4f",
            "AVATAR_CIRCLE_BG": "#efdfc7",
            "AVATAR_CIRCLE_BORDER": "#dcc7a8",
            "AVATAR_BUILDING": "#826246",
            "AVATAR_WINDOW": "#fff7ec",
            "AVATAR_OVERLAY": "#3d2d20",
        },
        "berry": {
            "APP_BG": "#f3edf7",
            "SURFACE": "#ffffff",
            "SURFACE_ALT": "#f5effa",
            "SIDEBAR_BG": "#3b264d",
            "TEXT_PRIMARY": "#271f30",
            "TEXT_MUTED": "#6c5f79",
            "TEXT_LIGHT": "#fbf7ff",
            "ACCENT": "#a33bd1",
            "ACCENT_HOVER": "#8a2db3",
            "ACCENT_PRESSED": "#742694",
            "DANGER": "#be123c",
            "DANGER_HOVER": "#9f1239",
            "BORDER": "#dbcfe6",
            "SHADOW_SOFT": "#d7cde2",
            "SECONDARY_HOVER": "#eee6f6",
            "SECONDARY_PRESSED": "#e5dbef",
            "SIDEBAR_META": "#d8c9e5",
            "SIDEBAR_BUTTON_FILL": "#53356c",
            "SIDEBAR_BUTTON_HOVER": "#644083",
            "SIDEBAR_BUTTON_PRESSED": "#4a305f",
            "SIDEBAR_BUTTON_TEXT": "#f6f0ff",
            "SIDEBAR_BUTTON_SHADOW": "#2a1a37",
            "TREE_HEADING_BG": "#ebdff6",
            "SCROLLBAR_BG": "#ceb8de",
            "SCROLLBAR_BG_ACTIVE": "#bc9ed2",
            "SCROLLBAR_BG_PRESSED": "#aa87c4",
            "SCROLLBAR_TROUGH": "#f1e9f8",
            "SCROLLBAR_BORDER": "#ddcee9",
            "SCROLLBAR_ARROW": "#6b527d",
            "SCROLLBAR_ARROW_ACTIVE": "#452d59",
            "LISTBOX_SELECTED_BG": "#e2d0f2",
            "HERO_BLOB_1": "#ead7f8",
            "HERO_BLOB_2": "#dde4fa",
            "HERO_BLOB_3": "#f2d8ea",
            "HERO_TITLE": "#2b2135",
            "HERO_SUBTITLE": "#675979",
            "AVATAR_CIRCLE_BG": "#e8dcf4",
            "AVATAR_CIRCLE_BORDER": "#d2bfe4",
            "AVATAR_BUILDING": "#6f4d8c",
            "AVATAR_WINDOW": "#f8f1ff",
            "AVATAR_OVERLAY": "#2d1d3a",
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
        style.configure("Shadow.TFrame", background=self.SHADOW_SOFT)

        style.configure("TLabel", background=self.APP_BG, foreground=self.TEXT_PRIMARY)
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
        style.configure("Card.TLabel", background=self.SURFACE, foreground=self.TEXT_PRIMARY)
        style.configure(
            "CardTitle.TLabel",
            background=self.SURFACE,
            foreground=self.TEXT_PRIMARY,
            font=(heading_font, 14, "bold"),
        )
        style.configure("CardSubtle.TLabel", background=self.SURFACE, foreground=self.TEXT_MUTED)
        style.configure("CardAlt.TLabel", background=self.SURFACE_ALT, foreground=self.TEXT_PRIMARY)
        style.configure(
            "CardAltTitle.TLabel",
            background=self.SURFACE_ALT,
            foreground=self.TEXT_PRIMARY,
            font=(heading_font, 14, "bold"),
        )
        style.configure("CardAltSubtle.TLabel", background=self.SURFACE_ALT, foreground=self.TEXT_MUTED)
        style.configure(
            "SidebarTitle.TLabel",
            background=self.SIDEBAR_BG,
            foreground=self.TEXT_LIGHT,
            font=(heading_font, 17, "bold"),
        )
        style.configure(
            "SidebarMeta.TLabel",
            background=self.SIDEBAR_BG,
            foreground=self.SIDEBAR_META,
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
            background=[("active", self.ACCENT_HOVER), ("pressed", self.ACCENT_PRESSED)],
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
            background=[("active", self.SECONDARY_HOVER), ("pressed", self.SECONDARY_PRESSED)],
            bordercolor=[("focus", self.ACCENT)],
            padding=[("active", (12, 7)), ("!active", (12, 8))],
        )

        style.configure(
            "SidebarNav.TButton",
            font=(body_font, 10, "bold"),
            padding=(12, 10),
            background=self.SIDEBAR_BG,
            foreground=self.SIDEBAR_BUTTON_TEXT,
            anchor="w",
            borderwidth=0,
            focusthickness=0,
        )
        style.map(
            "SidebarNav.TButton",
            background=[("active", self.SIDEBAR_BUTTON_HOVER), ("pressed", self.SIDEBAR_BUTTON_PRESSED)],
            foreground=[("active", self.SIDEBAR_BUTTON_TEXT), ("pressed", self.SIDEBAR_BUTTON_TEXT)],
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
            "PopupFilter.TCombobox",
            fieldbackground=self.SURFACE,
            background=self.SURFACE,
            foreground=self.TEXT_PRIMARY,
            bordercolor=self.BORDER,
            lightcolor=self.BORDER,
            darkcolor=self.BORDER,
            padding=5,
            arrowsize=12,
        )
        style.map(
            "PopupFilter.TCombobox",
            bordercolor=[("focus", self.ACCENT), ("readonly", self.BORDER)],
            fieldbackground=[("readonly", self.SURFACE), ("disabled", self.SURFACE_ALT)],
            foreground=[("readonly", self.TEXT_PRIMARY), ("disabled", self.TEXT_MUTED)],
            background=[("readonly", self.SURFACE), ("disabled", self.SURFACE_ALT)],
        )

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
            "FlatTabs.TNotebook",
            background=self.SURFACE,
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        style.configure(
            "FlatTabs.TNotebook.Tab",
            background=self.SURFACE_ALT,
            foreground=self.TEXT_PRIMARY,
            padding=(12, 8),
            borderwidth=0,
            lightcolor=self.BORDER,
            darkcolor=self.BORDER,
        )
        style.map(
            "FlatTabs.TNotebook.Tab",
            background=[
                ("selected", self.ACCENT),
                ("active", self.SECONDARY_HOVER),
            ],
            foreground=[
                ("selected", self.TEXT_LIGHT),
                ("active", self.TEXT_PRIMARY),
            ],
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
            background=self.TREE_HEADING_BG,
            foreground=self.TEXT_PRIMARY,
            bordercolor=self.BORDER,
            font=(body_font, 10, "bold"),
            padding=(6, 8),
        )

        try:
            style.layout(
                "App.Vertical.TScrollbar",
                [
                    (
                        "Vertical.Scrollbar.trough",
                        {
                            "sticky": "ns",
                            "children": [
                                ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"}),
                            ],
                        },
                    )
                ],
            )
        except tk.TclError:
            # Fallback for themes that do not expose layout elements.
            pass
        style.configure(
            "App.Vertical.TScrollbar",
            background=self.SCROLLBAR_BG,
            troughcolor=self.SCROLLBAR_TROUGH,
            bordercolor=self.SCROLLBAR_BORDER,
            darkcolor=self.SCROLLBAR_BG,
            lightcolor=self.SCROLLBAR_BG,
            arrowcolor=self.SCROLLBAR_ARROW,
            relief="solid",
            borderwidth=1,
            arrowsize=8,
            width=14,
            gripcount=0,
        )
        style.map(
            "App.Vertical.TScrollbar",
            background=[("active", self.SCROLLBAR_BG_ACTIVE), ("pressed", self.SCROLLBAR_BG_PRESSED)],
            arrowcolor=[("active", self.SCROLLBAR_ARROW_ACTIVE), ("pressed", self.SCROLLBAR_ARROW_ACTIVE)],
        )

    def style_listbox(self, box: tk.Listbox) -> None:
        box.configure(
            bg=self.SURFACE,
            fg=self.TEXT_PRIMARY,
            selectbackground=self.LISTBOX_SELECTED_BG,
            selectforeground=self.TEXT_PRIMARY,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            borderwidth=0,
            relief=tk.FLAT,
        )
