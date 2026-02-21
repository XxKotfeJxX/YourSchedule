from __future__ import annotations

from datetime import date, timedelta
import tkinter as tk
from tkinter import messagebox, ttk
from uuid import uuid4

from app.config.database import session_scope
from app.controllers.auth_controller import AuthController
from app.controllers.calendar_controller import CalendarController
from app.controllers.requirement_controller import RequirementController
from app.controllers.resource_controller import ResourceController
from app.controllers.schedule_validation_controller import ScheduleValidationController
from app.controllers.schedule_view_controller import ScheduleViewController
from app.controllers.scheduler_controller import SchedulerController
from app.domain.enums import MarkKind, ResourceType, UserRole
from app.domain.models import User
from app.repositories.calendar_repository import CalendarRepository
from app.services.schedule_visualization import WEEKDAY_LABELS


class ScheduleMainWindow:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Розклад")
        self.root.geometry("1260x760")
        self.root.minsize(1060, 680)

        self.current_user: User | None = None

        self._show_start_screen()

    def run(self) -> None:
        self.root.mainloop()

    def _clear_root(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def _show_start_screen(self) -> None:
        with session_scope() as session:
            has_company = AuthController(session=session).has_company_account()

        if has_company:
            self._show_login_screen()
        else:
            self._show_bootstrap_screen()

    def _logout(self) -> None:
        self.current_user = None
        self._show_login_screen()

    def _create_default_template_period(
        self,
        *,
        company_id: int,
        start: date,
        end: date,
    ) -> int:
        suffix = uuid4().hex[:6]
        with session_scope() as session:
            repo = CalendarRepository(session=session)
            teaching = repo.create_mark_type(
                name=f"Навчання45-{start.isoformat()}-{suffix}",
                kind=MarkKind.TEACHING,
                duration_minutes=45,
                company_id=company_id,
            )
            break_mark = repo.create_mark_type(
                name=f"Перерва10-{start.isoformat()}-{suffix}",
                kind=MarkKind.BREAK,
                duration_minutes=10,
                company_id=company_id,
            )
            day = repo.create_day_pattern(
                name=f"БазовийДень-{start.isoformat()}-{suffix}",
                mark_types=[teaching, break_mark, teaching, teaching],
                company_id=company_id,
            )
            week = repo.create_week_pattern(day_pattern=day, company_id=company_id)
            period = repo.create_calendar_period(
                start_date=start,
                end_date=end,
                week_pattern=week,
                company_id=company_id,
            )
            CalendarController(session=session).generate_time_blocks(period.id)
            return period.id

    def _show_bootstrap_screen(self) -> None:
        self._clear_root()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Розклад", font=("TkDefaultFont", 18, "bold")).pack(anchor="w", pady=(0, 12))
        ttk.Label(frame, text="Перший запуск: створіть акаунт компанії").pack(anchor="w", pady=(0, 14))

        company_var = tk.StringVar()
        username_var = tk.StringVar()
        password_var = tk.StringVar()

        form = ttk.Frame(frame)
        form.pack(anchor="w")

        ttk.Label(form, text="Компанія").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(form, textvariable=company_var, width=36).grid(row=0, column=1, sticky="w", pady=(0, 6))

        ttk.Label(form, text="Логін адміністратора").grid(row=1, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(form, textvariable=username_var, width=36).grid(row=1, column=1, sticky="w", pady=(0, 6))

        ttk.Label(form, text="Пароль").grid(row=2, column=0, sticky="w", pady=(0, 12))
        ttk.Entry(form, textvariable=password_var, show="*", width=36).grid(row=2, column=1, sticky="w", pady=(0, 12))

        def on_create() -> None:
            company_name = company_var.get().strip()
            username = username_var.get().strip()
            password = password_var.get()
            if not company_name or not username or not password:
                messagebox.showerror("Помилка вводу", "Заповніть усі поля.")
                return
            try:
                with session_scope() as session:
                    controller = AuthController(session=session)
                    user = controller.bootstrap_company_account(
                        company_name=company_name,
                        username=username,
                        password=password,
                    )
                    self.current_user = user
            except Exception as exc:
                messagebox.showerror("Не вдалося створити акаунт", str(exc))
                return

            self._show_company_dashboard()

        ttk.Button(frame, text="Створити акаунт компанії", command=on_create).pack(anchor="w")

    def _show_login_screen(self) -> None:
        self._clear_root()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Розклад", font=("TkDefaultFont", 18, "bold")).pack(anchor="w", pady=(0, 12))
        ttk.Label(frame, text="Вхід").pack(anchor="w", pady=(0, 14))

        username_var = tk.StringVar()
        password_var = tk.StringVar()

        form = ttk.Frame(frame)
        form.pack(anchor="w")
        ttk.Label(form, text="Логін").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(form, textvariable=username_var, width=36).grid(row=0, column=1, sticky="w", pady=(0, 6))

        ttk.Label(form, text="Пароль").grid(row=1, column=0, sticky="w", pady=(0, 12))
        ttk.Entry(form, textvariable=password_var, show="*", width=36).grid(row=1, column=1, sticky="w", pady=(0, 12))

        def on_login() -> None:
            username = username_var.get().strip()
            password = password_var.get()
            if not username or not password:
                messagebox.showerror("Помилка вводу", "Введіть логін і пароль.")
                return
            with session_scope() as session:
                user = AuthController(session=session).authenticate(username=username, password=password)
            if user is None:
                messagebox.showerror("Помилка входу", "Неправильний логін або пароль.")
                return
            self.current_user = user
            if user.role == UserRole.COMPANY:
                self._show_company_dashboard()
            else:
                self._show_personal_dashboard()

        ttk.Button(frame, text="Увійти", command=on_login).pack(anchor="w")

    def _show_company_dashboard(self) -> None:
        user = self.current_user
        if user is None:
            self._show_login_screen()
            return

        self._clear_root()

        root_frame = ttk.Frame(self.root)
        root_frame.pack(fill=tk.BOTH, expand=True)

        sidebar = ttk.Frame(root_frame, padding=10, width=220)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        content = ttk.Frame(root_frame, padding=10)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        with session_scope() as session:
            company = AuthController(session=session).get_company(user.company_id)
        company_name = company.name if company else f"Компанія #{user.company_id}"

        ttk.Label(sidebar, text="Розклад", font=("TkDefaultFont", 14, "bold")).pack(anchor="w", pady=(0, 6))
        ttk.Label(sidebar, text=company_name).pack(anchor="w", pady=(0, 14))

        views: dict[str, ttk.Frame] = {}
        for key in ("schedule", "groups", "settings"):
            frame = ttk.Frame(content)
            views[key] = frame

        def open_view(name: str) -> None:
            for frame in views.values():
                frame.pack_forget()
            views[name].pack(fill=tk.BOTH, expand=True)

        ttk.Button(sidebar, text="Розклад", command=lambda: open_view("schedule")).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(sidebar, text="Групи", command=lambda: open_view("groups")).pack(fill=tk.X, pady=(0, 6))
        ttk.Button(sidebar, text="Налаштування", command=lambda: open_view("settings")).pack(fill=tk.X, pady=(0, 12))
        ttk.Button(sidebar, text="Вийти", command=self._logout).pack(fill=tk.X)

        self._build_company_schedule_view(views["schedule"], user.company_id)
        self._build_company_groups_view(views["groups"], user.company_id)
        self._build_company_settings_view(views["settings"], user.company_id, user.username)

        open_view("schedule")

    def _build_company_schedule_view(self, parent: ttk.Frame, company_id: int) -> None:
        period_var = tk.StringVar()
        week_start_var = tk.StringVar()
        group_filter_var = tk.StringVar(value="Усі групи")
        status_var = tk.StringVar(value="Готово.")

        subject_name_var = tk.StringVar()
        subject_duration_var = tk.StringVar(value="1")
        subject_sessions_var = tk.StringVar(value="4")
        subject_max_week_var = tk.StringVar(value="2")
        subject_teacher_var = tk.StringVar()
        subject_group_var = tk.StringVar()

        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(header, text="Розклад", font=("TkDefaultFont", 13, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Період = інтервал дат (наприклад семестр).",
        ).grid(row=0, column=1, columnspan=5, sticky="w", padx=(10, 0))
        ttk.Label(header, text="Період").grid(row=1, column=0, sticky="w", pady=(8, 0))

        period_box = ttk.Combobox(header, textvariable=period_var, width=22, state="readonly")
        period_box.grid(row=1, column=1, sticky="w", padx=(6, 10), pady=(8, 0))

        ttk.Label(header, text="Початок тижня").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(header, textvariable=week_start_var, width=14).grid(row=1, column=3, sticky="w", padx=(6, 10), pady=(8, 0))

        ttk.Label(header, text="Група").grid(row=1, column=4, sticky="w", pady=(8, 0))
        group_box = ttk.Combobox(header, textvariable=group_filter_var, width=22, state="readonly")
        group_box.grid(row=1, column=5, sticky="w", padx=(6, 10), pady=(8, 0))

        tree = ttk.Treeview(
            parent,
            columns=("slot", "mon", "tue", "wed", "thu", "fri", "sat", "sun"),
            show="headings",
            height=16,
        )
        tree.heading("slot", text="Пара")
        tree.column("slot", width=120, anchor="center", stretch=False)
        for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun"):
            tree.heading(day, text=day.upper())
            tree.column(day, width=145, anchor="center", stretch=True)
        tree.pack(fill=tk.BOTH, expand=True, pady=(8, 10))

        subject_box = ttk.LabelFrame(parent, text="Предмет", padding=10)
        subject_box.pack(fill=tk.X)

        ttk.Label(subject_box, text="Назва").grid(row=0, column=0, sticky="w")
        ttk.Entry(subject_box, textvariable=subject_name_var, width=20).grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(subject_box, text="Тривалість (блоків)").grid(row=0, column=2, sticky="w")
        ttk.Entry(subject_box, textvariable=subject_duration_var, width=6).grid(row=0, column=3, sticky="w", padx=(6, 12))
        ttk.Label(subject_box, text="Кількість занять").grid(row=0, column=4, sticky="w")
        ttk.Entry(subject_box, textvariable=subject_sessions_var, width=6).grid(row=0, column=5, sticky="w", padx=(6, 12))
        ttk.Label(subject_box, text="Макс/тиждень").grid(row=0, column=6, sticky="w")
        ttk.Entry(subject_box, textvariable=subject_max_week_var, width=6).grid(row=0, column=7, sticky="w", padx=(6, 12))
        ttk.Label(subject_box, text="Викладач").grid(row=1, column=0, sticky="w", pady=(8, 0))
        teacher_box = ttk.Combobox(subject_box, textvariable=subject_teacher_var, width=20, state="readonly")
        teacher_box.grid(row=1, column=1, sticky="w", padx=(6, 12), pady=(8, 0))
        ttk.Label(subject_box, text="Група").grid(row=1, column=2, sticky="w", pady=(8, 0))
        subject_group_box = ttk.Combobox(subject_box, textvariable=subject_group_var, width=20, state="readonly")
        subject_group_box.grid(row=1, column=3, sticky="w", padx=(6, 12), pady=(8, 0))

        buttons = ttk.Frame(parent)
        buttons.pack(fill=tk.X, pady=(8, 8))

        status = ttk.Label(parent, textvariable=status_var, anchor="w")
        status.pack(fill=tk.X)

        def parse_period_id() -> int:
            raw = period_var.get().strip()
            if not raw:
                raise ValueError("Оберіть період.")
            return int(raw.split("|", maxsplit=1)[0].strip())

        def parse_week_start() -> date | None:
            raw = week_start_var.get().strip()
            if not raw:
                return None
            return date.fromisoformat(raw)

        def selected_group_resource_id() -> int | None:
            raw = group_filter_var.get().strip()
            if not raw or raw == "Усі групи":
                return None
            return int(raw.split("|", maxsplit=1)[0].strip())

        def selected_teacher_resource_id() -> int:
            raw = subject_teacher_var.get().strip()
            if not raw:
                raise ValueError("Оберіть викладача.")
            return int(raw.split("|", maxsplit=1)[0].strip())

        def selected_subject_group_id() -> int:
            raw = subject_group_var.get().strip()
            if not raw:
                raise ValueError("Оберіть групу для предмета.")
            return int(raw.split("|", maxsplit=1)[0].strip())

        def load_reference_data() -> None:
            with session_scope() as session:
                calendar = CalendarController(session=session)
                periods = calendar.list_calendar_periods(company_id=company_id)
                resources = ResourceController(session=session)
                groups = resources.list_resources(resource_type=ResourceType.GROUP, company_id=company_id)
                teachers = resources.list_resources(resource_type=ResourceType.TEACHER, company_id=company_id)

            period_values = [f"{item.id} | {item.start_date}..{item.end_date}" for item in periods]
            period_box["values"] = period_values
            if period_values and not period_var.get():
                period_var.set(period_values[0])
            if not period_values:
                period_var.set("")
                status_var.set("Періоди відсутні. Створи період у налаштуваннях або кнопкою нижче.")

            group_values = [f"{item.id} | {item.name}" for item in groups]
            group_box["values"] = ["Усі групи"] + group_values
            if group_filter_var.get() not in group_box["values"]:
                group_filter_var.set("Усі групи")

            teacher_values = [f"{item.id} | {item.name}" for item in teachers]
            teacher_box["values"] = teacher_values
            if teacher_values and not subject_teacher_var.get():
                subject_teacher_var.set(teacher_values[0])

            subject_group_box["values"] = group_values
            if group_values and not subject_group_var.get():
                subject_group_var.set(group_values[0])

        def render_grid(grid) -> None:
            for item in tree.get_children():
                tree.delete(item)
            for weekday, day_date in enumerate(grid.weekdays):
                cid = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")[weekday]
                tree.heading(cid, text=f"{WEEKDAY_LABELS[weekday]}\n{day_date.isoformat()}")
            for row in grid.rows:
                values = [row.slot_label] + [row.cells.get(i, "") for i in range(7)]
                tree.insert("", tk.END, values=values)

        def on_load_week() -> None:
            try:
                period_id = parse_period_id()
                week_start = parse_week_start()
                resource_id = selected_group_resource_id()
                with session_scope() as session:
                    grid = ScheduleViewController(session=session).get_weekly_grid(
                        calendar_period_id=period_id,
                        week_start=week_start,
                        resource_id=resource_id,
                    )
            except Exception as exc:
                messagebox.showerror("Не вдалося завантажити розклад", str(exc))
                return
            render_grid(grid)
            status_var.set(f"Завантажено тиждень {grid.week_start}. Рядків: {len(grid.rows)}.")

        def on_build_schedule() -> None:
            try:
                period_id = parse_period_id()
                with session_scope() as session:
                    result = SchedulerController(session=session).build_schedule(period_id, replace_existing=True)
            except Exception as exc:
                messagebox.showerror("Не вдалося згенерувати розклад", str(exc))
                return
            status_var.set(
                f"Генерацію завершено. Створено: {len(result.created_entries)} | "
                f"Нерозміщено занять: {sum(result.unscheduled_sessions.values())}"
            )
            on_load_week()

        def on_validate() -> None:
            try:
                period_id = parse_period_id()
                with session_scope() as session:
                    report = ScheduleValidationController(session=session).validate_schedule(period_id)
            except Exception as exc:
                messagebox.showerror("Не вдалося перевірити розклад", str(exc))
                return
            if report.is_valid:
                messagebox.showinfo("Перевірка", "Проблем не знайдено.")
                status_var.set("Перевірка успішна.")
                return
            details = "\n".join(f"[{item.code}] {item.message}" for item in report.issues[:10])
            messagebox.showwarning("Проблеми перевірки", details)
            status_var.set(f"Знайдено проблем: {len(report.issues)}")

        def on_add_subject() -> None:
            try:
                name = subject_name_var.get().strip()
                if not name:
                    raise ValueError("Вкажіть назву предмета.")
                duration = int(subject_duration_var.get().strip())
                sessions_total = int(subject_sessions_var.get().strip())
                max_per_week = int(subject_max_week_var.get().strip())
                teacher_id = selected_teacher_resource_id()
                group_id = selected_subject_group_id()

                with session_scope() as session:
                    req_controller = RequirementController(session=session)
                    requirement = req_controller.create_requirement(
                        name=name,
                        duration_blocks=duration,
                        sessions_total=sessions_total,
                        max_per_week=max_per_week,
                        company_id=company_id,
                    )
                    req_controller.assign_resource(requirement.id, teacher_id, "TEACHER")
                    req_controller.assign_resource(requirement.id, group_id, "GROUP")
            except Exception as exc:
                messagebox.showerror("Не вдалося додати предмет", str(exc))
                return
            status_var.set(f"Предмет '{name}' додано.")

        def on_create_default_period() -> None:
            try:
                start = date.today()
                end = start + timedelta(days=120)
                period_id = self._create_default_template_period(
                    company_id=company_id,
                    start=start,
                    end=end,
                )
            except Exception as exc:
                messagebox.showerror("Не вдалося створити період", str(exc))
                return

            load_reference_data()
            for value in period_box["values"]:
                if value.startswith(f"{period_id} |"):
                    period_var.set(value)
                    break
            status_var.set(
                f"Створено період #{period_id}: {start.isoformat()}..{end.isoformat()}."
            )
            on_load_week()

        ttk.Button(buttons, text="Завантажити тиждень", command=on_load_week).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(buttons, text="Згенерувати", command=on_build_schedule).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(buttons, text="Перевірити", command=on_validate).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(buttons, text="Додати предмет", command=on_add_subject).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Button(buttons, text="Швидко створити період", command=on_create_default_period).pack(side=tk.LEFT)

        load_reference_data()
        if period_var.get():
            on_load_week()

    def _build_company_groups_view(self, parent: ttk.Frame, company_id: int) -> None:
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(header, text="Групи", font=("TkDefaultFont", 13, "bold")).pack(anchor="w")

        status_var = tk.StringVar(value="Готово.")
        groups_list = tk.Listbox(parent, height=10)
        groups_list.pack(fill=tk.X, pady=(6, 10))

        add_group_var = tk.StringVar()
        add_group_box = ttk.Frame(parent)
        add_group_box.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(add_group_box, text="Нова група").pack(side=tk.LEFT)
        ttk.Entry(add_group_box, textvariable=add_group_var, width=28).pack(side=tk.LEFT, padx=(6, 8))

        users_list = tk.Listbox(parent, height=8)
        users_list.pack(fill=tk.X, pady=(6, 10))

        participant_user_var = tk.StringVar()
        participant_pass_var = tk.StringVar()
        participant_group_var = tk.StringVar()

        form = ttk.Frame(parent)
        form.pack(fill=tk.X)
        ttk.Label(form, text="Логін").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=participant_user_var, width=18).grid(row=0, column=1, sticky="w", padx=(6, 10))
        ttk.Label(form, text="Пароль").grid(row=0, column=2, sticky="w")
        ttk.Entry(form, textvariable=participant_pass_var, show="*", width=18).grid(row=0, column=3, sticky="w", padx=(6, 10))
        ttk.Label(form, text="Група").grid(row=0, column=4, sticky="w")
        participant_group_box = ttk.Combobox(form, textvariable=participant_group_var, width=22, state="readonly")
        participant_group_box.grid(row=0, column=5, sticky="w", padx=(6, 10))

        status = ttk.Label(parent, textvariable=status_var, anchor="w")
        status.pack(fill=tk.X, pady=(8, 0))

        def load_groups() -> list[str]:
            with session_scope() as session:
                resources = ResourceController(session=session).list_resources(
                    resource_type=ResourceType.GROUP,
                    company_id=company_id,
                )
            groups_list.delete(0, tk.END)
            group_values = []
            for item in resources:
                line = f"{item.id} | {item.name}"
                groups_list.insert(tk.END, line)
                group_values.append(line)
            participant_group_box["values"] = group_values
            if group_values and not participant_group_var.get():
                participant_group_var.set(group_values[0])
            return group_values

        def load_users() -> None:
            with session_scope() as session:
                users = AuthController(session=session).list_company_users(company_id=company_id)
            users_list.delete(0, tk.END)
            for item in users:
                users_list.insert(
                    tk.END,
                    f"{item.id} | {item.username} | {item.role.value} | resource={item.resource_id}",
                )

        def on_add_group() -> None:
            name = add_group_var.get().strip()
            if not name:
                messagebox.showerror("Помилка вводу", "Вкажіть назву групи.")
                return
            try:
                with session_scope() as session:
                    ResourceController(session=session).create_resource(
                        name=name,
                        resource_type=ResourceType.GROUP,
                        company_id=company_id,
                    )
            except Exception as exc:
                messagebox.showerror("Не вдалося додати групу", str(exc))
                return
            add_group_var.set("")
            load_groups()
            status_var.set(f"Групу '{name}' додано.")

        def on_add_participant() -> None:
            username = participant_user_var.get().strip()
            password = participant_pass_var.get()
            selected_group = participant_group_var.get().strip()
            if not username or not password or not selected_group:
                messagebox.showerror("Помилка вводу", "Заповніть логін, пароль і групу.")
                return
            group_id = int(selected_group.split("|", maxsplit=1)[0].strip())
            try:
                with session_scope() as session:
                    AuthController(session=session).create_personal_user(
                        company_id=company_id,
                        username=username,
                        password=password,
                        resource_id=group_id,
                    )
            except Exception as exc:
                messagebox.showerror("Не вдалося додати учасника", str(exc))
                return
            participant_user_var.set("")
            participant_pass_var.set("")
            load_users()
            status_var.set(f"Учасника '{username}' додано.")

        buttons = ttk.Frame(parent)
        buttons.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(buttons, text="Додати групу", command=on_add_group).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(buttons, text="Додати учасника", command=on_add_participant).pack(side=tk.LEFT)

        load_groups()
        load_users()

    def _build_company_settings_view(self, parent: ttk.Frame, company_id: int, username: str) -> None:
        ttk.Label(parent, text="Налаштування", font=("TkDefaultFont", 13, "bold")).pack(anchor="w", pady=(0, 8))

        with session_scope() as session:
            company = AuthController(session=session).get_company(company_id)
        company_name = company.name if company else f"Компанія #{company_id}"

        ttk.Label(parent, text=f"Компанія: {company_name}").pack(anchor="w")
        ttk.Label(parent, text=f"Акаунт: {username}").pack(anchor="w", pady=(0, 10))

        ttk.Separator(parent).pack(fill=tk.X, pady=(2, 10))

        ttk.Label(parent, text="Створити шаблон розкладу").pack(anchor="w", pady=(0, 2))
        ttk.Label(parent, text="Період буде створений разом із блоками часу.").pack(anchor="w", pady=(0, 6))
        start_var = tk.StringVar(value=date.today().isoformat())
        end_var = tk.StringVar(value=(date.today() + timedelta(days=120)).isoformat())
        status_var = tk.StringVar(value="Готово.")

        box = ttk.Frame(parent)
        box.pack(anchor="w")
        ttk.Label(box, text="Початок").grid(row=0, column=0, sticky="w")
        ttk.Entry(box, textvariable=start_var, width=12).grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(box, text="Кінець").grid(row=0, column=2, sticky="w")
        ttk.Entry(box, textvariable=end_var, width=12).grid(row=0, column=3, sticky="w", padx=(6, 12))

        def on_create_template() -> None:
            try:
                start = date.fromisoformat(start_var.get().strip())
                end = date.fromisoformat(end_var.get().strip())
                if end < start:
                    raise ValueError("Дата завершення має бути не раніше дати початку.")
                period_id = self._create_default_template_period(
                    company_id=company_id,
                    start=start,
                    end=end,
                )
                status_var.set(f"Шаблон створено. ID періоду: {period_id}")
            except Exception as exc:
                messagebox.showerror("Не вдалося створити шаблон", str(exc))

        ttk.Button(parent, text="Створити шаблон", command=on_create_template).pack(anchor="w", pady=(10, 0))
        ttk.Label(parent, textvariable=status_var, anchor="w").pack(fill=tk.X, pady=(8, 0))

    def _show_personal_dashboard(self) -> None:
        user = self.current_user
        if user is None:
            self._show_login_screen()
            return

        self._clear_root()

        container = ttk.Frame(self.root, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(container, text="Розклад", font=("TkDefaultFont", 16, "bold")).pack(anchor="w", pady=(0, 4))
        ttk.Label(container, text="Особистий акаунт").pack(anchor="w", pady=(0, 8))

        content = ttk.Frame(container)
        content.pack(fill=tk.BOTH, expand=True)

        status_var = tk.StringVar(value="Готово.")
        period_var = tk.StringVar()
        week_var = tk.StringVar()

        nav_frame = ttk.Frame(container)
        nav_frame.pack(fill=tk.X, pady=(8, 0))

        home_frame = ttk.Frame(content)
        notes_frame = ttk.Frame(content)
        settings_frame = ttk.Frame(content)

        tree = ttk.Treeview(
            home_frame,
            columns=("slot", "mon", "tue", "wed", "thu", "fri", "sat", "sun"),
            show="headings",
            height=19,
        )
        tree.heading("slot", text="Пара")
        tree.column("slot", width=120, anchor="center", stretch=False)
        for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun"):
            tree.heading(day, text=day.upper())
            tree.column(day, width=140, anchor="center", stretch=True)

        controls = ttk.Frame(home_frame)
        controls.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(controls, text="Період").pack(side=tk.LEFT)
        period_box = ttk.Combobox(controls, textvariable=period_var, width=24, state="readonly")
        period_box.pack(side=tk.LEFT, padx=(6, 10))
        ttk.Label(controls, text="Початок тижня").pack(side=tk.LEFT)
        ttk.Entry(controls, textvariable=week_var, width=12).pack(side=tk.LEFT, padx=(6, 10))

        def parse_period() -> int:
            raw = period_var.get().strip()
            if not raw:
                raise ValueError("Оберіть період.")
            return int(raw.split("|", maxsplit=1)[0].strip())

        def parse_week() -> date | None:
            raw = week_var.get().strip()
            if not raw:
                return None
            return date.fromisoformat(raw)

        def load_periods() -> None:
            with session_scope() as session:
                periods = CalendarController(session=session).list_calendar_periods(company_id=user.company_id)
            values = [f"{item.id} | {item.start_date}..{item.end_date}" for item in periods]
            period_box["values"] = values
            if values and not period_var.get():
                period_var.set(values[0])
            if not values:
                status_var.set("Поки що немає періоду. Звернись до адміністратора компанії.")

        def render_grid(grid) -> None:
            for item in tree.get_children():
                tree.delete(item)
            for weekday, day_date in enumerate(grid.weekdays):
                cid = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")[weekday]
                tree.heading(cid, text=f"{WEEKDAY_LABELS[weekday]}\n{day_date.isoformat()}")
            for row in grid.rows:
                values = [row.slot_label] + [row.cells.get(i, "") for i in range(7)]
                tree.insert("", tk.END, values=values)

        def load_personal_schedule() -> None:
            try:
                if user.resource_id is None:
                    raise ValueError("Ваш акаунт ще не прив'язаний до групи.")
                period_id = parse_period()
                week_start = parse_week()
                with session_scope() as session:
                    grid = ScheduleViewController(session=session).get_weekly_grid(
                        calendar_period_id=period_id,
                        week_start=week_start,
                        resource_id=user.resource_id,
                    )
            except Exception as exc:
                messagebox.showerror("Не вдалося завантажити розклад", str(exc))
                return
            render_grid(grid)
            status_var.set(f"Завантажено тиждень {grid.week_start}.")

        ttk.Button(controls, text="Завантажити", command=load_personal_schedule).pack(side=tk.LEFT)

        tree.pack(fill=tk.BOTH, expand=True)
        ttk.Label(home_frame, textvariable=status_var, anchor="w").pack(fill=tk.X, pady=(8, 0))

        ttk.Label(notes_frame, text="Нагадування (скоро буде)").pack(anchor="w", pady=(8, 0))
        ttk.Label(settings_frame, text=f"Користувач: {user.username}").pack(anchor="w", pady=(8, 0))
        ttk.Label(settings_frame, text="Редагування профілю з'явиться в наступних фазах.").pack(anchor="w")
        ttk.Button(settings_frame, text="Вийти", command=self._logout).pack(anchor="w", pady=(10, 0))

        frames = {
            "home": home_frame,
            "notes": notes_frame,
            "settings": settings_frame,
        }

        def open_tab(tab: str) -> None:
            for frame in frames.values():
                frame.pack_forget()
            frames[tab].pack(fill=tk.BOTH, expand=True)

        ttk.Button(nav_frame, text="Головна", command=lambda: open_tab("home")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(nav_frame, text="Нагадування", command=lambda: open_tab("notes")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(nav_frame, text="Налаштування", command=lambda: open_tab("settings")).pack(side=tk.LEFT)

        load_periods()
        open_tab("home")
        if period_var.get():
            load_personal_schedule()
