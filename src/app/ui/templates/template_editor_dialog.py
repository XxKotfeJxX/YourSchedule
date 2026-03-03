from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from app.ui.fx_widgets import RoundedMotionCard


MotionButtonFactory = Callable[..., object]
SubmitHandler = Callable[[], bool | None]
ActionHandler = Callable[[], None]


class TemplateEditorDialog:
    def __init__(
        self,
        *,
        parent: tk.Widget,
        theme,
        motion_button_factory: MotionButtonFactory,
        mode: str,
        template_level: str,
        template_id: int | None = None,
        title: str,
        on_submit: SubmitHandler | None = None,
        on_duplicate: ActionHandler | None = None,
        on_archive_delete: ActionHandler | None = None,
    ) -> None:
        self.parent = parent
        self.theme = theme
        self.motion_button_factory = motion_button_factory
        self.mode = mode
        self.template_level = template_level
        self.template_id = template_id
        self._on_submit = on_submit
        self._on_duplicate = on_duplicate
        self._on_archive_delete = on_archive_delete

        self.window = tk.Toplevel(parent.winfo_toplevel())
        self.window.title(title)
        self.window.geometry("980x640")
        self.window.minsize(900, 580)
        self.window.transient(parent.winfo_toplevel())
        self.window.grab_set()
        self.window.configure(bg=self.theme.APP_BG)
        self.window.protocol("WM_DELETE_WINDOW", self._close)

        root = ttk.Frame(self.window, style="Card.TFrame", padding=16)
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root, style="Card.TFrame")
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text=title, style="CardTitle.TLabel").pack(side=tk.LEFT)
        badge = tk.Label(
            header,
            text=self._build_badge_text(),
            bg=self.theme.SECONDARY_HOVER,
            fg=self.theme.ACCENT,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            bd=0,
        )
        badge.pack(side=tk.LEFT, padx=(10, 0))

        body = ttk.Frame(root, style="Card.TFrame")
        body.pack(fill=tk.BOTH, expand=True)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left_shell = RoundedMotionCard(
            body,
            bg_color=self.theme.SURFACE,
            card_color=self.theme.SURFACE,
            shadow_color=self.theme.SHADOW_SOFT,
            radius=16,
            padding=4,
            shadow_offset=4,
            motion_enabled=True,
        )
        left_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.fields_frame = ttk.Frame(left_shell.content, style="Card.TFrame", padding=8)
        self.fields_frame.pack(fill=tk.BOTH, expand=True)

        right_shell = RoundedMotionCard(
            body,
            bg_color=self.theme.SURFACE,
            card_color=self.theme.SURFACE,
            shadow_color=self.theme.SHADOW_SOFT,
            radius=16,
            padding=4,
            shadow_offset=4,
            motion_enabled=True,
        )
        right_shell.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.editor_frame = ttk.Frame(right_shell.content, style="Card.TFrame", padding=8)
        self.editor_frame.pack(fill=tk.BOTH, expand=True)

        footer = ttk.Frame(root, style="Card.TFrame")
        footer.pack(fill=tk.X, pady=(10, 0))

        self.motion_button_factory(
            footer,
            text="Скасувати",
            command=self._close,
            primary=False,
            width=130,
            height=40,
        ).pack(side=tk.RIGHT)

        if self.mode == "edit":
            self.motion_button_factory(
                footer,
                text="Архівувати/Видалити",
                command=self._archive_delete,
                primary=False,
                width=170,
                height=40,
                fill=self.theme.DANGER,
                hover_fill=self.theme.DANGER_HOVER,
                pressed_fill=self.theme.DANGER_HOVER,
                text_color=self.theme.TEXT_LIGHT,
            ).pack(side=tk.LEFT)
            self.motion_button_factory(
                footer,
                text="Дублювати",
                command=self._duplicate,
                primary=False,
                width=130,
                height=40,
            ).pack(side=tk.LEFT, padx=(8, 0))

        primary_label = "Створити" if self.mode == "create" else "Зберегти"
        self.motion_button_factory(
            footer,
            text=primary_label,
            command=self._submit,
            primary=True,
            width=130,
            height=40,
        ).pack(side=tk.RIGHT, padx=(0, 8))

    def show_modal(self) -> None:
        self.window.wait_window()

    def set_submit_handler(self, handler: SubmitHandler) -> None:
        self._on_submit = handler

    def set_duplicate_handler(self, handler: ActionHandler) -> None:
        self._on_duplicate = handler

    def set_archive_delete_handler(self, handler: ActionHandler) -> None:
        self._on_archive_delete = handler

    def _submit(self) -> None:
        if self._on_submit is None:
            self._close()
            return
        try:
            should_close = self._on_submit()
        except Exception as exc:
            messagebox.showerror("Помилка збереження", str(exc), parent=self.window)
            return
        if should_close is False:
            return
        self._close()

    def _duplicate(self) -> None:
        if self._on_duplicate is None:
            return
        try:
            self._on_duplicate()
        except Exception as exc:
            messagebox.showerror("Помилка дублювання", str(exc), parent=self.window)
            return
        self._close()

    def _archive_delete(self) -> None:
        if self._on_archive_delete is None:
            return
        try:
            self._on_archive_delete()
        except Exception as exc:
            messagebox.showerror("Помилка архівації", str(exc), parent=self.window)
            return
        self._close()

    def _close(self) -> None:
        if self.window.winfo_exists():
            self.window.destroy()

    def _build_badge_text(self) -> str:
        level_label = {
            "marktype": "БЛОК",
            "daypattern": "ШАБЛОН ДНЯ",
            "weekpattern": "ШАБЛОН ТИЖНЯ",
        }.get(self.template_level.lower(), self.template_level.upper())
        mode_label = "СТВОРЕННЯ" if self.mode == "create" else "РЕДАГУВАННЯ"
        return f"{level_label} - {mode_label}"

