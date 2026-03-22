from __future__ import annotations

import tkinter as tk
from datetime import datetime, time, timedelta
from collections.abc import Callable
from tkinter import messagebox, ttk

from app.config.database import session_scope
from app.controllers.template_controller import TemplateController
from app.domain.enums import MarkKind
from app.services.template_models import DayTemplateOverview, MarkTypeOverview
from app.ui.templates.day_template_logic import (
    build_preset_45_10,
    build_timeline_rows,
    choose_default_break_mark,
    insert_break_between_teaching,
)
from app.ui.templates.template_editor_dialog import TemplateEditorDialog
from app.ui.templates.text_utils import truncate_text


MotionButtonFactory = Callable[..., object]
RefreshCallback = Callable[[], None]
FeedbackCallback = Callable[[str], None]


from app.ui.templates.day_template_workflow_methods import ensure_day_template_workflow_method_impls

ensure_day_template_workflow_method_impls(globals())

class DayTemplateWorkflow:
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

    def open_create_dialog(self, mark_types: list[MarkTypeOverview]) -> None:
        self.open_edit_dialog(item=None, mark_types=mark_types)

    def open_edit_dialog(self, *args, **kwargs):
        return globals()["open_edit_dialog__impl"](self, *args, **kwargs)


    def duplicate(self, item: DayTemplateOverview) -> None:
        self._execute_mutation(
            action="дублювання шаблону дня",
            mutation=lambda controller: controller.duplicate_day_template(
                company_id=self.company_id,
                day_template_id=item.id,
            ),
            success_message="Шаблон дубльовано",
        )

    def archive_or_delete(self, *, item: DayTemplateOverview, mark_types: list[MarkTypeOverview]) -> None:
        if item.used_in_week_templates > 0:
            answer = messagebox.askyesnocancel(
                "Шаблон дня використовується",
                (
                    f"Шаблон '{item.name}' використовується в {item.used_in_week_templates} шаблонах тижня.\n\n"
                    "Так: архівувати\n"
                    "Ні: дублювати і відкрити копію\n"
                    "Скасувати: нічого не робити"
                ),
                parent=self.parent.winfo_toplevel(),
            )
            if answer is None:
                return
            if answer:
                self._execute_mutation(
                    action="архівація шаблону дня",
                    mutation=lambda controller: controller.delete_day_template(
                        company_id=self.company_id,
                        day_template_id=item.id,
                    ),
                    success_message="Заархівовано",
                )
                return
            self._duplicate_and_edit(item=item, mark_types=mark_types)
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
                action="видалення шаблону дня",
                mutation=lambda controller: controller.delete_day_template_permanently(
                    company_id=self.company_id,
                    day_template_id=item.id,
                ),
                success_message="Видалено",
            )
            return
        self._execute_mutation(
            action="архівація шаблону дня",
            mutation=lambda controller: controller.delete_day_template(
                company_id=self.company_id,
                day_template_id=item.id,
            ),
            success_message="Заархівовано",
        )

    def _duplicate_and_edit(self, *, item: DayTemplateOverview, mark_types: list[MarkTypeOverview]) -> None:
        try:
            with session_scope() as session:
                duplicate = TemplateController(session=session).duplicate_day_template(
                    company_id=self.company_id,
                    day_template_id=item.id,
                )
        except Exception as exc:
            messagebox.showerror("Помилка", f"Не вдалося продублювати шаблон дня: {exc}")
            return
        self.on_changed()
        self._notify("Шаблон дубльовано")
        self.open_edit_dialog(item=duplicate, mark_types=mark_types)

    def _execute_mutation(self, *, action: str, mutation, success_message: str | None = None) -> None:
        try:
            with session_scope() as session:
                controller = TemplateController(session=session)
                mutation(controller)
        except Exception as exc:
            messagebox.showerror("Помилка", f"Не вдалося виконати {action}: {exc}")
            return
        self.on_changed()
        if success_message:
            self._notify(success_message)

    def _notify(self, message: str) -> None:
        if self.on_feedback is not None:
            self.on_feedback(message)
