from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from app.domain.enums import MarkKind
from app.services.template_models import DayTemplateOverview, MarkTypeOverview, WeekTemplateOverview
from app.ui.fx_widgets import RoundedMotionCard
from app.ui.templates.text_utils import truncate_text


WEEKDAY_LABELS_UA = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд")


OpenCallback = Callable[[], None]
ActionCallback = Callable[[], None]


class _BaseTemplateCard(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Frame,
        *,
        theme,
        title: str,
        subtitle: str,
        meta: str,
        archived: bool,
        on_open: OpenCallback,
        on_edit: ActionCallback,
        on_duplicate: ActionCallback,
        on_archive_delete: ActionCallback,
        archive_delete_label: str,
        width: int = 268,
        height: int = 150,
    ) -> None:
        super().__init__(parent, style="Card.TFrame")
        self.theme = theme
        self._on_open = on_open
        self._on_edit = on_edit
        self._on_duplicate = on_duplicate
        self._on_archive_delete = on_archive_delete
        self._archive_delete_label = archive_delete_label
        self._archived = archived
        self._card_color = self.theme.SURFACE_ALT

        self.shell = RoundedMotionCard(
            self,
            bg_color=self.theme.SURFACE,
            card_color=self._card_color,
            shadow_color=self.theme.SHADOW_SOFT,
            radius=16,
            padding=4,
            shadow_offset=4,
            motion_enabled=True,
            width=width,
            height=height,
        )
        self.shell.pack(fill=tk.BOTH, expand=True)

        self.top_row = tk.Frame(self.shell.content, bg=self._card_color)
        self.top_row.pack(fill=tk.X)
        self.title_label = tk.Label(
            self.top_row,
            text=title,
            bg=self._card_color,
            fg=self.theme.TEXT_PRIMARY,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=220,
        )
        self.title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.subtitle_label = tk.Label(
            self.shell.content,
            text=subtitle,
            bg=self._card_color,
            fg=self.theme.TEXT_MUTED,
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=230,
        )
        self.subtitle_label.pack(fill=tk.X, pady=(6, 4))

        self.preview_host = tk.Frame(self.shell.content, bg=self._card_color)
        self.preview_host.pack(fill=tk.X, pady=(0, 6))

        meta_text = meta if not archived else f"{meta}  •  Архів"
        meta_fg = self.theme.TEXT_MUTED if not archived else self.theme.DANGER
        self.meta_label = tk.Label(
            self.shell.content,
            text=meta_text,
            bg=self._card_color,
            fg=meta_fg,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=230,
        )
        self.meta_label.pack(fill=tk.X)

        self._bind_interactions()

    def _bind_interactions(self) -> None:
        self._bind_recursive(self, "<Button-1>", self._handle_open_click)
        self._bind_recursive(self, "<Button-3>", self._show_menu_event)

    def _bind_recursive(self, widget: tk.Widget, event_name: str, handler) -> None:
        widget.bind(event_name, handler, add="+")
        for child in widget.winfo_children():
            self._bind_recursive(child, event_name, handler)

    def _handle_open_click(self, event: tk.Event) -> str:
        self._on_open()
        return "break"

    def _show_menu_event(self, event: tk.Event) -> str:
        self._show_context_menu(x=event.x_root, y=event.y_root)
        return "break"

    def _show_context_menu(self, *, x: int, y: int) -> None:
        def queue_action(action: ActionCallback) -> None:
            root = self.winfo_toplevel()
            try:
                if bool(root.winfo_exists()):
                    root.after(1, action)
                    return
            except Exception:
                pass
            action()

        menu = tk.Menu(
            self,
            tearoff=0,
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            activebackground=self.theme.SECONDARY_HOVER,
            activeforeground=self.theme.TEXT_PRIMARY,
            bd=0,
            borderwidth=0,
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        menu.add_command(label="Редагувати", command=lambda: queue_action(self._on_edit))
        menu.add_command(label="Дублювати", command=lambda: queue_action(self._on_duplicate))
        menu.add_separator()
        menu.add_command(
            label=self._archive_delete_label,
            command=lambda: queue_action(self._on_archive_delete),
            foreground=self.theme.DANGER,
            activebackground=self.theme.DANGER_HOVER,
            activeforeground=self.theme.TEXT_LIGHT,
        )
        try:
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass
            try:
                menu.destroy()
            except Exception:
                pass


class MarkTypeCard(_BaseTemplateCard):
    def __init__(
        self,
        parent: ttk.Frame,
        *,
        theme,
        item: MarkTypeOverview,
        on_open: OpenCallback,
        on_edit: ActionCallback,
        on_duplicate: ActionCallback,
        on_archive_delete: ActionCallback,
        archive_delete_label: str,
    ) -> None:
        super().__init__(
            parent,
            theme=theme,
            title=truncate_text(item.name, 24),
            subtitle=f"{'Навчання' if item.kind == MarkKind.TEACHING else 'Перерва'} • {item.duration_minutes} хв",
            meta=f"Використано у шаблонах дня: {item.used_in_day_templates}",
            archived=item.is_archived,
            on_open=on_open,
            on_edit=on_edit,
            on_duplicate=on_duplicate,
            on_archive_delete=on_archive_delete,
            archive_delete_label=archive_delete_label,
            height=140,
        )

        badge_fill = self.theme.ACCENT if item.kind == MarkKind.TEACHING else self.theme.DANGER
        badge_text = "Навчання" if item.kind == MarkKind.TEACHING else "Перерва"
        self.preview_host.pack_forget()
        badge = tk.Label(
            self.top_row,
            text=badge_text,
            bg=badge_fill,
            fg=self.theme.TEXT_LIGHT,
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=5,
            bd=0,
        )
        self.title_label.pack_forget()
        badge.pack(side=tk.RIGHT, padx=(10, 0))
        self.title_label.configure(wraplength=138)
        self.title_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))


