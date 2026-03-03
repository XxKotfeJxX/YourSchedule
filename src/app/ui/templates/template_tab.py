from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from app.config.database import session_scope
from app.controllers.template_controller import TemplateController
from app.domain.enums import MarkKind
from app.services.template_models import (
    DayTemplateOverview,
    MarkTypeOverview,
    TemplatesOverview,
    WeekTemplateOverview,
)
from app.ui.templates.cards import DayTemplateCard, MarkTypeCard, WeekTemplateCard
from app.ui.templates.day_template_workflow import DayTemplateWorkflow
from app.ui.templates.mark_type_workflow import MarkTypeWorkflow
from app.ui.templates.shelf_widgets import TemplateShelf
from app.ui.templates.week_template_workflow import WeekTemplateWorkflow


MotionButtonFactory = Callable[..., object]


class CompanyTemplatesTab:
    def __init__(
        self,
        *,
        parent: ttk.Frame,
        company_id: int,
        theme,
        motion_button_factory: MotionButtonFactory,
    ) -> None:
        self.parent = parent
        self.company_id = company_id
        self.theme = theme
        self.motion_button_factory = motion_button_factory
        self._sections: dict[str, ttk.Frame] = {}
        self._overview = TemplatesOverview(mark_types=[], day_templates=[], week_templates=[])
        self._blocks_shelf: TemplateShelf | None = None
        self._days_shelf: TemplateShelf | None = None
        self._weeks_shelf: TemplateShelf | None = None
        self._mark_type_workflow: MarkTypeWorkflow | None = None
        self._day_template_workflow: DayTemplateWorkflow | None = None
        self._week_template_workflow: WeekTemplateWorkflow | None = None
        self._snackbar_window: tk.Toplevel | None = None
        self._snackbar_hide_job: str | None = None
        self._request_sync_scroll: Callable[[], None] | None = None

    def build(self) -> None:
        shell = ttk.Frame(self.parent, style="Card.TFrame")
        shell.pack(fill=tk.BOTH, expand=True)

        section_specs = (("blocks", "Блоки"), ("days", "Дні"), ("weeks", "Тижні"))

        jump_shell = ttk.Frame(shell, style="Card.TFrame")
        jump_shell.pack(fill=tk.X, pady=(0, 8))
        jump_bar = ttk.Frame(jump_shell, style="Card.TFrame")
        jump_bar.pack(fill=tk.X)

        for section_key, label in section_specs:
            self.motion_button_factory(
                jump_bar,
                text=label,
                command=lambda key=section_key: self._scroll_to_section(canvas=canvas, section_key=key),
                primary=False,
                width=130,
                height=40,
            ).pack(side=tk.LEFT, padx=(0, 8))

        content_shell = ttk.Frame(shell, style="Card.TFrame")
        content_shell.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(
            content_shell,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(
            content_shell,
            orient=tk.VERTICAL,
            command=canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)

        body = ttk.Frame(canvas, style="Card.TFrame")
        body_window = canvas.create_window((0, 0), anchor="nw", window=body)

        def sync_scroll(_event=None) -> None:
            viewport_width = max(1, canvas.winfo_width())
            canvas.itemconfigure(
                body_window,
                width=viewport_width,
            )
            bbox = canvas.bbox("all")
            if bbox is not None:
                canvas.configure(scrollregion=bbox)

        def request_sync_scroll() -> None:
            canvas.after_idle(sync_scroll)

        self._request_sync_scroll = request_sync_scroll

        def scroll_templates(step_units: int) -> str:
            canvas.yview_scroll(step_units, "units")
            return "break"

        body.bind("<Configure>", sync_scroll, add="+")
        canvas.bind("<Configure>", sync_scroll, add="+")

        def on_mouse_wheel(event: tk.Event) -> str:
            delta = int(getattr(event, "delta", 0))
            if not delta:
                return "break"
            direction = -1 if delta > 0 else 1
            steps = max(1, int(abs(delta) / 120))
            for _ in range(steps):
                scroll_templates(direction)
            return "break"

        def on_mouse_wheel_up(_event: tk.Event | None = None) -> str:
            return scroll_templates(-1)

        def on_mouse_wheel_down(_event: tk.Event | None = None) -> str:
            return scroll_templates(1)

        for widget in (canvas, body, jump_shell, jump_bar):
            widget.bind("<MouseWheel>", on_mouse_wheel, add="+")
            widget.bind("<Button-4>", on_mouse_wheel_up, add="+")
            widget.bind("<Button-5>", on_mouse_wheel_down, add="+")

        blocks_section = ttk.Frame(body, style="Card.TFrame")
        blocks_section.pack(fill=tk.X, pady=(0, 14))
        days_section = ttk.Frame(body, style="Card.TFrame")
        days_section.pack(fill=tk.X, pady=(0, 14))
        weeks_section = ttk.Frame(body, style="Card.TFrame")
        weeks_section.pack(fill=tk.X, pady=(0, 14))
        self._sections = {"blocks": blocks_section, "days": days_section, "weeks": weeks_section}

        self._blocks_shelf = TemplateShelf(
            blocks_section,
            title="Блоки",
            add_button_text="+ Додати",
            empty_text="Ще немає блоків. Створіть перший блок.",
            on_add=lambda: self._ensure_mark_type_workflow().open_create_dialog(),
            motion_button_factory=self.motion_button_factory,
            theme=self.theme,
            item_name_getter=lambda item: getattr(item, "name", ""),
            item_usage_getter=lambda item: int(getattr(item, "used_in_day_templates", 0)),
            item_archived_getter=lambda item: bool(getattr(item, "is_archived", False)),
            item_id_getter=lambda item: int(getattr(item, "id", 0)),
            wheel_handler=on_mouse_wheel,
            wheel_up_handler=on_mouse_wheel_up,
            wheel_down_handler=on_mouse_wheel_down,
            on_layout_changed=request_sync_scroll,
        )
        self._blocks_shelf.pack(fill=tk.X)

        self._days_shelf = TemplateShelf(
            days_section,
            title="Шаблони дня",
            add_button_text="+ Додати",
            empty_text="Ще немає шаблонів дня. Створіть перший шаблон дня.",
            on_add=lambda: self._ensure_day_template_workflow().open_create_dialog(list(self._overview.mark_types)),
            motion_button_factory=self.motion_button_factory,
            theme=self.theme,
            item_name_getter=lambda item: getattr(item, "name", ""),
            item_usage_getter=lambda item: int(getattr(item, "used_in_week_templates", 0)),
            item_archived_getter=lambda item: bool(getattr(item, "is_archived", False)),
            item_id_getter=lambda item: int(getattr(item, "id", 0)),
            wheel_handler=on_mouse_wheel,
            wheel_up_handler=on_mouse_wheel_up,
            wheel_down_handler=on_mouse_wheel_down,
            on_layout_changed=request_sync_scroll,
        )
        self._days_shelf.pack(fill=tk.X)

        self._weeks_shelf = TemplateShelf(
            weeks_section,
            title="Шаблони тижня",
            add_button_text="+ Додати",
            empty_text="Ще немає шаблонів тижня. Створіть перший шаблон тижня.",
            on_add=lambda: self._ensure_week_template_workflow().open_create_dialog(
                day_templates=list(self._overview.day_templates),
                mark_types=list(self._overview.mark_types),
            ),
            motion_button_factory=self.motion_button_factory,
            theme=self.theme,
            item_name_getter=lambda item: getattr(item, "name", ""),
            item_usage_getter=lambda item: int(getattr(item, "used_in_calendar_periods", 0)),
            item_archived_getter=lambda item: bool(getattr(item, "is_archived", False)),
            item_id_getter=lambda item: int(getattr(item, "id", 0)),
            wheel_handler=on_mouse_wheel,
            wheel_up_handler=on_mouse_wheel_up,
            wheel_down_handler=on_mouse_wheel_down,
            on_layout_changed=request_sync_scroll,
        )
        self._weeks_shelf.pack(fill=tk.X)

        self._mark_type_workflow = MarkTypeWorkflow(
            parent=self.parent,
            company_id=self.company_id,
            theme=self.theme,
            motion_button_factory=self.motion_button_factory,
            on_changed=self._reload_and_render,
            on_feedback=self._show_snackbar,
        )
        self._day_template_workflow = DayTemplateWorkflow(
            parent=self.parent,
            company_id=self.company_id,
            theme=self.theme,
            motion_button_factory=self.motion_button_factory,
            on_changed=self._reload_and_render,
            on_feedback=self._show_snackbar,
        )
        self._week_template_workflow = WeekTemplateWorkflow(
            parent=self.parent,
            company_id=self.company_id,
            theme=self.theme,
            motion_button_factory=self.motion_button_factory,
            on_changed=self._reload_and_render,
            on_feedback=self._show_snackbar,
        )

        self._reload_overview()
        self._render_shelves()
        request_sync_scroll()

    def _reload_overview(self) -> None:
        self._show_loading_state()
        try:
            with session_scope() as session:
                self._overview = TemplateController(session=session).load_templates_overview(self.company_id)
        except Exception as exc:
            messagebox.showerror("Помилка завантаження", str(exc))
            self._overview = TemplatesOverview(mark_types=[], day_templates=[], week_templates=[])

    def _render_shelves(self) -> None:
        if self._blocks_shelf is not None:
            self._blocks_shelf.set_items(
                items=list(self._overview.mark_types),
                card_builder=self._build_mark_card_widget,
            )
        if self._days_shelf is not None:
            self._days_shelf.set_items(
                items=list(self._overview.day_templates),
                card_builder=self._build_day_card_widget,
            )
        if self._weeks_shelf is not None:
            self._weeks_shelf.set_items(
                items=list(self._overview.week_templates),
                card_builder=self._build_week_card_widget,
            )

    def _reload_and_render(self) -> None:
        self._reload_overview()
        self._render_shelves()
        if self._request_sync_scroll is not None:
            self._request_sync_scroll()

    def _build_mark_card_widget(self, parent: ttk.Frame, item: object) -> tk.Widget:
        mark_item = item if isinstance(item, MarkTypeOverview) else None
        if mark_item is None:
            return ttk.Frame(parent, style="Card.TFrame")
        return MarkTypeCard(
            parent,
            theme=self.theme,
            item=mark_item,
            on_open=lambda: self._ensure_mark_type_workflow().open_edit_dialog(mark_item),
            on_edit=lambda: self._ensure_mark_type_workflow().open_edit_dialog(mark_item),
            on_duplicate=lambda: self._ensure_mark_type_workflow().duplicate(mark_item),
            on_archive_delete=lambda: self._ensure_mark_type_workflow().archive_or_delete(mark_item),
            archive_delete_label="Архів" if mark_item.used_in_day_templates > 0 else "Архів / Видалити",
        )

    def _build_day_card_widget(self, parent: ttk.Frame, item: object) -> tk.Widget:
        day_item = item if isinstance(item, DayTemplateOverview) else None
        if day_item is None:
            return ttk.Frame(parent, style="Card.TFrame")
        return DayTemplateCard(
            parent,
            theme=self.theme,
            item=day_item,
            block_kinds=self._resolve_day_block_kinds(day_item),
            on_open=lambda: self._ensure_day_template_workflow().open_edit_dialog(
                item=day_item,
                mark_types=list(self._overview.mark_types),
            ),
            on_edit=lambda: self._ensure_day_template_workflow().open_edit_dialog(
                item=day_item,
                mark_types=list(self._overview.mark_types),
            ),
            on_duplicate=lambda: self._ensure_day_template_workflow().duplicate(day_item),
            on_archive_delete=lambda: self._ensure_day_template_workflow().archive_or_delete(
                item=day_item,
                mark_types=list(self._overview.mark_types),
            ),
            archive_delete_label="Архів" if day_item.used_in_week_templates > 0 else "Архів / Видалити",
        )

    def _build_week_card_widget(self, parent: ttk.Frame, item: object) -> tk.Widget:
        week_item = item if isinstance(item, WeekTemplateOverview) else None
        if week_item is None:
            return ttk.Frame(parent, style="Card.TFrame")
        return WeekTemplateCard(
            parent,
            theme=self.theme,
            item=week_item,
            on_open=lambda: self._ensure_week_template_workflow().open_edit_dialog(
                item=week_item,
                day_templates=list(self._overview.day_templates),
                mark_types=list(self._overview.mark_types),
            ),
            on_edit=lambda: self._ensure_week_template_workflow().open_edit_dialog(
                item=week_item,
                day_templates=list(self._overview.day_templates),
                mark_types=list(self._overview.mark_types),
            ),
            on_duplicate=lambda: self._ensure_week_template_workflow().duplicate(week_item),
            on_archive_delete=lambda: self._ensure_week_template_workflow().archive_or_delete(week_item),
            archive_delete_label="Архів" if week_item.used_in_calendar_periods > 0 else "Архів / Видалити",
        )

    def _resolve_day_block_kinds(self, day_item: DayTemplateOverview) -> list[tuple[MarkKind, int]]:
        mark_by_id = {item.id: item for item in self._overview.mark_types}
        result: list[tuple[MarkKind, int]] = []
        for mark_id in day_item.mark_type_ids:
            mark = mark_by_id.get(mark_id)
            if mark is None:
                continue
            result.append((mark.kind, mark.duration_minutes))
        return result

    def _ensure_mark_type_workflow(self) -> MarkTypeWorkflow:
        if self._mark_type_workflow is None:
            self._mark_type_workflow = MarkTypeWorkflow(
                parent=self.parent,
                company_id=self.company_id,
                theme=self.theme,
                motion_button_factory=self.motion_button_factory,
                on_changed=self._reload_and_render,
                on_feedback=self._show_snackbar,
            )
        return self._mark_type_workflow

    def _ensure_day_template_workflow(self) -> DayTemplateWorkflow:
        if self._day_template_workflow is None:
            self._day_template_workflow = DayTemplateWorkflow(
                parent=self.parent,
                company_id=self.company_id,
                theme=self.theme,
                motion_button_factory=self.motion_button_factory,
                on_changed=self._reload_and_render,
                on_feedback=self._show_snackbar,
            )
        return self._day_template_workflow

    def _ensure_week_template_workflow(self) -> WeekTemplateWorkflow:
        if self._week_template_workflow is None:
            self._week_template_workflow = WeekTemplateWorkflow(
                parent=self.parent,
                company_id=self.company_id,
                theme=self.theme,
                motion_button_factory=self.motion_button_factory,
                on_changed=self._reload_and_render,
                on_feedback=self._show_snackbar,
            )
        return self._week_template_workflow

    def _show_loading_state(self) -> None:
        for shelf in (self._blocks_shelf, self._days_shelf, self._weeks_shelf):
            if shelf is not None:
                shelf.show_loading()
        self.parent.update_idletasks()

    def _show_snackbar(self, message: str) -> None:
        root = self.parent.winfo_toplevel()
        self._hide_snackbar()

        window = tk.Toplevel(root)
        window.overrideredirect(True)
        try:
            window.attributes("-topmost", True)
        except Exception:
            pass
        window.configure(bg=self.theme.TEXT_PRIMARY)
        label = tk.Label(
            window,
            text=message,
            bg=self.theme.TEXT_PRIMARY,
            fg=self.theme.TEXT_LIGHT,
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=10,
        )
        label.pack()

        root.update_idletasks()
        window.update_idletasks()
        x = root.winfo_rootx() + root.winfo_width() - window.winfo_width() - 22
        y = root.winfo_rooty() + root.winfo_height() - window.winfo_height() - 34
        window.geometry(f"+{max(8, x)}+{max(8, y)}")

        self._snackbar_window = window
        self._snackbar_hide_job = root.after(2200, self._hide_snackbar)

    def _hide_snackbar(self) -> None:
        root = self.parent.winfo_toplevel()
        if self._snackbar_hide_job is not None:
            try:
                root.after_cancel(self._snackbar_hide_job)
            except Exception:
                pass
            self._snackbar_hide_job = None
        if self._snackbar_window is not None and self._snackbar_window.winfo_exists():
            self._snackbar_window.destroy()
        self._snackbar_window = None

    def _scroll_to_section(self, *, canvas: tk.Canvas, section_key: str) -> None:
        section = self._sections.get(section_key)
        if section is None:
            return
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox is None:
            return
        content_height = max(1.0, float(bbox[3] - bbox[1]))
        viewport_height = float(max(1, canvas.winfo_height()))
        visible_fraction = min(1.0, viewport_height / content_height)
        max_first_fraction = max(0.0, 1.0 - visible_fraction)

        target_y = max(0.0, float(section.winfo_y()) - 4.0)
        target_fraction = max(0.0, min(1.0, target_y / content_height))
        canvas.yview_moveto(min(target_fraction, max_first_fraction))
