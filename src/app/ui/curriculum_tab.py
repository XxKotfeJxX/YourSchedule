from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from sqlalchemy.exc import IntegrityError

from app.config.database import session_scope
from app.controllers.academic_controller import AcademicController
from app.controllers.curriculum_controller import CurriculumController
from app.controllers.resource_controller import ResourceController
from app.domain.enums import PlanComponentType, PlanTargetType, ResourceType
from app.ui.theme import UiTheme


class CompanyCurriculumTab:
    def __init__(
        self,
        *,
        parent: ttk.Frame,
        company_id: int,
        theme: UiTheme,
        motion_button_factory: Callable[..., object],
    ) -> None:
        self.parent = parent
        self.company_id = company_id
        self.theme = theme
        self._motion_button = motion_button_factory

        self.status_var = tk.StringVar(value="Готово.")

        # Teachers
        self.teacher_name_var = tk.StringVar()
        self.teacher_listbox: tk.Listbox | None = None
        self._teacher_ids: list[int] = []
        self._teacher_name_by_id: dict[int, str] = {}

        # Subjects
        self.subject_name_var = tk.StringVar()
        self.subject_code_var = tk.StringVar()
        self.subject_department_var = tk.StringVar()
        self.subject_listbox: tk.Listbox | None = None
        self.subject_department_box: ttk.Combobox | None = None
        self._subject_ids: list[int] = []
        self._subject_name_by_id: dict[int, str] = {}
        self._department_name_by_id: dict[int, str] = {}

        # Plans
        self.plan_listbox: tk.Listbox | None = None
        self._plan_ids: list[int] = []
        self._selected_plan_id: int | None = None
        self._selected_component_id: int | None = None
        self._selected_assignment_id: int | None = None

        self.plan_name_var = tk.StringVar()
        self.plan_semester_var = tk.StringVar()
        self.plan_specialty_var = tk.StringVar()
        self.plan_course_var = tk.StringVar()
        self.plan_stream_var = tk.StringVar()

        self.component_subject_var = tk.StringVar()
        self.component_type_var = tk.StringVar(value=PlanComponentType.LECTURE.value)
        self.component_duration_var = tk.StringVar(value="1")
        self.component_sessions_var = tk.StringVar(value="4")
        self.component_max_per_week_var = tk.StringVar(value="2")
        self.component_notes_var = tk.StringVar()

        self.assignment_teacher_var = tk.StringVar()
        self.assignment_target_type_var = tk.StringVar(value=PlanTargetType.STREAM.value)
        self.assignment_stream_var = tk.StringVar()
        self.assignment_group_var = tk.StringVar()
        self.assignment_subgroup_var = tk.StringVar()
        self.assignment_sessions_var = tk.StringVar()
        self.assignment_max_per_week_var = tk.StringVar()

        self.plan_specialty_box: ttk.Combobox | None = None
        self.plan_course_box: ttk.Combobox | None = None
        self.plan_stream_box: ttk.Combobox | None = None
        self.component_subject_box: ttk.Combobox | None = None
        self.assignment_teacher_box: ttk.Combobox | None = None
        self.assignment_stream_box: ttk.Combobox | None = None
        self.assignment_group_box: ttk.Combobox | None = None
        self.assignment_subgroup_box: ttk.Combobox | None = None
        self.assignment_target_type_box: ttk.Combobox | None = None

        self.component_tree: ttk.Treeview | None = None
        self.assignment_tree: ttk.Treeview | None = None
        self._component_ids_by_iid: dict[str, int] = {}
        self._assignment_ids_by_iid: dict[str, int] = {}

        self._stream_name_by_id: dict[int, str] = {}
        self._group_name_by_id: dict[int, str] = {}
        self._subgroup_name_by_id: dict[int, str] = {}

    def build(self) -> None:
        tabs_bar = ttk.Frame(self.parent, style="Card.TFrame")
        tabs_bar.pack(fill=tk.X, pady=(0, 4))

        content = ttk.Frame(self.parent, style="Card.TFrame")
        content.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 2))

        views: dict[str, ttk.Frame] = {
            "teachers": ttk.Frame(content, style="Card.TFrame", padding=6),
            "subjects": ttk.Frame(content, style="Card.TFrame", padding=6),
            "plans": ttk.Frame(content, style="Card.TFrame", padding=6),
        }
        nav_buttons: dict[str, object] = {}

        def _set_nav_button_state(button: object, *, active: bool) -> None:
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
            ("teachers", "Викладачі"),
            ("subjects", "Предмети"),
            ("plans", "Плани"),
        )
        for key, label in tab_specs:
            button = self._motion_button(
                tabs_bar,
                text=label,
                command=lambda selected=key: open_tab(selected),
                primary=False,
                width=150,
                height=36,
            )
            button.pack(side=tk.LEFT, padx=(0, 8))
            nav_buttons[key] = button

        self._build_teachers_tab(views["teachers"])
        self._build_subjects_tab(views["subjects"])
        self._build_plans_tab(views["plans"])

        open_tab("teachers")

        ttk.Label(self.parent, textvariable=self.status_var, style="CardSubtle.TLabel").pack(fill=tk.X, pady=(4, 0))

        self._refresh_all()

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    @staticmethod
    def _parse_prefixed_id(raw: str) -> int | None:
        value = raw.strip()
        if not value or "|" not in value:
            return None
        try:
            return int(value.split("|", maxsplit=1)[0].strip())
        except ValueError:
            return None

    @staticmethod
    def _parse_optional_positive_int(raw: str) -> int | None:
        value = raw.strip()
        if not value:
            return None
        parsed = int(value)
        if parsed <= 0:
            raise ValueError("Значення має бути більше нуля")
        return parsed

    def _selected_listbox_id(self, listbox: tk.Listbox | None, ids: list[int]) -> int | None:
        if listbox is None:
            return None
        selected = listbox.curselection()
        if not selected:
            return None
        idx = int(selected[0])
        if idx < 0 or idx >= len(ids):
            return None
        return ids[idx]

    def _set_combobox_values(
        self,
        box: ttk.Combobox | None,
        variable: tk.StringVar,
        values: list[str],
        *,
        allow_empty: bool = True,
    ) -> None:
        if box is None:
            return
        box["values"] = values
        current = variable.get()
        if current in values:
            return
        if allow_empty and "" in values:
            variable.set("")
        elif values:
            variable.set(values[0])
        else:
            variable.set("")

    def _bind_responsive_split(
        self,
        *,
        container: ttk.Frame,
        left: ttk.Frame,
        right: ttk.Frame,
        breakpoint: int,
        wide_left_weight: int,
        wide_right_weight: int,
        stacked_top_weight: int = 1,
        stacked_bottom_weight: int = 1,
    ) -> None:
        state = {"mode": ""}

        def apply_layout() -> None:
            width = container.winfo_width() or container.winfo_reqwidth()
            mode = "wide" if width >= breakpoint else "stacked"
            if state["mode"] == mode:
                return
            state["mode"] = mode

            if mode == "wide":
                container.grid_columnconfigure(0, weight=wide_left_weight)
                container.grid_columnconfigure(1, weight=wide_right_weight)
                container.grid_rowconfigure(0, weight=1)
                container.grid_rowconfigure(1, weight=0)
                left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
                right.grid(row=0, column=1, sticky="nsew")
                return

            container.grid_columnconfigure(0, weight=1)
            container.grid_columnconfigure(1, weight=0)
            container.grid_rowconfigure(0, weight=stacked_top_weight)
            container.grid_rowconfigure(1, weight=stacked_bottom_weight)
            left.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 6))
            right.grid(row=1, column=0, sticky="nsew")

        container.bind("<Configure>", lambda _e: apply_layout(), add="+")
        container.after_idle(apply_layout)

    def _grid_action_buttons(
        self,
        *,
        parent: ttk.Frame,
        items: list[tuple[str, Callable[[], None], bool]],
        columns: int,
        width: int,
        height: int,
    ) -> None:
        for column in range(columns):
            parent.grid_columnconfigure(column, weight=1, uniform=f"actions-{id(parent)}")

        for idx, (text, command, primary) in enumerate(items):
            row = idx // columns
            column = idx % columns
            is_last_column = column == columns - 1
            is_last_row = row == (len(items) - 1) // columns
            padx = (0, 6) if not is_last_column else 0
            pady = (0, 6) if not is_last_row else 0
            self._motion_button(
                parent,
                text=text,
                command=command,
                primary=primary,
                width=width,
                height=height,
            ).grid(row=row, column=column, sticky="ew", padx=padx, pady=pady)

    def _refresh_all(self) -> None:
        self._load_subject_departments()
        self._load_teachers()
        self._load_subjects()
        self._load_plan_reference_data()
        self._load_plans()
        self._refresh_assignment_target_controls()

    def _refresh_subjects(self) -> None:
        self._load_subject_departments()
        self._load_subjects()
        self._load_plan_reference_data()
        if self._selected_plan_id is not None:
            self._load_components(self._selected_plan_id)

    # Teachers
    def _build_teachers_tab(self, parent: ttk.Frame) -> None:
        content = ttk.Frame(parent, style="Card.TFrame")
        content.pack(fill=tk.BOTH, expand=True)

        list_wrap = ttk.Frame(content, style="Card.TFrame")
        self.teacher_listbox = tk.Listbox(
            list_wrap,
            activestyle="none",
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            selectbackground=self.theme.LISTBOX_SELECTED_BG,
            selectforeground=self.theme.TEXT_PRIMARY,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            relief=tk.FLAT,
            font=("Segoe UI", 11),
            exportselection=False,
        )
        self.teacher_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 0), pady=2)
        scroll = ttk.Scrollbar(
            list_wrap,
            orient=tk.VERTICAL,
            command=self.teacher_listbox.yview,
            style="App.Vertical.TScrollbar",
        )
        scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0), pady=2)
        self.teacher_listbox.configure(yscrollcommand=scroll.set)
        self.teacher_listbox.bind("<<ListboxSelect>>", lambda _e: self._on_teacher_select(), add="+")

        form = ttk.Frame(content, style="Card.TFrame")
        form.grid_columnconfigure(0, weight=1)
        ttk.Label(form, text="Ім'я викладача", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.teacher_name_var).grid(row=1, column=0, sticky="ew", pady=(4, 6))

        buttons = ttk.Frame(form, style="Card.TFrame")
        buttons.grid(row=2, column=0, sticky="ew")
        self._grid_action_buttons(
            parent=buttons,
            items=[
                ("Додати", self._add_teacher, True),
                ("Змінити", self._update_teacher, False),
                ("Видалити", self._delete_teacher, False),
                ("Оновити", self._load_teachers, False),
            ],
            columns=2,
            width=120,
            height=34,
        )

        self._bind_responsive_split(
            container=content,
            left=list_wrap,
            right=form,
            breakpoint=930,
            wide_left_weight=3,
            wide_right_weight=5,
        )

    def _load_teachers(self) -> None:
        if self.teacher_listbox is None:
            return
        selected_id = self._selected_listbox_id(self.teacher_listbox, self._teacher_ids)
        with session_scope() as session:
            teachers = ResourceController(session=session).list_resources(
                resource_type=ResourceType.TEACHER,
                company_id=self.company_id,
            )
        teachers = sorted(teachers, key=lambda item: item.name.casefold())
        self._teacher_ids = [item.id for item in teachers]
        self._teacher_name_by_id = {item.id: item.name for item in teachers}
        self.teacher_listbox.delete(0, tk.END)
        for item in teachers:
            self.teacher_listbox.insert(tk.END, f"  {item.name}")
        if selected_id is not None and selected_id in self._teacher_ids:
            idx = self._teacher_ids.index(selected_id)
            self.teacher_listbox.selection_set(idx)
            self.teacher_listbox.see(idx)

    def _on_teacher_select(self) -> None:
        teacher_id = self._selected_listbox_id(self.teacher_listbox, self._teacher_ids)
        if teacher_id is None:
            return
        self.teacher_name_var.set(self._teacher_name_by_id.get(teacher_id, ""))

    def _add_teacher(self) -> None:
        name = self.teacher_name_var.get().strip()
        if not name:
            messagebox.showerror("Помилка валідації", "Ім'я викладача обов'язкове.")
            return
        try:
            with session_scope() as session:
                ResourceController(session=session).create_resource(
                    name=name,
                    resource_type=ResourceType.TEACHER,
                    company_id=self.company_id,
                )
        except IntegrityError:
            messagebox.showerror("Конфлікт", "Викладач із таким ім'ям вже існує.")
            return
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self.teacher_name_var.set("")
        self._load_teachers()
        self._load_plan_reference_data()
        self._set_status(f"Викладача '{name}' створено.")

    def _update_teacher(self) -> None:
        teacher_id = self._selected_listbox_id(self.teacher_listbox, self._teacher_ids)
        if teacher_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери викладача.")
            return
        name = self.teacher_name_var.get().strip()
        if not name:
            messagebox.showerror("Помилка валідації", "Ім'я викладача обов'язкове.")
            return
        try:
            with session_scope() as session:
                ResourceController(session=session).update_resource(teacher_id, name=name)
        except IntegrityError:
            messagebox.showerror("Конфлікт", "Викладач із таким ім'ям вже існує.")
            return
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self._load_teachers()
        self._load_plan_reference_data()
        self._set_status(f"Викладача #{teacher_id} оновлено.")

    def _delete_teacher(self) -> None:
        teacher_id = self._selected_listbox_id(self.teacher_listbox, self._teacher_ids)
        if teacher_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери викладача.")
            return
        if not messagebox.askyesno("Видалення викладача", "Видалити вибраного викладача?"):
            return
        try:
            with session_scope() as session:
                deleted = ResourceController(session=session).delete_resource(teacher_id)
                if not deleted:
                    raise ValueError("Викладача не знайдено")
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self.teacher_name_var.set("")
        self._load_teachers()
        self._load_plan_reference_data()
        self._set_status(f"Викладача #{teacher_id} видалено.")

    # Subjects
    def _build_subjects_tab(self, parent: ttk.Frame) -> None:
        content = ttk.Frame(parent, style="Card.TFrame")
        content.pack(fill=tk.BOTH, expand=True)

        list_wrap = ttk.Frame(content, style="Card.TFrame")
        self.subject_listbox = tk.Listbox(
            list_wrap,
            activestyle="none",
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            selectbackground=self.theme.LISTBOX_SELECTED_BG,
            selectforeground=self.theme.TEXT_PRIMARY,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            relief=tk.FLAT,
            font=("Segoe UI", 11),
            exportselection=False,
        )
        self.subject_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 0), pady=2)
        scroll = ttk.Scrollbar(
            list_wrap,
            orient=tk.VERTICAL,
            command=self.subject_listbox.yview,
            style="App.Vertical.TScrollbar",
        )
        scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0), pady=2)
        self.subject_listbox.configure(yscrollcommand=scroll.set)
        self.subject_listbox.bind("<<ListboxSelect>>", lambda _e: self._on_subject_select(), add="+")

        form = ttk.Frame(content, style="Card.TFrame")
        form.grid_columnconfigure(0, weight=1)
        ttk.Label(form, text="Назва предмета", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.subject_name_var).grid(row=1, column=0, sticky="ew", pady=(4, 6))
        ttk.Label(form, text="Код (необов'язково)", style="Card.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.subject_code_var).grid(row=3, column=0, sticky="ew", pady=(4, 6))
        ttk.Label(form, text="Кафедра (необов'язково)", style="Card.TLabel").grid(row=4, column=0, sticky="w")
        self.subject_department_box = ttk.Combobox(form, textvariable=self.subject_department_var, state="readonly")
        self.subject_department_box.grid(row=5, column=0, sticky="ew", pady=(4, 6))

        buttons = ttk.Frame(form, style="Card.TFrame")
        buttons.grid(row=6, column=0, sticky="ew")
        self._grid_action_buttons(
            parent=buttons,
            items=[
                ("Додати", self._add_subject, True),
                ("Змінити", self._update_subject, False),
                ("Видалити", self._delete_subject, False),
                ("Оновити", self._refresh_subjects, False),
            ],
            columns=2,
            width=120,
            height=34,
        )

        self._bind_responsive_split(
            container=content,
            left=list_wrap,
            right=form,
            breakpoint=960,
            wide_left_weight=3,
            wide_right_weight=5,
        )

    def _load_subject_departments(self) -> None:
        with session_scope() as session:
            departments = AcademicController(session=session).list_departments(
                company_id=self.company_id,
                include_archived=False,
            )
        self._department_name_by_id = {item.id: item.name for item in departments}
        values = [""] + [f"{item.id} | {item.name}" for item in departments]
        if self.subject_department_box is not None:
            self.subject_department_box["values"] = values
            if self.subject_department_var.get() not in values:
                self.subject_department_var.set("")

    def _load_subjects(self) -> None:
        if self.subject_listbox is None:
            return
        selected_id = self._selected_listbox_id(self.subject_listbox, self._subject_ids)
        with session_scope() as session:
            subjects = CurriculumController(session=session).list_subjects(
                company_id=self.company_id,
                include_archived=False,
            )
        subjects = sorted(subjects, key=lambda item: item.name.casefold())
        self._subject_ids = [item.id for item in subjects]
        self._subject_name_by_id = {item.id: item.name for item in subjects}
        self.subject_listbox.delete(0, tk.END)
        for item in subjects:
            code = f" [{item.code}]" if item.code else ""
            dept_name = self._department_name_by_id.get(item.department_id)
            dept_suffix = f" — {dept_name}" if dept_name else ""
            self.subject_listbox.insert(tk.END, f"  {item.name}{code}{dept_suffix}")
        if selected_id is not None and selected_id in self._subject_ids:
            idx = self._subject_ids.index(selected_id)
            self.subject_listbox.selection_set(idx)
            self.subject_listbox.see(idx)

    def _on_subject_select(self) -> None:
        subject_id = self._selected_listbox_id(self.subject_listbox, self._subject_ids)
        if subject_id is None:
            return
        with session_scope() as session:
            subject = CurriculumController(session=session).get_subject(subject_id)
        if subject is None:
            return
        self.subject_name_var.set(subject.name)
        self.subject_code_var.set(subject.code or "")
        if subject.department_id is None:
            self.subject_department_var.set("")
        else:
            self.subject_department_var.set(
                f"{subject.department_id} | {self._department_name_by_id.get(subject.department_id, f'Кафедра #{subject.department_id}')}"
            )

    def _add_subject(self) -> None:
        name = self.subject_name_var.get().strip()
        if not name:
            messagebox.showerror("Помилка валідації", "Назва предмета обов'язкова.")
            return
        try:
            with session_scope() as session:
                CurriculumController(session=session).create_subject(
                    name=name,
                    code=self.subject_code_var.get().strip() or None,
                    department_id=self._parse_prefixed_id(self.subject_department_var.get()),
                    company_id=self.company_id,
                )
        except IntegrityError:
            messagebox.showerror("Конфлікт", "Предмет з такою назвою або кодом вже існує.")
            return
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self.subject_name_var.set("")
        self.subject_code_var.set("")
        self.subject_department_var.set("")
        self._refresh_subjects()
        self._set_status(f"Предмет '{name}' створено.")

    def _update_subject(self) -> None:
        subject_id = self._selected_listbox_id(self.subject_listbox, self._subject_ids)
        if subject_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери предмет.")
            return
        name = self.subject_name_var.get().strip()
        if not name:
            messagebox.showerror("Помилка валідації", "Назва предмета обов'язкова.")
            return
        try:
            with session_scope() as session:
                CurriculumController(session=session).update_subject(
                    subject_id,
                    name=name,
                    code=self.subject_code_var.get().strip() or None,
                    department_id=self._parse_prefixed_id(self.subject_department_var.get()),
                )
        except IntegrityError:
            messagebox.showerror("Конфлікт", "Предмет з такою назвою або кодом вже існує.")
            return
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self._refresh_subjects()
        self._set_status(f"Предмет #{subject_id} оновлено.")

    def _delete_subject(self) -> None:
        subject_id = self._selected_listbox_id(self.subject_listbox, self._subject_ids)
        if subject_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери предмет.")
            return
        if not messagebox.askyesno("Видалення предмета", "Видалити вибраний предмет?"):
            return
        try:
            with session_scope() as session:
                deleted = CurriculumController(session=session).delete_subject(subject_id)
                if not deleted:
                    raise ValueError("Предмет не знайдено")
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self.subject_name_var.set("")
        self.subject_code_var.set("")
        self.subject_department_var.set("")
        self._refresh_subjects()
        self._set_status(f"Предмет #{subject_id} видалено.")

    # Plans
    def _build_plans_tab(self, parent: ttk.Frame) -> None:
        content = ttk.Frame(parent, style="Card.TFrame")
        content.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(content, style="Card.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)
        ttk.Label(left, text="Плани", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.plan_listbox = tk.Listbox(
            left,
            activestyle="none",
            bg=self.theme.SURFACE,
            fg=self.theme.TEXT_PRIMARY,
            selectbackground=self.theme.LISTBOX_SELECTED_BG,
            selectforeground=self.theme.TEXT_PRIMARY,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.theme.BORDER,
            relief=tk.FLAT,
            font=("Segoe UI", 11),
            exportselection=False,
        )
        self.plan_listbox.grid(row=1, column=0, sticky="nsew", padx=(2, 0), pady=(4, 6))
        plan_scroll = ttk.Scrollbar(
            left,
            orient=tk.VERTICAL,
            command=self.plan_listbox.yview,
            style="App.Vertical.TScrollbar",
        )
        plan_scroll.grid(row=1, column=1, sticky="ns", padx=(4, 0), pady=(4, 6))
        self.plan_listbox.configure(yscrollcommand=plan_scroll.set)
        self.plan_listbox.bind("<<ListboxSelect>>", lambda _e: self._on_plan_select(), add="+")
        self._motion_button(
            left,
            text="Оновити",
            command=self._load_plans,
            primary=False,
            width=120,
            height=34,
        ).grid(row=2, column=0, sticky="w")

        right_shell = ttk.Frame(content, style="Card.TFrame")
        right_canvas = tk.Canvas(
            right_shell,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scroll = ttk.Scrollbar(
            right_shell,
            orient=tk.VERTICAL,
            command=right_canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        right_canvas.configure(yscrollcommand=right_scroll.set)
        plans_scroll_state = {"visible": False}

        right = ttk.Frame(right_canvas, style="Card.TFrame")
        right_window = right_canvas.create_window((0, 0), anchor="nw", window=right)
        right.grid_columnconfigure(0, weight=1)

        self._build_plan_editor(right)
        self._build_components_editor(right)
        self._build_assignments_editor(right)

        def _sync_plans_scroll(_event=None) -> None:
            viewport_width = max(1, right_canvas.winfo_width())
            right_canvas.itemconfigure(right_window, width=viewport_width)
            requested_height = max(1, right.winfo_reqheight())
            viewport_height = max(1, right_canvas.winfo_height())
            needs_scroll = requested_height > (viewport_height + 1)

            if needs_scroll and not plans_scroll_state["visible"]:
                right_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 0), pady=2)
                plans_scroll_state["visible"] = True
                right_canvas.after_idle(_sync_plans_scroll)
            elif (not needs_scroll) and plans_scroll_state["visible"]:
                right_scroll.pack_forget()
                plans_scroll_state["visible"] = False
                right_canvas.yview_moveto(0.0)
                right_canvas.after_idle(_sync_plans_scroll)

            bbox = right_canvas.bbox("all")
            if bbox is not None:
                right_canvas.configure(scrollregion=bbox)

        def _create_smooth_wheel_handlers(get_view, set_view, *, gain: float = 0.15):
            state: dict[str, float] = {"velocity": 0.0}

            def _wheel_step(step_units: float) -> str:
                first, last = get_view()
                first_f = float(first)
                last_f = float(last)
                visible = max(0.0001, last_f - first_f)
                if visible >= 0.999:
                    return "break"

                smoothed_units = state["velocity"] * 0.35 + max(-4.0, min(4.0, step_units)) * 0.65
                if abs(smoothed_units) < 0.01:
                    smoothed_units = step_units
                state["velocity"] = smoothed_units

                max_first = max(0.0, 1.0 - visible)
                next_first = max(0.0, min(first_f + smoothed_units * visible * gain, max_first))
                if abs(next_first - first_f) < 0.00001:
                    return "break"
                set_view(next_first)
                return "break"

            def _on_wheel(event: tk.Event) -> str:
                delta = float(getattr(event, "delta", 0.0))
                if delta == 0:
                    return "break"
                return _wheel_step(-delta / 120.0)

            def _on_button4(_event: tk.Event) -> str:
                return _wheel_step(-1.0)

            def _on_button5(_event: tk.Event) -> str:
                return _wheel_step(1.0)

            return _on_wheel, _on_button4, _on_button5

        _on_plans_wheel, _on_plans_up, _on_plans_down = _create_smooth_wheel_handlers(
            right_canvas.yview,
            right_canvas.yview_moveto,
            gain=0.15,
        )

        def _bind_plans_wheel_recursive(widget: tk.Widget) -> None:
            if not isinstance(widget, (ttk.Treeview, tk.Listbox, tk.Canvas)):
                widget.bind("<MouseWheel>", _on_plans_wheel, add="+")
                widget.bind("<Button-4>", _on_plans_up, add="+")
                widget.bind("<Button-5>", _on_plans_down, add="+")
            for child in widget.winfo_children():
                _bind_plans_wheel_recursive(child)

        right.bind("<Configure>", _sync_plans_scroll, add="+")
        right_canvas.bind("<Configure>", _sync_plans_scroll, add="+")
        right_canvas.bind("<MouseWheel>", _on_plans_wheel, add="+")
        right_canvas.bind("<Button-4>", _on_plans_up, add="+")
        right_canvas.bind("<Button-5>", _on_plans_down, add="+")
        _bind_plans_wheel_recursive(right)
        right.after_idle(_sync_plans_scroll)

        self._bind_responsive_split(
            container=content,
            left=left,
            right=right_shell,
            breakpoint=980,
            wide_left_weight=2,
            wide_right_weight=5,
            stacked_top_weight=1,
            stacked_bottom_weight=1,
        )

    def _build_plan_editor(self, parent: ttk.Frame) -> None:
        plan_editor = ttk.Frame(parent, style="Card.TFrame")
        plan_editor.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        plan_editor.grid_columnconfigure(0, weight=1)
        plan_editor.grid_columnconfigure(1, weight=1)
        plan_editor.grid_columnconfigure(2, weight=1)

        ttk.Label(plan_editor, text="Параметри плану", style="Card.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        ttk.Label(plan_editor, text="Назва").grid(row=1, column=0, sticky="w")
        ttk.Entry(plan_editor, textvariable=self.plan_name_var).grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
        ttk.Label(plan_editor, text="Семестр").grid(row=1, column=1, sticky="w")
        ttk.Entry(plan_editor, textvariable=self.plan_semester_var).grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))

        ttk.Label(plan_editor, text="Потік").grid(row=1, column=2, sticky="w")
        self.plan_stream_box = ttk.Combobox(plan_editor, textvariable=self.plan_stream_var, state="readonly")
        self.plan_stream_box.grid(row=2, column=2, sticky="ew", pady=(2, 4))

        ttk.Label(plan_editor, text="Спеціальність").grid(row=3, column=0, sticky="w")
        self.plan_specialty_box = ttk.Combobox(plan_editor, textvariable=self.plan_specialty_var, state="readonly")
        self.plan_specialty_box.grid(row=4, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
        ttk.Label(plan_editor, text="Курс").grid(row=3, column=1, sticky="w")
        self.plan_course_box = ttk.Combobox(plan_editor, textvariable=self.plan_course_var, state="readonly")
        self.plan_course_box.grid(row=4, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))

        buttons = ttk.Frame(plan_editor, style="Card.TFrame")
        buttons.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(2, 0))
        self._grid_action_buttons(
            parent=buttons,
            items=[
                ("Створити", self._create_plan, True),
                ("Змінити", self._update_plan, False),
                ("Видалити", self._delete_plan, False),
                ("Синхр. план", self._sync_plan, False),
            ],
            columns=2,
            width=118,
            height=34,
        )

    def _build_components_editor(self, parent: ttk.Frame) -> None:
        components = ttk.Frame(parent, style="Card.TFrame")
        components.grid(row=1, column=0, sticky="nsew", pady=(0, 6))
        components.grid_columnconfigure(0, weight=1)
        components.grid_rowconfigure(1, weight=1)

        ttk.Label(components, text="Компоненти", style="Card.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.component_tree = ttk.Treeview(
            components,
            columns=("id", "subject", "type", "duration", "sessions", "max"),
            show="headings",
            height=7,
        )
        for cid, title, width in (
            ("id", "ID", 46),
            ("subject", "Предмет", 170),
            ("type", "Тип", 90),
            ("duration", "Трив.", 56),
            ("sessions", "Занять", 70),
            ("max", "Макс/тиж", 70),
        ):
            self.component_tree.heading(cid, text=title)
            self.component_tree.column(cid, width=width, anchor="center")
        self.component_tree.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(components, orient=tk.VERTICAL, command=self.component_tree.yview, style="App.Vertical.TScrollbar")
        scroll.grid(row=1, column=1, sticky="ns")
        self.component_tree.configure(yscrollcommand=scroll.set)
        self.component_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_component_select(), add="+")

        form = ttk.Frame(components, style="Card.TFrame")
        form.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(2, weight=1)

        ttk.Label(form, text="Предмет").grid(row=0, column=0, sticky="w")
        ttk.Label(form, text="Тип").grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Тривалість").grid(row=0, column=2, sticky="w")

        self.component_subject_box = ttk.Combobox(form, textvariable=self.component_subject_var, state="readonly")
        self.component_subject_box.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
        ttk.Combobox(
            form,
            textvariable=self.component_type_var,
            values=[item.value for item in PlanComponentType],
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))
        ttk.Entry(form, textvariable=self.component_duration_var).grid(row=1, column=2, sticky="ew", pady=(2, 4))

        ttk.Label(form, text="Занять").grid(row=2, column=0, sticky="w")
        ttk.Label(form, text="Макс/тижд").grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="Нотатки").grid(row=2, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.component_sessions_var).grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
        ttk.Entry(form, textvariable=self.component_max_per_week_var).grid(row=3, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))
        ttk.Entry(form, textvariable=self.component_notes_var).grid(row=3, column=2, sticky="ew", pady=(2, 4))

        buttons = ttk.Frame(form, style="Card.TFrame")
        buttons.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(2, 0))
        self._grid_action_buttons(
            parent=buttons,
            items=[
                ("Додати", self._create_component, True),
                ("Змінити", self._update_component, False),
                ("Видалити", self._delete_component, False),
            ],
            columns=3,
            width=108,
            height=32,
        )

    def _build_assignments_editor(self, parent: ttk.Frame) -> None:
        assignments = ttk.Frame(parent, style="Card.TFrame")
        assignments.grid(row=2, column=0, sticky="nsew")
        assignments.grid_columnconfigure(0, weight=1)
        assignments.grid_rowconfigure(1, weight=1)

        ttk.Label(assignments, text="Призначення", style="Card.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.assignment_tree = ttk.Treeview(
            assignments,
            columns=("id", "teacher", "target", "sessions", "max", "req"),
            show="headings",
            height=7,
        )
        for cid, title, width in (
            ("id", "ID", 46),
            ("teacher", "Викладач", 150),
            ("target", "Ціль", 180),
            ("sessions", "Занять", 70),
            ("max", "Макс/тиж", 70),
            ("req", "Вим.", 60),
        ):
            self.assignment_tree.heading(cid, text=title)
            self.assignment_tree.column(cid, width=width, anchor="center")
        self.assignment_tree.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(assignments, orient=tk.VERTICAL, command=self.assignment_tree.yview, style="App.Vertical.TScrollbar")
        scroll.grid(row=1, column=1, sticky="ns")
        self.assignment_tree.configure(yscrollcommand=scroll.set)
        self.assignment_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_assignment_select(), add="+")

        form = ttk.Frame(assignments, style="Card.TFrame")
        form.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)
        form.grid_columnconfigure(2, weight=1)

        ttk.Label(form, text="Викладач").grid(row=0, column=0, sticky="w")
        ttk.Label(form, text="Тип цілі").grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Потік").grid(row=0, column=2, sticky="w")

        self.assignment_teacher_box = ttk.Combobox(form, textvariable=self.assignment_teacher_var, state="readonly")
        self.assignment_teacher_box.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
        self.assignment_target_type_box = ttk.Combobox(
            form,
            textvariable=self.assignment_target_type_var,
            values=[item.value for item in PlanTargetType],
            state="readonly",
        )
        self.assignment_target_type_box.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))
        self.assignment_target_type_box.bind("<<ComboboxSelected>>", lambda _e: self._refresh_assignment_target_controls(), add="+")
        self.assignment_stream_box = ttk.Combobox(form, textvariable=self.assignment_stream_var, state="readonly")
        self.assignment_stream_box.grid(row=1, column=2, sticky="ew", pady=(2, 4))

        ttk.Label(form, text="Група").grid(row=2, column=0, sticky="w")
        ttk.Label(form, text="Підгрупа").grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="Занять (порожньо = авто)").grid(row=2, column=2, sticky="w")

        self.assignment_group_box = ttk.Combobox(form, textvariable=self.assignment_group_var, state="readonly")
        self.assignment_group_box.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
        self.assignment_subgroup_box = ttk.Combobox(form, textvariable=self.assignment_subgroup_var, state="readonly")
        self.assignment_subgroup_box.grid(row=3, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))
        ttk.Entry(form, textvariable=self.assignment_sessions_var).grid(row=3, column=2, sticky="ew", pady=(2, 4))

        ttk.Label(form, text="Макс/тиж (порожньо = авто)").grid(row=4, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.assignment_max_per_week_var).grid(row=5, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))

        buttons = ttk.Frame(form, style="Card.TFrame")
        buttons.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(2, 0))
        self._grid_action_buttons(
            parent=buttons,
            items=[
                ("Додати", self._create_assignment, True),
                ("Змінити", self._update_assignment, False),
                ("Видалити", self._delete_assignment, False),
                ("Синхр.", self._sync_assignment, False),
            ],
            columns=2,
            width=108,
            height=32,
        )

    def _load_plan_reference_data(self) -> None:
        with session_scope() as session:
            academic = AcademicController(session=session)
            resources = ResourceController(session=session)
            curriculum = CurriculumController(session=session)

            specialties = academic.list_specialties(company_id=self.company_id, include_archived=False)
            courses = academic.list_courses(company_id=self.company_id, include_archived=False)
            streams = academic.list_streams(company_id=self.company_id, include_archived=False)
            teachers = resources.list_resources(resource_type=ResourceType.TEACHER, company_id=self.company_id)
            groups = resources.list_resources(resource_type=ResourceType.GROUP, company_id=self.company_id)
            subgroups = resources.list_resources(resource_type=ResourceType.SUBGROUP, company_id=self.company_id)
            subjects = curriculum.list_subjects(company_id=self.company_id, include_archived=False)

        self._subject_name_by_id = {item.id: item.name for item in subjects}
        self._teacher_name_by_id = {item.id: item.name for item in teachers}
        self._stream_name_by_id = {item.id: item.name for item in streams}
        self._group_name_by_id = {item.id: item.name for item in groups}
        self._subgroup_name_by_id = {item.id: item.name for item in subgroups}

        specialty_values = [""] + [f"{item.id} | {item.name}" for item in specialties]
        course_values = [""] + [f"{item.id} | {item.name}" for item in courses]
        stream_values = [""] + [f"{item.id} | {item.name}" for item in streams]
        teacher_values = [f"{item.id} | {item.name}" for item in teachers]
        subject_values = [f"{item.id} | {item.name}" for item in subjects]
        group_values = [""] + [f"{item.id} | {item.name}" for item in groups]
        subgroup_values = [""] + [f"{item.id} | {item.name}" for item in subgroups]

        self._set_combobox_values(self.plan_specialty_box, self.plan_specialty_var, specialty_values)
        self._set_combobox_values(self.plan_course_box, self.plan_course_var, course_values)
        self._set_combobox_values(self.plan_stream_box, self.plan_stream_var, stream_values)
        self._set_combobox_values(self.component_subject_box, self.component_subject_var, subject_values, allow_empty=False)
        self._set_combobox_values(self.assignment_teacher_box, self.assignment_teacher_var, teacher_values, allow_empty=False)
        self._set_combobox_values(self.assignment_stream_box, self.assignment_stream_var, stream_values)
        self._set_combobox_values(self.assignment_group_box, self.assignment_group_var, group_values)
        self._set_combobox_values(self.assignment_subgroup_box, self.assignment_subgroup_var, subgroup_values)

    def _load_plans(self) -> None:
        if self.plan_listbox is None:
            return
        selected_id = self._selected_listbox_id(self.plan_listbox, self._plan_ids)
        with session_scope() as session:
            plans = CurriculumController(session=session).list_plans(
                company_id=self.company_id,
                include_archived=False,
            )
        plans = sorted(plans, key=lambda item: item.name.casefold())

        self._plan_ids = [item.id for item in plans]
        self.plan_listbox.delete(0, tk.END)
        for item in plans:
            sem_suffix = f" (семестр {item.semester})" if item.semester is not None else ""
            self.plan_listbox.insert(tk.END, f"  {item.name}{sem_suffix}")

        if selected_id is not None and selected_id in self._plan_ids:
            idx = self._plan_ids.index(selected_id)
            self.plan_listbox.selection_set(idx)
            self.plan_listbox.see(idx)
            self._on_plan_select()
        else:
            self._selected_plan_id = None
            self._load_components(None)

    def _on_plan_select(self) -> None:
        plan_id = self._selected_listbox_id(self.plan_listbox, self._plan_ids)
        self._selected_plan_id = plan_id
        self._selected_component_id = None
        self._selected_assignment_id = None
        if plan_id is None:
            self._load_components(None)
            return
        with session_scope() as session:
            plan = CurriculumController(session=session).get_plan(plan_id)
        if plan is None:
            self._load_components(None)
            return

        self.plan_name_var.set(plan.name)
        self.plan_semester_var.set("" if plan.semester is None else str(plan.semester))
        self.plan_specialty_var.set(self._format_optional_ref(plan.specialty_id, "specialty"))
        self.plan_course_var.set(self._format_optional_ref(plan.course_id, "course"))
        self.plan_stream_var.set(
            "" if plan.stream_id is None else f"{plan.stream_id} | {self._stream_name_by_id.get(plan.stream_id, f'Потік #{plan.stream_id}')}"
        )
        self._load_components(plan_id)

    def _format_optional_ref(self, value: int | None, kind: str) -> str:
        if value is None:
            return ""
        with session_scope() as session:
            academic = AcademicController(session=session)
            if kind == "specialty":
                item = academic.get_specialty(value)
            elif kind == "course":
                item = academic.get_course(value)
            else:
                item = None
        label = item.name if item is not None else f"{kind.capitalize()} #{value}"
        return f"{value} | {label}"

    def _create_plan(self) -> None:
        name = self.plan_name_var.get().strip()
        if not name:
            messagebox.showerror("Помилка валідації", "Назва плану обов'язкова.")
            return
        try:
            semester = self._parse_optional_positive_int(self.plan_semester_var.get())
            with session_scope() as session:
                CurriculumController(session=session).create_plan(
                    name=name,
                    company_id=self.company_id,
                    specialty_id=self._parse_prefixed_id(self.plan_specialty_var.get()),
                    course_id=self._parse_prefixed_id(self.plan_course_var.get()),
                    stream_id=self._parse_prefixed_id(self.plan_stream_var.get()),
                    semester=semester,
                )
        except IntegrityError:
            messagebox.showerror("Конфлікт", "План з такою назвою вже існує.")
            return
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self._load_plans()
        self._set_status(f"План '{name}' створено.")

    def _update_plan(self) -> None:
        if self._selected_plan_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери план.")
            return
        name = self.plan_name_var.get().strip()
        if not name:
            messagebox.showerror("Помилка валідації", "Назва плану обов'язкова.")
            return
        try:
            semester = self._parse_optional_positive_int(self.plan_semester_var.get())
            with session_scope() as session:
                CurriculumController(session=session).update_plan(
                    self._selected_plan_id,
                    name=name,
                    specialty_id=self._parse_prefixed_id(self.plan_specialty_var.get()),
                    course_id=self._parse_prefixed_id(self.plan_course_var.get()),
                    stream_id=self._parse_prefixed_id(self.plan_stream_var.get()),
                    semester=semester,
                )
        except IntegrityError:
            messagebox.showerror("Конфлікт", "План з такою назвою вже існує.")
            return
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self._load_plans()
        self._set_status(f"План #{self._selected_plan_id} оновлено.")

    def _delete_plan(self) -> None:
        if self._selected_plan_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери план.")
            return
        if not messagebox.askyesno("Видалення плану", "Видалити вибраний план разом з компонентами та призначеннями?"):
            return
        plan_id = self._selected_plan_id
        try:
            with session_scope() as session:
                CurriculumController(session=session).delete_plan(plan_id, delete_requirements=True)
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self._selected_plan_id = None
        self._selected_component_id = None
        self._selected_assignment_id = None
        self._load_plans()
        self._set_status(f"План #{plan_id} видалено.")

    def _sync_plan(self) -> None:
        if self._selected_plan_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери план.")
            return
        try:
            with session_scope() as session:
                synced = CurriculumController(session=session).sync_plan_requirements(self._selected_plan_id)
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self._load_assignments(self._selected_component_id)
        self._set_status(f"Синхронізовано {len(synced)} призначень для плану #{self._selected_plan_id}.")

    def _load_components(self, plan_id: int | None) -> None:
        if self.component_tree is None:
            return
        self._component_ids_by_iid.clear()
        for iid in self.component_tree.get_children():
            self.component_tree.delete(iid)
        self._selected_component_id = None
        self._selected_assignment_id = None
        if plan_id is None:
            self._load_assignments(None)
            return
        with session_scope() as session:
            components = CurriculumController(session=session).list_components(plan_id=plan_id)
        for item in components:
            iid = self.component_tree.insert(
                "",
                tk.END,
                values=(
                    item.id,
                    self._subject_name_by_id.get(item.subject_id, f"Предмет #{item.subject_id}"),
                    item.component_type.value,
                    item.duration_blocks,
                    item.sessions_total,
                    item.max_per_week,
                ),
            )
            self._component_ids_by_iid[iid] = item.id
        self._load_assignments(None)

    def _on_component_select(self) -> None:
        if self.component_tree is None:
            return
        selected = self.component_tree.selection()
        if not selected:
            self._selected_component_id = None
            self._load_assignments(None)
            return
        component_id = self._component_ids_by_iid.get(selected[0])
        self._selected_component_id = component_id
        self._selected_assignment_id = None
        if component_id is None:
            self._load_assignments(None)
            return
        with session_scope() as session:
            component = CurriculumController(session=session).get_component(component_id)
        if component is None:
            self._load_assignments(None)
            return
        self.component_subject_var.set(
            f"{component.subject_id} | {self._subject_name_by_id.get(component.subject_id, f'Предмет #{component.subject_id}')}"
        )
        self.component_type_var.set(component.component_type.value)
        self.component_duration_var.set(str(component.duration_blocks))
        self.component_sessions_var.set(str(component.sessions_total))
        self.component_max_per_week_var.set(str(component.max_per_week))
        self.component_notes_var.set(component.notes or "")
        self._load_assignments(component_id)

    def _create_component(self) -> None:
        if self._selected_plan_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери план.")
            return
        subject_id = self._parse_prefixed_id(self.component_subject_var.get())
        if subject_id is None:
            messagebox.showerror("Помилка валідації", "Вибери предмет.")
            return
        try:
            with session_scope() as session:
                CurriculumController(session=session).create_component(
                    plan_id=self._selected_plan_id,
                    subject_id=subject_id,
                    component_type=PlanComponentType(self.component_type_var.get().strip().upper()),
                    duration_blocks=int(self.component_duration_var.get().strip()),
                    sessions_total=int(self.component_sessions_var.get().strip()),
                    max_per_week=int(self.component_max_per_week_var.get().strip()),
                    notes=self.component_notes_var.get().strip() or None,
                )
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self._load_components(self._selected_plan_id)
        self._set_status(f"Компонент додано до плану #{self._selected_plan_id}.")

    def _update_component(self) -> None:
        if self._selected_component_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери компонент.")
            return
        subject_id = self._parse_prefixed_id(self.component_subject_var.get())
        if subject_id is None:
            messagebox.showerror("Помилка валідації", "Вибери предмет.")
            return
        try:
            with session_scope() as session:
                CurriculumController(session=session).update_component(
                    self._selected_component_id,
                    subject_id=subject_id,
                    component_type=PlanComponentType(self.component_type_var.get().strip().upper()),
                    duration_blocks=int(self.component_duration_var.get().strip()),
                    sessions_total=int(self.component_sessions_var.get().strip()),
                    max_per_week=int(self.component_max_per_week_var.get().strip()),
                    notes=self.component_notes_var.get().strip() or None,
                )
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        if self._selected_plan_id is not None:
            self._load_components(self._selected_plan_id)
        self._set_status(f"Компонент #{self._selected_component_id} оновлено.")

    def _delete_component(self) -> None:
        if self._selected_component_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери компонент.")
            return
        if not messagebox.askyesno("Видалення компонента", "Видалити вибраний компонент і всі призначення?"):
            return
        component_id = self._selected_component_id
        try:
            with session_scope() as session:
                CurriculumController(session=session).delete_component(component_id, delete_requirements=True)
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        if self._selected_plan_id is not None:
            self._load_components(self._selected_plan_id)
        self._set_status(f"Компонент #{component_id} видалено.")

    def _load_assignments(self, component_id: int | None) -> None:
        if self.assignment_tree is None:
            return
        self._assignment_ids_by_iid.clear()
        for iid in self.assignment_tree.get_children():
            self.assignment_tree.delete(iid)
        self._selected_assignment_id = None
        if component_id is None:
            return
        with session_scope() as session:
            assignments = CurriculumController(session=session).list_assignments(component_id=component_id)
        for item in assignments:
            iid = self.assignment_tree.insert(
                "",
                tk.END,
                values=(
                    item.id,
                    self._teacher_name_by_id.get(item.teacher_resource_id, f"Викладач #{item.teacher_resource_id}"),
                    self._target_display(item.target_type, item.stream_id, item.target_resource_id),
                    item.sessions_total,
                    item.max_per_week,
                    item.requirement_id or "",
                ),
            )
            self._assignment_ids_by_iid[iid] = item.id

    def _target_display(self, target_type: PlanTargetType, stream_id: int | None, target_resource_id: int | None) -> str:
        if target_type == PlanTargetType.STREAM:
            return f"ПОТІК: {self._stream_name_by_id.get(stream_id or 0, f'#{stream_id}')}"
        if target_type == PlanTargetType.GROUP:
            return f"ГРУПА: {self._group_name_by_id.get(target_resource_id or 0, f'#{target_resource_id}')}"
        return f"ПІДГРУПА: {self._subgroup_name_by_id.get(target_resource_id or 0, f'#{target_resource_id}')}"

    def _on_assignment_select(self) -> None:
        if self.assignment_tree is None:
            return
        selected = self.assignment_tree.selection()
        if not selected:
            self._selected_assignment_id = None
            return
        assignment_id = self._assignment_ids_by_iid.get(selected[0])
        self._selected_assignment_id = assignment_id
        if assignment_id is None:
            return
        with session_scope() as session:
            assignment = CurriculumController(session=session).get_assignment(assignment_id)
        if assignment is None:
            return
        self.assignment_teacher_var.set(
            f"{assignment.teacher_resource_id} | {self._teacher_name_by_id.get(assignment.teacher_resource_id, f'Викладач #{assignment.teacher_resource_id}')}"
        )
        self.assignment_target_type_var.set(assignment.target_type.value)
        self.assignment_stream_var.set("")
        self.assignment_group_var.set("")
        self.assignment_subgroup_var.set("")
        if assignment.stream_id is not None:
            self.assignment_stream_var.set(
                f"{assignment.stream_id} | {self._stream_name_by_id.get(assignment.stream_id, f'Потік #{assignment.stream_id}')}"
            )
        if assignment.target_type == PlanTargetType.GROUP and assignment.target_resource_id is not None:
            self.assignment_group_var.set(
                f"{assignment.target_resource_id} | {self._group_name_by_id.get(assignment.target_resource_id, f'Група #{assignment.target_resource_id}')}"
            )
        if assignment.target_type == PlanTargetType.SUBGROUP and assignment.target_resource_id is not None:
            self.assignment_subgroup_var.set(
                f"{assignment.target_resource_id} | {self._subgroup_name_by_id.get(assignment.target_resource_id, f'Підгрупа #{assignment.target_resource_id}')}"
            )
        self.assignment_sessions_var.set(str(assignment.sessions_total))
        self.assignment_max_per_week_var.set(str(assignment.max_per_week))
        self._refresh_assignment_target_controls()

    def _refresh_assignment_target_controls(self) -> None:
        raw = self.assignment_target_type_var.get().strip().upper()
        try:
            target_type = PlanTargetType(raw)
        except ValueError:
            target_type = PlanTargetType.STREAM
            self.assignment_target_type_var.set(target_type.value)
        if self.assignment_stream_box is not None:
            self.assignment_stream_box.configure(state="readonly" if target_type == PlanTargetType.STREAM else "disabled")
        if self.assignment_group_box is not None:
            self.assignment_group_box.configure(state="readonly" if target_type == PlanTargetType.GROUP else "disabled")
        if self.assignment_subgroup_box is not None:
            self.assignment_subgroup_box.configure(state="readonly" if target_type == PlanTargetType.SUBGROUP else "disabled")

    def _resolve_target_ids(self, target_type: PlanTargetType) -> tuple[int | None, int | None]:
        if target_type == PlanTargetType.STREAM:
            stream_id = self._parse_prefixed_id(self.assignment_stream_var.get())
            if stream_id is None:
                raise ValueError("Вибери потік для цілі.")
            return stream_id, None
        if target_type == PlanTargetType.GROUP:
            target_id = self._parse_prefixed_id(self.assignment_group_var.get())
            if target_id is None:
                raise ValueError("Вибери групу для цілі.")
            return None, target_id
        target_id = self._parse_prefixed_id(self.assignment_subgroup_var.get())
        if target_id is None:
            raise ValueError("Вибери підгрупу для цілі.")
        return None, target_id

    def _create_assignment(self) -> None:
        if self._selected_component_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери компонент.")
            return
        teacher_id = self._parse_prefixed_id(self.assignment_teacher_var.get())
        if teacher_id is None:
            messagebox.showerror("Помилка валідації", "Вибери викладача.")
            return
        try:
            target_type = PlanTargetType(self.assignment_target_type_var.get().strip().upper())
            stream_id, target_resource_id = self._resolve_target_ids(target_type)
            with session_scope() as session:
                controller = CurriculumController(session=session)
                assignment = controller.create_assignment(
                    component_id=self._selected_component_id,
                    teacher_resource_id=teacher_id,
                    target_type=target_type,
                    target_resource_id=target_resource_id,
                    stream_id=stream_id,
                    sessions_total=self._parse_optional_positive_int(self.assignment_sessions_var.get()),
                    max_per_week=self._parse_optional_positive_int(self.assignment_max_per_week_var.get()),
                )
                controller.sync_assignment_requirement(assignment.id)
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        self._load_assignments(self._selected_component_id)
        self._set_status("Призначення додано і синхронізовано.")

    def _update_assignment(self) -> None:
        if self._selected_assignment_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери призначення.")
            return
        teacher_id = self._parse_prefixed_id(self.assignment_teacher_var.get())
        if teacher_id is None:
            messagebox.showerror("Помилка валідації", "Вибери викладача.")
            return
        try:
            target_type = PlanTargetType(self.assignment_target_type_var.get().strip().upper())
            stream_id, target_resource_id = self._resolve_target_ids(target_type)
            with session_scope() as session:
                controller = CurriculumController(session=session)
                controller.update_assignment(
                    self._selected_assignment_id,
                    teacher_resource_id=teacher_id,
                    target_type=target_type,
                    target_resource_id=target_resource_id,
                    stream_id=stream_id,
                    sessions_total=self._parse_optional_positive_int(self.assignment_sessions_var.get()),
                    max_per_week=self._parse_optional_positive_int(self.assignment_max_per_week_var.get()),
                )
                controller.sync_assignment_requirement(self._selected_assignment_id)
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        if self._selected_component_id is not None:
            self._load_assignments(self._selected_component_id)
        self._set_status("Призначення оновлено і синхронізовано.")

    def _delete_assignment(self) -> None:
        if self._selected_assignment_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери призначення.")
            return
        if not messagebox.askyesno("Видалення призначення", "Видалити вибране призначення?"):
            return
        assignment_id = self._selected_assignment_id
        try:
            with session_scope() as session:
                CurriculumController(session=session).delete_assignment(assignment_id, delete_requirement=True)
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        if self._selected_component_id is not None:
            self._load_assignments(self._selected_component_id)
        self._set_status(f"Призначення #{assignment_id} видалено.")

    def _sync_assignment(self) -> None:
        if self._selected_assignment_id is None:
            messagebox.showerror("Помилка валідації", "Спочатку вибери призначення.")
            return
        assignment_id = self._selected_assignment_id
        try:
            with session_scope() as session:
                CurriculumController(session=session).sync_assignment_requirement(assignment_id)
        except Exception as exc:
            messagebox.showerror("Помилка", str(exc))
            return
        if self._selected_component_id is not None:
            self._load_assignments(self._selected_component_id)
        self._set_status(f"Призначення #{assignment_id} синхронізовано.")
