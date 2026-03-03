from __future__ import annotations

from datetime import date, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4

from PIL import Image, ImageDraw, ImageTk, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError

from app.config.database import session_scope
from app.controllers.auth_controller import AuthController
from app.controllers.building_controller import BuildingController
from app.controllers.calendar_controller import CalendarController
from app.controllers.requirement_controller import RequirementController
from app.controllers.resource_controller import ResourceController
from app.controllers.room_controller import RoomController
from app.controllers.schedule_validation_controller import ScheduleValidationController
from app.controllers.schedule_view_controller import ScheduleViewController
from app.controllers.scheduler_controller import SchedulerController
from app.domain.enums import MarkKind, ResourceType, RoomType, UserRole
from app.domain.models import User
from app.repositories.calendar_repository import CalendarRepository
from app.services.avatar_storage import AvatarStorageService
from app.services.schedule_visualization import WEEKDAY_LABELS
from app.ui.avatar_template import draw_default_company_avatar
from app.ui.fx_widgets import HoverCircleIconButton, RoundedMotionButton, RoundedMotionCard
from app.ui.profile_data import DEFAULT_LANGUAGE_CODE, DEFAULT_TIMEZONE, LANGUAGE_OPTIONS, all_timezones
from app.ui.templates import CompanyTemplatesTab
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
            text="Розумне планування розкладу",
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
            shadow_color=self.theme.SHADOW_SOFT,
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
            pressed_fill = pressed_fill or self.theme.ACCENT_PRESSED
            text_color = text_color or self.theme.TEXT_LIGHT
            shadow_color = shadow_color or self.theme.SHADOW_SOFT
        else:
            fill = fill or self.theme.SURFACE_ALT
            hover_fill = hover_fill or self.theme.SECONDARY_HOVER
            pressed_fill = pressed_fill or self.theme.SECONDARY_PRESSED
            text_color = text_color or self.theme.TEXT_PRIMARY
            shadow_color = shadow_color or self.theme.SHADOW_SOFT

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

    def _build_rounded_avatar_photo(self, image_path: str, size: int) -> ImageTk.PhotoImage | None:
        try:
            with Image.open(image_path) as image:
                rgb = image.convert("RGB")
                min_side = min(rgb.width, rgb.height)
                left = (rgb.width - min_side) // 2
                top = (rgb.height - min_side) // 2
                square = rgb.crop((left, top, left + min_side, top + min_side))
                resized = square.resize((size, size), Image.Resampling.LANCZOS)

                mask = Image.new("L", (size, size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)

                rounded = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                rounded.paste(resized, (0, 0), mask)
        except (FileNotFoundError, OSError, UnidentifiedImageError):
            return None
        return ImageTk.PhotoImage(rounded)

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
        hero.create_oval(-60, -120, 220, 120, fill=self.theme.HERO_BLOB_1, outline="")
        hero.create_oval(200, -60, 520, 180, fill=self.theme.HERO_BLOB_2, outline="")
        hero.create_oval(500, -100, 900, 180, fill=self.theme.HERO_BLOB_3, outline="")
        hero.create_text(
            22,
            18,
            text="Компанійний простір",
            fill=self.theme.HERO_TITLE,
            anchor="nw",
            font=("Segoe UI", 16, "bold"),
        )
        hero.create_text(
            22,
            48,
            text="Керуйте групами, підгрупами та розкладом в одному місці.",
            fill=self.theme.HERO_SUBTITLE,
            anchor="nw",
            font=("Segoe UI", 10),
        )

        content_card_shell = RoundedMotionCard(
            content,
            bg_color=self.theme.APP_BG,
            card_color=self.theme.SURFACE,
            shadow_color=self.theme.SHADOW_SOFT,
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
        for key in ("schedule", "groups", "rooms", "settings"):
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
            fill=self.theme.SIDEBAR_BUTTON_FILL,
            hover_fill=self.theme.SIDEBAR_BUTTON_HOVER,
            pressed_fill=self.theme.SIDEBAR_BUTTON_PRESSED,
            text_color=self.theme.SIDEBAR_BUTTON_TEXT,
            shadow_color=self.theme.SIDEBAR_BUTTON_SHADOW,
        ).pack(pady=(0, 6), anchor="w")
        self._motion_button(
            sidebar,
            text="Групи",
            command=lambda: open_view("groups"),
            primary=True,
            width=224,
            height=44,
            canvas_bg=self.theme.SIDEBAR_BG,
            fill=self.theme.SIDEBAR_BUTTON_FILL,
            hover_fill=self.theme.SIDEBAR_BUTTON_HOVER,
            pressed_fill=self.theme.SIDEBAR_BUTTON_PRESSED,
            text_color=self.theme.SIDEBAR_BUTTON_TEXT,
            shadow_color=self.theme.SIDEBAR_BUTTON_SHADOW,
        ).pack(pady=(0, 6), anchor="w")
        self._motion_button(
            sidebar,
            text="Приміщення",
            command=lambda: open_view("rooms"),
            primary=True,
            width=224,
            height=44,
            canvas_bg=self.theme.SIDEBAR_BG,
            fill=self.theme.SIDEBAR_BUTTON_FILL,
            hover_fill=self.theme.SIDEBAR_BUTTON_HOVER,
            pressed_fill=self.theme.SIDEBAR_BUTTON_PRESSED,
            text_color=self.theme.SIDEBAR_BUTTON_TEXT,
            shadow_color=self.theme.SIDEBAR_BUTTON_SHADOW,
        ).pack(pady=(0, 6), anchor="w")
        self._motion_button(
            sidebar,
            text="Налаштування",
            command=lambda: open_view("settings"),
            primary=True,
            width=224,
            height=44,
            canvas_bg=self.theme.SIDEBAR_BG,
            fill=self.theme.SIDEBAR_BUTTON_FILL,
            hover_fill=self.theme.SIDEBAR_BUTTON_HOVER,
            pressed_fill=self.theme.SIDEBAR_BUTTON_PRESSED,
            text_color=self.theme.SIDEBAR_BUTTON_TEXT,
            shadow_color=self.theme.SIDEBAR_BUTTON_SHADOW,
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
            fill=self.theme.DANGER,
            hover_fill=self.theme.DANGER_HOVER,
            pressed_fill=self.theme.DANGER_HOVER,
            text_color=self.theme.TEXT_LIGHT,
            shadow_color=self.theme.SIDEBAR_BUTTON_SHADOW,
        ).pack(anchor="w")

        self._build_company_schedule_view(views["schedule"], user.company_id)
        self._build_company_groups_view(views["groups"], user.company_id)
        self._build_company_rooms_view(views["rooms"], user.company_id)
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
            hover_bg=self.theme.SECONDARY_HOVER,
            hover_icon_color=self.theme.TEXT_PRIMARY,
            pressed_bg=self.theme.SECONDARY_PRESSED,
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
                    card_color=self.theme.SURFACE_ALT,
                    shadow_color=self.theme.SHADOW_SOFT,
                    radius=16,
                    padding=4,
                    shadow_offset=4,
                    motion_enabled=True,
                    width=280,
                    height=120,
                )
                card.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
                card.content.grid_columnconfigure(0, weight=1)
                title = ttk.Label(card.content, text=group_name, style="CardAltTitle.TLabel")
                title.grid(row=0, column=0, sticky="w", pady=(4, 2))
                count = ttk.Label(card.content, text=f"Учасників: {user_count}", style="CardAltSubtle.TLabel")
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
                    card_color=self.theme.SURFACE_ALT,
                    shadow_color=self.theme.SHADOW_SOFT,
                    radius=14,
                    padding=3,
                    shadow_offset=3,
                    motion_enabled=True,
                    height=104,
                )
                card.pack(fill=tk.X, pady=(0, 8))
                card.content.grid_columnconfigure(0, weight=1)
                username_label = ttk.Label(card.content, text=user.username, style="CardAltTitle.TLabel")
                username_label.grid(row=0, column=0, sticky="w")
                badge_color = self.theme.SECONDARY_HOVER if user.subgroup_id is not None else self.theme.SURFACE
                badge_fg = self.theme.ACCENT if user.subgroup_id is not None else self.theme.TEXT_MUTED
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
                text="Вкажи назву, додай учасників за логіном, створи підгрупи і розподіли перетягуванням.",
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

    def _build_company_rooms_view(self, parent: ttk.Frame, company_id: int) -> None:
        buildings_state: dict[str, list[object]] = {"items": []}
        columns_state = {"value": 4}
        selected_building = {"item": None}
        rooms_state: dict[str, list[object]] = {"items": []}
        room_type_options: list[tuple[str, RoomType | None]] = [
            ("Усі", None),
            ("Лекційна аудиторія", RoomType.LECTURE_HALL),
            ("Клас", RoomType.CLASSROOM),
            ("Лабораторія", RoomType.LAB),
            ("Комп'ютерна лабораторія", RoomType.COMPUTER_LAB),
            ("Викладацька", RoomType.TEACHERS_OFFICE),
            ("Технічне", RoomType.TECHNICAL),
            ("Інше", RoomType.OTHER),
        ]
        room_type_by_label = {label: room_type for label, room_type in room_type_options if room_type is not None}
        room_type_label_by_enum = {room_type: label for label, room_type in room_type_options if room_type is not None}
        room_type_choices = [label for label, room_type in room_type_options if room_type is not None]

        list_view = ttk.Frame(parent, style="Card.TFrame")
        list_view.pack(fill=tk.BOTH, expand=True)

        detail_view = ttk.Frame(parent, style="Card.TFrame")
        detail_view.pack(fill=tk.BOTH, expand=True)
        detail_view.pack_forget()

        header = ttk.Frame(list_view, style="Card.TFrame")
        header.pack(fill=tk.X, pady=(0, 10))
        titles = ttk.Frame(header, style="Card.TFrame")
        titles.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(titles, text="Приміщення", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            titles,
            text="Керуйте корпусами й аудиторіями. Натисніть картку корпусу, щоб відкрити деталі.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        cards_shell = ttk.Frame(list_view, style="Card.TFrame")
        cards_shell.pack(fill=tk.BOTH, expand=True)
        cards_canvas = tk.Canvas(
            cards_shell,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        cards_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cards_scroll = ttk.Scrollbar(
            cards_shell,
            orient=tk.VERTICAL,
            command=cards_canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        cards_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        cards_canvas.configure(yscrollcommand=cards_scroll.set)

        cards_grid = ttk.Frame(cards_canvas, style="Card.TFrame")
        cards_window = cards_canvas.create_window((0, 0), anchor="nw", window=cards_grid)

        detail_header = ttk.Frame(detail_view, style="Card.TFrame")
        detail_header.pack(fill=tk.X, pady=(0, 10))
        back_button = HoverCircleIconButton(
            detail_header,
            text="←",
            command=lambda: open_list_view(),
            diameter=42,
            canvas_bg=self.theme.SURFACE,
            icon_color=self.theme.TEXT_PRIMARY,
            hover_bg=self.theme.SECONDARY_HOVER,
            hover_icon_color=self.theme.TEXT_PRIMARY,
            pressed_bg=self.theme.SECONDARY_PRESSED,
        )
        back_button.pack(side=tk.LEFT)

        detail_title_var = tk.StringVar(value="")
        detail_address_var = tk.StringVar(value="")
        detail_titles = ttk.Frame(detail_header, style="Card.TFrame")
        detail_titles.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        ttk.Label(detail_titles, textvariable=detail_title_var, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(detail_titles, textvariable=detail_address_var, style="CardSubtle.TLabel").pack(anchor="w", pady=(2, 0))

        detail_actions = ttk.Frame(detail_header, style="Card.TFrame")
        detail_actions.pack(side=tk.RIGHT)

        room_search_var = tk.StringVar(value="")
        room_type_filter_var = tk.StringVar(value="Усі")
        room_min_capacity_var = tk.StringVar(value="")
        room_include_archived_var = tk.BooleanVar(value=False)
        rooms_count_var = tk.StringVar(value="Аудиторій: 0")

        detail_body = ttk.Frame(detail_view, style="Card.TFrame")
        detail_body.pack(fill=tk.BOTH, expand=True)
        detail_card = RoundedMotionCard(
            detail_body,
            bg_color=self.theme.SURFACE,
            card_color=self.theme.SURFACE_ALT,
            shadow_color=self.theme.SHADOW_SOFT,
            radius=16,
            padding=4,
            shadow_offset=4,
            motion_enabled=True,
            height=120,
        )
        detail_card.pack(fill=tk.X, pady=(0, 8))
        detail_card.content.grid_columnconfigure(0, weight=1)
        ttk.Label(detail_card.content, text="Аудиторії", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(2, 2))
        ttk.Label(
            detail_card.content,
            text="Керуйте аудиторіями та фільтруйте список приміщень.",
            style="CardSubtle.TLabel",
        ).grid(row=1, column=0, sticky="w")
        ttk.Label(detail_card.content, textvariable=rooms_count_var, style="CardSubtle.TLabel").grid(
            row=2,
            column=0,
            sticky="w",
            pady=(8, 0),
        )

        filters_row = ttk.Frame(detail_body, style="Card.TFrame")
        filters_row.pack(fill=tk.X, pady=(2, 8))
        ttk.Label(filters_row, text="Пошук", style="Card.TLabel").pack(side=tk.LEFT)
        room_search_entry = ttk.Entry(filters_row, textvariable=room_search_var, width=26)
        room_search_entry.pack(side=tk.LEFT, padx=(6, 10))
        ttk.Label(filters_row, text="Тип", style="Card.TLabel").pack(side=tk.LEFT)
        room_type_box = ttk.Combobox(
            filters_row,
            textvariable=room_type_filter_var,
            values=[label for label, _ in room_type_options],
            state="readonly",
            width=16,
        )
        room_type_box.pack(side=tk.LEFT, padx=(6, 10))
        ttk.Label(filters_row, text="Мін. місткість", style="Card.TLabel").pack(side=tk.LEFT)
        room_capacity_entry = ttk.Entry(filters_row, textvariable=room_min_capacity_var, width=8)
        room_capacity_entry.pack(side=tk.LEFT, padx=(6, 10))
        ttk.Checkbutton(
            filters_row,
            text="Показати архівні",
            variable=room_include_archived_var,
        ).pack(side=tk.LEFT)

        rooms_table_wrap = ttk.Frame(detail_body, style="Card.TFrame")
        rooms_table_wrap.pack(fill=tk.BOTH, expand=True)
        rooms_table = ttk.Treeview(
            rooms_table_wrap,
            columns=("name", "type", "capacity", "floor", "status"),
            show="headings",
            height=12,
        )
        rooms_table.heading("name", text="Назва")
        rooms_table.heading("type", text="Тип")
        rooms_table.heading("capacity", text="Місткість")
        rooms_table.heading("floor", text="Поверх")
        rooms_table.heading("status", text="Статус")
        rooms_table.column("name", width=280, anchor="w")
        rooms_table.column("type", width=150, anchor="center")
        rooms_table.column("capacity", width=110, anchor="center")
        rooms_table.column("floor", width=110, anchor="center")
        rooms_table.column("status", width=130, anchor="center")
        rooms_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rooms_table_scroll = ttk.Scrollbar(
            rooms_table_wrap,
            orient=tk.VERTICAL,
            command=rooms_table.yview,
            style="App.Vertical.TScrollbar",
        )
        rooms_table_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        rooms_table.configure(yscrollcommand=rooms_table_scroll.set)

        def open_list_view() -> None:
            detail_view.pack_forget()
            list_view.pack(fill=tk.BOTH, expand=True)

        def open_building_view(building) -> None:
            selected_building["item"] = building
            detail_title_var.set(str(building.name))
            detail_address_var.set(str(building.address or "Адресу не вказано"))
            room_search_var.set("")
            room_type_filter_var.set("Усі")
            room_min_capacity_var.set("")
            room_include_archived_var.set(False)
            load_rooms()
            list_view.pack_forget()
            detail_view.pack(fill=tk.BOTH, expand=True)

        def parse_optional_int(raw: str, *, field_name: str, allow_negative: bool = False) -> int | None:
            text = raw.strip()
            if not text:
                return None
            try:
                value = int(text)
            except ValueError as exc:
                raise ValueError(f"Поле '{field_name}' має бути цілим числом.") from exc
            if not allow_negative and value < 0:
                raise ValueError(f"Поле '{field_name}' не може бути від'ємним.")
            return value

        def get_selected_room() -> object | None:
            selected = rooms_table.selection()
            if not selected:
                return None
            item_id = selected[0]
            for room in rooms_state["items"]:
                if str(room.id) == str(item_id):
                    return room
            return None

        def render_rooms() -> None:
            for item in rooms_table.get_children():
                rooms_table.delete(item)

            items = rooms_state["items"]
            rooms_count_var.set(f"Аудиторій: {len(items)}")
            for room in items:
                rooms_table.insert(
                    "",
                    tk.END,
                    iid=str(room.id),
                    values=(
                        str(room.name),
                        room_type_label_by_enum.get(room.room_type, "Інше"),
                        "" if room.capacity is None else str(room.capacity),
                        "" if room.floor is None else str(room.floor),
                        "Архівна" if bool(room.is_archived) else "Активна",
                    ),
                )

        def load_rooms() -> None:
            building = selected_building["item"]
            if building is None:
                rooms_state["items"] = []
                render_rooms()
                return

            selected_type_label = room_type_filter_var.get().strip() or "Усі"
            room_type_filter = None
            if selected_type_label != "Усі":
                room_type_filter = room_type_by_label.get(selected_type_label)
                if room_type_filter is None:
                    messagebox.showerror("Некоректний фільтр", "Невідомий тип аудиторії.", parent=self.root)
                    return

            try:
                min_capacity = parse_optional_int(
                    room_min_capacity_var.get(),
                    field_name="Мін. місткість",
                    allow_negative=False,
                )
            except ValueError as exc:
                messagebox.showerror("Некоректний фільтр", str(exc), parent=self.root)
                return

            with session_scope() as session:
                controller = RoomController(session=session)
                rooms = controller.list_rooms(
                    building_id=building.id,
                    include_archived=room_include_archived_var.get(),
                    search=room_search_var.get().strip() or None,
                    room_type=room_type_filter,
                    min_capacity=min_capacity,
                )
            rooms_state["items"] = rooms
            render_rooms()

        def open_room_modal(room=None) -> None:
            building = selected_building["item"]
            if building is None:
                messagebox.showerror("Аудиторія", "Спочатку виберіть корпус.", parent=self.root)
                return

            is_edit = room is not None
            modal = tk.Toplevel(self.root)
            modal.title("Редагування аудиторії" if is_edit else "Створення аудиторії")
            modal.transient(self.root)
            modal.resizable(False, False)
            modal.grab_set()

            shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
            shell.pack(fill=tk.BOTH, expand=True)
            ttk.Label(shell, text="Редагування аудиторії" if is_edit else "Створення аудиторії", style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(shell, text=f"Корпус: {building.name}", style="CardSubtle.TLabel").pack(anchor="w", pady=(2, 10))

            name_var = tk.StringVar(value=str(room.name) if is_edit else "")
            type_var = tk.StringVar(value=room_type_label_by_enum.get(room.room_type, "Клас") if is_edit else "Клас")
            capacity_var = tk.StringVar(value="" if (not is_edit or room.capacity is None) else str(room.capacity))
            floor_var = tk.StringVar(value="" if (not is_edit or room.floor is None) else str(room.floor))

            ttk.Label(shell, text="Назва", style="Card.TLabel").pack(anchor="w")
            name_entry = ttk.Entry(shell, textvariable=name_var, width=38)
            name_entry.pack(fill=tk.X, pady=(6, 10))

            ttk.Label(shell, text="Тип", style="Card.TLabel").pack(anchor="w")
            ttk.Combobox(
                shell,
                textvariable=type_var,
                values=room_type_choices,
                state="readonly",
                width=24,
            ).pack(fill=tk.X, pady=(6, 10))

            row = ttk.Frame(shell, style="Card.TFrame")
            row.pack(fill=tk.X, pady=(0, 12))
            ttk.Label(row, text="Місткість", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=capacity_var, width=10).pack(side=tk.LEFT, padx=(6, 14))
            ttk.Label(row, text="Поверх", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=floor_var, width=10).pack(side=tk.LEFT, padx=(6, 0))

            actions = ttk.Frame(shell, style="Card.TFrame")
            actions.pack(fill=tk.X)

            def on_submit() -> None:
                clean_name = name_var.get().strip()
                if not clean_name:
                    messagebox.showerror("Некоректні дані", "Назва аудиторії обов'язкова.", parent=modal)
                    return

                selected_type = room_type_by_label.get(type_var.get().strip())
                if selected_type is None:
                    messagebox.showerror("Некоректні дані", "Оберіть тип аудиторії зі списку.", parent=modal)
                    return

                try:
                    capacity = parse_optional_int(capacity_var.get(), field_name="Місткість", allow_negative=False)
                    floor = parse_optional_int(floor_var.get(), field_name="Поверх", allow_negative=True)
                except ValueError as exc:
                    messagebox.showerror("Некоректні дані", str(exc), parent=modal)
                    return

                try:
                    with session_scope() as session:
                        controller = RoomController(session=session)
                        if is_edit:
                            controller.update_room(
                                room.id,
                                name=clean_name,
                                room_type=selected_type,
                                capacity=capacity,
                                floor=floor,
                                is_archived=False,
                            )
                        else:
                            controller.create_room(
                                building_id=building.id,
                                name=clean_name,
                                room_type=selected_type,
                                capacity=capacity,
                                floor=floor,
                                company_id=company_id,
                            )
                except IntegrityError:
                    messagebox.showerror(
                        "Не вдалося зберегти аудиторію",
                        "Аудиторія з такою назвою вже існує в цьому корпусі.",
                        parent=modal,
                    )
                    return
                except Exception as exc:
                    messagebox.showerror("Не вдалося зберегти аудиторію", str(exc), parent=modal)
                    return

                modal.destroy()
                load_rooms()

            self._motion_button(actions, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
            self._motion_button(actions, text="Зберегти", command=on_submit, primary=True, width=130).pack(
                side=tk.RIGHT,
                padx=(0, 8),
            )

            name_entry.focus_set()
            modal.update_idletasks()
            modal.geometry(f"+{self.root.winfo_rootx() + 220}+{self.root.winfo_rooty() + 120}")

        def archive_selected_room() -> None:
            room = get_selected_room()
            if room is None:
                messagebox.showerror("Архівація аудиторії", "Оберіть аудиторію у списку.", parent=self.root)
                return
            if not messagebox.askyesno("Архівація аудиторії", f"Архівувати аудиторію '{room.name}'?", parent=self.root):
                return
            with session_scope() as session:
                controller = RoomController(session=session)
                controller.archive_room(room.id)
            load_rooms()

        def delete_selected_room() -> None:
            room = get_selected_room()
            if room is None:
                messagebox.showerror("Видалення аудиторії", "Оберіть аудиторію у списку.", parent=self.root)
                return
            if not messagebox.askyesno("Видалення аудиторії", f"Видалити аудиторію '{room.name}' назавжди?", parent=self.root):
                return
            try:
                with session_scope() as session:
                    controller = RoomController(session=session)
                    was_deleted = controller.delete_room(room.id)
                if not was_deleted:
                    messagebox.showerror("Видалення аудиторії", "Аудиторію не знайдено.", parent=self.root)
                    return
            except IntegrityError:
                messagebox.showerror(
                    "Видалення аудиторії",
                    "Аудиторію використано в пов'язаних даних і її не можна видалити.",
                    parent=self.root,
                )
                return
            except Exception as exc:
                messagebox.showerror("Видалення аудиторії", str(exc), parent=self.root)
                return
            load_rooms()

        def open_bulk_create_rooms_modal() -> None:
            building = selected_building["item"]
            if building is None:
                messagebox.showerror("Масове створення", "Спочатку виберіть корпус.", parent=self.root)
                return

            modal = tk.Toplevel(self.root)
            modal.title("Масове створення аудиторій")
            modal.transient(self.root)
            modal.resizable(False, False)
            modal.grab_set()

            shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
            shell.pack(fill=tk.BOTH, expand=True)
            ttk.Label(shell, text="Масове створення аудиторій", style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(shell, text=f"Корпус: {building.name}", style="CardSubtle.TLabel").pack(anchor="w", pady=(2, 10))

            mode_var = tk.StringVar(value="range")
            ttk.Radiobutton(shell, text="Діапазон", value="range", variable=mode_var).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Radiobutton(shell, text="Список", value="list", variable=mode_var).pack(side=tk.LEFT)

            prefix_var = tk.StringVar(value=f"{building.name}-")
            start_var = tk.StringVar(value="101")
            end_var = tk.StringVar(value="120")
            step_var = tk.StringVar(value="1")
            exclude_var = tk.StringVar(value="")
            list_text = tk.Text(
                shell,
                height=6,
                width=48,
                bg=self.theme.SURFACE_ALT,
                fg=self.theme.TEXT_PRIMARY,
                insertbackground=self.theme.TEXT_PRIMARY,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=self.theme.BORDER,
                highlightcolor=self.theme.ACCENT,
            )

            grid = ttk.Frame(shell, style="Card.TFrame")
            grid.pack(fill=tk.X, pady=(8, 4))
            ttk.Label(grid, text="Префікс", style="Card.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Entry(grid, textvariable=prefix_var, width=14).grid(row=1, column=0, sticky="w", pady=(4, 8))
            ttk.Label(grid, text="Початок", style="Card.TLabel").grid(row=0, column=1, sticky="w", padx=(10, 0))
            ttk.Entry(grid, textvariable=start_var, width=8).grid(row=1, column=1, sticky="w", padx=(10, 0), pady=(4, 8))
            ttk.Label(grid, text="Кінець", style="Card.TLabel").grid(row=0, column=2, sticky="w", padx=(10, 0))
            ttk.Entry(grid, textvariable=end_var, width=8).grid(row=1, column=2, sticky="w", padx=(10, 0), pady=(4, 8))
            ttk.Label(grid, text="Крок", style="Card.TLabel").grid(row=0, column=3, sticky="w", padx=(10, 0))
            ttk.Entry(grid, textvariable=step_var, width=8).grid(row=1, column=3, sticky="w", padx=(10, 0), pady=(4, 8))
            ttk.Label(grid, text="Виключити (через кому)", style="CardSubtle.TLabel").grid(
                row=2,
                column=0,
                columnspan=4,
                sticky="w",
            )
            ttk.Entry(grid, textvariable=exclude_var, width=40).grid(row=3, column=0, columnspan=4, sticky="ew", pady=(4, 0))

            ttk.Label(shell, text="Список назв: одна назва аудиторії на рядок", style="CardSubtle.TLabel").pack(anchor="w", pady=(4, 0))
            list_text.pack(fill=tk.BOTH, expand=True, pady=(4, 10))

            settings_row = ttk.Frame(shell, style="Card.TFrame")
            settings_row.pack(fill=tk.X, pady=(0, 10))
            type_var = tk.StringVar(value="Клас")
            capacity_var = tk.StringVar(value="")
            floor_var = tk.StringVar(value="")
            policy_var = tk.StringVar(value="Пропустити дублікати")

            ttk.Label(settings_row, text="Тип", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Combobox(settings_row, textvariable=type_var, values=room_type_choices, state="readonly", width=16).pack(
                side=tk.LEFT,
                padx=(6, 10),
            )
            ttk.Label(settings_row, text="Місткість", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Entry(settings_row, textvariable=capacity_var, width=8).pack(side=tk.LEFT, padx=(6, 10))
            ttk.Label(settings_row, text="Поверх", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Entry(settings_row, textvariable=floor_var, width=8).pack(side=tk.LEFT, padx=(6, 10))
            ttk.Label(settings_row, text="Дублікати", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Combobox(
                settings_row,
                textvariable=policy_var,
                values=["Пропустити дублікати", "Зупинити при дублікаті", "Оновити наявні"],
                state="readonly",
                width=17,
            ).pack(side=tk.LEFT, padx=(6, 0))

            footer = ttk.Frame(shell, style="Card.TFrame")
            footer.pack(fill=tk.X)

            def on_submit_bulk() -> None:
                selected_type = room_type_by_label.get(type_var.get().strip())
                if selected_type is None:
                    messagebox.showerror("Некоректні дані", "Оберіть тип аудиторії зі списку.", parent=modal)
                    return

                policy = {
                    "Пропустити дублікати": "skip",
                    "Зупинити при дублікаті": "fail",
                    "Оновити наявні": "update",
                }.get(policy_var.get().strip())
                if policy is None:
                    messagebox.showerror("Некоректні дані", "Оберіть коректну політику дублікатів.", parent=modal)
                    return

                try:
                    capacity = parse_optional_int(capacity_var.get(), field_name="Місткість", allow_negative=False)
                    floor = parse_optional_int(floor_var.get(), field_name="Поверх", allow_negative=True)
                except ValueError as exc:
                    messagebox.showerror("Некоректні дані", str(exc), parent=modal)
                    return

                if mode_var.get() == "list":
                    names = [line.strip() for line in list_text.get("1.0", "end").splitlines() if line.strip()]
                else:
                    try:
                        start = int(start_var.get().strip())
                        end = int(end_var.get().strip())
                        step = int(step_var.get().strip())
                    except ValueError:
                        messagebox.showerror("Некоректні дані", "Початок, кінець і крок мають бути цілими числами.", parent=modal)
                        return
                    if step <= 0 or end < start:
                        messagebox.showerror("Некоректні дані", "Діапазон номерів некоректний.", parent=modal)
                        return
                    excluded = set()
                    raw_excluded = exclude_var.get().strip()
                    if raw_excluded:
                        try:
                            excluded = {
                                int(token.strip())
                                for token in raw_excluded.replace(";", ",").split(",")
                                if token.strip()
                            }
                        except ValueError:
                            messagebox.showerror("Некоректні дані", "Список виключень має містити лише числа.", parent=modal)
                            return
                    prefix = prefix_var.get().strip()
                    names = [f"{prefix}{number}" for number in range(start, end + 1, step) if number not in excluded]

                if not names:
                    messagebox.showerror("Некоректні дані", "Немає назв аудиторій для створення.", parent=modal)
                    return

                try:
                    with session_scope() as session:
                        controller = RoomController(session=session)
                        result = controller.bulk_create_rooms(
                            building_id=building.id,
                            names=names,
                            room_type=selected_type,
                            capacity=capacity,
                            floor=floor,
                            company_id=company_id,
                            duplicate_policy=policy,
                        )
                except IntegrityError:
                    messagebox.showerror("Не вдалося створити аудиторії", "Сталася помилка цілісності даних.", parent=modal)
                    return
                except Exception as exc:
                    messagebox.showerror("Не вдалося створити аудиторії", str(exc), parent=modal)
                    return

                modal.destroy()
                load_rooms()
                messagebox.showinfo(
                    "Масове створення",
                    f"Створено: {result['created']}\nОновлено: {result['updated']}\nПропущено: {result['skipped']}",
                    parent=self.root,
                )

            self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
            self._motion_button(footer, text="Створити", command=on_submit_bulk, primary=True, width=130).pack(
                side=tk.RIGHT,
                padx=(0, 8),
            )

            modal.update_idletasks()
            modal.geometry(f"+{self.root.winfo_rootx() + 210}+{self.root.winfo_rooty() + 90}")

        def sync_cards_scroll(_event=None) -> None:
            viewport_width = max(1, cards_canvas.winfo_width())
            cards_canvas.itemconfigure(cards_window, width=viewport_width)
            bbox = cards_canvas.bbox("all")
            if bbox is not None:
                cards_canvas.configure(scrollregion=bbox)

        def compute_columns(width: int) -> int:
            if width >= 1280:
                return 4
            if width >= 980:
                return 3
            if width >= 680:
                return 2
            return 1

        def render_buildings() -> None:
            for child in cards_grid.winfo_children():
                child.destroy()

            items = buildings_state["items"]
            if not items:
                empty = ttk.Label(
                    cards_grid,
                    text="Ще немає корпусів. Додайте перший корпус.",
                    style="CardSubtle.TLabel",
                )
                empty.grid(row=0, column=0, sticky="w", padx=8, pady=8)
                sync_cards_scroll()
                return

            columns = max(1, int(columns_state["value"]))
            for col in range(columns):
                cards_grid.grid_columnconfigure(col, weight=1, uniform="building-col")

            for index, building in enumerate(items):
                row = index // columns
                col = index % columns
                card = RoundedMotionCard(
                    cards_grid,
                    bg_color=self.theme.SURFACE,
                    card_color=self.theme.SURFACE_ALT,
                    shadow_color=self.theme.SHADOW_SOFT,
                    radius=16,
                    padding=4,
                    shadow_offset=4,
                    motion_enabled=True,
                    height=150,
                )
                card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
                card.content.grid_columnconfigure(0, weight=1)

                title_label = tk.Label(
                    card.content,
                    text=str(building.name),
                    bg=self.theme.SURFACE_ALT,
                    fg=self.theme.TEXT_PRIMARY,
                    font=("Segoe UI", 12, "bold"),
                    anchor="w",
                    justify=tk.LEFT,
                    wraplength=220,
                )
                title_label.grid(row=0, column=0, sticky="ew", pady=(2, 2))
                address_label = tk.Label(
                    card.content,
                    text=str(building.address or "Адресу не вказано"),
                    bg=self.theme.SURFACE_ALT,
                    fg=self.theme.TEXT_MUTED,
                    font=("Segoe UI", 10),
                    anchor="w",
                    justify=tk.LEFT,
                    wraplength=220,
                )
                address_label.grid(row=1, column=0, sticky="ew", pady=(2, 0))
                meta_label = tk.Label(
                    card.content,
                    text=f"ID корпусу: {building.id}",
                    bg=self.theme.SURFACE_ALT,
                    fg=self.theme.TEXT_MUTED,
                    font=("Segoe UI", 9, "bold"),
                    anchor="w",
                )
                meta_label.grid(row=2, column=0, sticky="w", pady=(8, 0))

                def on_card_resize(
                    event: tk.Event,
                    name_ref: tk.Label = title_label,
                    addr_ref: tk.Label = address_label,
                ) -> None:
                    wrap = max(120, event.width - 28)
                    name_ref.configure(wraplength=wrap)
                    addr_ref.configure(wraplength=wrap)

                card.content.bind("<Configure>", on_card_resize, add="+")

                for widget in (card, card.canvas, card.content, title_label, address_label, meta_label):
                    widget.bind("<Button-1>", lambda _e, b=building: open_building_view(b), add="+")

            sync_cards_scroll()

        def load_buildings() -> None:
            with session_scope() as session:
                controller = BuildingController(session=session)
                buildings = controller.list_buildings(company_id=company_id, include_archived=False)
            buildings_state["items"] = buildings

        def on_cards_resize(_event=None) -> None:
            sync_cards_scroll()
            new_columns = compute_columns(cards_canvas.winfo_width())
            if new_columns == columns_state["value"]:
                return
            columns_state["value"] = new_columns
            render_buildings()

        cards_grid.bind("<Configure>", sync_cards_scroll, add="+")
        cards_canvas.bind("<Configure>", on_cards_resize, add="+")

        def on_reset_room_filters() -> None:
            room_search_var.set("")
            room_type_filter_var.set("Усі")
            room_min_capacity_var.set("")
            room_include_archived_var.set(False)
            load_rooms()

        self._motion_button(
            detail_actions,
            text="+ Нова аудиторія",
            command=lambda: open_room_modal(room=None),
            primary=True,
            width=150,
        ).pack(side=tk.RIGHT)
        self._motion_button(
            detail_actions,
            text="+ Масове додавання",
            command=open_bulk_create_rooms_modal,
            primary=False,
            width=170,
        ).pack(side=tk.RIGHT, padx=(0, 8))
        self._motion_button(
            detail_actions,
            text="Редагувати",
            command=lambda: open_room_modal(room=get_selected_room()) if get_selected_room() is not None else messagebox.showerror(
                "Редагування аудиторії",
                "Оберіть аудиторію у списку.",
                parent=self.root,
            ),
            primary=False,
            width=96,
        ).pack(side=tk.RIGHT, padx=(0, 8))
        self._motion_button(
            detail_actions,
            text="Архівувати",
            command=archive_selected_room,
            primary=False,
            width=110,
        ).pack(side=tk.RIGHT, padx=(0, 8))
        self._motion_button(
            detail_actions,
            text="Видалити",
            command=delete_selected_room,
            primary=False,
            width=100,
            fill="#e11d48",
            hover_fill="#be123c",
            pressed_fill="#9f1239",
            text_color=self.theme.TEXT_LIGHT,
        ).pack(side=tk.RIGHT, padx=(0, 8))

        self._motion_button(
            filters_row,
            text="Застосувати",
            command=load_rooms,
            primary=False,
            width=104,
            height=34,
        ).pack(side=tk.RIGHT)
        self._motion_button(
            filters_row,
            text="Скинути",
            command=on_reset_room_filters,
            primary=False,
            width=104,
            height=34,
        ).pack(side=tk.RIGHT, padx=(0, 8))

        room_search_entry.bind("<Return>", lambda _e: load_rooms(), add="+")
        room_capacity_entry.bind("<Return>", lambda _e: load_rooms(), add="+")
        room_type_box.bind("<<ComboboxSelected>>", lambda _e: load_rooms(), add="+")

        def open_create_building_modal() -> None:
            modal = tk.Toplevel(self.root)
            modal.title("Новий корпус")
            modal.transient(self.root)
            modal.resizable(False, False)
            modal.grab_set()

            shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
            shell.pack(fill=tk.BOTH, expand=True)
            ttk.Label(shell, text="Створення корпусу", style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(
                shell,
                text="Назва обов'язкова. Адреса необов'язкова.",
                style="CardSubtle.TLabel",
            ).pack(anchor="w", pady=(2, 10))

            name_var = tk.StringVar()
            address_var = tk.StringVar()

            ttk.Label(shell, text="Назва", style="Card.TLabel").pack(anchor="w")
            name_entry = ttk.Entry(shell, textvariable=name_var, width=44)
            name_entry.pack(fill=tk.X, pady=(6, 10))
            ttk.Label(shell, text="Адреса", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=address_var, width=44).pack(fill=tk.X, pady=(6, 12))

            buttons = ttk.Frame(shell, style="Card.TFrame")
            buttons.pack(fill=tk.X, pady=(2, 0))

            def on_submit() -> None:
                clean_name = name_var.get().strip()
                clean_address = address_var.get().strip()
                if not clean_name:
                    messagebox.showerror("Некоректні дані", "Назва корпусу обов'язкова.", parent=modal)
                    return
                try:
                    with session_scope() as session:
                        controller = BuildingController(session=session)
                        controller.create_building(
                            name=clean_name,
                            address=clean_address or None,
                            company_id=company_id,
                        )
                except IntegrityError:
                    messagebox.showerror(
                        "Не вдалося створити корпус",
                        "Корпус з такою назвою вже існує.",
                        parent=modal,
                    )
                    return
                except Exception as exc:
                    messagebox.showerror("Не вдалося створити корпус", str(exc), parent=modal)
                    return

                modal.destroy()
                load_buildings()
                render_buildings()

            self._motion_button(
                buttons,
                text="Скасувати",
                command=modal.destroy,
                primary=False,
                width=140,
            ).pack(side=tk.RIGHT)
            self._motion_button(
                buttons,
                text="Створити",
                command=on_submit,
                primary=True,
                width=140,
            ).pack(side=tk.RIGHT, padx=(0, 8))

            name_entry.focus_set()
            modal.update_idletasks()
            modal.geometry(
                f"+{self.root.winfo_rootx() + 180}+{self.root.winfo_rooty() + 110}"
            )

        self._motion_button(
            header,
            text="+ Створити корпус",
            command=open_create_building_modal,
            primary=True,
            width=190,
        ).pack(side=tk.RIGHT)

        load_buildings()
        columns_state["value"] = compute_columns(max(1, cards_canvas.winfo_width()))
        render_buildings()
        render_rooms()

    def _build_company_settings_view(self, parent: ttk.Frame, company_id: int, username: str) -> None:
        settings_shell = ttk.Frame(parent, style="Card.TFrame")
        settings_shell.pack(fill=tk.BOTH, expand=True)

        settings_canvas = tk.Canvas(
            settings_shell,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        settings_scroll = ttk.Scrollbar(
            settings_shell,
            orient=tk.VERTICAL,
            command=settings_canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        settings_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        settings_canvas.configure(yscrollcommand=settings_scroll.set)

        body = ttk.Frame(settings_canvas, style="Card.TFrame")
        body_window = settings_canvas.create_window((0, 0), anchor="nw", window=body)

        def _sync_settings_scroll(_event=None) -> None:
            viewport_width = max(1, settings_canvas.winfo_width())
            viewport_height = max(1, settings_canvas.winfo_height())
            requested_height = max(1, body.winfo_reqheight())
            settings_canvas.itemconfigure(
                body_window,
                width=viewport_width,
                height=max(viewport_height, requested_height),
            )
            bbox = settings_canvas.bbox("all")
            if bbox is not None:
                settings_canvas.configure(scrollregion=bbox)

        def _scroll_settings(step_units: int) -> str:
            first, last = settings_canvas.yview()
            visible = float(last) - float(first)
            if visible >= 0.999:
                return "break"
            if step_units < 0 and float(first) <= 0.0001:
                return "break"
            if step_units > 0 and float(last) >= 0.9999:
                return "break"
            settings_canvas.yview_scroll(step_units, "units")
            return "break"

        body.bind("<Configure>", _sync_settings_scroll)
        settings_canvas.bind("<Configure>", _sync_settings_scroll)

        def _on_settings_wheel(event: tk.Event) -> str:
            delta = getattr(event, "delta", 0)
            if not delta:
                return "break"
            direction = -1 if delta > 0 else 1
            steps = max(1, int(abs(delta) / 120))
            for _ in range(steps):
                _scroll_settings(direction)
            return "break"

        def _on_settings_up(_event: tk.Event) -> str:
            return _scroll_settings(-1)

        def _on_settings_down(_event: tk.Event) -> str:
            return _scroll_settings(1)

        for widget in (settings_canvas, body):
            widget.bind("<MouseWheel>", _on_settings_wheel, add="+")
            widget.bind("<Button-4>", _on_settings_up, add="+")
            widget.bind("<Button-5>", _on_settings_down, add="+")

        tabs_bar = ttk.Frame(body, style="Card.TFrame")
        tabs_bar.pack(fill=tk.X, pady=(0, 8))

        content = ttk.Frame(body, style="Card.TFrame")
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
        timezone_default = (profile.timezone or DEFAULT_TIMEZONE).strip()
        language_default_code = (profile.language or DEFAULT_LANGUAGE_CODE).strip().lower()
        theme_default = (profile.theme or UiTheme.DEFAULT_VARIANT).strip().lower()
        logo_default = profile.logo_path

        company_name_var = tk.StringVar(value=company_name_default)
        timezone_var = tk.StringVar(value=timezone_default)
        avatar_storage = AvatarStorageService()
        avatar_state = {
            "current_logo_path": logo_default,
            "pending_source_path": None,
            "remove_current": False,
            "hover": False,
            "image": None,
        }

        theme_label_by_key = {
            "ocean": "Океан",
            "graphite": "Графіт",
            "sunrise": "Світанок",
            "aurora": "Аврора",
            "sand": "Пісок",
            "berry": "Ягідна",
        }
        theme_key_by_label = {label: key for key, label in theme_label_by_key.items()}
        theme_var = tk.StringVar(value=theme_label_by_key.get(theme_default, theme_label_by_key["ocean"]))

        timezone_options = all_timezones()
        if timezone_default not in timezone_options:
            timezone_options.append(timezone_default)
            timezone_options = sorted(timezone_options)

        language_label_by_code = {code: f"{label} ({code})" for code, label in LANGUAGE_OPTIONS}
        language_code_by_label = {value: key for key, value in language_label_by_code.items()}
        language_var = tk.StringVar(
            value=language_label_by_code.get(
                language_default_code,
                language_label_by_code[DEFAULT_LANGUAGE_CODE],
            )
        )

        header_shell = RoundedMotionCard(
            parent,
            bg_color=self.theme.SURFACE,
            card_color=self.theme.SURFACE,
            shadow_color=self.theme.SHADOW_SOFT,
            radius=18,
            padding=4,
            shadow_offset=4,
            motion_enabled=True,
            height=170,
        )
        header_shell.pack(fill=tk.X, pady=(0, 10))
        header_shell.pack_propagate(False)
        header = ttk.Frame(header_shell.content, style="Card.TFrame", padding=8)
        header.pack(fill=tk.BOTH, expand=True)
        header.grid_columnconfigure(1, weight=1)

        avatar_canvas = tk.Canvas(
            header,
            width=132,
            height=132,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            cursor="hand2",
        )
        avatar_canvas.grid(row=0, column=0, rowspan=4, sticky="nw", padx=(0, 16))

        ttk.Label(header, text="Назва компанії", style="Card.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Entry(header, textvariable=company_name_var).grid(row=1, column=1, sticky="ew", pady=(6, 8))
        ttk.Label(header, text=f"Акаунт: {username}", style="CardSubtle.TLabel").grid(row=2, column=1, sticky="w", pady=(0, 2))

        avatar_actions = ttk.Frame(header, style="Card.TFrame")
        avatar_actions.grid(row=3, column=1, sticky="w", pady=(2, 0))
        self._motion_button(
            avatar_actions,
            text="Скинути фото",
            command=lambda: on_remove_avatar(),
            primary=False,
            width=140,
            height=38,
        ).pack(side=tk.LEFT)

        details_shell = RoundedMotionCard(
            parent,
            bg_color=self.theme.SURFACE,
            card_color=self.theme.SURFACE,
            shadow_color=self.theme.SHADOW_SOFT,
            radius=16,
            padding=4,
            shadow_offset=4,
            motion_enabled=True,
            height=128,
        )
        details_shell.pack(fill=tk.X)
        details_shell.pack_propagate(False)
        details = ttk.Frame(details_shell.content, style="Card.TFrame", padding=4)
        details.pack(fill=tk.BOTH, expand=True)
        details.grid_columnconfigure(0, weight=1)
        details.grid_columnconfigure(1, weight=1)
        details.grid_columnconfigure(2, weight=1)

        timezone_col = ttk.Frame(details, style="Card.TFrame")
        timezone_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(timezone_col, text="Часовий пояс", style="Card.TLabel").pack(anchor="w", pady=(0, 4))
        timezone_box = ttk.Combobox(timezone_col, textvariable=timezone_var, values=timezone_options, state="readonly")
        timezone_box.pack(fill=tk.X)

        language_col = ttk.Frame(details, style="Card.TFrame")
        language_col.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        ttk.Label(language_col, text="Мова", style="Card.TLabel").pack(anchor="w", pady=(0, 4))
        language_box = ttk.Combobox(
            language_col,
            textvariable=language_var,
            values=[language_label_by_code[code] for code, _ in LANGUAGE_OPTIONS],
            state="readonly",
        )
        language_box.pack(fill=tk.X)

        theme_col = ttk.Frame(details, style="Card.TFrame")
        theme_col.grid(row=0, column=2, sticky="nsew")
        ttk.Label(theme_col, text="Тема", style="Card.TLabel").pack(anchor="w", pady=(0, 4))
        theme_box = ttk.Combobox(
            theme_col,
            textvariable=theme_var,
            values=[theme_label_by_key[key] for key in ("ocean", "graphite", "sunrise", "aurora", "sand", "berry")],
            state="readonly",
        )
        theme_box.pack(fill=tk.X)

        def _resolve_preview_path() -> str | None:
            pending_source = avatar_state["pending_source_path"]
            if pending_source:
                return str(pending_source)
            if avatar_state["remove_current"]:
                return None
            current_logo_path = avatar_state["current_logo_path"]
            if not current_logo_path:
                return None
            return str(current_logo_path)

        def _draw_avatar() -> None:
            avatar_canvas.delete("all")
            center_x = 66
            center_y = 66
            size = 110
            image_path = _resolve_preview_path()
            photo = self._build_rounded_avatar_photo(image_path, size) if image_path else None
            avatar_state["image"] = photo

            if photo is None:
                draw_default_company_avatar(
                    avatar_canvas,
                    x=center_x,
                    y=center_y,
                    size=size,
                    circle_fill=self.theme.AVATAR_CIRCLE_BG,
                    building_fill=self.theme.AVATAR_BUILDING,
                    window_fill=self.theme.AVATAR_WINDOW,
                    outline=self.theme.AVATAR_CIRCLE_BORDER,
                )
            else:
                avatar_canvas.create_oval(
                    center_x - size // 2 - 2,
                    center_y - size // 2 - 2,
                    center_x + size // 2 + 2,
                    center_y + size // 2 + 2,
                    fill=self.theme.AVATAR_CIRCLE_BG,
                    outline=self.theme.AVATAR_CIRCLE_BORDER,
                    width=2,
                )
                avatar_canvas.create_image(center_x, center_y, image=photo)

            if avatar_state["hover"]:
                avatar_canvas.create_oval(
                    center_x - size // 2,
                    center_y - size // 2,
                    center_x + size // 2,
                    center_y + size // 2,
                    fill=self.theme.AVATAR_OVERLAY,
                    outline="",
                    stipple="gray50",
                )
                avatar_canvas.create_text(
                    center_x,
                    center_y,
                    text="Змінити фото",
                    fill=self.theme.TEXT_LIGHT,
                    font=("Segoe UI", 10, "bold"),
                )

        def on_pick_avatar() -> None:
            selected = filedialog.askopenfilename(
                title="Оберіть фото профілю",
                filetypes=[
                    ("Зображення", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"),
                    ("Усі файли", "*.*"),
                ],
            )
            if not selected:
                return
            avatar_state["pending_source_path"] = selected
            avatar_state["remove_current"] = False
            _draw_avatar()

        def on_remove_avatar() -> None:
            avatar_state["pending_source_path"] = None
            avatar_state["remove_current"] = True
            _draw_avatar()

        def on_avatar_enter(_event=None) -> None:
            avatar_state["hover"] = True
            _draw_avatar()

        def on_avatar_leave(_event=None) -> None:
            avatar_state["hover"] = False
            _draw_avatar()

        avatar_canvas.bind("<Enter>", on_avatar_enter, add="+")
        avatar_canvas.bind("<Leave>", on_avatar_leave, add="+")
        avatar_canvas.bind("<Button-1>", lambda _e: on_pick_avatar(), add="+")

        _draw_avatar()

        def on_reset() -> None:
            company_name_var.set(company_name_default)
            timezone_var.set(timezone_default)
            language_var.set(
                language_label_by_code.get(
                    language_default_code,
                    language_label_by_code[DEFAULT_LANGUAGE_CODE],
                )
            )
            theme_var.set(theme_label_by_key.get(theme_default, theme_label_by_key["ocean"]))
            avatar_state["pending_source_path"] = None
            avatar_state["remove_current"] = False
            avatar_state["current_logo_path"] = logo_default
            _draw_avatar()

        def on_save_profile() -> None:
            selected_theme = theme_key_by_label.get(theme_var.get().strip(), UiTheme.DEFAULT_VARIANT)
            selected_language = language_code_by_label.get(language_var.get().strip(), DEFAULT_LANGUAGE_CODE)
            existing_logo_path = str(avatar_state["current_logo_path"]) if avatar_state["current_logo_path"] else None
            pending_source = str(avatar_state["pending_source_path"]) if avatar_state["pending_source_path"] else None
            remove_current = bool(avatar_state["remove_current"])
            new_logo_path: str | None = existing_logo_path
            update_logo = False
            generated_logo_path: str | None = None

            try:
                if pending_source:
                    generated_logo_path = avatar_storage.save_company_avatar(
                        company_id=company_id,
                        source_path=pending_source,
                    )
                    new_logo_path = generated_logo_path
                    update_logo = True
                elif remove_current:
                    new_logo_path = None
                    update_logo = True

                with session_scope() as session:
                    controller = AuthController(session=session)
                    controller.update_company_profile(
                        company_id=company_id,
                        company_name=company_name_var.get().strip(),
                        timezone=timezone_var.get().strip(),
                        theme=selected_theme,
                        language=selected_language,
                        logo_path=new_logo_path,
                        update_logo_path=update_logo,
                    )
            except IntegrityError:
                if generated_logo_path:
                    avatar_storage.delete_avatar(generated_logo_path)
                messagebox.showerror("Не вдалося зберегти", "Компанія з такою назвою вже існує.")
                return
            except Exception as exc:
                if generated_logo_path:
                    avatar_storage.delete_avatar(generated_logo_path)
                messagebox.showerror("Не вдалося зберегти", str(exc))
                return

            if update_logo and existing_logo_path and existing_logo_path != new_logo_path:
                avatar_storage.delete_avatar(existing_logo_path)

            self._show_company_dashboard(initial_view="settings")

        controls = ttk.Frame(parent, style="Card.TFrame")
        controls.pack(fill=tk.X, pady=(10, 0))
        self._motion_button(
            controls,
            text="Зберегти зміни",
            command=on_save_profile,
            primary=True,
            width=200,
        ).pack(side=tk.LEFT)
        self._motion_button(
            controls,
            text="Скинути",
            command=on_reset,
            primary=False,
            width=140,
        ).pack(side=tk.LEFT, padx=(8, 0))

    def _build_company_settings_templates_tab(self, parent: ttk.Frame, *, company_id: int) -> None:
        CompanyTemplatesTab(
            parent=parent,
            company_id=company_id,
            theme=self.theme,
            motion_button_factory=self._motion_button,
        ).build()

    def _build_company_settings_system_tab(self, parent: ttk.Frame, *, company_id: int, username: str) -> None:
        ttk.Label(parent, text="Система", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 2))
        ttk.Label(
            parent,
            text="Системні функції будуть розширюватися у наступних фазах.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        info = ttk.Frame(parent, style="Card.TFrame")
        info.pack(fill=tk.X)
        ttk.Label(info, text=f"ID компанії: {company_id}", style="Card.TLabel").pack(anchor="w")
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


