from __future__ import annotations

from datetime import date, timedelta
import tkinter as tk
from tkinter import messagebox, ttk
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

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
from app.ui.fx_widgets import HoverCircleIconButton, RoundedMotionButton, RoundedMotionCard
from app.ui.theme import UiTheme


class ScheduleMainWindow:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Розклад")
        self.root.geometry("1260x760")
        self.root.minsize(1060, 680)
        self.theme = UiTheme(self.root)
        self.theme.apply()

        self.current_user: User | None = None

        self._show_start_screen()

    def _create_auth_shell(self, subtitle: str) -> tuple[ttk.Frame, ttk.Frame]:
        self._clear_root()

        page = ttk.Frame(self.root, padding=24)
        page.pack(fill=tk.BOTH, expand=True)
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(2, weight=1)
        page.grid_rowconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)

        brand = ttk.Frame(page)
        brand.grid(row=1, column=0, sticky="nsew", padx=(0, 28))
        art = tk.Canvas(
            brand,
            width=430,
            height=270,
            bg=self.theme.SIDEBAR_BG,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        art.pack(anchor="w", pady=(0, 14))
        art.create_oval(-120, -80, 220, 250, fill="#1f4767", outline="")
        art.create_oval(180, -40, 480, 240, fill="#0f766e", outline="")
        art.create_oval(140, 120, 520, 340, fill="#244966", outline="")
        art.create_text(
            34,
            38,
            text="Розклад",
            fill="#f6fbff",
            anchor="nw",
            font=("Segoe UI", 22, "bold"),
        )
        art.create_text(
            34,
            82,
            text="Smart schedule studio",
            fill="#d5e7f8",
            anchor="nw",
            font=("Segoe UI", 12),
        )
        art.create_text(
            34,
            132,
            text="• Планування без конфліктів\n• Компанії та персональні акаунти\n• Підгрупи і керування доступом",
            fill="#e3f0fb",
            anchor="nw",
            font=("Segoe UI", 11),
        )

        ttk.Label(brand, text="Розклад", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            brand,
            text="Плануй навчальний процес швидко і без конфліктів.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        card_shell = RoundedMotionCard(
            page,
            bg_color=self.theme.APP_BG,
            card_color=self.theme.SURFACE,
            shadow_color="#cfd8e3",
            radius=22,
            padding=6,
            shadow_offset=5,
            motion_enabled=True,
            width=520,
            height=520,
        )
        card_shell.grid(row=1, column=1, sticky="n", pady=(8, 0))
        card = ttk.Frame(card_shell.content, style="Card.TFrame", padding=12)
        card.pack(fill=tk.BOTH, expand=True)

        ttk.Label(card, text=subtitle, style="CardTitle.TLabel").pack(anchor="w", pady=(0, 12))

        return page, card

    def _motion_button(
        self,
        parent: tk.Widget,
        *,
        text: str,
        command,
        primary: bool = True,
        width: int = 170,
        height: int = 42,
        canvas_bg: str | None = None,
        fill: str | None = None,
        hover_fill: str | None = None,
        pressed_fill: str | None = None,
        text_color: str | None = None,
        shadow_color: str | None = None,
    ) -> RoundedMotionButton:
        if canvas_bg is None:
            canvas_bg = self.theme.SURFACE

        if primary:
            fill = fill or self.theme.ACCENT
            hover_fill = hover_fill or self.theme.ACCENT_HOVER
            pressed_fill = pressed_fill or "#0d5f58"
            text_color = text_color or self.theme.TEXT_LIGHT
            shadow_color = shadow_color or "#cfdae6"
        else:
            fill = fill or self.theme.SURFACE_ALT
            hover_fill = hover_fill or "#e8eff8"
            pressed_fill = pressed_fill or "#dfe8f3"
            text_color = text_color or self.theme.TEXT_PRIMARY
            shadow_color = shadow_color or "#d8e0eb"

        return RoundedMotionButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=height,
            radius=12,
            fill=fill,
            hover_fill=hover_fill,
            pressed_fill=pressed_fill,
            text_color=text_color,
            shadow_color=shadow_color,
            canvas_bg=canvas_bg,
        )

    def run(self) -> None:
        self.root.mainloop()

    def _clear_root(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def _show_start_screen(self) -> None:
        self._show_login_screen()

    def _logout(self) -> None:
        self.current_user = None
        self._apply_theme_variant(UiTheme.DEFAULT_VARIANT)
        self._show_login_screen()

    def _apply_theme_variant(self, variant: str) -> None:
        self.theme.set_variant(variant)
        self.theme.apply()

    def _apply_company_theme(self, company_id: int) -> None:
        theme_name = UiTheme.DEFAULT_VARIANT
        with session_scope() as session:
            profile = AuthController(session=session).get_company_profile(company_id)
            if profile.theme:
                theme_name = profile.theme
        self._apply_theme_variant(theme_name)

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
        self._show_register_screen()

    def _show_login_screen(self) -> None:
        _, card = self._create_auth_shell("Вхід")
        ttk.Label(
            card,
            text="Увійдіть у свій акаунт компанії або особистий акаунт.",
            style="CardSubtle.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(0, 16))

        with session_scope() as session:
            has_any = AuthController(session=session).has_any_account()
        if not has_any:
            ttk.Label(
                card,
                text="Акаунтів ще немає. Зареєструйтесь нижче.",
                style="CardSubtle.TLabel",
            ).pack(anchor="w", pady=(0, 10))

        username_var = tk.StringVar()
        password_var = tk.StringVar()

        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(anchor="w")
        ttk.Label(form, text="Логін", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(form, textvariable=username_var, width=36).grid(row=0, column=1, sticky="w", pady=(0, 6))

        ttk.Label(form, text="Пароль", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 12))
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

        self._motion_button(
            card,
            text="Увійти",
            command=on_login,
            primary=True,
            width=180,
        ).pack(anchor="w", pady=(2, 8))
        self._motion_button(
            card,
            text="Не маєте акаунту? Зареєструйтесь",
            command=self._show_register_screen,
            primary=False,
            width=320,
        ).pack(anchor="w")

    def _show_register_screen(self) -> None:
        _, card = self._create_auth_shell("Реєстрація")
        ttk.Label(
            card,
            text=(
                "Назва компанії необов'язкова. Якщо заповнено - створюється акаунт компанії, "
                "якщо порожньо - особистий акаунт."
            ),
            style="CardSubtle.TLabel",
            wraplength=420,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(0, 16))

        company_var = tk.StringVar()
        username_var = tk.StringVar()
        password_var = tk.StringVar()

        form = ttk.Frame(card, style="Card.TFrame")
        form.pack(anchor="w")

        ttk.Label(form, text="Назва компанії (необов'язково)", style="Card.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        ttk.Entry(form, textvariable=company_var, width=36).grid(row=0, column=1, sticky="w", pady=(0, 6))

        ttk.Label(form, text="Логін", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(form, textvariable=username_var, width=36).grid(row=1, column=1, sticky="w", pady=(0, 6))

        ttk.Label(form, text="Пароль", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 12))
        ttk.Entry(form, textvariable=password_var, show="*", width=36).grid(row=2, column=1, sticky="w", pady=(0, 12))

        def on_register() -> None:
            company_name = company_var.get().strip()
            username = username_var.get().strip()
            password = password_var.get()
            if not username or not password:
                messagebox.showerror("Помилка вводу", "Логін і пароль обов'язкові.")
                return
            try:
                with session_scope() as session:
                    controller = AuthController(session=session)
                    user = controller.register_user(
                        username=username,
                        password=password,
                        company_name=company_name or None,
                    )
                    self.current_user = user
            except Exception as exc:
                messagebox.showerror("Не вдалося зареєструватись", str(exc))
                return

            if self.current_user and self.current_user.role == UserRole.COMPANY:
                self._show_company_dashboard()
            else:
                self._show_personal_dashboard()

        self._motion_button(
            card,
            text="Зареєструватись",
            command=on_register,
            primary=True,
            width=210,
        ).pack(anchor="w", pady=(2, 8))
        self._motion_button(
            card,
            text="Вже маєте акаунт? Увійдіть",
            command=self._show_login_screen,
            primary=False,
            width=280,
        ).pack(anchor="w")

    def _show_company_dashboard(self, initial_view: str = "schedule") -> None:
        user = self.current_user
        if user is None:
            self._show_login_screen()
            return

        self._apply_company_theme(user.company_id)
        self._clear_root()

        root_frame = ttk.Frame(self.root)
        root_frame.pack(fill=tk.BOTH, expand=True)

        sidebar = ttk.Frame(root_frame, style="Sidebar.TFrame", padding=16, width=260)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        content = ttk.Frame(root_frame, padding=20)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        hero = tk.Canvas(
            content,
            height=88,
            bg=self.theme.SURFACE,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        hero.pack(fill=tk.X, pady=(0, 12))
        hero.create_oval(-60, -120, 220, 120, fill="#d7f2ee", outline="")
        hero.create_oval(200, -60, 520, 180, fill="#dfeaf8", outline="")
        hero.create_oval(500, -100, 900, 180, fill="#e9e2fb", outline="")
        hero.create_text(
            22,
            18,
            text="Компанійний простір",
            fill="#1f2937",
            anchor="nw",
            font=("Segoe UI", 16, "bold"),
        )
        hero.create_text(
            22,
            48,
            text="Керуйте групами, підгрупами та розкладом в одному місці.",
            fill="#57657a",
            anchor="nw",
            font=("Segoe UI", 10),
        )

        content_card_shell = RoundedMotionCard(
            content,
            bg_color=self.theme.APP_BG,
            card_color=self.theme.SURFACE,
            shadow_color="#cfd8e3",
            radius=18,
            padding=4,
            shadow_offset=5,
            motion_enabled=True,
        )
        content_card_shell.pack(fill=tk.BOTH, expand=True)
        views_container = ttk.Frame(content_card_shell.content, style="Card.TFrame", padding=14)
        views_container.pack(fill=tk.BOTH, expand=True)

        with session_scope() as session:
            company = AuthController(session=session).get_company(user.company_id)
        company_name = company.name if company else f"Компанія #{user.company_id}"

        ttk.Label(sidebar, text="Розклад", style="SidebarTitle.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(sidebar, text=company_name, style="SidebarMeta.TLabel").pack(anchor="w", pady=(0, 16))

        views: dict[str, ttk.Frame] = {}
        for key in ("schedule", "groups", "settings"):
            frame = ttk.Frame(views_container, style="Card.TFrame", padding=18)
            views[key] = frame

        def open_view(name: str) -> None:
            for frame in views.values():
                frame.pack_forget()
            views[name].pack(fill=tk.BOTH, expand=True)

        self._motion_button(
            sidebar,
            text="Розклад",
            command=lambda: open_view("schedule"),
            primary=True,
            width=224,
            height=44,
            canvas_bg=self.theme.SIDEBAR_BG,
            fill="#1f4563",
            hover_fill="#295676",
            pressed_fill="#173b56",
            text_color="#edf5ff",
            shadow_color="#11263a",
        ).pack(pady=(0, 6), anchor="w")
        self._motion_button(
            sidebar,
            text="Групи",
            command=lambda: open_view("groups"),
            primary=True,
            width=224,
            height=44,
            canvas_bg=self.theme.SIDEBAR_BG,
            fill="#1f4563",
            hover_fill="#295676",
            pressed_fill="#173b56",
            text_color="#edf5ff",
            shadow_color="#11263a",
        ).pack(pady=(0, 6), anchor="w")
        self._motion_button(
            sidebar,
            text="Налаштування",
            command=lambda: open_view("settings"),
            primary=True,
            width=224,
            height=44,
            canvas_bg=self.theme.SIDEBAR_BG,
            fill="#1f4563",
            hover_fill="#295676",
            pressed_fill="#173b56",
            text_color="#edf5ff",
            shadow_color="#11263a",
        ).pack(pady=(0, 6), anchor="w")

        ttk.Frame(sidebar, style="Sidebar.TFrame").pack(fill=tk.BOTH, expand=True)
        self._motion_button(
            sidebar,
            text="Вийти",
            command=self._logout,
            primary=True,
            width=224,
            height=44,
            canvas_bg=self.theme.SIDEBAR_BG,
            fill="#be123c",
            hover_fill="#9f1239",
            pressed_fill="#881337",
            text_color="#fff1f2",
            shadow_color="#5a0f23",
        ).pack(anchor="w")

        self._build_company_schedule_view(views["schedule"], user.company_id)
        self._build_company_groups_view(views["groups"], user.company_id)
        self._build_company_settings_view(views["settings"], user.company_id, user.username)

        selected_view = initial_view if initial_view in views else "schedule"
        open_view(selected_view)

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

        header = ttk.Frame(parent, style="Card.TFrame")
        header.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(header, text="Розклад", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Період = інтервал дат (наприклад семестр).",
            style="CardSubtle.TLabel",
        ).grid(row=0, column=1, columnspan=5, sticky="w", padx=(10, 0))
        ttk.Label(header, text="Період", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))

        period_box = ttk.Combobox(header, textvariable=period_var, width=22, state="readonly")
        period_box.grid(row=1, column=1, sticky="w", padx=(6, 10), pady=(8, 0))

        ttk.Label(header, text="Початок тижня", style="Card.TLabel").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(header, textvariable=week_start_var, width=14).grid(row=1, column=3, sticky="w", padx=(6, 10), pady=(8, 0))

        ttk.Label(header, text="Група", style="Card.TLabel").grid(row=1, column=4, sticky="w", pady=(8, 0))
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

        buttons = ttk.Frame(parent, style="Card.TFrame")
        buttons.pack(fill=tk.X, pady=(8, 8))

        status = ttk.Label(parent, textvariable=status_var, anchor="w", style="CardSubtle.TLabel")
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

        self._motion_button(
            buttons,
            text="Завантажити тиждень",
            command=on_load_week,
            primary=False,
            width=180,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._motion_button(
            buttons,
            text="Згенерувати",
            command=on_build_schedule,
            primary=True,
            width=140,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._motion_button(
            buttons,
            text="Перевірити",
            command=on_validate,
            primary=False,
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._motion_button(
            buttons,
            text="Додати предмет",
            command=on_add_subject,
            primary=False,
            width=170,
        ).pack(side=tk.LEFT, padx=(0, 16))
        self._motion_button(
            buttons,
            text="Швидко створити період",
            command=on_create_default_period,
            primary=True,
            width=220,
        ).pack(side=tk.LEFT)

        load_reference_data()
        if period_var.get():
            on_load_week()


    def _build_company_groups_view(self, parent: ttk.Frame, company_id: int) -> None:
        group_state: dict[str, int | str | None] = {"id": None, "name": None}
    
        def subgroup_short_name(full_name: str) -> str:
            marker = "::"
            if marker not in full_name:
                return full_name
            return full_name.split(marker, maxsplit=1)[1]
    
        content = ttk.Frame(parent, style="Card.TFrame")
        content.pack(fill=tk.BOTH, expand=True)
    
        main_view = ttk.Frame(content, style="Card.TFrame")
        detail_view = ttk.Frame(content, style="Card.TFrame")
        for frame in (main_view, detail_view):
            frame.pack(fill=tk.BOTH, expand=True)
            frame.pack_forget()
    
        header = ttk.Frame(main_view, style="Card.TFrame")
        header.pack(fill=tk.X, pady=(0, 8))
        self._motion_button(
            header,
            text="+ Створити групу",
            command=lambda: open_create_group_modal(),
            primary=True,
            width=190,
        ).pack(side=tk.RIGHT)
        titles = ttk.Frame(header, style="Card.TFrame")
        titles.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(titles, text="Групи", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            titles,
            text="Картки груп: ЛКМ - відкрити сторінку, ПКМ - видалити.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(2, 0))
    
        cards_container = ttk.Frame(main_view, style="Card.TFrame")
        cards_container.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        cards_container.grid_columnconfigure(0, weight=1)
        cards_container.grid_columnconfigure(1, weight=1)
        cards_container.grid_columnconfigure(2, weight=1)
    
        detail_scroll_wrap = ttk.Frame(detail_view, style="Card.TFrame")
        detail_scroll_wrap.pack(fill=tk.BOTH, expand=True)
        detail_canvas = tk.Canvas(
            detail_scroll_wrap,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        detail_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll = ttk.Scrollbar(
            detail_scroll_wrap,
            orient=tk.VERTICAL,
            command=detail_canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        detail_canvas.configure(yscrollcommand=detail_scroll.set)
        detail_body = ttk.Frame(detail_canvas, style="Card.TFrame")
        detail_body_window = detail_canvas.create_window((0, 0), anchor="nw", window=detail_body)

        def _sync_detail_scroll(_event=None) -> None:
            detail_canvas.configure(scrollregion=detail_canvas.bbox("all"))
            detail_canvas.itemconfigure(detail_body_window, width=detail_canvas.winfo_width())

        detail_body.bind("<Configure>", _sync_detail_scroll)
        detail_canvas.bind("<Configure>", _sync_detail_scroll)

        detail_nav = ttk.Frame(detail_body, style="Card.TFrame")
        detail_nav.pack(fill=tk.X, pady=(0, 6))
        detail_title_var = tk.StringVar(value="")
        back_button = HoverCircleIconButton(
            detail_nav,
            text="←",
            command=lambda: None,
            diameter=44,
            canvas_bg=self.theme.SURFACE,
            icon_color=self.theme.TEXT_PRIMARY,
            hover_bg="#e8eff8",
            hover_icon_color="#163554",
            pressed_bg="#dfe8f4",
        )
        back_button.pack(side=tk.LEFT)
        ttk.Label(detail_nav, textvariable=detail_title_var, style="CardTitle.TLabel").pack(side=tk.LEFT, padx=(10, 0))
        detail_subtitle = ttk.Label(
            detail_body,
            text="Додавай учасників за логіном і перетягуй їх між підгрупами.",
            style="CardSubtle.TLabel",
        )
        detail_subtitle.pack(anchor="w", pady=(0, 10))

        participant_username_var = tk.StringVar()

        participants_panel = ttk.Frame(detail_body, style="Card.TFrame")
        participants_panel.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(participants_panel, text="Учасники", style="CardTitle.TLabel").pack(anchor="w")

        participant_row = ttk.Frame(participants_panel, style="Card.TFrame")
        participant_row.pack(fill=tk.X, pady=(8, 10))
        participant_login_label = ttk.Label(participant_row, text="Логін", style="Card.TLabel")
        participant_login_label.grid(row=0, column=0, sticky="w")
        participant_row.grid_columnconfigure(0, weight=1)
        participant_input_box = ttk.Combobox(participant_row, textvariable=participant_username_var, width=26, state="normal")
        participant_input_box.grid(row=1, column=0, sticky="ew", pady=(6, 8))
        participant_add_button = self._motion_button(
            participant_row,
            text="Додати учасника",
            command=lambda: on_add_participant(),
            primary=True,
            width=180,
        )
        participant_add_button.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(6, 8))

        participants_scroll_wrap = ttk.Frame(participants_panel, style="Card.TFrame")
        participants_scroll_wrap.pack(fill=tk.X)
        participants_scroll_wrap.configure(height=250)
        participants_scroll_wrap.pack_propagate(False)
        participants_canvas = tk.Canvas(
            participants_scroll_wrap,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            height=250,
        )
        participants_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        participants_scroll = ttk.Scrollbar(
            participants_scroll_wrap,
            orient=tk.VERTICAL,
            command=participants_canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        participants_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        participants_canvas.configure(yscrollcommand=participants_scroll.set)
        participants_cards_frame = ttk.Frame(participants_canvas, style="Card.TFrame")
        participants_cards_window = participants_canvas.create_window((0, 0), anchor="nw", window=participants_cards_frame)

        def _sync_participants_scroll(_event=None) -> None:
            participants_canvas.configure(scrollregion=participants_canvas.bbox("all"))
            participants_canvas.itemconfigure(participants_cards_window, width=participants_canvas.winfo_width())

        participants_cards_frame.bind("<Configure>", _sync_participants_scroll)
        participants_canvas.bind("<Configure>", _sync_participants_scroll)

        subgroups_panel = ttk.Frame(detail_body, style="Card.TFrame")
        subgroups_panel.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(subgroups_panel, text="Підгрупи", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            subgroups_panel,
            text="Перетягни картку учасника в підгрупу. Щоб прибрати з підгрупи - перетягни у 'Без підгрупи'.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(2, 8))

        subgroup_name_var = tk.StringVar()
        subgroup_row = ttk.Frame(subgroups_panel, style="Card.TFrame")
        subgroup_row.pack(fill=tk.X, pady=(0, 8))
        subgroup_name_label = ttk.Label(subgroup_row, text="Нова підгрупа", style="Card.TLabel")
        subgroup_name_label.grid(row=0, column=0, sticky="w")
        subgroup_row.grid_columnconfigure(0, weight=1)
        subgroup_entry = ttk.Entry(subgroup_row, textvariable=subgroup_name_var, width=24)
        subgroup_entry.grid(row=1, column=0, sticky="ew", pady=(6, 8))
        subgroup_create_button = self._motion_button(
            subgroup_row,
            text="Створити підгрупу",
            command=lambda: on_create_subgroup(),
            primary=False,
            width=180,
        )
        subgroup_create_button.grid(row=1, column=1, sticky="w", padx=(10, 6), pady=(6, 8))
        subgroup_delete_button = self._motion_button(
            subgroup_row,
            text="Видалити підгрупу",
            command=lambda: on_delete_subgroup(),
            primary=False,
            width=180,
        )
        subgroup_delete_button.grid(row=1, column=2, sticky="w", pady=(6, 8))

        subgroup_tree_wrap = ttk.Frame(subgroups_panel, style="Card.TFrame")
        subgroup_tree_wrap.pack(fill=tk.X)
        subgroup_tree_wrap.configure(height=300)
        subgroup_tree_wrap.pack_propagate(False)
        subgroup_tree = ttk.Treeview(subgroup_tree_wrap, show="tree", height=14)
        subgroup_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        subgroup_tree_scroll = ttk.Scrollbar(
            subgroup_tree_wrap,
            orient=tk.VERTICAL,
            command=subgroup_tree.yview,
            style="App.Vertical.TScrollbar",
        )
        subgroup_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        subgroup_tree.configure(yscrollcommand=subgroup_tree_scroll.set)

        tree_subgroup_id_by_iid: dict[str, int | None] = {}
        tree_drag_state: dict[str, str | bool | None] = {"item": None, "active": False}
        current_users_by_id: dict[int, User] = {}
        current_subgroups_by_id: dict[int, object] = {}
        detail_layout_state = {"compact": False}

        def _update_detail_responsive(_event=None) -> None:
            width = detail_canvas.winfo_width()
            compact = width < 980
            if detail_layout_state["compact"] == compact:
                return
            detail_layout_state["compact"] = compact

            participant_add_button.grid_forget()
            if compact:
                participant_add_button.grid(row=2, column=0, sticky="w", pady=(0, 4))
            else:
                participant_add_button.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(6, 8))

            subgroup_create_button.grid_forget()
            subgroup_delete_button.grid_forget()
            if compact:
                subgroup_create_button.grid(row=2, column=0, sticky="w", pady=(0, 4))
                subgroup_delete_button.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(0, 4))
            else:
                subgroup_create_button.grid(row=1, column=1, sticky="w", padx=(10, 6), pady=(6, 8))
                subgroup_delete_button.grid(row=1, column=2, sticky="w", pady=(6, 8))

        def _create_smooth_wheel_handlers(get_view, set_view, *, gain: float = 0.14):
            # Keep scroll deterministic (no async inertia loop) to avoid jitter
            # while still smoothing raw wheel/touchpad input.
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

        def _bind_wheel_recursive(widget: tk.Widget, on_wheel, on_up, on_down) -> None:
            widget.bind("<MouseWheel>", on_wheel, add="+")
            widget.bind("<Button-4>", on_up, add="+")
            widget.bind("<Button-5>", on_down, add="+")
            for child in widget.winfo_children():
                _bind_wheel_recursive(child, on_wheel, on_up, on_down)

        def _with_fallback(primary_handler, primary_view, fallback_handler):
            def _handler(event: tk.Event) -> str:
                first, last = primary_view()
                first_f = float(first)
                last_f = float(last)
                if last_f - first_f >= 0.999:
                    return fallback_handler(event)
                event_num = getattr(event, "num", 0)
                delta = float(getattr(event, "delta", 0.0))
                scroll_up = bool(event_num == 4 or delta > 0)
                scroll_down = bool(event_num == 5 or delta < 0)
                if scroll_up and first_f <= 0.0001:
                    return fallback_handler(event)
                if scroll_down and last_f >= 0.9999:
                    return fallback_handler(event)
                return primary_handler(event)

            return _handler

        detail_canvas.bind("<Configure>", _update_detail_responsive, add="+")
        detail_wheel, detail_wheel_up, detail_wheel_down = _create_smooth_wheel_handlers(
            detail_canvas.yview,
            detail_canvas.yview_moveto,
            gain=0.14,
        )

        participants_wheel, participants_wheel_up, participants_wheel_down = _create_smooth_wheel_handlers(
            participants_canvas.yview,
            participants_canvas.yview_moveto,
            gain=0.13,
        )
        participants_wheel_f = _with_fallback(participants_wheel, participants_canvas.yview, detail_wheel)
        participants_wheel_up_f = _with_fallback(participants_wheel_up, participants_canvas.yview, detail_wheel_up)
        participants_wheel_down_f = _with_fallback(participants_wheel_down, participants_canvas.yview, detail_wheel_down)

        tree_wheel, tree_wheel_up, tree_wheel_down = _create_smooth_wheel_handlers(
            subgroup_tree.yview,
            subgroup_tree.yview_moveto,
            gain=0.14,
        )
        tree_wheel_f = _with_fallback(tree_wheel, subgroup_tree.yview, detail_wheel)
        tree_wheel_up_f = _with_fallback(tree_wheel_up, subgroup_tree.yview, detail_wheel_up)
        tree_wheel_down_f = _with_fallback(tree_wheel_down, subgroup_tree.yview, detail_wheel_down)

        _bind_wheel_recursive(detail_nav, detail_wheel, detail_wheel_up, detail_wheel_down)
        _bind_wheel_recursive(detail_subtitle, detail_wheel, detail_wheel_up, detail_wheel_down)
        _bind_wheel_recursive(participants_panel, participants_wheel_f, participants_wheel_up_f, participants_wheel_down_f)
        _bind_wheel_recursive(subgroups_panel, tree_wheel_f, tree_wheel_up_f, tree_wheel_down_f)
        detail_canvas.bind("<MouseWheel>", detail_wheel, add="+")
        detail_canvas.bind("<Button-4>", detail_wheel_up, add="+")
        detail_canvas.bind("<Button-5>", detail_wheel_down, add="+")
    
        def open_main_view() -> None:
            group_state["id"] = None
            group_state["name"] = None
            detail_view.pack_forget()
            main_view.pack(fill=tk.BOTH, expand=True)
            render_group_cards()
    
        def open_group_view(group_id: int, group_name: str) -> None:
            group_state["id"] = group_id
            group_state["name"] = group_name
            detail_title_var.set(group_name)
            main_view.pack_forget()
            detail_view.pack(fill=tk.BOTH, expand=True)
            load_group_detail()
    
        def delete_group(group_id: int, group_name: str) -> None:
            if not messagebox.askyesno("Підтвердження", f"Видалити групу '{group_name}' разом із підгрупами?"):
                return
            try:
                with session_scope() as session:
                    auth_controller = AuthController(session=session)
                    resource_controller = ResourceController(session=session)
                    subgroups = resource_controller.list_subgroups(group_id=group_id, company_id=company_id)
                    subgroup_ids = [item.id for item in subgroups]
                    users = auth_controller.list_group_users(
                        company_id=company_id,
                        group_id=group_id,
                        subgroup_ids=subgroup_ids,
                    )
                    for user in users:
                        auth_controller.update_user_membership(user.id, resource_id=None, subgroup_id=None)
                    deleted = resource_controller.delete_group_with_subgroups(group_id)
                    if not deleted:
                        raise ValueError("Групу не знайдено.")
            except Exception as exc:
                messagebox.showerror("Не вдалося видалити групу", str(exc))
                return
            if group_state["id"] == group_id:
                open_main_view()
            else:
                render_group_cards()
    
        def load_group_cards_data() -> list[tuple[int, str, int]]:
            with session_scope() as session:
                auth_controller = AuthController(session=session)
                resource_controller = ResourceController(session=session)
                groups = resource_controller.list_resources(resource_type=ResourceType.GROUP, company_id=company_id)
                result: list[tuple[int, str, int]] = []
                for group in groups:
                    subgroups = resource_controller.list_subgroups(group_id=group.id, company_id=company_id)
                    users = auth_controller.list_group_users(
                        company_id=company_id,
                        group_id=group.id,
                        subgroup_ids=[item.id for item in subgroups],
                    )
                    result.append((group.id, group.name, len(users)))
                return result
    
        def render_group_cards() -> None:
            for child in cards_container.winfo_children():
                child.destroy()
            try:
                groups = load_group_cards_data()
            except Exception as exc:
                messagebox.showerror("Помилка завантаження груп", str(exc))
                return
    
            if not groups:
                empty = ttk.Frame(cards_container, style="Card.TFrame")
                empty.grid(row=0, column=0, sticky="w")
                ttk.Label(
                    empty,
                    text="Поки що немає груп. Створи першу групу.",
                    style="CardSubtle.TLabel",
                ).pack(anchor="w")
                return
    
            def on_card_context(event: tk.Event, group_id: int, group_name: str) -> None:
                menu = tk.Menu(
                    self.root,
                    tearoff=0,
                    bg=self.theme.SURFACE,
                    fg=self.theme.TEXT_PRIMARY,
                    activebackground=self.theme.DANGER_HOVER,
                    activeforeground=self.theme.TEXT_LIGHT,
                    bd=0,
                    borderwidth=0,
                    relief=tk.FLAT,
                    font=("Segoe UI", 10, "bold"),
                    cursor="hand2",
                )
                menu.add_command(
                    label="Видалити",
                    command=lambda: delete_group(group_id, group_name),
                    foreground=self.theme.DANGER,
                    activebackground=self.theme.DANGER_HOVER,
                    activeforeground=self.theme.TEXT_LIGHT,
                )
                try:
                    menu.tk_popup(event.x_root, event.y_root)
                finally:
                    menu.grab_release()
    
            for index, (group_id, group_name, user_count) in enumerate(groups):
                row = index // 3
                column = index % 3
                card = RoundedMotionCard(
                    cards_container,
                    bg_color=self.theme.SURFACE,
                    card_color="#f7fbff",
                    shadow_color="#d4dee9",
                    radius=16,
                    padding=4,
                    shadow_offset=4,
                    motion_enabled=True,
                    width=280,
                    height=120,
                )
                card.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
                card.content.grid_columnconfigure(0, weight=1)
                title = ttk.Label(card.content, text=group_name, style="CardTitle.TLabel")
                title.grid(row=0, column=0, sticky="w", pady=(4, 2))
                count = ttk.Label(card.content, text=f"Учасників: {user_count}", style="CardSubtle.TLabel")
                count.grid(row=1, column=0, sticky="w")
    
                for widget in (card, card.canvas, card.content, title, count):
                    widget.bind("<Button-1>", lambda _e, gid=group_id, gname=group_name: open_group_view(gid, gname))
                    widget.bind("<Button-3>", lambda e, gid=group_id, gname=group_name: on_card_context(e, gid, gname))
    
        def render_participant_cards(users: list[User]) -> None:
            for child in participants_cards_frame.winfo_children():
                child.destroy()

            if not users:
                empty_label = ttk.Label(
                    participants_cards_frame,
                    text="У групі поки немає учасників.",
                    style="CardSubtle.TLabel",
                )
                empty_label.pack(anchor="w", pady=(2, 0))
                _bind_wheel_recursive(
                    empty_label,
                    participants_wheel_f,
                    participants_wheel_up_f,
                    participants_wheel_down_f,
                )
                _sync_participants_scroll()
                return

            for user in users:
                subgroup_label = "Без підгрупи"
                if user.subgroup_id and user.subgroup_id in current_subgroups_by_id:
                    subgroup_label = subgroup_short_name(current_subgroups_by_id[user.subgroup_id].name)

                card = RoundedMotionCard(
                    participants_cards_frame,
                    bg_color=self.theme.SURFACE,
                    card_color="#f7fbff",
                    shadow_color="#d8e2ee",
                    radius=14,
                    padding=3,
                    shadow_offset=3,
                    motion_enabled=True,
                    height=104,
                )
                card.pack(fill=tk.X, pady=(0, 8))
                card.content.grid_columnconfigure(0, weight=1)
                username_label = ttk.Label(card.content, text=user.username, style="CardTitle.TLabel")
                username_label.grid(row=0, column=0, sticky="w")
                badge_color = "#dff4ef" if user.subgroup_id is not None else "#e9eef5"
                badge_fg = "#0f766e" if user.subgroup_id is not None else "#516174"
                badge_label = tk.Label(
                    card.content,
                    text=subgroup_label,
                    bg=badge_color,
                    fg=badge_fg,
                    font=("Segoe UI", 9, "bold"),
                    padx=10,
                    pady=4,
                    bd=0,
                    relief=tk.FLAT,
                )
                badge_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
                _bind_wheel_recursive(
                    card,
                    participants_wheel_f,
                    participants_wheel_up_f,
                    participants_wheel_down_f,
                )

            _sync_participants_scroll()

        def render_subgroup_tree(users: list[User]) -> None:
            subgroup_tree.delete(*subgroup_tree.get_children())
            tree_subgroup_id_by_iid.clear()

            unassigned_iid = "sg_none"
            subgroup_tree.insert("", tk.END, iid=unassigned_iid, text="Без підгрупи", open=True)
            tree_subgroup_id_by_iid[unassigned_iid] = None

            for subgroup in current_subgroups_by_id.values():
                iid = f"sg_{subgroup.id}"
                subgroup_tree.insert("", tk.END, iid=iid, text=subgroup_short_name(subgroup.name), open=True)
                tree_subgroup_id_by_iid[iid] = subgroup.id

            for user in users:
                parent_iid = unassigned_iid
                if user.subgroup_id is not None and user.subgroup_id in current_subgroups_by_id:
                    parent_iid = f"sg_{user.subgroup_id}"
                subgroup_tree.insert(parent_iid, tk.END, iid=f"user_{user.id}", text=user.username, tags=("participant",))

        def load_group_detail() -> None:
            nonlocal current_users_by_id, current_subgroups_by_id

            group_id = group_state["id"]
            if group_id is None:
                return
            with session_scope() as session:
                auth_controller = AuthController(session=session)
                resource_controller = ResourceController(session=session)
                group = resource_controller.get_resource(group_id)
                if group is None or group.type != ResourceType.GROUP:
                    messagebox.showerror("Помилка", "Групу не знайдено.")
                    open_main_view()
                    return
                subgroups = resource_controller.list_subgroups(group_id=group_id, company_id=company_id)
                subgroup_ids = [item.id for item in subgroups]
                users = auth_controller.list_group_users(
                    company_id=company_id,
                    group_id=group_id,
                    subgroup_ids=subgroup_ids,
                )
                available_users = auth_controller.list_available_personal_users_for_company(company_id=company_id)

            current_subgroups_by_id = {item.id: item for item in subgroups}
            current_users_by_id = {item.id: item for item in users}

            render_participant_cards(users)
            render_subgroup_tree(users)

            available_usernames = [item.username for item in available_users if item.id not in current_users_by_id]
            participant_input_box["values"] = available_usernames
            if participant_username_var.get().strip() not in available_usernames:
                participant_username_var.set("")

        def on_add_participant() -> None:
            group_id = group_state["id"]
            if group_id is None:
                return

            username = participant_username_var.get().strip()
            if not username:
                messagebox.showerror("Некоректні дані", "Вкажи логін учасника.")
                return

            if any(user.username == username for user in current_users_by_id.values()):
                messagebox.showerror("Помилка", "Цей учасник уже в групі.")
                return

            try:
                with session_scope() as session:
                    auth_controller = AuthController(session=session)
                    company_users = auth_controller.list_company_users(company_id=company_id)
                    company_personals = {item.username: item for item in company_users if item.role == UserRole.PERSONAL}
                    available_personals = {
                        item.username: item
                        for item in auth_controller.list_available_personal_users_for_company(company_id=company_id)
                    }

                    user = company_personals.get(username) or available_personals.get(username)
                    if user is None:
                        raise ValueError("Особистий акаунт із таким логіном не знайдено.")

                    if user.company_id != company_id:
                        auth_controller.reassign_personal_user_company(user_id=user.id, company_id=company_id)

                    auth_controller.update_user_membership(
                        user.id,
                        resource_id=int(group_id),
                        subgroup_id=None,
                    )
            except Exception as exc:
                messagebox.showerror("Не вдалося додати учасника", str(exc))
                return

            participant_username_var.set("")
            load_group_detail()
            render_group_cards()

        def on_create_subgroup() -> None:
            group_id = group_state["id"]
            group_name = group_state["name"]
            if group_id is None or not isinstance(group_name, str):
                return
            raw_name = subgroup_name_var.get().strip()
            if not raw_name:
                messagebox.showerror("Некоректні дані", "Введи назву підгрупи.")
                return
            stored_name = f"{group_name}::{raw_name}"
            try:
                with session_scope() as session:
                    ResourceController(session=session).create_resource(
                        name=stored_name,
                        resource_type=ResourceType.SUBGROUP,
                        company_id=company_id,
                        parent_group_id=int(group_id),
                    )
            except Exception as exc:
                messagebox.showerror("Не вдалося створити підгрупу", str(exc))
                return
            subgroup_name_var.set("")
            load_group_detail()

        def on_delete_subgroup() -> None:
            group_id = group_state["id"]
            if group_id is None:
                return
            selection = subgroup_tree.selection()
            if not selection:
                messagebox.showerror("Помилка", "Обери підгрупу для видалення.")
                return
            selected_iid = selection[0]
            subgroup_id = tree_subgroup_id_by_iid.get(selected_iid)
            if subgroup_id is None:
                messagebox.showerror("Помилка", "Обери саме підгрупу, а не учасника.")
                return

            subgroup_name = subgroup_tree.item(selected_iid, "text")
            if not messagebox.askyesno("Підтвердження", f"Видалити підгрупу '{subgroup_name}'?"):
                return
            try:
                with session_scope() as session:
                    auth_controller = AuthController(session=session)
                    users = auth_controller.list_group_users(
                        company_id=company_id,
                        group_id=int(group_id),
                        subgroup_ids=[subgroup_id],
                    )
                    for user in users:
                        if user.subgroup_id == subgroup_id:
                            auth_controller.update_user_membership(user.id, resource_id=int(group_id), subgroup_id=None)
                    ResourceController(session=session).delete_resource(subgroup_id)
            except Exception as exc:
                messagebox.showerror("Не вдалося видалити підгрупу", str(exc))
                return
            load_group_detail()

        def on_detail_tree_press(event: tk.Event) -> None:
            item = subgroup_tree.identify_row(event.y)
            if item.startswith("user_"):
                tree_drag_state["item"] = item
                tree_drag_state["active"] = False
            else:
                tree_drag_state["item"] = None
                tree_drag_state["active"] = False

        def on_detail_tree_motion(event: tk.Event) -> None:
            item = tree_drag_state["item"]
            if item is None:
                return
            tree_drag_state["active"] = True
            target = subgroup_tree.identify_row(event.y)
            if target:
                subgroup_tree.selection_set(target)

        def on_detail_tree_release(event: tk.Event) -> None:
            item = tree_drag_state["item"]
            if item is None:
                return

            target = subgroup_tree.identify_row(event.y)
            if not target:
                selected = subgroup_tree.selection()
                target = selected[0] if selected else "sg_none"
            if target.startswith("user_"):
                target = subgroup_tree.parent(target)
            if target not in tree_subgroup_id_by_iid:
                target = "sg_none"

            user_id = int(item.split("_", maxsplit=1)[1])
            subgroup_id = tree_subgroup_id_by_iid.get(target)
            group_id = group_state["id"]

            tree_drag_state["item"] = None
            was_drag = bool(tree_drag_state["active"])
            tree_drag_state["active"] = False
            if not was_drag or group_id is None:
                return

            try:
                with session_scope() as session:
                    AuthController(session=session).update_user_membership(
                        user_id,
                        resource_id=int(group_id),
                        subgroup_id=subgroup_id,
                    )
            except Exception as exc:
                messagebox.showerror("Не вдалося оновити підгрупу", str(exc))
                return

            load_group_detail()

        subgroup_tree.bind("<ButtonPress-1>", on_detail_tree_press)
        subgroup_tree.bind("<B1-Motion>", on_detail_tree_motion)
        subgroup_tree.bind("<ButtonRelease-1>", on_detail_tree_release)
    
        def open_create_group_modal() -> None:
            with session_scope() as session:
                personal_users = AuthController(session=session).list_available_personal_users_for_company(
                    company_id=company_id
                )
            user_by_username = {item.username: item for item in personal_users}
            user_by_id = {item.id: item for item in personal_users}
    
            modal = tk.Toplevel(self.root)
            modal.title("Створення групи")
            modal.geometry("900x640")
            modal.minsize(840, 560)
            modal.transient(self.root)
            modal.grab_set()
            modal.configure(bg=self.theme.APP_BG)
    
            root = ttk.Frame(modal, padding=14, style="Card.TFrame")
            root.pack(fill=tk.BOTH, expand=True)
    
            ttk.Label(root, text="Нова група", style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(
                root,
                text="Вкажи назву, додай учасників за логіном, створи підгрупи і розподіли drag & drop.",
                style="CardSubtle.TLabel",
            ).pack(anchor="w", pady=(2, 10))
    
            group_name_var = tk.StringVar()
            group_row = ttk.Frame(root, style="Card.TFrame")
            group_row.pack(fill=tk.X, pady=(0, 10))
            ttk.Label(group_row, text="Назва групи", style="Card.TLabel").pack(side=tk.LEFT)
            group_name_entry = ttk.Entry(group_row, textvariable=group_name_var, width=34)
            group_name_entry.pack(side=tk.LEFT, padx=(8, 0))
    
            participant_var = tk.StringVar()
            add_row = ttk.Frame(root, style="Card.TFrame")
            add_row.pack(fill=tk.X, pady=(0, 10))
            ttk.Label(add_row, text="Учасник (логін)", style="Card.TLabel").pack(side=tk.LEFT)
            participant_box = ttk.Combobox(add_row, textvariable=participant_var, width=26, state="normal")
            participant_box.pack(side=tk.LEFT, padx=(8, 8))
    
            subgroup_var = tk.StringVar()
            subgroup_row = ttk.Frame(root, style="Card.TFrame")
            subgroup_row.pack(fill=tk.X, pady=(0, 10))
            ttk.Label(subgroup_row, text="Підгрупа", style="Card.TLabel").pack(side=tk.LEFT)
            subgroup_entry = ttk.Entry(subgroup_row, textvariable=subgroup_var, width=22)
            subgroup_entry.pack(side=tk.LEFT, padx=(8, 8))
    
            footer = ttk.Frame(root, style="Card.TFrame")
            footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

            tree_container = ttk.Frame(root, style="Card.TFrame")
            tree_container.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            tree = ttk.Treeview(tree_container, show="tree", height=10)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tree_scroll = ttk.Scrollbar(
                tree_container,
                orient=tk.VERTICAL,
                command=tree.yview,
                style="App.Vertical.TScrollbar",
            )
            tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            tree.configure(yscrollcommand=tree_scroll.set)
    
            unassigned_iid = "group_none"
            tree.insert("", tk.END, iid=unassigned_iid, text="Без підгрупи", open=True)
            subgroup_iid_by_name: dict[str, str] = {}
            subgroup_name_by_iid: dict[str, str] = {}
            added_users: dict[int, str] = {}
            assignment_by_user_id: dict[int, str | None] = {}
            drag_state: dict[str, str | bool | None] = {"item": None, "active": False}
    
            def refresh_suggestions() -> None:
                available = [item.username for item in personal_users if item.id not in added_users]
                participant_box["values"] = available
                if participant_var.get().strip() not in available:
                    participant_var.set("")
    
            def add_participant_from_input() -> None:
                username = participant_var.get().strip()
                if not username:
                    messagebox.showerror("Помилка", "Вкажи логін учасника.", parent=modal)
                    return
                user = user_by_username.get(username)
                if user is None:
                    messagebox.showerror("Помилка", "Користувача з таким логіном не знайдено.", parent=modal)
                    return
                if user.id in added_users:
                    return
                item_iid = f"user_{user.id}"
                tree.insert(unassigned_iid, tk.END, iid=item_iid, text=user.username, tags=("participant",))
                added_users[user.id] = user.username
                assignment_by_user_id[user.id] = None
                participant_var.set("")
                refresh_suggestions()
    
            def remove_selected_participant() -> None:
                selected = tree.selection()
                if not selected:
                    return
                item = selected[0]
                if not item.startswith("user_"):
                    return
                user_id = int(item.split("_", maxsplit=1)[1])
                tree.delete(item)
                added_users.pop(user_id, None)
                assignment_by_user_id.pop(user_id, None)
                refresh_suggestions()
    
            def add_subgroup() -> None:
                name = subgroup_var.get().strip()
                if not name:
                    messagebox.showerror("Помилка", "Вкажи назву підгрупи.", parent=modal)
                    return
                if name in subgroup_iid_by_name:
                    return
                iid = f"sg_{len(subgroup_iid_by_name) + 1}_{uuid4().hex[:4]}"
                tree.insert("", tk.END, iid=iid, text=name, open=True)
                subgroup_iid_by_name[name] = iid
                subgroup_name_by_iid[iid] = name
                subgroup_var.set("")
    
            def remove_selected_subgroup() -> None:
                selected = tree.selection()
                if not selected:
                    return
                iid = selected[0]
                if iid not in subgroup_name_by_iid:
                    return
                for child in tree.get_children(iid):
                    tree.move(child, unassigned_iid, tk.END)
                    user_id = int(child.split("_", maxsplit=1)[1])
                    assignment_by_user_id[user_id] = None
                name = subgroup_name_by_iid.pop(iid)
                subgroup_iid_by_name.pop(name, None)
                tree.delete(iid)
    
            def on_tree_press(event: tk.Event) -> None:
                item = tree.identify_row(event.y)
                if item.startswith("user_"):
                    drag_state["item"] = item
                    drag_state["active"] = False
                else:
                    drag_state["item"] = None
                    drag_state["active"] = False

            def on_tree_motion(event: tk.Event) -> None:
                item = drag_state["item"]
                if item is None:
                    return
                drag_state["active"] = True
                target = tree.identify_row(event.y)
                if target:
                    tree.selection_set(target)
    
            def on_tree_release(event: tk.Event) -> None:
                item = drag_state["item"]
                if item is None:
                    return

                target = tree.identify_row(event.y)
                if not target:
                    selected = tree.selection()
                    target = selected[0] if selected else unassigned_iid
                if target.startswith("user_"):
                    target = tree.parent(target)
                if target != unassigned_iid and target not in subgroup_name_by_iid:
                    target = unassigned_iid
                if drag_state["active"] and tree.parent(item) != target:
                    tree.move(item, target, tk.END)
                user_id = int(item.split("_", maxsplit=1)[1])
                assignment_by_user_id[user_id] = subgroup_name_by_iid.get(target)
                drag_state["item"] = None
                drag_state["active"] = False
    
            def save_group() -> None:
                group_name = group_name_var.get().strip()
                if not group_name:
                    messagebox.showerror("Некоректні дані", "Введи назву групи.", parent=modal)
                    return
                try:
                    with session_scope() as session:
                        resource_controller = ResourceController(session=session)
                        auth_controller = AuthController(session=session)
                        group = resource_controller.create_resource(
                            name=group_name,
                            resource_type=ResourceType.GROUP,
                            company_id=company_id,
                        )
                        subgroup_id_by_name: dict[str, int] = {}
                        for subgroup_name in subgroup_iid_by_name:
                            created = resource_controller.create_resource(
                                name=f"{group_name}::{subgroup_name}",
                                resource_type=ResourceType.SUBGROUP,
                                company_id=company_id,
                                parent_group_id=group.id,
                            )
                            subgroup_id_by_name[subgroup_name] = created.id

                        for user_id, subgroup_name in assignment_by_user_id.items():
                            user = user_by_id.get(user_id)
                            if user is not None and user.company_id != company_id:
                                auth_controller.reassign_personal_user_company(user_id=user_id, company_id=company_id)
                                user.company_id = company_id
                            auth_controller.update_user_membership(
                                user_id,
                                resource_id=group.id,
                                subgroup_id=subgroup_id_by_name.get(subgroup_name) if subgroup_name else None,
                            )
                except IntegrityError:
                    messagebox.showerror(
                        "Не вдалося створити групу",
                        "Група або підгрупа з такою назвою вже існує.",
                        parent=modal,
                    )
                    return
                except Exception as exc:
                    messagebox.showerror("Не вдалося створити групу", str(exc), parent=modal)
                    return
                modal.destroy()
                render_group_cards()
    
            self._motion_button(add_row, text="Додати", command=add_participant_from_input, primary=True, width=110).pack(
                side=tk.LEFT,
                padx=(0, 8),
            )
            self._motion_button(add_row, text="Прибрати", command=remove_selected_participant, primary=False, width=120).pack(
                side=tk.LEFT
            )
    
            self._motion_button(subgroup_row, text="Додати підгрупу", command=add_subgroup, primary=False, width=150).pack(
                side=tk.LEFT,
                padx=(0, 8),
            )
            self._motion_button(
                subgroup_row,
                text="Видалити підгрупу",
                command=remove_selected_subgroup,
                primary=False,
                width=170,
            ).pack(side=tk.LEFT)
    
            self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=140).pack(side=tk.RIGHT)
            self._motion_button(footer, text="Зберегти", command=save_group, primary=True, width=140).pack(
                side=tk.RIGHT,
                padx=(0, 8),
            )
    
            tree.bind("<ButtonPress-1>", on_tree_press)
            tree.bind("<B1-Motion>", on_tree_motion)
            tree.bind("<ButtonRelease-1>", on_tree_release)
            group_name_entry.focus_set()
            refresh_suggestions()
    
        back_button.command = open_main_view
        open_main_view()
    
    def _build_company_settings_view(self, parent: ttk.Frame, company_id: int, username: str) -> None:
        ttk.Label(parent, text="Налаштування", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(
            parent,
            text="Керуй профілем компанії, шаблонами та системними параметрами.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        tabs_bar = ttk.Frame(parent, style="Card.TFrame")
        tabs_bar.pack(fill=tk.X, pady=(0, 10))

        content = ttk.Frame(parent, style="Card.TFrame")
        content.pack(fill=tk.BOTH, expand=True)

        views: dict[str, ttk.Frame] = {
            "profile": ttk.Frame(content, style="Card.TFrame"),
            "templates": ttk.Frame(content, style="Card.TFrame"),
            "system": ttk.Frame(content, style="Card.TFrame"),
        }
        nav_buttons: dict[str, RoundedMotionButton] = {}

        def _set_nav_button_state(button: RoundedMotionButton, *, active: bool) -> None:
            if active:
                button.fill = self.theme.ACCENT
                button.hover_fill = self.theme.ACCENT_HOVER
                button.pressed_fill = self.theme.ACCENT_HOVER
                button.text_color = self.theme.TEXT_LIGHT
                button.shadow_color = "#cfd8e3"
            else:
                button.fill = self.theme.SURFACE_ALT
                button.hover_fill = "#e7eef7"
                button.pressed_fill = "#dfe7f0"
                button.text_color = self.theme.TEXT_PRIMARY
                button.shadow_color = "#d8e0eb"
            button._draw()

        def open_tab(name: str) -> None:
            for frame in views.values():
                frame.pack_forget()
            views[name].pack(fill=tk.BOTH, expand=True)
            for key, button in nav_buttons.items():
                _set_nav_button_state(button, active=key == name)

        tab_specs = (
            ("profile", "Профіль"),
            ("templates", "Шаблони"),
            ("system", "Система"),
        )
        for key, label in tab_specs:
            button = self._motion_button(
                tabs_bar,
                text=label,
                command=lambda selected=key: open_tab(selected),
                primary=False,
                width=150,
                height=40,
            )
            button.pack(side=tk.LEFT, padx=(0, 8))
            nav_buttons[key] = button

        self._build_company_settings_profile_tab(
            views["profile"],
            company_id=company_id,
            username=username,
        )
        self._build_company_settings_templates_tab(views["templates"], company_id=company_id)
        self._build_company_settings_system_tab(views["system"], company_id=company_id, username=username)

        open_tab("profile")

    def _build_company_settings_profile_tab(self, parent: ttk.Frame, *, company_id: int, username: str) -> None:
        with session_scope() as session:
            controller = AuthController(session=session)
            company = controller.get_company(company_id)
            profile = controller.get_company_profile(company_id)

        company_name_default = company.name if company is not None else f"Компанія #{company_id}"
        timezone_default = (profile.timezone or "Europe/Kyiv").strip()
        language_default = "Українська" if profile.language == "uk" else profile.language
        theme_default = (profile.theme or UiTheme.DEFAULT_VARIANT).strip().lower()

        company_name_var = tk.StringVar(value=company_name_default)
        timezone_var = tk.StringVar(value=timezone_default)
        language_var = tk.StringVar(value=language_default)
        logo_var = tk.StringVar(value=profile.logo_path or "Завантаження лого буде доступне пізніше")
        status_var = tk.StringVar(value="Готово.")

        theme_label_by_key = {
            "ocean": "Океан",
            "graphite": "Графіт",
            "sunrise": "Світанок",
        }
        theme_key_by_label = {label: key for key, label in theme_label_by_key.items()}
        theme_var = tk.StringVar(value=theme_label_by_key.get(theme_default, theme_label_by_key["ocean"]))

        timezone_options = [
            "Europe/Kyiv",
            "Europe/Warsaw",
            "Europe/Berlin",
            "Europe/London",
            "UTC",
        ]
        if timezone_default not in timezone_options:
            timezone_options.append(timezone_default)

        ttk.Label(parent, text="Профіль компанії", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 2))
        ttk.Label(
            parent,
            text="Зміни назву, часовий пояс і тему. Мова та лого поки що в режимі перегляду.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        form = ttk.Frame(parent, style="Card.TFrame")
        form.pack(fill=tk.X)
        form.grid_columnconfigure(1, weight=1)

        ttk.Label(form, text="Назва компанії", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(form, textvariable=company_name_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))

        ttk.Label(form, text="Лого", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 6))
        logo_row = ttk.Frame(form, style="Card.TFrame")
        logo_row.grid(row=1, column=1, sticky="ew", pady=(0, 6))
        logo_row.grid_columnconfigure(0, weight=1)
        logo_entry = ttk.Entry(logo_row, textvariable=logo_var, state="disabled")
        logo_entry.grid(row=0, column=0, sticky="ew")
        logo_action = ttk.Button(logo_row, text="Змінити (скоро)", state="disabled")
        logo_action.grid(row=0, column=1, padx=(8, 0))

        ttk.Label(form, text="Часовий пояс", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 6))
        timezone_box = ttk.Combobox(form, textvariable=timezone_var, values=timezone_options, state="readonly")
        timezone_box.grid(row=2, column=1, sticky="ew", pady=(0, 6))

        ttk.Label(form, text="Мова", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=(0, 6))
        language_box = ttk.Combobox(form, textvariable=language_var, values=["Українська"], state="disabled")
        language_box.grid(row=3, column=1, sticky="ew", pady=(0, 6))

        ttk.Label(form, text="Тема", style="Card.TLabel").grid(row=4, column=0, sticky="w", pady=(0, 6))
        theme_box = ttk.Combobox(
            form,
            textvariable=theme_var,
            values=[theme_label_by_key[key] for key in ("ocean", "graphite", "sunrise")],
            state="readonly",
        )
        theme_box.grid(row=4, column=1, sticky="ew", pady=(0, 6))

        ttk.Label(form, text=f"Акаунт: {username}", style="CardSubtle.TLabel").grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(2, 0),
        )

        def on_reset() -> None:
            company_name_var.set(company_name_default)
            timezone_var.set(timezone_default)
            language_var.set(language_default)
            theme_var.set(theme_label_by_key.get(theme_default, theme_label_by_key["ocean"]))
            status_var.set("Дані повернуто до збережених значень.")

        def on_save_profile() -> None:
            selected_theme = theme_key_by_label.get(theme_var.get().strip(), UiTheme.DEFAULT_VARIANT)
            try:
                with session_scope() as session:
                    controller = AuthController(session=session)
                    controller.update_company_profile(
                        company_id=company_id,
                        company_name=company_name_var.get().strip(),
                        timezone=timezone_var.get().strip(),
                        theme=selected_theme,
                    )
            except IntegrityError:
                messagebox.showerror("Не вдалося зберегти", "Компанія з такою назвою вже існує.")
                return
            except Exception as exc:
                messagebox.showerror("Не вдалося зберегти", str(exc))
                return

            self._show_company_dashboard(initial_view="settings")

        controls = ttk.Frame(parent, style="Card.TFrame")
        controls.pack(fill=tk.X, pady=(10, 0))
        self._motion_button(
            controls,
            text="Зберегти профіль",
            command=on_save_profile,
            primary=True,
            width=190,
        ).pack(side=tk.LEFT)
        self._motion_button(
            controls,
            text="Скинути",
            command=on_reset,
            primary=False,
            width=140,
        ).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(parent, textvariable=status_var, anchor="w", style="CardSubtle.TLabel").pack(fill=tk.X, pady=(8, 0))

    def _build_company_settings_templates_tab(self, parent: ttk.Frame, *, company_id: int) -> None:
        ttk.Label(parent, text="Шаблони розкладу", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 2))
        ttk.Label(
            parent,
            text="Період буде створений разом із базовими блоками часу.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        start_var = tk.StringVar(value=date.today().isoformat())
        end_var = tk.StringVar(value=(date.today() + timedelta(days=120)).isoformat())
        status_var = tk.StringVar(value="Готово.")

        box = ttk.Frame(parent, style="Card.TFrame")
        box.pack(anchor="w")
        ttk.Label(box, text="Початок", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(box, textvariable=start_var, width=12).grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(box, text="Кінець", style="Card.TLabel").grid(row=0, column=2, sticky="w")
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

        self._motion_button(
            parent,
            text="Створити шаблон",
            command=on_create_template,
            primary=True,
            width=190,
        ).pack(anchor="w", pady=(10, 0))
        ttk.Label(parent, textvariable=status_var, anchor="w", style="CardSubtle.TLabel").pack(fill=tk.X, pady=(8, 0))

    def _build_company_settings_system_tab(self, parent: ttk.Frame, *, company_id: int, username: str) -> None:
        ttk.Label(parent, text="Система", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 2))
        ttk.Label(
            parent,
            text="Системні функції будуть розширюватися у наступних фазах.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        info = ttk.Frame(parent, style="Card.TFrame")
        info.pack(fill=tk.X)
        ttk.Label(info, text=f"Компанія ID: {company_id}", style="Card.TLabel").pack(anchor="w")
        ttk.Label(info, text=f"Користувач: {username}", style="Card.TLabel").pack(anchor="w", pady=(4, 0))
        ttk.Label(
            info,
            text="Експорт, аудит і розширені нотифікації з'являться тут.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(8, 0))

    def _show_personal_dashboard(self) -> None:
        user = self.current_user
        if user is None:
            self._show_login_screen()
            return

        self._clear_root()

        container = ttk.Frame(self.root, padding=18)
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(header, text="Розклад", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(header, text="Особистий акаунт", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

        content = ttk.Frame(container, style="Card.TFrame", padding=16)
        content.pack(fill=tk.BOTH, expand=True)

        status_var = tk.StringVar(value="Готово.")
        period_var = tk.StringVar()
        week_var = tk.StringVar()

        nav_frame = ttk.Frame(container)
        nav_frame.pack(fill=tk.X, pady=(10, 0))

        home_frame = ttk.Frame(content, style="Card.TFrame")
        notes_frame = ttk.Frame(content, style="Card.TFrame")
        settings_frame = ttk.Frame(content, style="Card.TFrame")

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

        controls = ttk.Frame(home_frame, style="Card.TFrame")
        controls.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(controls, text="Період", style="Card.TLabel").pack(side=tk.LEFT)
        period_box = ttk.Combobox(controls, textvariable=period_var, width=24, state="readonly")
        period_box.pack(side=tk.LEFT, padx=(6, 10))
        ttk.Label(controls, text="Початок тижня", style="Card.TLabel").pack(side=tk.LEFT)
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

        self._motion_button(
            controls,
            text="Завантажити",
            command=load_personal_schedule,
            primary=True,
            width=140,
        ).pack(side=tk.LEFT)

        tree.pack(fill=tk.BOTH, expand=True)
        ttk.Label(home_frame, textvariable=status_var, anchor="w", style="CardSubtle.TLabel").pack(fill=tk.X, pady=(8, 0))

        ttk.Label(notes_frame, text="Нагадування (скоро буде)", style="CardTitle.TLabel").pack(anchor="w", pady=(8, 0))
        ttk.Label(
            notes_frame,
            text="Тут з'являться персональні нотатки та нагадування.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(4, 0))
        ttk.Label(settings_frame, text=f"Користувач: {user.username}", style="CardTitle.TLabel").pack(anchor="w", pady=(8, 0))
        ttk.Label(settings_frame, text="Редагування профілю з'явиться в наступних фазах.", style="CardSubtle.TLabel").pack(
            anchor="w"
        )
        self._motion_button(
            settings_frame,
            text="Вийти",
            command=self._logout,
            primary=True,
            width=120,
        ).pack(anchor="w", pady=(10, 0))

        frames = {
            "home": home_frame,
            "notes": notes_frame,
            "settings": settings_frame,
        }

        def open_tab(tab: str) -> None:
            for frame in frames.values():
                frame.pack_forget()
            frames[tab].pack(fill=tk.BOTH, expand=True)

        self._motion_button(
            nav_frame,
            text="Головна",
            command=lambda: open_tab("home"),
            primary=False,
            width=130,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._motion_button(
            nav_frame,
            text="Нагадування",
            command=lambda: open_tab("notes"),
            primary=False,
            width=150,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._motion_button(
            nav_frame,
            text="Налаштування",
            command=lambda: open_tab("settings"),
            primary=False,
            width=150,
        ).pack(side=tk.LEFT)

        load_periods()
        open_tab("home")
        if period_var.get():
            load_personal_schedule()
