from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from app.config.database import session_scope
from app.controllers.template_controller import TemplateController
from app.domain.enums import MarkKind
from app.services.template_models import MarkTypeOverview
from app.ui.templates.template_editor_dialog import TemplateEditorDialog


MotionButtonFactory = Callable[..., object]
RefreshCallback = Callable[[], None]
FeedbackCallback = Callable[[str], None]


class MarkTypeWorkflow:
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

    def open_create_dialog(self) -> None:
        self.open_edit_dialog(None)

    def open_edit_dialog(self, item: MarkTypeOverview | None) -> None:
        mode = "edit" if item is not None else "create"
        title = "Редагування блоку" if item is not None else "Створення блоку"
        dialog = TemplateEditorDialog(
            parent=self.parent,
            theme=self.theme,
            motion_button_factory=self.motion_button_factory,
            mode=mode,
            template_level="marktype",
            template_id=item.id if item else None,
            title=title,
        )

        name_var = tk.StringVar(value=item.name if item else "")
        kind_var = tk.StringVar(value=(item.kind.value if item else MarkKind.TEACHING.value))
        duration_var = tk.StringVar(value=str(item.duration_minutes if item else 45))

        ttk.Label(dialog.fields_frame, text="Назва", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(dialog.fields_frame, textvariable=name_var).pack(fill=tk.X, pady=(6, 10))

        ttk.Label(dialog.fields_frame, text="Тип", style="Card.TLabel").pack(anchor="w")
        ttk.Combobox(
            dialog.fields_frame,
            textvariable=kind_var,
            values=[MarkKind.TEACHING.value, MarkKind.BREAK.value],
            state="readonly",
        ).pack(fill=tk.X, pady=(6, 10))

        ttk.Label(dialog.fields_frame, text="Тривалість (хв)", style="Card.TLabel").pack(anchor="w")
        ttk.Entry(dialog.fields_frame, textvariable=duration_var).pack(fill=tk.X, pady=(6, 10))

        ttk.Label(dialog.editor_frame, text="Попередній перегляд", style="CardTitle.TLabel").pack(anchor="w")
        preview_kind_var = tk.StringVar()
        preview_line_var = tk.StringVar()
        preview_kind = tk.Label(
            dialog.editor_frame,
            textvariable=preview_kind_var,
            bg=self.theme.SECONDARY_HOVER,
            fg=self.theme.ACCENT,
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=5,
            bd=0,
        )
        preview_kind.pack(anchor="w", pady=(8, 6))
        ttk.Label(dialog.editor_frame, textvariable=preview_line_var, style="CardSubtle.TLabel").pack(anchor="w")

        def refresh_preview(*_args) -> None:
            current_kind = kind_var.get().strip() or MarkKind.TEACHING.value
            duration_text = duration_var.get().strip() or "0"
            if current_kind == MarkKind.BREAK.value:
                preview_kind.configure(bg=self.theme.DANGER, fg=self.theme.TEXT_LIGHT)
                preview_kind_var.set("Перерва")
            else:
                preview_kind.configure(bg=self.theme.ACCENT, fg=self.theme.TEXT_LIGHT)
                preview_kind_var.set("Навчання")
            preview_line_var.set(f"Тривалість: {duration_text} хв")

        kind_var.trace_add("write", refresh_preview)
        duration_var.trace_add("write", refresh_preview)
        refresh_preview()

        def on_submit() -> bool:
            name_value = name_var.get().strip()
            if not name_value:
                raise ValueError("Назва блоку обов'язкова.")
            try:
                duration_value = int(duration_var.get().strip())
            except ValueError as exc:
                raise ValueError("Тривалість має бути цілим числом.") from exc
            if duration_value <= 0:
                raise ValueError("Тривалість має бути більшою за 0.")

            with session_scope() as session:
                controller = TemplateController(session=session)
                if item is None:
                    controller.create_mark_type(
                        company_id=self.company_id,
                        name=name_value,
                        kind=kind_var.get().strip(),
                        duration_minutes=duration_value,
                    )
                else:
                    controller.update_mark_type(
                        company_id=self.company_id,
                        mark_type_id=item.id,
                        name=name_value,
                        kind=kind_var.get().strip(),
                        duration_minutes=duration_value,
                    )
            self.on_changed()
            self._notify("Збережено")
            return True

        dialog.set_submit_handler(on_submit)
        if item is not None:
            dialog.set_duplicate_handler(lambda: self.duplicate(item))
            dialog.set_archive_delete_handler(lambda: self.archive_or_delete(item))
        dialog.show_modal()

    def duplicate(self, item: MarkTypeOverview) -> None:
        self._execute_mutation(
            action="дублювання блоку",
            mutation=lambda controller: controller.duplicate_mark_type(
                company_id=self.company_id,
                mark_type_id=item.id,
            ),
            success_message="Блок дубльовано",
        )

    def archive_or_delete(self, item: MarkTypeOverview) -> None:
        if item.used_in_day_templates > 0:
            should_archive = messagebox.askyesno(
                "Блок використовується",
                (
                    f"Блок '{item.name}' використовується в {item.used_in_day_templates} шаблонах дня.\n"
                    "Його можна лише архівувати.\n\nАрхівувати блок"
                ),
                parent=self.parent.winfo_toplevel(),
            )
            if not should_archive:
                return
            self._execute_mutation(
                action="архівація блоку",
                mutation=lambda controller: controller.delete_mark_type(
                    company_id=self.company_id,
                    mark_type_id=item.id,
                ),
                success_message="Заархівовано",
            )
            return

        answer = messagebox.askyesnocancel(
            "Видалити / Архівувати",
            (
                f"Блок '{item.name}' не використовується.\n\n"
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
                action="видалення блоку",
                mutation=lambda controller: controller.delete_mark_type_permanently(
                    company_id=self.company_id,
                    mark_type_id=item.id,
                ),
                success_message="Видалено",
            )
            return
        self._execute_mutation(
            action="архівація блоку",
            mutation=lambda controller: controller.delete_mark_type(
                company_id=self.company_id,
                mark_type_id=item.id,
            ),
            success_message="Заархівовано",
        )

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
