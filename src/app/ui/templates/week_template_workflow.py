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


from app.ui.templates.week_template_workflow_methods import ensure_week_template_workflow_method_impls

ensure_week_template_workflow_method_impls(globals())

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

    def open_edit_dialog(self, *args, **kwargs):
        return globals()["open_edit_dialog__impl"](self, *args, **kwargs)


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