class DayTemplateCard(_BaseTemplateCard):
    def __init__(
        self,
        parent: ttk.Frame,
        *,
        theme,
        item: DayTemplateOverview,
        block_kinds: list[tuple[MarkKind, int]],
        on_open: OpenCallback,
        on_edit: ActionCallback,
        on_duplicate: ActionCallback,
        on_archive_delete: ActionCallback,
        archive_delete_label: str,
    ) -> None:
        preview = item.preview
        super().__init__(
            parent,
            theme=theme,
            title=truncate_text(item.name, 28),
            subtitle=f"Блоків: {preview.total_blocks} (Н:{preview.teaching_blocks} / П:{preview.break_blocks})",
            meta=f"День: {preview.total_minutes} хв до {preview.estimated_end_time} • Використано у тижнях: {item.used_in_week_templates}",
            archived=item.is_archived,
            on_open=on_open,
            on_edit=on_edit,
            on_duplicate=on_duplicate,
            on_archive_delete=on_archive_delete,
            archive_delete_label=archive_delete_label,
            height=170,
        )
        self._draw_timeline(block_kinds)

    def _draw_timeline(self, block_kinds: list[tuple[MarkKind, int]]) -> None:
        canvas = tk.Canvas(
            self.preview_host,
            width=232,
            height=34,
            bg=self._card_color,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        canvas.pack(fill=tk.X)

        if not block_kinds:
            canvas.create_text(6, 17, text="Немає блоків", fill=self.theme.TEXT_MUTED, anchor="w", font=("Segoe UI", 9))
            return

        total_duration = sum(duration for _, duration in block_kinds)
        total_duration = max(total_duration, 1)
        available_width = 220
        x = 6
        for index, (kind, duration) in enumerate(block_kinds):
            if index == len(block_kinds) - 1:
                width = max(12, 6 + available_width - x)
            else:
                width = max(12, int(available_width * (duration / total_duration)))
            fill = self.theme.ACCENT if kind == MarkKind.TEACHING else self.theme.DANGER
            canvas.create_rectangle(x, 6, x + width, 28, fill=fill, outline="")
            label = "Н" if kind == MarkKind.TEACHING else "П"
            if width >= 26:
                canvas.create_text(
                    x + width / 2,
                    17,
                    text=label,
                    fill=self.theme.TEXT_LIGHT,
                    font=("Segoe UI", 8, "bold"),
                )
            x += width + 2


class WeekTemplateCard(_BaseTemplateCard):
    def __init__(
        self,
        parent: ttk.Frame,
        *,
        theme,
        item: WeekTemplateOverview,
        on_open: OpenCallback,
        on_edit: ActionCallback,
        on_duplicate: ActionCallback,
        on_archive_delete: ActionCallback,
        archive_delete_label: str,
    ) -> None:
        preview = item.preview
        super().__init__(
            parent,
            theme=theme,
            title=truncate_text(item.name, 28),
            subtitle=f"Днів: {preview.assigned_days} • Унікальних: {preview.unique_day_templates}",
            meta=f"Блоків/тиждень: {preview.total_blocks} (Н:{preview.teaching_blocks} / П:{preview.break_blocks}) • Використано у періодах: {item.used_in_calendar_periods}",
            archived=item.is_archived,
            on_open=on_open,
            on_edit=on_edit,
            on_duplicate=on_duplicate,
            on_archive_delete=on_archive_delete,
            archive_delete_label=archive_delete_label,
            height=182,
        )
        self._draw_week_preview(item)

    def _draw_week_preview(self, item: WeekTemplateOverview) -> None:
        canvas = tk.Canvas(
            self.preview_host,
            width=232,
            height=52,
            bg=self._card_color,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        canvas.pack(fill=tk.X)

        palette = (
            self.theme.ACCENT,
            self.theme.HERO_BLOB_2,
            self.theme.HERO_BLOB_3,
            self.theme.SECONDARY_PRESSED,
            "#f59e0b",
        )

        x = 4
        for weekday in range(7):
            day_template_id = item.weekday_to_day_template_id.get(weekday, 0)
            color = palette[day_template_id % len(palette)] if day_template_id else self.theme.SURFACE
            canvas.create_rectangle(x, 4, x + 30, 46, fill=color, outline="")
            canvas.create_text(
                x + 15,
                13,
                text=WEEKDAY_LABELS_UA[weekday],
                fill=self.theme.TEXT_LIGHT if day_template_id else self.theme.TEXT_MUTED,
                font=("Segoe UI", 8, "bold"),
            )
            day_name = item.weekday_to_day_template_name.get(weekday, "—")
            day_short = day_name[:2] if day_name else "--"
            canvas.create_text(
                x + 15,
                30,
                text=day_short,
                fill=self.theme.TEXT_LIGHT if day_template_id else self.theme.TEXT_MUTED,
                font=("Segoe UI", 8),
            )
            x += 32

