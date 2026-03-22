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


from app.ui.curriculum_tab_methods import ensure_curriculum_tab_method_impls

ensure_curriculum_tab_method_impls(globals())

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

    def _setup_autohide_scrollbar(
        self,
        *,
        listbox: tk.Listbox,
        scrollbar: ttk.Scrollbar,
        manager: str,
        layout_kwargs: dict[str, object],
    ) -> None:
        state = {"visible": False}

        def _show() -> None:
            if state["visible"]:
                return
            if manager == "pack":
                scrollbar.pack(**layout_kwargs)
            else:
                scrollbar.grid(**layout_kwargs)
            state["visible"] = True

        def _hide() -> None:
            if not state["visible"]:
                return
            if manager == "pack":
                scrollbar.pack_forget()
            else:
                scrollbar.grid_remove()
            state["visible"] = False

        def _sync(first: str, last: str) -> None:
            scrollbar.set(first, last)
            try:
                needs_scroll = (float(last) - float(first)) < 0.999
            except ValueError:
                needs_scroll = True
            if needs_scroll:
                _show()
            else:
                _hide()

        def _refresh(_event=None) -> None:
            first, last = listbox.yview()
            _sync(str(first), str(last))

        listbox.configure(yscrollcommand=_sync)
        listbox.bind("<Configure>", _refresh, add="+")
        listbox.after_idle(_refresh)

    def _setup_autohide_tree_scrollbar(
        self,
        *,
        tree: ttk.Treeview,
        scrollbar: ttk.Scrollbar,
        layout_kwargs: dict[str, object],
    ) -> None:
        state = {"visible": False}

        def _show() -> None:
            if state["visible"]:
                return
            scrollbar.grid(**layout_kwargs)
            state["visible"] = True

        def _hide() -> None:
            if not state["visible"]:
                return
            scrollbar.grid_remove()
            state["visible"] = False

        def _sync(first: str, last: str) -> None:
            scrollbar.set(first, last)
            try:
                needs_scroll = (float(last) - float(first)) < 0.999
            except ValueError:
                needs_scroll = True
            if needs_scroll:
                _show()
            else:
                _hide()

        def _refresh(_event=None) -> None:
            first, last = tree.yview()
            _sync(str(first), str(last))

        tree.configure(yscrollcommand=_sync)
        tree.bind("<Configure>", _refresh, add="+")
        tree.bind("<<TreeviewOpen>>", _refresh, add="+")
        tree.bind("<<TreeviewClose>>", _refresh, add="+")
        tree.after_idle(_refresh)

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
        self._setup_autohide_scrollbar(
            listbox=self.teacher_listbox,
            scrollbar=scroll,
            manager="pack",
            layout_kwargs={"side": tk.RIGHT, "fill": tk.Y, "padx": (4, 0), "pady": 2},
        )
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
        self._setup_autohide_scrollbar(
            listbox=self.subject_listbox,
            scrollbar=scroll,
            manager="pack",
            layout_kwargs={"side": tk.RIGHT, "fill": tk.Y, "padx": (4, 0), "pady": 2},
        )
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
    def _build_plans_tab(self, *args, **kwargs):
        return _build_plans_tab__impl(self, *args, **kwargs)


    def _build_plan_editor(self, *args, **kwargs):
        return _build_plan_editor__impl(self, *args, **kwargs)


    def _build_components_editor(self, *args, **kwargs):
        return _build_components_editor__impl(self, *args, **kwargs)


    def _build_assignments_editor(self, *args, **kwargs):
        return _build_assignments_editor__impl(self, *args, **kwargs)


    def _load_plan_reference_data(self, *args, **kwargs):
        return _load_plan_reference_data__impl(self, *args, **kwargs)


    def _load_plans(self, *args, **kwargs):
        return _load_plans__impl(self, *args, **kwargs)


    def _on_plan_select(self, *args, **kwargs):
        return _on_plan_select__impl(self, *args, **kwargs)


    def _format_optional_ref(self, *args, **kwargs):
        return _format_optional_ref__impl(self, *args, **kwargs)


    def _create_plan(self, *args, **kwargs):
        return _create_plan__impl(self, *args, **kwargs)


    def _update_plan(self, *args, **kwargs):
        return _update_plan__impl(self, *args, **kwargs)


    def _delete_plan(self, *args, **kwargs):
        return _delete_plan__impl(self, *args, **kwargs)


    def _sync_plan(self, *args, **kwargs):
        return _sync_plan__impl(self, *args, **kwargs)


    def _load_components(self, *args, **kwargs):
        return _load_components__impl(self, *args, **kwargs)


    def _on_component_select(self, *args, **kwargs):
        return _on_component_select__impl(self, *args, **kwargs)


    def _create_component(self, *args, **kwargs):
        return _create_component__impl(self, *args, **kwargs)


    def _update_component(self, *args, **kwargs):
        return _update_component__impl(self, *args, **kwargs)


    def _delete_component(self, *args, **kwargs):
        return _delete_component__impl(self, *args, **kwargs)


    def _load_assignments(self, *args, **kwargs):
        return _load_assignments__impl(self, *args, **kwargs)


    def _target_display(self, *args, **kwargs):
        return _target_display__impl(self, *args, **kwargs)


    def _on_assignment_select(self, *args, **kwargs):
        return _on_assignment_select__impl(self, *args, **kwargs)


    def _refresh_assignment_target_controls(self, *args, **kwargs):
        return _refresh_assignment_target_controls__impl(self, *args, **kwargs)


    def _resolve_target_ids(self, *args, **kwargs):
        return _resolve_target_ids__impl(self, *args, **kwargs)


    def _create_assignment(self, *args, **kwargs):
        return _create_assignment__impl(self, *args, **kwargs)


    def _update_assignment(self, *args, **kwargs):
        return _update_assignment__impl(self, *args, **kwargs)


    def _delete_assignment(self, *args, **kwargs):
        return _delete_assignment__impl(self, *args, **kwargs)


    def _sync_assignment(self, *args, **kwargs):
        return _sync_assignment__impl(self, *args, **kwargs)

