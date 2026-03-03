from __future__ import annotations

import tkinter as tk
from datetime import time
from collections.abc import Callable
from tkinter import messagebox, ttk

from app.config.database import session_scope
from app.controllers.template_controller import TemplateController
from app.domain.enums import MarkKind
from app.services.template_models import DayTemplateOverview, MarkTypeOverview, WeekTemplateOverview
from app.ui.templates.day_template_logic import build_timeline_rows
from app.ui.templates.template_editor_dialog import TemplateEditorDialog
from app.ui.templates.text_utils import truncate_text


MotionButtonFactory = Callable[..., object]
RefreshCallback = Callable[[], None]
MutationFn = Callable[[TemplateController], object]
FeedbackCallback = Callable[[str], None]

WEEKDAY_LABELS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд")


class WeekTemplateWorkflow:
    def __init__(
        self,
        *,
        parent: tk.Widget,
        company_id: int,
        theme,
        motion_button_factory: MotionButtonFactory,
        on_changed: RefreshCallback,
        on_feedback: FeedbackCallback | None = None,
    ) -> None:
        self.parent = parent
        self.company_id = company_id
        self.theme = theme
        self.motion_button_factory = motion_button_factory
        self.on_changed = on_changed
        self.on_feedback = on_feedback

    def open_create_dialog(
        self,
        *,
        day_templates: list[DayTemplateOverview],
        mark_types: list[MarkTypeOverview],
    ) -> None:
        self.open_edit_dialog(item=None, day_templates=day_templates, mark_types=mark_types)

    def open_edit_dialog(
        self,
        *,
        item: WeekTemplateOverview | None,
        day_templates: list[DayTemplateOverview],
        mark_types: list[MarkTypeOverview],
    ) -> None:
        available_days = [day for day in day_templates if not day.is_archived]
        available_marks = [mark for mark in mark_types if not mark.is_archived]
        default_day_id = available_days[0].id if available_days else None

        mode = "edit" if item is not None else "create"
        title = "Редагування шаблону тижня" if item is not None else "Створення шаблону тижня"
        dialog = TemplateEditorDialog(
            parent=self.parent,
            theme=self.theme,
            motion_button_factory=self.motion_button_factory,
            mode=mode,
            template_level="weekpattern",
            template_id=item.id if item else None,
            title=title,
        )

        ttk.Label(dialog.fields_frame, text="Назва", style="Card.TLabel").pack(anchor="w")
        name_var = tk.StringVar(value=item.name if item else "")
        ttk.Entry(dialog.fields_frame, textvariable=name_var).pack(fill=tk.X, pady=(6, 12))

        all_days_by_id = {day.id: day for day in day_templates}
        available_ids = {day.id for day in day_templates}
        mark_by_id = {mark.id: mark for mark in mark_types}
        if item is None:
            mapping: dict[int, int | None] = {
                weekday: (default_day_id if weekday < 5 else None) for weekday in range(7)
            }
            day_enabled = {weekday: tk.BooleanVar(value=weekday < 5) for weekday in range(7)}
        else:
            mapping = {
                weekday: (
                    item.weekday_to_day_template_id.get(weekday)
                    if item.weekday_to_day_template_id.get(weekday) in available_ids
                    else None
                )
                for weekday in range(7)
            }
            day_enabled = {}
            for weekday in range(7):
                day = all_days_by_id.get(mapping.get(weekday))
                day_enabled[weekday] = tk.BooleanVar(value=day is not None and day.preview.total_blocks > 0)

        if not any(var.get() for var in day_enabled.values()):
            for weekday in range(7):
                day_enabled[weekday].set(weekday < 5)
                mapping[weekday] = default_day_id if weekday < 5 else None

        def resolve_mark_ids_for_day(weekday: int) -> list[int]:
            day_id = mapping.get(weekday)
            if day_id is None:
                return []
            day = all_days_by_id.get(day_id)
            if day is None:
                return []
            return [mark_id for mark_id in day.mark_type_ids if mark_id in mark_by_id]

        draft_mark_ids = {weekday: resolve_mark_ids_for_day(weekday) for weekday in range(7)}
        selected_weekday = {"value": next((idx for idx in range(7) if day_enabled[idx].get()), 0)}
        drag_state = {"kind": None, "payload": None, "moved": False, "grab_widget": None}
        drop_target = {"active": False}
        row_frames: list[tk.Widget] = []
        day_buttons: dict[int, tk.Button] = {}
        selected_row_index = {"value": -1}

        ttk.Label(dialog.fields_frame, text="Дні для побудови", style="CardTitle.TLabel").pack(anchor="w")
        days_box = tk.Frame(dialog.fields_frame, bg=self.theme.SURFACE)
        days_box.pack(fill=tk.X, pady=(6, 10))
        for idx in range(7):
            tk.Checkbutton(
                days_box,
                text=WEEKDAY_LABELS[idx],
                variable=day_enabled[idx],
                onvalue=True,
                offvalue=False,
                indicatoron=True,
                bg=self.theme.SURFACE,
                fg=self.theme.TEXT_PRIMARY,
                activebackground=self.theme.SURFACE,
                activeforeground=self.theme.TEXT_PRIMARY,
                selectcolor=self.theme.SURFACE_ALT,
                font=("Segoe UI", 11, "bold"),
                anchor="w",
                bd=0,
                highlightthickness=0,
                relief=tk.FLAT,
                padx=8,
                pady=4,
                cursor="hand2",
                command=lambda target=idx: on_toggle_day(target),
            ).grid(row=idx // 4, column=idx % 4, sticky="w", padx=(0, 10), pady=(0, 6))
        for col in range(4):
            days_box.grid_columnconfigure(col, weight=1)

        ttk.Separator(dialog.fields_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(2, 10))
        ttk.Label(dialog.fields_frame, text="Палітра шаблонів", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            dialog.fields_frame,
            text="Перетягуйте шаблони дня або типи блоків (навчання/перерва) у зону праворуч.",
            style="CardSubtle.TLabel",
            justify=tk.LEFT,
            wraplength=320,
        ).pack(anchor="w", pady=(4, 8))

        palette_wrap = ttk.Frame(dialog.fields_frame, style="Card.TFrame")
        palette_wrap.pack(fill=tk.BOTH, expand=True)
        palette_canvas = tk.Canvas(
            palette_wrap,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            highlightcolor=self.theme.BORDER,
            relief=tk.FLAT,
        )
        palette_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        palette_scroll = ttk.Scrollbar(
            palette_wrap,
            orient=tk.VERTICAL,
            command=palette_canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        palette_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        palette_canvas.configure(yscrollcommand=palette_scroll.set)

        palette_body = ttk.Frame(palette_canvas, style="Card.TFrame")
        palette_window = palette_canvas.create_window((0, 0), anchor="nw", window=palette_body)

        tk.Label(
            palette_body,
            text="Шаблони дня",
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill=tk.X, pady=(2, 6))

        day_palette_cards: dict[int | None, tk.Frame] = {}

        def create_day_palette_card(*, day: DayTemplateOverview | None) -> None:
            name = "Порожній день" if day is None else truncate_text(day.name, 30)
            is_simple = day is None
            meta = "Без занять" if day is None else f"Б:{day.preview.total_blocks} {day.preview.total_minutes}хв"
            badge_text = "Простий" if is_simple else "День"
            badge_bg = self.theme.SECONDARY_PRESSED if is_simple else self.theme.ACCENT
            badge_fg = self.theme.TEXT_PRIMARY if is_simple else self.theme.TEXT_LIGHT

            card = tk.Frame(
                palette_body,
                bg=self.theme.SURFACE_ALT,
                highlightthickness=1,
                highlightbackground=self.theme.BORDER,
                highlightcolor=self.theme.BORDER,
                padx=10,
                pady=8,
                cursor="hand2",
            )
            card.pack(fill=tk.X, pady=(0, 8))

            top = tk.Frame(card, bg=self.theme.SURFACE_ALT)
            top.pack(fill=tk.X)
            tk.Label(
                top,
                text=name,
                bg=self.theme.SURFACE_ALT,
                fg=self.theme.TEXT_PRIMARY,
                font=("Segoe UI", 10, "bold"),
                anchor="w",
                justify=tk.LEFT,
                wraplength=220,
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Label(
                top,
                text=badge_text,
                bg=badge_bg,
                fg=badge_fg,
                font=("Segoe UI", 8, "bold"),
                padx=8,
                pady=2,
                bd=0,
            ).pack(side=tk.RIGHT, padx=(8, 0))

            tk.Label(
                card,
                text=meta,
                bg=self.theme.SURFACE_ALT,
                fg=self.theme.TEXT_MUTED,
                font=("Segoe UI", 9),
                anchor="w",
            ).pack(anchor="w", pady=(6, 0))
            day_palette_cards[day.id if day is not None else None] = card

        for day in available_days:
            create_day_palette_card(day=day)
        create_day_palette_card(day=None)

        tk.Label(
            palette_body,
            text="Блоки",
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill=tk.X, pady=(4, 6))

        mark_palette_cards: dict[int, tk.Frame] = {}
        if not available_marks:
            tk.Label(
                palette_body,
                text="Немає доступних блоків.",
                bg=self.theme.SURFACE,
                fg=self.theme.TEXT_MUTED,
                font=("Segoe UI", 9),
                anchor="w",
            ).pack(fill=tk.X, pady=(0, 8))
        else:
            for mark in available_marks:
                badge_text = "Навчання" if mark.kind == MarkKind.TEACHING else "Перерва"
                badge_bg = self.theme.ACCENT if mark.kind == MarkKind.TEACHING else self.theme.DANGER
                card = tk.Frame(
                    palette_body,
                    bg=self.theme.SURFACE_ALT,
                    highlightthickness=1,
                    highlightbackground=self.theme.BORDER,
                    highlightcolor=self.theme.BORDER,
                    padx=10,
                    pady=8,
                    cursor="hand2",
                )
                card.pack(fill=tk.X, pady=(0, 8))
                top = tk.Frame(card, bg=self.theme.SURFACE_ALT)
                top.pack(fill=tk.X)
                tk.Label(
                    top,
                    text=truncate_text(mark.name, 30),
                    bg=self.theme.SURFACE_ALT,
                    fg=self.theme.TEXT_PRIMARY,
                    font=("Segoe UI", 10, "bold"),
                    anchor="w",
                    justify=tk.LEFT,
                    wraplength=220,
                ).pack(side=tk.LEFT, fill=tk.X, expand=True)
                tk.Label(
                    top,
                    text=badge_text,
                    bg=badge_bg,
                    fg=self.theme.TEXT_LIGHT,
                    font=("Segoe UI", 8, "bold"),
                    padx=8,
                    pady=2,
                    bd=0,
                ).pack(side=tk.RIGHT, padx=(8, 0))
                tk.Label(
                    card,
                    text=f"{mark.duration_minutes} хв",
                    bg=self.theme.SURFACE_ALT,
                    fg=self.theme.TEXT_MUTED,
                    font=("Segoe UI", 9),
                    anchor="w",
                ).pack(anchor="w", pady=(6, 0))
                mark_palette_cards[mark.id] = card

        ttk.Label(dialog.editor_frame, text="Зона розкладу тижня", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            dialog.editor_frame,
            text="Перемикайте день вище і формуйте розклад цього дня перетягуванням.",
            style="CardSubtle.TLabel",
            justify=tk.LEFT,
            wraplength=420,
        ).pack(anchor="w", pady=(4, 8))

        day_switch = tk.Frame(dialog.editor_frame, bg=self.theme.SURFACE)
        day_switch.pack(fill=tk.X, pady=(0, 8))
        for weekday in range(7):
            btn = tk.Button(
                day_switch,
                text=WEEKDAY_LABELS[weekday],
                bd=0,
                relief=tk.FLAT,
                font=("Segoe UI", 9, "bold"),
                padx=10,
                pady=6,
                command=lambda target=weekday: on_switch_day(target),
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            day_buttons[weekday] = btn

        selected_day_title_var = tk.StringVar()
        selected_day_meta_var = tk.StringVar()
        selected_day_header = ttk.Frame(dialog.editor_frame, style="Card.TFrame")
        selected_day_header.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            selected_day_header,
            textvariable=selected_day_title_var,
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            selected_day_header,
            textvariable=selected_day_meta_var,
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_MUTED,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill=tk.X, pady=(2, 0))

        schedule_wrap = ttk.Frame(dialog.editor_frame, style="Card.TFrame")
        schedule_wrap.pack(fill=tk.BOTH, expand=True)
        schedule_canvas = tk.Canvas(
            schedule_wrap,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            highlightcolor=self.theme.BORDER,
            relief=tk.FLAT,
        )
        schedule_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        schedule_scroll = ttk.Scrollbar(
            schedule_wrap,
            orient=tk.VERTICAL,
            command=schedule_canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        schedule_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        schedule_canvas.configure(yscrollcommand=schedule_scroll.set)

        schedule_body = ttk.Frame(schedule_canvas, style="Card.TFrame")
        schedule_window = schedule_canvas.create_window((0, 0), anchor="nw", window=schedule_body)

        actions_row = ttk.Frame(dialog.editor_frame, style="Card.TFrame")
        actions_row.pack(fill=tk.X, pady=(8, 0))
        drop_indicator = tk.Frame(schedule_body, bg=self.theme.ACCENT, bd=0, height=3)
        drag_preview = tk.Toplevel(dialog.window)
        drag_preview.withdraw()
        drag_preview.overrideredirect(True)
        try:
            drag_preview.attributes("-topmost", True)
        except Exception:
            pass
        drag_preview.configure(bg=self.theme.BORDER)
        preview_shell = tk.Frame(drag_preview, bg=self.theme.SURFACE)
        preview_shell.pack(padx=1, pady=1)
        preview_card = tk.Frame(
            preview_shell,
            bg=self.theme.SURFACE_ALT,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            highlightcolor=self.theme.BORDER,
            padx=10,
            pady=8,
        )
        preview_card.pack(fill=tk.BOTH, expand=True)
        preview_card.pack_propagate(False)

        preview_top = tk.Frame(preview_card, bg=self.theme.SURFACE_ALT)
        preview_top.pack(fill=tk.X)
        preview_title_var = tk.StringVar(value="")
        preview_badge_var = tk.StringVar(value="")
        preview_meta_var = tk.StringVar(value="")

        preview_title_label = tk.Label(
            preview_top,
            textvariable=preview_title_var,
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=220,
        )
        preview_title_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        preview_badge_label = tk.Label(
            preview_top,
            textvariable=preview_badge_var,
            bg=self.theme.ACCENT,
            fg=self.theme.TEXT_LIGHT,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=2,
            bd=0,
        )
        preview_badge_label.pack(side=tk.RIGHT, padx=(8, 0))
        tk.Label(
            preview_card,
            textvariable=preview_meta_var,
            bg=self.theme.SURFACE_ALT,
            fg=self.theme.TEXT_MUTED,
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(6, 0))

        def sync_palette(_event=None) -> None:
            palette_canvas.itemconfigure(palette_window, width=max(1, palette_canvas.winfo_width() - 2))
            bbox = palette_canvas.bbox("all")
            if bbox is not None:
                palette_canvas.configure(scrollregion=bbox)

        def sync_schedule(_event=None) -> None:
            schedule_canvas.itemconfigure(schedule_window, width=max(1, schedule_canvas.winfo_width() - 2))
            bbox = schedule_canvas.bbox("all")
            if bbox is not None:
                schedule_canvas.configure(scrollregion=bbox)

        def bind_wheel_recursive(widget: tk.Widget, handler) -> None:
            widget.bind("<MouseWheel>", handler, add="+")
            widget.bind("<Button-4>", handler, add="+")
            widget.bind("<Button-5>", handler, add="+")
            for child in widget.winfo_children():
                bind_wheel_recursive(child, handler)

        def on_palette_wheel(event: tk.Event) -> str:
            delta = int(getattr(event, "delta", 0))
            if delta:
                direction = -1 if delta > 0 else 1
                steps = max(1, int(abs(delta) / 120))
                for _ in range(steps):
                    palette_canvas.yview_scroll(direction, "units")
                return "break"
            if getattr(event, "num", None) == 4:
                palette_canvas.yview_scroll(-1, "units")
                return "break"
            if getattr(event, "num", None) == 5:
                palette_canvas.yview_scroll(1, "units")
                return "break"
            return "break"

        def on_schedule_wheel(event: tk.Event) -> str:
            delta = int(getattr(event, "delta", 0))
            if delta:
                direction = -1 if delta > 0 else 1
                steps = max(1, int(abs(delta) / 120))
                for _ in range(steps):
                    schedule_canvas.yview_scroll(direction, "units")
                return "break"
            if getattr(event, "num", None) == 4:
                schedule_canvas.yview_scroll(-1, "units")
                return "break"
            if getattr(event, "num", None) == 5:
                schedule_canvas.yview_scroll(1, "units")
                return "break"
            return "break"

        def resolve_drop_index(x_root: int, y_root: int) -> int | None:
            if not schedule_canvas.winfo_ismapped():
                return None
            inside_x = schedule_canvas.winfo_rootx() <= x_root <= schedule_canvas.winfo_rootx() + schedule_canvas.winfo_width()
            inside_y = schedule_canvas.winfo_rooty() <= y_root <= schedule_canvas.winfo_rooty() + schedule_canvas.winfo_height()
            if not (inside_x and inside_y):
                return None
            if not row_frames:
                return 0
            for index, frame in enumerate(row_frames):
                midpoint = frame.winfo_rooty() + frame.winfo_height() // 2
                if y_root < midpoint:
                    return index
            return len(row_frames)

        def hide_drop_indicator() -> None:
            if not drop_indicator.winfo_exists():
                return
            try:
                drop_indicator.place_forget()
            except tk.TclError:
                return

        def show_drag_preview(
            *,
            title: str,
            meta: str,
            badge_text: str,
            badge_bg: str,
            badge_fg: str,
            x_root: int,
            y_root: int,
            source_widget: tk.Widget | None = None,
        ) -> None:
            preview_title_var.set(title)
            preview_meta_var.set(meta)
            preview_badge_var.set(badge_text)
            preview_badge_label.configure(bg=badge_bg, fg=badge_fg)

            target_width = 260
            target_height = 66
            if source_widget is not None and source_widget.winfo_exists():
                source_widget.update_idletasks()
                target_width = max(180, int(source_widget.winfo_width()))
                target_height = max(56, int(source_widget.winfo_height()))
            preview_card.configure(width=target_width, height=target_height)
            preview_title_label.configure(wraplength=max(120, target_width - 130))
            drag_preview.update_idletasks()
            drag_preview.geometry(f"+{x_root + 14}+{y_root + 14}")
            drag_preview.deiconify()
            drag_preview.lift()

        def move_drag_preview(x_root: int, y_root: int) -> None:
            if not drag_preview.winfo_exists():
                return
            drag_preview.geometry(f"+{x_root + 14}+{y_root + 14}")

        def hide_drag_preview() -> None:
            if drag_preview.winfo_exists():
                drag_preview.withdraw()

        def release_drag_grab() -> None:
            grabbed_widget = drag_state.get("grab_widget")
            drag_state["grab_widget"] = None
            if grabbed_widget is None:
                return
            try:
                if grabbed_widget.winfo_exists():
                    grabbed_widget.grab_release()
            except tk.TclError:
                pass

        def build_palette_preview(kind: str, payload: int | None) -> tuple[str, str, str, str, str]:
            if kind == "day":
                if payload is None:
                    return (
                        "Порожній день",
                        "Без занять",
                        "Простий",
                        self.theme.SECONDARY_PRESSED,
                        self.theme.TEXT_PRIMARY,
                    )
                day = all_days_by_id.get(int(payload))
                if day is None:
                    return ("Шаблон дня", "Виберіть інший або перетягніть новий", "День", self.theme.ACCENT, self.theme.TEXT_LIGHT)
                return (
                    truncate_text(day.name, 30),
                    f"Б:{day.preview.total_blocks} {day.preview.total_minutes}хв",
                    "День",
                    self.theme.ACCENT,
                    self.theme.TEXT_LIGHT,
                )

            if kind == "mark" and payload is not None:
                mark = mark_by_id.get(int(payload))
                if mark is None:
                    return ("Блок", "Перетягніть, щоб додати блок", "Блок", self.theme.SECONDARY_PRESSED, self.theme.TEXT_PRIMARY)
                mark_kind = "Навчання" if mark.kind == MarkKind.TEACHING else "Перерва"
                badge_bg = self.theme.ACCENT if mark.kind == MarkKind.TEACHING else self.theme.DANGER
                return (truncate_text(mark.name, 30), f"{mark.duration_minutes} хв", mark_kind, badge_bg, self.theme.TEXT_LIGHT)
            return ("Шаблон", "Перетягніть у розклад", "Шаблон", self.theme.SECONDARY_PRESSED, self.theme.TEXT_PRIMARY)

        def show_drop_indicator(index: int | None) -> None:
            if index is None:
                hide_drop_indicator()
                return
            if not drop_indicator.winfo_exists():
                return
            schedule_body.update_idletasks()
            row_count = len(row_frames)
            safe_index = max(0, min(index, row_count))
            if row_count == 0 or safe_index == 0:
                y = 0
            elif safe_index >= row_count:
                last = row_frames[-1]
                y = last.winfo_y() + last.winfo_height()
            else:
                y = row_frames[safe_index].winfo_y()
            left_offset = 92
            width = max(120, schedule_body.winfo_width() - left_offset - 4)
            drop_indicator.place(x=left_offset, y=max(0, y - 1), width=width, height=3)
            drop_indicator.lift()

        def update_drop_highlight(active: bool) -> None:
            if drop_target["active"] == active:
                return
            drop_target["active"] = active
            border = self.theme.ACCENT if active else self.theme.BORDER
            schedule_canvas.configure(highlightbackground=border, highlightcolor=border)

        def reset_palette_drag_state() -> None:
            drag_state["kind"] = None
            drag_state["payload"] = None
            drag_state["moved"] = False
            schedule_canvas.configure(cursor="")
            update_drop_highlight(False)
            hide_drop_indicator()
            hide_drag_preview()
            release_drag_grab()

        def update_switcher() -> None:
            for weekday, btn in day_buttons.items():
                enabled = bool(day_enabled[weekday].get())
                active = weekday == selected_weekday["value"]
                if active:
                    bg, fg = self.theme.ACCENT, self.theme.TEXT_LIGHT
                elif enabled:
                    bg, fg = self.theme.SURFACE_ALT, self.theme.TEXT_PRIMARY
                else:
                    bg, fg = self.theme.SECONDARY_HOVER, self.theme.TEXT_MUTED
                btn.configure(bg=bg, fg=fg, activebackground=bg, activeforeground=fg)

        def set_from_day_template(weekday: int, day_id: int | None) -> None:
            mapping[weekday] = day_id
            if day_id is None:
                draft_mark_ids[weekday] = []
                return
            day = all_days_by_id.get(day_id)
            draft_mark_ids[weekday] = (
                [mark_id for mark_id in day.mark_type_ids if mark_id in mark_by_id]
                if day is not None
                else []
            )

        def apply_mark_card(weekday: int, mark_id: int, insert_index: int | None = None) -> None:
            if mark_id not in mark_by_id:
                return
            mark_ids = draft_mark_ids.get(weekday, [])
            if insert_index is None:
                mark_ids.append(mark_id)
                selected_row_index["value"] = len(mark_ids) - 1
            else:
                safe_index = max(0, min(insert_index, len(mark_ids)))
                mark_ids.insert(safe_index, mark_id)
                selected_row_index["value"] = safe_index
            draft_mark_ids[weekday] = mark_ids
            mapping[weekday] = None

        def on_toggle_day(weekday: int) -> None:
            if day_enabled[weekday].get() and not draft_mark_ids.get(weekday) and default_day_id is not None:
                # When a previously-off day is enabled, prefill it with the default working-day template.
                set_from_day_template(weekday, default_day_id)
            if not day_enabled[weekday].get() and selected_weekday["value"] == weekday:
                selected_weekday["value"] = next((idx for idx in range(7) if day_enabled[idx].get()), weekday)
            update_switcher()
            render_selected_day()

        def on_switch_day(weekday: int) -> None:
            selected_weekday["value"] = weekday
            selected_row_index["value"] = -1
            update_switcher()
            render_selected_day()

        def render_selected_day() -> None:
            current_top = schedule_canvas.yview()[0] if schedule_canvas.yview() else 0.0
            hide_drop_indicator()
            for child in schedule_body.winfo_children():
                if child is drop_indicator:
                    continue
                child.destroy()
            row_frames.clear()

            weekday = selected_weekday["value"]
            label = WEEKDAY_LABELS[weekday]
            if not day_enabled[weekday].get():
                selected_day_title_var.set(f"Розклад {label}")
                selected_day_meta_var.set("День вимкнений. Увімкніть перемикач ліворуч, щоб редагувати розклад.")
                disabled_hint = tk.Label(
                    schedule_body,
                    text="Цей день вимкнений. Увімкніть перемикач ліворуч для редагування.",
                    bg=self.theme.SURFACE_ALT,
                    fg=self.theme.TEXT_MUTED,
                    font=("Segoe UI", 10),
                    padx=14,
                    pady=12,
                    anchor="w",
                )
                disabled_hint.pack(fill=tk.X)
                bind_wheel_recursive(disabled_hint, on_schedule_wheel)
                schedule_canvas.after_idle(lambda: (sync_schedule(), schedule_canvas.yview_moveto(current_top)))
                return

            mark_ids = list(draft_mark_ids.get(weekday, []))
            rows = build_timeline_rows(
                mark_type_ids=mark_ids,
                mark_by_id=mark_by_id,
                start_time=time(hour=8, minute=30),
            )
            teaching = sum(1 for row in rows if row.kind == MarkKind.TEACHING)
            breaks = sum(1 for row in rows if row.kind == MarkKind.BREAK)
            total_minutes = sum(row.duration_minutes for row in rows)
            source_day = all_days_by_id.get(mapping.get(weekday)) if mapping.get(weekday) is not None else None
            source = source_day.name if source_day is not None else "Порожній день"
            selected_day_title_var.set(f"Розклад {label}")
            selected_day_meta_var.set(
                f"Джерело: {truncate_text(source, 30)} | Б:{len(rows)} (Н:{teaching}/П:{breaks}) {total_minutes}хв"
            )

            if not rows:
                selected_row_index["value"] = -1
                empty_hint = tk.Label(
                    schedule_body,
                    text="Перетягніть шаблон дня або блок у цю зону.",
                    bg=self.theme.SURFACE_ALT,
                    fg=self.theme.TEXT_MUTED,
                    font=("Segoe UI", 10),
                    padx=14,
                    pady=14,
                    anchor="w",
                )
                empty_hint.pack(fill=tk.X)
                bind_wheel_recursive(empty_hint, on_schedule_wheel)
                schedule_canvas.after_idle(lambda: (sync_schedule(), schedule_canvas.yview_moveto(current_top)))
                return

            if selected_row_index["value"] < 0 or selected_row_index["value"] >= len(rows):
                selected_row_index["value"] = len(rows) - 1

            for index, row in enumerate(rows):
                row_shell = tk.Frame(schedule_body, bg=self.theme.SURFACE)
                row_shell.pack(fill=tk.X, pady=(0, 8))
                row_frames.append(row_shell)

                time_col = tk.Frame(row_shell, bg=self.theme.SURFACE, width=84)
                time_col.pack(side=tk.LEFT, fill=tk.Y)
                time_col.pack_propagate(False)
                tk.Label(time_col, text=row.start_time, bg=self.theme.SURFACE, fg=self.theme.TEXT_PRIMARY, font=("Segoe UI", 9, "bold"), anchor="w").pack(anchor="w", pady=(6, 0))
                tk.Frame(time_col, bg=self.theme.BORDER, width=72, height=1).pack(anchor="w", pady=(3, 3))
                tk.Label(time_col, text=row.end_time, bg=self.theme.SURFACE, fg=self.theme.TEXT_MUTED, font=("Segoe UI", 9), anchor="w").pack(anchor="w")

                selected = index == selected_row_index["value"]
                card_bg = self.theme.SECONDARY_HOVER if selected else self.theme.SURFACE_ALT
                outline = self.theme.ACCENT if selected else self.theme.BORDER
                card = tk.Frame(
                    row_shell,
                    bg=card_bg,
                    bd=0,
                    highlightthickness=1,
                    highlightbackground=outline,
                    highlightcolor=outline,
                    padx=10,
                    pady=8,
                )
                card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

                header = tk.Frame(card, bg=card_bg)
                header.pack(fill=tk.X)
                tk.Label(
                    header,
                    text=truncate_text(row.mark_name, 36),
                    bg=card_bg,
                    fg=self.theme.TEXT_PRIMARY,
                    font=("Segoe UI", 10, "bold"),
                    anchor="w",
                    justify=tk.LEFT,
                    wraplength=320,
                ).pack(side=tk.LEFT, fill=tk.X, expand=True)
                tk.Label(
                    header,
                    text="Навчання" if row.kind == MarkKind.TEACHING else "Перерва",
                    bg=self.theme.ACCENT if row.kind == MarkKind.TEACHING else self.theme.DANGER,
                    fg=self.theme.TEXT_LIGHT,
                    font=("Segoe UI", 8, "bold"),
                    padx=8,
                    pady=2,
                    bd=0,
                ).pack(side=tk.RIGHT, padx=(8, 0))
                tk.Label(
                    card,
                    text=f"{row.start_time}-{row.end_time} | {row.duration_minutes} хв",
                    bg=card_bg,
                    fg=self.theme.TEXT_MUTED,
                    font=("Segoe UI", 9),
                    anchor="w",
                ).pack(anchor="w", pady=(6, 0))

                def on_select(_event=None, slot=index) -> str:
                    selected_row_index["value"] = slot
                    render_selected_day()
                    return "break"

                def bind_select_recursive(widget: tk.Widget) -> None:
                    widget.bind("<ButtonPress-1>", on_select, add="+")
                    for child in widget.winfo_children():
                        bind_select_recursive(child)

                bind_select_recursive(row_shell)
                bind_wheel_recursive(row_shell, on_schedule_wheel)

            schedule_canvas.after_idle(lambda: (sync_schedule(), schedule_canvas.yview_moveto(current_top)))

        def on_palette_press(
            event: tk.Event,
            *,
            kind: str,
            payload: int | None,
            source_widget: tk.Widget | None = None,
        ) -> str:
            drag_state["kind"] = kind
            drag_state["payload"] = payload
            drag_state["moved"] = False
            schedule_canvas.configure(cursor="plus")
            release_drag_grab()
            try:
                event.widget.grab_set()
                drag_state["grab_widget"] = event.widget
            except tk.TclError:
                drag_state["grab_widget"] = None
            preview_title, preview_meta, badge_text, badge_bg, badge_fg = build_palette_preview(kind, payload)
            show_drag_preview(
                title=preview_title,
                meta=preview_meta,
                badge_text=badge_text,
                badge_bg=badge_bg,
                badge_fg=badge_fg,
                x_root=event.x_root,
                y_root=event.y_root,
                source_widget=source_widget,
            )
            return "break"

        def on_palette_drag(event: tk.Event) -> str:
            if drag_state["kind"] is not None:
                drag_state["moved"] = True
            target_index = resolve_drop_index(event.x_root, event.y_root)
            update_drop_highlight(target_index is not None)
            show_drop_indicator(target_index)
            move_drag_preview(event.x_root, event.y_root)
            return "break"

        def on_palette_release(event: tk.Event, *, kind: str, payload: int | None) -> str:
            if drag_state["kind"] != kind or drag_state["payload"] != payload:
                return "break"

            weekday = selected_weekday["value"]
            drop_index = resolve_drop_index(event.x_root, event.y_root)
            try:
                if kind == "day" and (drop_index is not None or not bool(drag_state["moved"])):
                    if not day_enabled[weekday].get():
                        day_enabled[weekday].set(True)
                    set_from_day_template(weekday, payload)
                elif kind == "mark" and payload is not None and drop_index is not None:
                    if not day_enabled[weekday].get():
                        day_enabled[weekday].set(True)
                    apply_mark_card(weekday, int(payload), insert_index=drop_index)
                elif kind == "mark" and payload is not None and not bool(drag_state["moved"]):
                    if not day_enabled[weekday].get():
                        day_enabled[weekday].set(True)
                    apply_mark_card(weekday, int(payload))
            finally:
                reset_palette_drag_state()
            update_switcher()
            render_selected_day()
            return "break"

        def bind_palette_drag(widget: tk.Widget, *, kind: str, payload: int | None) -> None:
            def bind_drag_recursive(node: tk.Widget) -> None:
                node.bind(
                    "<ButtonPress-1>",
                    lambda event, k=kind, p=payload, src=widget: on_palette_press(
                        event,
                        kind=k,
                        payload=p,
                        source_widget=src,
                    ),
                    add="+",
                )
                node.bind("<B1-Motion>", on_palette_drag, add="+")
                node.bind(
                    "<ButtonRelease-1>",
                    lambda event, k=kind, p=payload: on_palette_release(event, kind=k, payload=p),
                    add="+",
                )
                for child in node.winfo_children():
                    bind_drag_recursive(child)

            bind_drag_recursive(widget)
            bind_wheel_recursive(widget, on_palette_wheel)

        for day_id, card in day_palette_cards.items():
            bind_palette_drag(card, kind="day", payload=day_id)
        for mark_id, card in mark_palette_cards.items():
            bind_palette_drag(card, kind="mark", payload=mark_id)

        delete_button = self.motion_button_factory(
            actions_row,
            text="Видалити слот",
            command=lambda: remove_selected_slot(),
            primary=False,
            width=130,
            height=36,
        )
        delete_button.pack(side=tk.LEFT, padx=(0, 6))
        clear_button = self.motion_button_factory(
            actions_row,
            text="Очистити день",
            command=lambda: clear_day_slots(),
            primary=False,
            width=130,
            height=36,
        )
        clear_button.pack(side=tk.LEFT)

        def remove_selected_slot() -> None:
            weekday = selected_weekday["value"]
            mark_ids = draft_mark_ids.get(weekday, [])
            if not mark_ids:
                return
            idx = selected_row_index["value"]
            if idx < 0 or idx >= len(mark_ids):
                idx = len(mark_ids) - 1
            mark_ids.pop(idx)
            draft_mark_ids[weekday] = mark_ids
            mapping[weekday] = None
            selected_row_index["value"] = min(idx, len(mark_ids) - 1) if mark_ids else -1
            render_selected_day()

        def clear_day_slots() -> None:
            weekday = selected_weekday["value"]
            draft_mark_ids[weekday] = []
            mapping[weekday] = None
            selected_row_index["value"] = -1
            render_selected_day()

        for widget in (palette_canvas, palette_body):
            widget.bind("<MouseWheel>", on_palette_wheel, add="+")
            widget.bind("<Button-4>", on_palette_wheel, add="+")
            widget.bind("<Button-5>", on_palette_wheel, add="+")

        for widget in (schedule_canvas, schedule_body):
            widget.bind("<MouseWheel>", on_schedule_wheel, add="+")
            widget.bind("<Button-4>", on_schedule_wheel, add="+")
            widget.bind("<Button-5>", on_schedule_wheel, add="+")

        palette_body.bind("<Configure>", sync_palette, add="+")
        palette_canvas.bind("<Configure>", sync_palette, add="+")
        schedule_body.bind("<Configure>", sync_schedule, add="+")
        schedule_canvas.bind("<Configure>", sync_schedule, add="+")

        update_switcher()
        render_selected_day()

        def on_submit() -> bool:
            clean_name = name_var.get().strip()
            if not clean_name:
                raise ValueError("Назва шаблону тижня обов'язкова.")

            signature_to_day_id: dict[tuple[int, ...], int] = {}
            for day in day_templates:
                signature = tuple(day.mark_type_ids)
                existing_id = signature_to_day_id.get(signature)
                if existing_id is None:
                    signature_to_day_id[signature] = day.id
                    continue
                existing_day = all_days_by_id.get(existing_id)
                if existing_day is not None and existing_day.is_archived and not day.is_archived:
                    signature_to_day_id[signature] = day.id

            existing_day_names = {day.name for day in day_templates}

            def generate_unique_day_name(base_name: str) -> str:
                candidate = base_name
                index = 2
                while candidate in existing_day_names:
                    candidate = f"{base_name} ({index})"
                    index += 1
                existing_day_names.add(candidate)
                return candidate

            normalized_mapping: dict[int, int] = {}
            with session_scope() as session:
                controller = TemplateController(session=session)
                empty_day_id: int | None = None
                for weekday in range(7):
                    if not day_enabled[weekday].get():
                        if empty_day_id is None:
                            empty_day_id = controller.ensure_empty_day_template(company_id=self.company_id)
                        normalized_mapping[weekday] = int(empty_day_id)
                        continue

                    mark_ids = [mark_id for mark_id in draft_mark_ids.get(weekday, []) if mark_id in mark_by_id]
                    if not mark_ids:
                        if empty_day_id is None:
                            empty_day_id = controller.ensure_empty_day_template(company_id=self.company_id)
                        normalized_mapping[weekday] = int(empty_day_id)
                        continue

                    signature = tuple(mark_ids)
                    mapped_day_id = mapping.get(weekday)
                    if mapped_day_id is not None:
                        mapped_day = all_days_by_id.get(mapped_day_id)
                        if mapped_day is not None and tuple(mapped_day.mark_type_ids) == signature:
                            normalized_mapping[weekday] = int(mapped_day_id)
                            signature_to_day_id.setdefault(signature, int(mapped_day_id))
                            continue

                    day_id = signature_to_day_id.get(signature)
                    if day_id is None:
                        generated_name = generate_unique_day_name(f"{clean_name} {WEEKDAY_LABELS[weekday]}")
                        created = controller.create_day_template(
                            company_id=self.company_id,
                            name=generated_name,
                            mark_type_ids=list(signature),
                        )
                        day_id = int(created.id)
                        signature_to_day_id[signature] = day_id
                        all_days_by_id[day_id] = created

                    if day_id is not None:
                        normalized_mapping[weekday] = int(day_id)

                if item is None:
                    controller.create_week_template(
                        company_id=self.company_id,
                        name=clean_name,
                        weekday_to_day_template_id=normalized_mapping,
                    )
                else:
                    controller.update_week_template(
                        company_id=self.company_id,
                        week_template_id=item.id,
                        name=clean_name,
                        weekday_to_day_template_id=normalized_mapping,
                    )
            self.on_changed()
            self._notify("Збережено")
            return True

        dialog.set_submit_handler(on_submit)
        if item is not None:
            dialog.set_duplicate_handler(lambda: self.duplicate(item))
            dialog.set_archive_delete_handler(lambda: self.archive_or_delete(item))
        dialog.show_modal()

    def duplicate(self, item: WeekTemplateOverview) -> None:
        self._execute_mutation(
            action="дублювання шаблону тижня",
            mutation=lambda controller: controller.duplicate_week_template(
                company_id=self.company_id,
                week_template_id=item.id,
            ),
            success_message="Шаблон дубльовано",
        )

    def archive_or_delete(self, item: WeekTemplateOverview) -> None:
        if item.used_in_calendar_periods > 0:
            should_archive = messagebox.askyesno(
                "Шаблон тижня використовується",
                (
                    f"Шаблон '{item.name}' використовується в {item.used_in_calendar_periods} календарних періодах.\n"
                    "Його можна лише архівувати.\n\nАрхівувати шаблон"
                ),
                parent=self.parent.winfo_toplevel(),
            )
            if not should_archive:
                return
            self._execute_mutation(
                action="архівація шаблону тижня",
                mutation=lambda controller: controller.delete_week_template(
                    company_id=self.company_id,
                    week_template_id=item.id,
                ),
                success_message="Заархівовано",
            )
            return

        answer = messagebox.askyesnocancel(
            "Видалити / Архівувати",
            (
                f"Шаблон '{item.name}' не використовується.\n\n"
                "Так: видалити назавжди\n"
                "Ні: архівувати\n"
                "Скасувати: нічого не робити"
            ),
            parent=self.parent.winfo_toplevel(),
        )
        if answer is None:
            return
        if answer:
            self._execute_mutation(
                action="видалення шаблону тижня",
                mutation=lambda controller: controller.delete_week_template_permanently(
                    company_id=self.company_id,
                    week_template_id=item.id,
                ),
                success_message="Видалено",
            )
            return
        self._execute_mutation(
            action="архівація шаблону тижня",
            mutation=lambda controller: controller.delete_week_template(
                company_id=self.company_id,
                week_template_id=item.id,
            ),
            success_message="Заархівовано",
        )

    def _execute_mutation(
        self,
        *,
        action: str,
        mutation: MutationFn,
        success_message: str | None = None,
    ) -> None:
        try:
            with session_scope() as session:
                mutation(TemplateController(session=session))
        except Exception as exc:
            messagebox.showerror("Помилка", f"Не вдалося виконати {action}: {exc}")
            return
        self.on_changed()
        if success_message:
            self._notify(success_message)

    def _notify(self, message: str) -> None:
        if self.on_feedback is not None:
            self.on_feedback(message)
