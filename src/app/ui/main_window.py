from __future__ import annotations

from datetime import date, datetime, time, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4

from PIL import Image, ImageDraw, ImageTk, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError

from app.config.database import session_scope
from app.controllers.academic_controller import AcademicController
from app.controllers.auth_controller import AuthController
from app.controllers.building_controller import BuildingController
from app.controllers.calendar_controller import CalendarController
from app.controllers.requirement_controller import RequirementController
from app.controllers.resource_controller import ResourceController
from app.controllers.room_controller import RoomController
from app.controllers.schedule_validation_controller import ScheduleValidationController
from app.controllers.schedule_view_controller import ScheduleViewController
from app.controllers.scheduler_controller import SchedulerController
from app.domain.enums import MarkKind, ResourceType, RoomType, TimePreference, UserRole
from app.domain.models import User
from app.repositories.calendar_repository import CalendarRepository
from app.services.avatar_storage import AvatarStorageService
from app.services.schedule_visualization import WEEKDAY_LABELS
from app.ui.avatar_template import draw_default_company_avatar
from app.ui.curriculum_tab import CompanyCurriculumTab
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
        for key in ("schedule", "groups", "rooms", "curriculum", "settings"):
            frame = ttk.Frame(views_container, style="Card.TFrame", padding=18)
            views[key] = frame

        nav_buttons: dict[str, RoundedMotionButton] = {}

        def _set_nav_button_active(button: RoundedMotionButton, *, active: bool) -> None:
            if active:
                button.fill = self.theme.ACCENT
                button.hover_fill = self.theme.ACCENT_HOVER
                button.pressed_fill = self.theme.ACCENT_PRESSED
                button.text_color = self.theme.TEXT_LIGHT
                button.shadow_color = self.theme.SIDEBAR_BUTTON_SHADOW
            else:
                button.fill = self.theme.SIDEBAR_BUTTON_FILL
                button.hover_fill = self.theme.SIDEBAR_BUTTON_HOVER
                button.pressed_fill = self.theme.SIDEBAR_BUTTON_PRESSED
                button.text_color = self.theme.SIDEBAR_BUTTON_TEXT
                button.shadow_color = self.theme.SIDEBAR_BUTTON_SHADOW
            button._state = "normal"
            button._lift = 0
            button._draw()

        def _refresh_nav_buttons(active_name: str) -> None:
            for key, button in nav_buttons.items():
                _set_nav_button_active(button, active=(key == active_name))

        def open_view(name: str) -> None:
            for frame in views.values():
                frame.pack_forget()
            views[name].pack(fill=tk.BOTH, expand=True)
            _refresh_nav_buttons(name)

        def _add_nav_button(*, key: str, label: str) -> None:
            button = self._motion_button(
                sidebar,
                text=label,
                command=lambda tab=key: open_view(tab),
                primary=True,
                width=224,
                height=44,
                canvas_bg=self.theme.SIDEBAR_BG,
                fill=self.theme.SIDEBAR_BUTTON_FILL,
                hover_fill=self.theme.SIDEBAR_BUTTON_HOVER,
                pressed_fill=self.theme.SIDEBAR_BUTTON_PRESSED,
                text_color=self.theme.SIDEBAR_BUTTON_TEXT,
                shadow_color=self.theme.SIDEBAR_BUTTON_SHADOW,
            )
            button.pack(pady=(0, 6), anchor="w")
            nav_buttons[key] = button

        _add_nav_button(key="schedule", label="Розклад")
        _add_nav_button(key="groups", label="Групи")
        _add_nav_button(key="rooms", label="Приміщення")
        _add_nav_button(key="curriculum", label="Навчальні плани")
        _add_nav_button(key="settings", label="Налаштування")

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
        self._build_company_curriculum_view(views["curriculum"], user.company_id)
        self._build_company_settings_view(views["settings"], user.company_id, user.username)

        selected_view = initial_view if initial_view in views else "schedule"
        open_view(selected_view)

    def _build_company_schedule_view(self, parent: ttk.Frame, company_id: int) -> None:
        period_var = tk.StringVar()
        week_start_var = tk.StringVar()
        group_filter_var = tk.StringVar(value="Усі групи")
        scenario_var = tk.StringVar(value="Опублікований")
        scenario_compare_var = tk.StringVar(value="Опублікований")
        status_var = tk.StringVar(value="Готово.")

        subject_name_var = tk.StringVar()
        subject_duration_var = tk.StringVar(value="1")
        subject_sessions_var = tk.StringVar(value="4")
        subject_max_week_var = tk.StringVar(value="2")
        subject_teacher_var = tk.StringVar()
        subject_target_var = tk.StringVar(value="Група")
        subject_group_var = tk.StringVar()
        subject_stream_var = tk.StringVar()
        subject_room_type_var = tk.StringVar(value="Не важливо")
        subject_min_capacity_var = tk.StringVar()
        subject_needs_projector_var = tk.BooleanVar(value=False)
        subject_fixed_room_var = tk.StringVar(value="Авто")

        blackout_scope_var = tk.StringVar(value="Викладач")
        blackout_resource_var = tk.StringVar()
        blackout_start_var = tk.StringVar()
        blackout_end_var = tk.StringVar()
        blackout_title_var = tk.StringVar()
        blackout_batch_start_date_var = tk.StringVar()
        blackout_batch_end_date_var = tk.StringVar()
        blackout_batch_start_time_var = tk.StringVar(value="08:30")
        blackout_batch_end_time_var = tk.StringVar(value="18:00")
        blackout_batch_weekdays_var = tk.StringVar(value="1,2,3,4,5")
        coverage_summary_var = tk.StringVar(value="Coverage: —")

        room_type_options: list[tuple[str, RoomType | None]] = [
            ("Не важливо", None),
            ("Лекційна", RoomType.LECTURE_HALL),
            ("Клас", RoomType.CLASSROOM),
            ("Лабораторія", RoomType.LAB),
            ("Комп'ютерна", RoomType.COMPUTER_LAB),
            ("Інше", RoomType.OTHER),
        ]
        room_type_by_label = {label: room_type for label, room_type in room_type_options}
        room_type_labels = [label for label, _ in room_type_options]

        blackout_scope_options: list[tuple[str, ResourceType]] = [
            ("Викладач", ResourceType.TEACHER),
            ("Група", ResourceType.GROUP),
            ("Аудиторія", ResourceType.ROOM),
        ]
        blackout_scope_type_by_label = {label: resource_type for label, resource_type in blackout_scope_options}
        blackout_scope_labels = [label for label, _ in blackout_scope_options]
        blackout_resource_values_by_scope: dict[str, list[str]] = {label: [] for label in blackout_scope_labels}
        blackout_resource_name_by_id: dict[int, str] = {}
        blackout_resource_scope_by_id: dict[int, str] = {}
        room_type_label_by_enum = {room_type: label for label, room_type in room_type_options if room_type is not None}
        requirements_state: dict[str, list[dict[str, object]]] = {"items": []}
        scenario_values_state: dict[str, list[str]] = {"values": ["Опублікований"]}

        policy_max_sessions_var = tk.StringVar(value="4")
        policy_max_consecutive_var = tk.StringVar(value="3")
        policy_no_gaps_var = tk.BooleanVar(value=False)
        policy_time_pref_var = tk.StringVar(value="Баланс")
        policy_weight_time_var = tk.StringVar(value="2")
        policy_weight_compact_var = tk.StringVar(value="3")
        policy_weight_building_var = tk.StringVar(value="2")
        policy_time_pref_options = {
            "Баланс": TimePreference.BALANCED,
            "Ранок": TimePreference.MORNING,
            "Вечір": TimePreference.EVENING,
        }

        manual_requirement_var = tk.StringVar()
        manual_date_var = tk.StringVar()
        manual_order_var = tk.StringVar(value="1")
        manual_room_var = tk.StringVar(value="Авто")
        manual_lock_var = tk.BooleanVar(value=True)

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

        ttk.Label(header, text="Сценарій", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 0))
        scenario_box = ttk.Combobox(header, textvariable=scenario_var, width=22, state="readonly")
        scenario_box.grid(row=2, column=1, sticky="w", padx=(6, 10), pady=(8, 0))

        ttk.Label(header, text="Порівняти з", style="Card.TLabel").grid(row=2, column=2, sticky="w", pady=(8, 0))
        scenario_compare_box = ttk.Combobox(header, textvariable=scenario_compare_var, width=22, state="readonly")
        scenario_compare_box.grid(row=2, column=3, sticky="w", padx=(6, 10), pady=(8, 0))
        scenario_compare_button = ttk.Button(header, text="Порівняти")
        scenario_compare_button.grid(row=2, column=4, sticky="w", pady=(8, 0))
        scenario_publish_button = ttk.Button(header, text="Опублікувати")
        scenario_publish_button.grid(row=2, column=5, sticky="w", padx=(6, 0), pady=(8, 0))

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
        ttk.Label(subject_box, text="Ціль").grid(row=1, column=2, sticky="w", pady=(8, 0))
        subject_target_box = ttk.Combobox(
            subject_box,
            textvariable=subject_target_var,
            values=["Група", "Потік"],
            width=10,
            state="readonly",
        )
        subject_target_box.grid(row=1, column=3, sticky="w", padx=(6, 12), pady=(8, 0))
        ttk.Label(subject_box, text="Група").grid(row=1, column=4, sticky="w", pady=(8, 0))
        subject_group_box = ttk.Combobox(subject_box, textvariable=subject_group_var, width=20, state="readonly")
        subject_group_box.grid(row=1, column=5, sticky="w", padx=(6, 12), pady=(8, 0))
        ttk.Label(subject_box, text="Потік").grid(row=1, column=6, sticky="w", pady=(8, 0))
        subject_stream_box = ttk.Combobox(subject_box, textvariable=subject_stream_var, width=22, state="readonly")
        subject_stream_box.grid(row=1, column=7, sticky="w", padx=(6, 0), pady=(8, 0))
        ttk.Label(subject_box, text="Тип аудиторії").grid(row=2, column=0, sticky="w", pady=(8, 0))
        subject_room_type_box = ttk.Combobox(
            subject_box,
            textvariable=subject_room_type_var,
            values=room_type_labels,
            width=20,
            state="readonly",
        )
        subject_room_type_box.grid(row=2, column=1, sticky="w", padx=(6, 12), pady=(8, 0))
        ttk.Label(subject_box, text="Мін. місткість").grid(row=2, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(subject_box, textvariable=subject_min_capacity_var, width=6).grid(
            row=2, column=3, sticky="w", padx=(6, 12), pady=(8, 0)
        )
        ttk.Checkbutton(
            subject_box,
            text="Потрібен проєктор",
            variable=subject_needs_projector_var,
        ).grid(row=2, column=4, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(subject_box, text="Фікс. аудиторія").grid(row=2, column=6, sticky="w", pady=(8, 0))
        subject_fixed_room_box = ttk.Combobox(subject_box, textvariable=subject_fixed_room_var, width=22, state="readonly")
        subject_fixed_room_box.grid(row=2, column=7, sticky="w", padx=(6, 0), pady=(8, 0))

        blackout_box = ttk.LabelFrame(parent, text="Недоступності ресурсів", padding=10)
        blackout_box.pack(fill=tk.X, pady=(8, 0))
        blackout_box.columnconfigure(1, weight=1)
        blackout_box.columnconfigure(3, weight=1)

        ttk.Label(blackout_box, text="Ресурс").grid(row=0, column=0, sticky="w")
        blackout_scope_box = ttk.Combobox(
            blackout_box,
            textvariable=blackout_scope_var,
            values=blackout_scope_labels,
            width=11,
            state="readonly",
        )
        blackout_scope_box.grid(row=0, column=1, sticky="w", padx=(6, 12))
        blackout_resource_box = ttk.Combobox(
            blackout_box,
            textvariable=blackout_resource_var,
            width=34,
            state="readonly",
        )
        blackout_resource_box.grid(row=0, column=2, columnspan=2, sticky="ew", padx=(0, 12))
        ttk.Label(blackout_box, text="Початок").grid(row=0, column=4, sticky="w")
        ttk.Entry(blackout_box, textvariable=blackout_start_var, width=17).grid(row=0, column=5, sticky="w", padx=(6, 12))
        ttk.Label(blackout_box, text="Кінець").grid(row=0, column=6, sticky="w")
        ttk.Entry(blackout_box, textvariable=blackout_end_var, width=17).grid(row=0, column=7, sticky="w", padx=(6, 0))

        ttk.Label(blackout_box, text="Причина").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(blackout_box, textvariable=blackout_title_var).grid(
            row=1,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=(6, 12),
            pady=(8, 0),
        )
        blackout_add_button = ttk.Button(blackout_box, text="Додати blackout")
        blackout_add_button.grid(row=1, column=5, sticky="w", padx=(6, 12), pady=(8, 0))
        blackout_delete_button = ttk.Button(blackout_box, text="Видалити")
        blackout_delete_button.grid(row=1, column=6, sticky="w", padx=(0, 12), pady=(8, 0))
        blackout_reload_button = ttk.Button(blackout_box, text="Оновити")
        blackout_reload_button.grid(row=1, column=7, sticky="w", pady=(8, 0))

        ttk.Label(blackout_box, text="Пакет: з дати").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(blackout_box, textvariable=blackout_batch_start_date_var, width=12).grid(
            row=2, column=1, sticky="w", padx=(6, 12), pady=(8, 0)
        )
        ttk.Label(blackout_box, text="по дату").grid(row=2, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(blackout_box, textvariable=blackout_batch_end_date_var, width=12).grid(
            row=2, column=3, sticky="w", padx=(6, 12), pady=(8, 0)
        )
        ttk.Label(blackout_box, text="час").grid(row=2, column=4, sticky="w", pady=(8, 0))
        ttk.Entry(blackout_box, textvariable=blackout_batch_start_time_var, width=8).grid(
            row=2, column=5, sticky="w", padx=(6, 6), pady=(8, 0)
        )
        ttk.Entry(blackout_box, textvariable=blackout_batch_end_time_var, width=8).grid(
            row=2, column=6, sticky="w", padx=(0, 12), pady=(8, 0)
        )
        blackout_batch_button = ttk.Button(blackout_box, text="Додати пакет")
        blackout_batch_button.grid(row=2, column=7, sticky="w", pady=(8, 0))

        ttk.Label(blackout_box, text="Дні тижня (1-7, через кому)").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(blackout_box, textvariable=blackout_batch_weekdays_var, width=28).grid(
            row=3,
            column=1,
            columnspan=3,
            sticky="w",
            padx=(6, 12),
            pady=(8, 0),
        )

        blackout_table_wrap = ttk.Frame(blackout_box, style="Card.TFrame")
        blackout_table_wrap.grid(row=4, column=0, columnspan=8, sticky="ew", pady=(10, 0))
        blackout_table = ttk.Treeview(
            blackout_table_wrap,
            columns=("resource", "start", "end", "title"),
            show="headings",
            height=5,
        )
        blackout_table.heading("resource", text="Ресурс")
        blackout_table.heading("start", text="Початок")
        blackout_table.heading("end", text="Кінець")
        blackout_table.heading("title", text="Причина")
        blackout_table.column("resource", width=280, anchor="w")
        blackout_table.column("start", width=160, anchor="center")
        blackout_table.column("end", width=160, anchor="center")
        blackout_table.column("title", width=300, anchor="w")
        blackout_table.pack(side=tk.LEFT, fill=tk.X, expand=True)
        blackout_scroll = ttk.Scrollbar(blackout_table_wrap, orient=tk.VERTICAL, command=blackout_table.yview)
        blackout_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        blackout_table.configure(yscrollcommand=blackout_scroll.set)

        requirements_box = ttk.LabelFrame(parent, text="Вимоги", padding=10)
        requirements_box.pack(fill=tk.X, pady=(8, 0))
        requirements_actions = ttk.Frame(requirements_box, style="Card.TFrame")
        requirements_actions.pack(fill=tk.X, pady=(0, 6))
        requirements_refresh_button = ttk.Button(requirements_actions, text="Оновити")
        requirements_refresh_button.pack(side=tk.LEFT, padx=(0, 8))
        requirements_edit_button = ttk.Button(requirements_actions, text="Редагувати")
        requirements_edit_button.pack(side=tk.LEFT, padx=(0, 8))
        requirements_delete_button = ttk.Button(requirements_actions, text="Видалити")
        requirements_delete_button.pack(side=tk.LEFT)

        requirements_table_wrap = ttk.Frame(requirements_box, style="Card.TFrame")
        requirements_table_wrap.pack(fill=tk.X)
        requirements_table = ttk.Treeview(
            requirements_table_wrap,
            columns=("name", "params", "teacher", "target", "room"),
            show="headings",
            height=6,
        )
        requirements_table.heading("name", text="Назва")
        requirements_table.heading("params", text="Параметри")
        requirements_table.heading("teacher", text="Викладачі")
        requirements_table.heading("target", text="Цілі")
        requirements_table.heading("room", text="Аудиторія")
        requirements_table.column("name", width=220, anchor="w")
        requirements_table.column("params", width=180, anchor="center")
        requirements_table.column("teacher", width=190, anchor="w")
        requirements_table.column("target", width=190, anchor="w")
        requirements_table.column("room", width=290, anchor="w")
        requirements_table.pack(side=tk.LEFT, fill=tk.X, expand=True)
        requirements_scroll = ttk.Scrollbar(requirements_table_wrap, orient=tk.VERTICAL, command=requirements_table.yview)
        requirements_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        requirements_table.configure(yscrollcommand=requirements_scroll.set)

        policy_box = ttk.LabelFrame(parent, text="Політика генерації", padding=10)
        policy_box.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(policy_box, text="Макс пар/день").grid(row=0, column=0, sticky="w")
        ttk.Entry(policy_box, textvariable=policy_max_sessions_var, width=8).grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(policy_box, text="Макс підряд блоків").grid(row=0, column=2, sticky="w")
        ttk.Entry(policy_box, textvariable=policy_max_consecutive_var, width=8).grid(row=0, column=3, sticky="w", padx=(6, 12))
        ttk.Checkbutton(policy_box, text="Заборонити вікна", variable=policy_no_gaps_var).grid(
            row=0, column=4, sticky="w", padx=(0, 12)
        )
        ttk.Label(policy_box, text="Перевага часу").grid(row=0, column=5, sticky="w")
        ttk.Combobox(
            policy_box,
            textvariable=policy_time_pref_var,
            values=list(policy_time_pref_options.keys()),
            state="readonly",
            width=10,
        ).grid(row=0, column=6, sticky="w", padx=(6, 12))
        ttk.Label(policy_box, text="W час").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(policy_box, textvariable=policy_weight_time_var, width=8).grid(row=1, column=1, sticky="w", padx=(6, 12), pady=(8, 0))
        ttk.Label(policy_box, text="W компактність").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(policy_box, textvariable=policy_weight_compact_var, width=8).grid(
            row=1, column=3, sticky="w", padx=(6, 12), pady=(8, 0)
        )
        ttk.Label(policy_box, text="W переходи").grid(row=1, column=4, sticky="w", pady=(8, 0))
        ttk.Entry(policy_box, textvariable=policy_weight_building_var, width=8).grid(
            row=1, column=5, sticky="w", padx=(6, 12), pady=(8, 0)
        )
        policy_save_button = ttk.Button(policy_box, text="Зберегти політику")
        policy_save_button.grid(row=1, column=6, sticky="w", pady=(8, 0))

        manual_box = ttk.LabelFrame(parent, text="Ручний слот", padding=10)
        manual_box.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(manual_box, text="Вимога").grid(row=0, column=0, sticky="w")
        manual_requirement_box = ttk.Combobox(
            manual_box,
            textvariable=manual_requirement_var,
            width=34,
            state="readonly",
        )
        manual_requirement_box.grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(manual_box, text="Дата").grid(row=0, column=2, sticky="w")
        ttk.Entry(manual_box, textvariable=manual_date_var, width=12).grid(row=0, column=3, sticky="w", padx=(6, 12))
        ttk.Label(manual_box, text="Номер блоку").grid(row=0, column=4, sticky="w")
        ttk.Entry(manual_box, textvariable=manual_order_var, width=8).grid(row=0, column=5, sticky="w", padx=(6, 12))
        ttk.Label(manual_box, text="Аудиторія").grid(row=0, column=6, sticky="w")
        manual_room_box = ttk.Combobox(manual_box, textvariable=manual_room_var, width=24, state="readonly")
        manual_room_box.grid(row=0, column=7, sticky="w", padx=(6, 12))
        ttk.Checkbutton(manual_box, text="Закріпити (LOCK)", variable=manual_lock_var).grid(row=1, column=0, sticky="w", pady=(8, 0))
        manual_add_button = ttk.Button(manual_box, text="Додати ручний слот")
        manual_add_button.grid(row=1, column=1, sticky="w", pady=(8, 0))

        coverage_box = ttk.LabelFrame(parent, text="Coverage dashboard", padding=10)
        coverage_box.pack(fill=tk.X, pady=(8, 0))
        coverage_actions = ttk.Frame(coverage_box, style="Card.TFrame")
        coverage_actions.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(coverage_actions, textvariable=coverage_summary_var, style="CardSubtle.TLabel").pack(side=tk.LEFT)
        coverage_refresh_button = ttk.Button(coverage_actions, text="Оновити coverage")
        coverage_refresh_button.pack(side=tk.RIGHT)
        coverage_table_wrap = ttk.Frame(coverage_box, style="Card.TFrame")
        coverage_table_wrap.pack(fill=tk.X)
        coverage_table = ttk.Treeview(
            coverage_table_wrap,
            columns=("reason", "requirements", "missing", "message"),
            show="headings",
            height=4,
        )
        coverage_table.heading("reason", text="Причина")
        coverage_table.heading("requirements", text="Вимог")
        coverage_table.heading("missing", text="Не закрито занять")
        coverage_table.heading("message", text="Приклад")
        coverage_table.column("reason", width=170, anchor="center")
        coverage_table.column("requirements", width=90, anchor="center")
        coverage_table.column("missing", width=150, anchor="center")
        coverage_table.column("message", width=520, anchor="w")
        coverage_table.pack(side=tk.LEFT, fill=tk.X, expand=True)
        coverage_scroll = ttk.Scrollbar(coverage_table_wrap, orient=tk.VERTICAL, command=coverage_table.yview)
        coverage_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        coverage_table.configure(yscrollcommand=coverage_scroll.set)

        buttons = ttk.Frame(parent, style="Card.TFrame")
        buttons.pack(fill=tk.X, pady=(8, 8))

        status = ttk.Label(parent, textvariable=status_var, anchor="w", style="CardSubtle.TLabel")
        status.pack(fill=tk.X)

        def parse_period_id() -> int:
            raw = period_var.get().strip()
            if not raw:
                raise ValueError("Оберіть період.")
            return int(raw.split("|", maxsplit=1)[0].strip())

        def parse_scenario_id(raw: str) -> int | None:
            value = raw.strip()
            if not value or value == "Опублікований":
                return None
            return int(value.split("|", maxsplit=1)[0].strip())

        def selected_scenario_id() -> int | None:
            return parse_scenario_id(scenario_var.get())

        def parse_week_start() -> date | None:
            raw = week_start_var.get().strip()
            if not raw:
                return None
            return date.fromisoformat(raw)

        def parse_prefixed_id(raw: str, *, field_name: str) -> int:
            value = raw.strip()
            if not value or "|" not in value:
                raise ValueError(f"Оберіть '{field_name}'.")
            return int(value.split("|", maxsplit=1)[0].strip())

        def parse_optional_positive_int(raw: str, *, field_name: str) -> int | None:
            value = raw.strip()
            if not value:
                return None
            try:
                parsed = int(value)
            except ValueError as exc:
                raise ValueError(f"Поле '{field_name}' має бути цілим числом.") from exc
            if parsed <= 0:
                raise ValueError(f"Поле '{field_name}' має бути більше нуля.")
            return parsed

        def parse_non_negative_int(raw: str, *, field_name: str) -> int:
            value = raw.strip()
            if not value:
                raise ValueError(f"Заповніть поле '{field_name}'.")
            try:
                parsed = int(value)
            except ValueError as exc:
                raise ValueError(f"Поле '{field_name}' має бути цілим числом.") from exc
            if parsed < 0:
                raise ValueError(f"Поле '{field_name}' має бути невід'ємним.")
            return parsed

        def parse_datetime_input(raw: str, *, field_name: str) -> datetime:
            value = raw.strip()
            if not value:
                raise ValueError(f"Заповніть поле '{field_name}'.")
            normalized = value.replace("T", " ")
            try:
                return datetime.fromisoformat(normalized)
            except ValueError as exc:
                raise ValueError(f"Поле '{field_name}' має формат YYYY-MM-DD HH:MM.") from exc

        def parse_date_input(raw: str, *, field_name: str) -> date:
            value = raw.strip()
            if not value:
                raise ValueError(f"Заповніть поле '{field_name}'.")
            try:
                return date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(f"Поле '{field_name}' має формат YYYY-MM-DD.") from exc

        def parse_time_input(raw: str, *, field_name: str) -> time:
            value = raw.strip()
            if not value:
                raise ValueError(f"Заповніть поле '{field_name}'.")
            try:
                return time.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(f"Поле '{field_name}' має формат HH:MM.") from exc

        def parse_weekdays(raw: str) -> set[int]:
            value = raw.strip()
            if not value:
                raise ValueError("Вкажіть дні тижня для пакетного blackout.")
            result: set[int] = set()
            for token in value.split(","):
                stripped = token.strip()
                if not stripped:
                    continue
                try:
                    weekday = int(stripped)
                except ValueError as exc:
                    raise ValueError("Дні тижня мають бути числами 1..7.") from exc
                if weekday < 1 or weekday > 7:
                    raise ValueError("Дні тижня мають бути в межах 1..7.")
                result.add(weekday)
            if not result:
                raise ValueError("Вкажіть хоча б один день тижня.")
            return result

        def selected_group_resource_id() -> int | None:
            raw = group_filter_var.get().strip()
            if not raw or raw == "Усі групи":
                return None
            return parse_prefixed_id(raw, field_name="група")

        def selected_teacher_resource_id() -> int:
            raw = subject_teacher_var.get().strip()
            if not raw:
                raise ValueError("Оберіть викладача.")
            return parse_prefixed_id(raw, field_name="викладач")

        def selected_subject_group_id() -> int:
            raw = subject_group_var.get().strip()
            if not raw:
                raise ValueError("Оберіть групу для предмета.")
            return parse_prefixed_id(raw, field_name="група")

        def selected_subject_stream_id() -> int:
            raw = subject_stream_var.get().strip()
            if not raw:
                raise ValueError("Оберіть потік для предмета.")
            return parse_prefixed_id(raw, field_name="потік")

        def selected_subject_target() -> str:
            normalized = subject_target_var.get().strip().lower()
            value = {"група": "GROUP", "потік": "STREAM"}.get(normalized)
            if value is None:
                raise ValueError("Оберіть ціль предмета: група або потік.")
            return value

        def selected_room_type() -> RoomType | None:
            label = subject_room_type_var.get().strip() or "Не важливо"
            if label not in room_type_by_label:
                raise ValueError("Оберіть тип аудиторії.")
            return room_type_by_label[label]

        def selected_fixed_room_id() -> int | None:
            raw = subject_fixed_room_var.get().strip()
            if not raw or raw == "Авто":
                return None
            return parse_prefixed_id(raw, field_name="фіксована аудиторія")

        def selected_blackout_scope() -> str:
            scope = blackout_scope_var.get().strip()
            if scope not in blackout_scope_type_by_label:
                raise ValueError("Оберіть тип ресурсу для blackout.")
            return scope

        def selected_blackout_resource_id() -> int:
            raw = blackout_resource_var.get().strip()
            if not raw:
                raise ValueError("Оберіть ресурс для blackout.")
            return parse_prefixed_id(raw, field_name="ресурс blackout")

        def selected_manual_requirement_id() -> int:
            raw = manual_requirement_var.get().strip()
            if not raw:
                raise ValueError("Оберіть вимогу для ручного слота.")
            return parse_prefixed_id(raw, field_name="вимога")

        def selected_manual_room_resource_id() -> int | None:
            raw = manual_room_var.get().strip()
            if not raw or raw == "Авто":
                return None
            return parse_prefixed_id(raw, field_name="аудиторія")

        def refresh_subject_target_controls() -> None:
            is_stream = selected_subject_target() == "STREAM"
            subject_group_box.configure(state="disabled" if is_stream else "readonly")
            subject_stream_box.configure(state="readonly" if is_stream else "disabled")

        def refresh_blackout_resource_choices() -> None:
            scope = selected_blackout_scope()
            values = blackout_resource_values_by_scope.get(scope, [])
            blackout_resource_box["values"] = values
            if values and blackout_resource_var.get() not in values:
                blackout_resource_var.set(values[0])
            if not values:
                blackout_resource_var.set("")

        def load_blackouts() -> None:
            with session_scope() as session:
                controller = ResourceController(session=session)
                blackouts = controller.list_blackouts(company_id=company_id)

            for item_id in blackout_table.get_children():
                blackout_table.delete(item_id)
            for blackout in blackouts:
                resource_id = int(blackout.resource_id)
                scope_label = blackout_resource_scope_by_id.get(resource_id, "Ресурс")
                resource_name = blackout_resource_name_by_id.get(resource_id, f"#{resource_id}")
                resource_label = f"{scope_label}: {resource_name}"
                blackout_table.insert(
                    "",
                    tk.END,
                    iid=str(blackout.id),
                    values=(
                        resource_label,
                        blackout.starts_at.strftime("%Y-%m-%d %H:%M"),
                        blackout.ends_at.strftime("%Y-%m-%d %H:%M"),
                        blackout.title or "—",
                    ),
                )

        def load_coverage_dashboard() -> None:
            try:
                period_id = parse_period_id()
                scenario_id = selected_scenario_id()
            except Exception:
                coverage_summary_var.set("Coverage: —")
                for item_id in coverage_table.get_children():
                    coverage_table.delete(item_id)
                return

            try:
                with session_scope() as session:
                    dashboard = SchedulerController(session=session).get_coverage_dashboard(
                        calendar_period_id=period_id,
                        scenario_id=scenario_id,
                    )
            except Exception as exc:
                coverage_summary_var.set(f"Coverage: помилка ({exc})")
                return

            coverage_summary_var.set(
                "Coverage: "
                f"вимог {dashboard.covered_requirements}/{dashboard.total_requirements}, "
                f"сесій {dashboard.total_sessions_scheduled}/{dashboard.total_sessions_required}, "
                f"не закрито вимог {dashboard.uncovered_requirements}"
            )
            for item_id in coverage_table.get_children():
                coverage_table.delete(item_id)
            for index, reason in enumerate(dashboard.reasons[:12], start=1):
                coverage_table.insert(
                    "",
                    tk.END,
                    iid=f"coverage_{index}",
                    values=(
                        reason.code,
                        str(reason.requirements_count),
                        str(reason.sessions_missing),
                        reason.sample_message,
                    ),
                )

        def selected_requirement_id() -> int | None:
            selected = requirements_table.selection()
            if not selected:
                return None
            return int(selected[0])

        def _compact_names(values: list[str], *, limit: int = 2) -> str:
            if not values:
                return "—"
            if len(values) <= limit:
                return ", ".join(values)
            return f"{', '.join(values[:limit])} +{len(values) - limit}"

        def _format_room_constraints(requirement, room_name_by_profile_id: dict[int, str]) -> str:
            parts: list[str] = []
            if requirement.room_type is not None:
                parts.append(room_type_label_by_enum.get(requirement.room_type, requirement.room_type.value))
            if requirement.min_capacity is not None:
                parts.append(f"≥ {requirement.min_capacity} місць")
            if requirement.needs_projector:
                parts.append("проєктор")
            if requirement.fixed_room_id is not None:
                room_label = room_name_by_profile_id.get(int(requirement.fixed_room_id), f"#{requirement.fixed_room_id}")
                parts.append(f"фікс: {room_label}")
            if not parts:
                return "без обмежень"
            return ", ".join(parts)

        def render_requirements() -> None:
            for item_id in requirements_table.get_children():
                requirements_table.delete(item_id)
            for item in requirements_state["items"]:
                requirements_table.insert(
                    "",
                    tk.END,
                    iid=str(item["id"]),
                    values=(
                        str(item["name"]),
                        str(item["params"]),
                        str(item["teachers"]),
                        str(item["targets"]),
                        str(item["room_constraints"]),
                    ),
                )

        def load_requirements() -> None:
            with session_scope() as session:
                req_controller = RequirementController(session=session)
                resource_controller = ResourceController(session=session)
                room_controller = RoomController(session=session)

                requirements = req_controller.list_requirements(company_id=company_id)
                resources = resource_controller.list_resources(company_id=company_id)
                room_profiles = room_controller.list_rooms(company_id=company_id, include_archived=True)

                resource_by_id = {int(resource.id): resource for resource in resources}
                room_name_by_profile_id = {int(room.id): str(room.name) for room in room_profiles}
                rows: list[dict[str, object]] = []

                for requirement in requirements:
                    links = req_controller.list_requirement_resources(requirement_id=int(requirement.id))
                    teachers: list[str] = []
                    targets: list[str] = []

                    for link in links:
                        resource = resource_by_id.get(int(link.resource_id))
                        if resource is None:
                            continue
                        if resource.type == ResourceType.TEACHER:
                            teachers.append(str(resource.name))
                        elif resource.type in {ResourceType.GROUP, ResourceType.SUBGROUP}:
                            targets.append(str(resource.name))

                    rows.append(
                        {
                            "id": int(requirement.id),
                            "label": f"{int(requirement.id)} | {str(requirement.name)}",
                            "name": str(requirement.name),
                            "params": (
                                f"{int(requirement.duration_blocks)} бл. | "
                                f"{int(requirement.sessions_total)} зан. | "
                                f"{int(requirement.max_per_week)} / тиж."
                            ),
                            "teachers": _compact_names(teachers),
                            "targets": _compact_names(targets),
                            "room_constraints": _format_room_constraints(requirement, room_name_by_profile_id),
                        }
                    )

            requirements_state["items"] = rows
            render_requirements()
            manual_values = [str(item["label"]) for item in rows]
            manual_requirement_box["values"] = manual_values
            if manual_values and manual_requirement_var.get() not in manual_values:
                manual_requirement_var.set(manual_values[0])
            if not manual_values:
                manual_requirement_var.set("")

        def open_requirement_edit_modal() -> None:
            requirement_id = selected_requirement_id()
            if requirement_id is None:
                messagebox.showwarning("Редагування вимоги", "Оберіть вимогу у списку.")
                return

            with session_scope() as session:
                req_controller = RequirementController(session=session)
                resource_controller = ResourceController(session=session)
                room_controller = RoomController(session=session)
                requirement = req_controller.get_requirement(requirement_id=requirement_id)
                requirement_links = (
                    req_controller.list_requirement_resources(requirement_id=requirement_id)
                    if requirement is not None
                    else []
                )
                room_profiles = room_controller.list_rooms(company_id=company_id, include_archived=True)
                teacher_resources = resource_controller.list_resources(
                    resource_type=ResourceType.TEACHER,
                    company_id=company_id,
                )
                group_resources = resource_controller.list_resources(
                    resource_type=ResourceType.GROUP,
                    company_id=company_id,
                )
                subgroup_resources = resource_controller.list_resources(
                    resource_type=ResourceType.SUBGROUP,
                    company_id=company_id,
                )
            if requirement is None:
                messagebox.showerror("Редагування вимоги", "Вимогу не знайдено.")
                load_requirements()
                return

            teacher_resource_ids = {int(resource.id) for resource in teacher_resources}
            group_resource_ids = {int(resource.id) for resource in group_resources}
            subgroup_resource_ids = {int(resource.id) for resource in subgroup_resources}
            assigned_teacher_ids: set[int] = set()
            assigned_group_ids: set[int] = set()
            assigned_subgroup_ids: set[int] = set()

            for link in requirement_links:
                resource_id = int(link.resource_id)
                if resource_id in teacher_resource_ids:
                    assigned_teacher_ids.add(resource_id)
                elif resource_id in group_resource_ids:
                    assigned_group_ids.add(resource_id)
                elif resource_id in subgroup_resource_ids:
                    assigned_subgroup_ids.add(resource_id)

            modal = tk.Toplevel(self.root)
            modal.title(f"Вимога #{requirement.id}")
            modal.transient(self.root)
            modal.grab_set()
            modal.resizable(False, False)
            body = ttk.Frame(modal, padding=12)
            body.pack(fill=tk.BOTH, expand=True)

            name_var = tk.StringVar(value=str(requirement.name))
            duration_var = tk.StringVar(value=str(requirement.duration_blocks))
            sessions_var = tk.StringVar(value=str(requirement.sessions_total))
            max_week_var = tk.StringVar(value=str(requirement.max_per_week))
            room_type_var = tk.StringVar(
                value=room_type_label_by_enum.get(requirement.room_type, "Не важливо")
                if requirement.room_type is not None
                else "Не важливо"
            )
            min_capacity_var = tk.StringVar(value="" if requirement.min_capacity is None else str(requirement.min_capacity))
            needs_projector_var = tk.BooleanVar(value=bool(requirement.needs_projector))

            fixed_room_values = ["Авто"] + [f"{room.id} | {room.name}" for room in room_profiles]
            fixed_room_var = tk.StringVar(value="Авто")
            if requirement.fixed_room_id is not None:
                for value in fixed_room_values:
                    if value.startswith(f"{int(requirement.fixed_room_id)} |"):
                        fixed_room_var.set(value)
                        break

            ttk.Label(body, text="Назва").grid(row=0, column=0, sticky="w")
            ttk.Entry(body, textvariable=name_var, width=44).grid(row=0, column=1, columnspan=3, sticky="w", padx=(8, 0))
            ttk.Label(body, text="Тривалість (блоків)").grid(row=1, column=0, sticky="w", pady=(8, 0))
            ttk.Entry(body, textvariable=duration_var, width=8).grid(row=1, column=1, sticky="w", padx=(8, 12), pady=(8, 0))
            ttk.Label(body, text="Кількість занять").grid(row=1, column=2, sticky="w", pady=(8, 0))
            ttk.Entry(body, textvariable=sessions_var, width=8).grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(8, 0))
            ttk.Label(body, text="Макс/тиждень").grid(row=2, column=0, sticky="w", pady=(8, 0))
            ttk.Entry(body, textvariable=max_week_var, width=8).grid(row=2, column=1, sticky="w", padx=(8, 12), pady=(8, 0))
            ttk.Label(body, text="Тип аудиторії").grid(row=2, column=2, sticky="w", pady=(8, 0))
            ttk.Combobox(
                body,
                textvariable=room_type_var,
                values=room_type_labels,
                state="readonly",
                width=18,
            ).grid(row=2, column=3, sticky="w", padx=(8, 0), pady=(8, 0))
            ttk.Label(body, text="Мін. місткість").grid(row=3, column=0, sticky="w", pady=(8, 0))
            ttk.Entry(body, textvariable=min_capacity_var, width=8).grid(row=3, column=1, sticky="w", padx=(8, 12), pady=(8, 0))
            ttk.Checkbutton(body, text="Потрібен проєктор", variable=needs_projector_var).grid(
                row=3, column=2, columnspan=2, sticky="w", pady=(8, 0)
            )
            ttk.Label(body, text="Фікс. аудиторія").grid(row=4, column=0, sticky="w", pady=(8, 0))
            ttk.Combobox(
                body,
                textvariable=fixed_room_var,
                values=fixed_room_values,
                state="readonly",
                width=30,
            ).grid(row=4, column=1, columnspan=3, sticky="w", padx=(8, 0), pady=(8, 0))

            resources_shell = ttk.LabelFrame(body, text="Прив'язки ресурсів", padding=8)
            resources_shell.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(12, 0))
            resources_shell.columnconfigure(0, weight=1)
            resources_shell.columnconfigure(1, weight=1)
            resources_shell.columnconfigure(2, weight=1)

            teacher_values = [f"{resource.id} | {resource.name}" for resource in teacher_resources]
            group_values = [f"{resource.id} | {resource.name}" for resource in group_resources]
            subgroup_values = [f"{resource.id} | {resource.name}" for resource in subgroup_resources]

            teacher_wrap = ttk.Frame(resources_shell, style="Card.TFrame")
            teacher_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            ttk.Label(teacher_wrap, text="Викладачі").pack(anchor="w")
            teacher_list_wrap = ttk.Frame(teacher_wrap, style="Card.TFrame")
            teacher_list_wrap.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
            teacher_listbox = tk.Listbox(
                teacher_list_wrap,
                selectmode=tk.EXTENDED,
                exportselection=False,
                height=7,
                width=26,
            )
            teacher_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            teacher_scroll = ttk.Scrollbar(teacher_list_wrap, orient=tk.VERTICAL, command=teacher_listbox.yview)
            teacher_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            teacher_listbox.configure(yscrollcommand=teacher_scroll.set)

            group_wrap = ttk.Frame(resources_shell, style="Card.TFrame")
            group_wrap.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
            ttk.Label(group_wrap, text="Групи").pack(anchor="w")
            group_list_wrap = ttk.Frame(group_wrap, style="Card.TFrame")
            group_list_wrap.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
            group_listbox = tk.Listbox(
                group_list_wrap,
                selectmode=tk.EXTENDED,
                exportselection=False,
                height=7,
                width=26,
            )
            group_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            group_scroll = ttk.Scrollbar(group_list_wrap, orient=tk.VERTICAL, command=group_listbox.yview)
            group_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            group_listbox.configure(yscrollcommand=group_scroll.set)

            subgroup_wrap = ttk.Frame(resources_shell, style="Card.TFrame")
            subgroup_wrap.grid(row=0, column=2, sticky="nsew")
            ttk.Label(subgroup_wrap, text="Підгрупи").pack(anchor="w")
            subgroup_list_wrap = ttk.Frame(subgroup_wrap, style="Card.TFrame")
            subgroup_list_wrap.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
            subgroup_listbox = tk.Listbox(
                subgroup_list_wrap,
                selectmode=tk.EXTENDED,
                exportselection=False,
                height=7,
                width=26,
            )
            subgroup_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            subgroup_scroll = ttk.Scrollbar(subgroup_list_wrap, orient=tk.VERTICAL, command=subgroup_listbox.yview)
            subgroup_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            subgroup_listbox.configure(yscrollcommand=subgroup_scroll.set)

            for row in teacher_values:
                teacher_listbox.insert(tk.END, row)
            for index, row in enumerate(teacher_values):
                if parse_prefixed_id(row, field_name="викладач") in assigned_teacher_ids:
                    teacher_listbox.selection_set(index)

            for row in group_values:
                group_listbox.insert(tk.END, row)
            for index, row in enumerate(group_values):
                if parse_prefixed_id(row, field_name="група") in assigned_group_ids:
                    group_listbox.selection_set(index)

            for row in subgroup_values:
                subgroup_listbox.insert(tk.END, row)
            for index, row in enumerate(subgroup_values):
                if parse_prefixed_id(row, field_name="підгрупа") in assigned_subgroup_ids:
                    subgroup_listbox.selection_set(index)

            actions = ttk.Frame(body, style="Card.TFrame")
            actions.grid(row=6, column=0, columnspan=4, sticky="e", pady=(12, 0))

            def selected_ids_from_listbox(listbox: tk.Listbox, *, field_name: str) -> set[int]:
                result: set[int] = set()
                for selected_index in listbox.curselection():
                    result.add(parse_prefixed_id(str(listbox.get(selected_index)), field_name=field_name))
                return result

            def save_requirement() -> None:
                try:
                    name = name_var.get().strip()
                    if not name:
                        raise ValueError("Назва вимоги не може бути порожньою.")
                    duration = int(duration_var.get().strip())
                    sessions_total = int(sessions_var.get().strip())
                    max_per_week = int(max_week_var.get().strip())
                    room_type_label = room_type_var.get().strip() or "Не важливо"
                    if room_type_label not in room_type_by_label:
                        raise ValueError("Оберіть тип аудиторії.")
                    room_type = room_type_by_label[room_type_label]
                    min_capacity = parse_optional_positive_int(min_capacity_var.get(), field_name="Мін. місткість")
                    fixed_room_id = None if fixed_room_var.get().strip() == "Авто" else parse_prefixed_id(
                        fixed_room_var.get(), field_name="фіксована аудиторія"
                    )
                    selected_teacher_ids = selected_ids_from_listbox(teacher_listbox, field_name="викладач")
                    selected_group_ids = selected_ids_from_listbox(group_listbox, field_name="група")
                    selected_subgroup_ids = selected_ids_from_listbox(subgroup_listbox, field_name="підгрупа")
                    if not selected_teacher_ids:
                        raise ValueError("Оберіть хоча б одного викладача.")
                    if not selected_group_ids and not selected_subgroup_ids:
                        raise ValueError("Оберіть хоча б одну групу або підгрупу.")
                    with session_scope() as session:
                        req_controller = RequirementController(session=session)
                        resource_controller = ResourceController(session=session)
                        req_controller.update_requirement(
                            requirement_id=requirement_id,
                            name=name,
                            duration_blocks=duration,
                            sessions_total=sessions_total,
                            max_per_week=max_per_week,
                            room_type=room_type,
                            min_capacity=min_capacity,
                            needs_projector=bool(needs_projector_var.get()),
                            fixed_room_id=fixed_room_id,
                        )
                        resources = resource_controller.list_resources(company_id=company_id)
                        resource_type_by_id = {int(resource.id): resource.type for resource in resources}
                        current_links = req_controller.list_requirement_resources(requirement_id=requirement_id)
                        for link in current_links:
                            resource_type = resource_type_by_id.get(int(link.resource_id))
                            if resource_type in {ResourceType.TEACHER, ResourceType.GROUP, ResourceType.SUBGROUP}:
                                req_controller.unassign_resource(
                                    requirement_id=requirement_id,
                                    resource_id=int(link.resource_id),
                                    role=str(link.role),
                                )

                        for resource_id in sorted(selected_teacher_ids):
                            req_controller.assign_resource(
                                requirement_id=requirement_id,
                                resource_id=resource_id,
                                role="TEACHER",
                            )
                        for resource_id in sorted(selected_group_ids):
                            req_controller.assign_resource(
                                requirement_id=requirement_id,
                                resource_id=resource_id,
                                role="GROUP",
                            )
                        for resource_id in sorted(selected_subgroup_ids):
                            req_controller.assign_resource(
                                requirement_id=requirement_id,
                                resource_id=resource_id,
                                role="SUBGROUP",
                            )
                except Exception as exc:
                    messagebox.showerror("Редагування вимоги", str(exc), parent=modal)
                    return
                modal.destroy()
                load_requirements()
                status_var.set(f"Вимогу #{requirement_id} оновлено.")

            self._motion_button(actions, text="Зберегти", command=save_requirement, primary=True, width=120).pack(
                side=tk.LEFT, padx=(0, 8)
            )
            self._motion_button(actions, text="Скасувати", command=modal.destroy, primary=False, width=120).pack(
                side=tk.LEFT
            )

        def on_delete_requirement() -> None:
            requirement_id = selected_requirement_id()
            if requirement_id is None:
                messagebox.showwarning("Видалення вимоги", "Оберіть вимогу у списку.")
                return
            if not messagebox.askyesno("Видалення вимоги", f"Видалити вимогу #{requirement_id}?", parent=self.root):
                return
            try:
                with session_scope() as session:
                    deleted = RequirementController(session=session).delete_requirement(requirement_id=requirement_id)
                    if not deleted:
                        raise ValueError("Вимогу не знайдено або вже видалено.")
            except Exception as exc:
                messagebox.showerror("Видалення вимоги", str(exc))
                return
            load_requirements()
            on_load_week()
            status_var.set(f"Вимогу #{requirement_id} видалено.")

        def load_scenarios(*, period_id: int | None = None) -> None:
            resolved_period_id = period_id
            if resolved_period_id is None:
                try:
                    resolved_period_id = parse_period_id()
                except Exception:
                    resolved_period_id = None

            values = ["Опублікований"]
            if resolved_period_id is not None:
                with session_scope() as session:
                    scenarios = SchedulerController(session=session).list_scenarios(
                        calendar_period_id=resolved_period_id
                    )
                for scenario in scenarios:
                    published_suffix = " [опублік.]" if scenario.is_published else ""
                    values.append(
                        f"{scenario.id} | {scenario.name}{published_suffix} ({scenario.entries_count})"
                    )

            scenario_values_state["values"] = values
            scenario_box["values"] = values
            scenario_compare_box["values"] = values
            if scenario_var.get() not in values:
                scenario_var.set(values[0])
            if scenario_compare_var.get() not in values:
                scenario_compare_var.set(values[0])

        def on_create_scenarios_ab() -> None:
            try:
                period_id = parse_period_id()
                created_names: list[str] = []
                with session_scope() as session:
                    controller = SchedulerController(session=session)
                    existing = controller.list_scenarios(calendar_period_id=period_id)
                    existing_names = {str(item.name).strip().lower() for item in existing}
                    for name in ("Чернетка A", "Чернетка B"):
                        if name.lower() in existing_names:
                            continue
                        controller.create_scenario(
                            calendar_period_id=period_id,
                            name=name,
                            copy_from_published=True,
                        )
                        created_names.append(name)
            except Exception as exc:
                messagebox.showerror("Сценарії", str(exc))
                return
            load_scenarios(period_id=period_id)
            if created_names:
                status_var.set(f"Створено сценарії: {', '.join(created_names)}.")
            else:
                status_var.set("Чернетки A/B вже існують.")

        def on_publish_scenario() -> None:
            try:
                period_id = parse_period_id()
                scenario_id = selected_scenario_id()
                if scenario_id is None:
                    raise ValueError("Оберіть чернетку для публікації.")
                with session_scope() as session:
                    published_entries = SchedulerController(session=session).publish_scenario(
                        scenario_id=scenario_id
                    )
            except Exception as exc:
                messagebox.showerror("Публікація сценарію", str(exc))
                return
            load_scenarios(period_id=period_id)
            on_load_week()
            status_var.set(f"Опубліковано сценарій #{scenario_id}. Занять: {published_entries}.")

        def on_compare_scenarios() -> None:
            try:
                period_id = parse_period_id()
                left_id = selected_scenario_id()
                right_id = parse_scenario_id(scenario_compare_var.get())
                with session_scope() as session:
                    comparison = SchedulerController(session=session).compare_scenarios(
                        calendar_period_id=period_id,
                        left_scenario_id=left_id,
                        right_scenario_id=right_id,
                    )
            except Exception as exc:
                messagebox.showerror("Порівняння сценаріїв", str(exc))
                return
            lines = [
                f"{comparison.left_label} vs {comparison.right_label}",
                f"Тільки ліворуч: {comparison.only_left_count}",
                f"Тільки праворуч: {comparison.only_right_count}",
                f"Змінені вимоги: {comparison.changed_count}",
            ]
            if comparison.items:
                lines.append("")
                lines.append("Приклади різниці:")
                lines.extend(f"[{item.code}] {item.message}" for item in comparison.items[:8])
            messagebox.showinfo("Порівняння сценаріїв", "\n".join(lines))
            status_var.set(
                f"Порівняння: left={comparison.only_left_count}, "
                f"right={comparison.only_right_count}, changed={comparison.changed_count}."
            )

        def on_period_changed() -> None:
            try:
                period_id = parse_period_id()
            except Exception:
                load_scenarios(period_id=None)
                load_coverage_dashboard()
                return
            load_scenarios(period_id=period_id)
            on_load_week()

        def load_reference_data() -> None:
            with session_scope() as session:
                calendar = CalendarController(session=session)
                periods = calendar.list_calendar_periods(company_id=company_id)
                resources = ResourceController(session=session)
                groups = resources.list_resources(resource_type=ResourceType.GROUP, company_id=company_id)
                teachers = resources.list_resources(resource_type=ResourceType.TEACHER, company_id=company_id)
                rooms = resources.list_resources(resource_type=ResourceType.ROOM, company_id=company_id)
                room_profiles = RoomController(session=session).list_rooms(company_id=company_id, include_archived=False)
                streams = AcademicController(session=session).list_streams(company_id=company_id, include_archived=False)

            period_values = [f"{item.id} | {item.start_date}..{item.end_date}" for item in periods]
            period_box["values"] = period_values
            if period_values and not period_var.get():
                period_var.set(period_values[0])
            if not period_values:
                period_var.set("")
                status_var.set("Періоди відсутні. Створи період у налаштуваннях або кнопкою нижче.")
            try:
                load_scenarios(period_id=parse_period_id())
            except Exception:
                load_scenarios(period_id=None)

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

            stream_values = []
            for stream in streams:
                year_suffix = f" • набір {stream.admission_year}" if stream.admission_year is not None else ""
                stream_values.append(f"{stream.id} | {stream.name}{year_suffix}")
            subject_stream_box["values"] = stream_values
            if stream_values and (subject_stream_var.get() not in stream_values):
                subject_stream_var.set(stream_values[0])
            if not stream_values:
                subject_stream_var.set("")

            room_values = [f"{item.id} | {item.name}" for item in rooms]
            room_profile_values = [f"{item.id} | {item.name}" for item in room_profiles]
            subject_fixed_room_box["values"] = ["Авто"] + room_profile_values
            if subject_fixed_room_var.get() not in subject_fixed_room_box["values"]:
                subject_fixed_room_var.set("Авто")
            manual_room_box["values"] = ["Авто"] + room_values
            if manual_room_var.get() not in manual_room_box["values"]:
                manual_room_var.set("Авто")
            if period_values and not manual_date_var.get():
                try:
                    period_start = str(period_values[0].split("|", maxsplit=1)[1].split("..", maxsplit=1)[0]).strip()
                    manual_date_var.set(period_start)
                except Exception:
                    pass
            if period_values and (not blackout_batch_start_date_var.get() or not blackout_batch_end_date_var.get()):
                try:
                    period_range = str(period_values[0].split("|", maxsplit=1)[1]).strip()
                    period_start = period_range.split("..", maxsplit=1)[0].strip()
                    period_end = period_range.split("..", maxsplit=1)[1].strip()
                    if not blackout_batch_start_date_var.get():
                        blackout_batch_start_date_var.set(period_start)
                    if not blackout_batch_end_date_var.get():
                        blackout_batch_end_date_var.set(period_end)
                except Exception:
                    pass

            blackout_resource_values_by_scope["Викладач"] = teacher_values
            blackout_resource_values_by_scope["Група"] = group_values
            blackout_resource_values_by_scope["Аудиторія"] = room_values

            blackout_resource_name_by_id.clear()
            blackout_resource_scope_by_id.clear()
            for resource in teachers:
                blackout_resource_name_by_id[int(resource.id)] = str(resource.name)
                blackout_resource_scope_by_id[int(resource.id)] = "Викладач"
            for resource in groups:
                blackout_resource_name_by_id[int(resource.id)] = str(resource.name)
                blackout_resource_scope_by_id[int(resource.id)] = "Група"
            for resource in rooms:
                blackout_resource_name_by_id[int(resource.id)] = str(resource.name)
                blackout_resource_scope_by_id[int(resource.id)] = "Аудиторія"

            try:
                refresh_subject_target_controls()
            except ValueError:
                subject_target_var.set("Група")
                refresh_subject_target_controls()
            try:
                refresh_blackout_resource_choices()
            except ValueError:
                blackout_scope_var.set("Викладач")
                refresh_blackout_resource_choices()

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
                scenario_id = selected_scenario_id()
                with session_scope() as session:
                    grid = ScheduleViewController(session=session).get_weekly_grid(
                        calendar_period_id=period_id,
                        week_start=week_start,
                        resource_id=resource_id,
                        scenario_id=scenario_id,
                    )
            except Exception as exc:
                messagebox.showerror("Не вдалося завантажити розклад", str(exc))
                return
            render_grid(grid)
            scope_label = "опублікований" if selected_scenario_id() is None else "чернетка"
            status_var.set(f"Завантажено тиждень {grid.week_start}. Рядків: {len(grid.rows)}. Режим: {scope_label}.")
            load_coverage_dashboard()

        def on_build_schedule() -> None:
            try:
                period_id = parse_period_id()
                scenario_id = selected_scenario_id()
                with session_scope() as session:
                    result = SchedulerController(session=session).build_schedule(
                        period_id,
                        replace_existing=True,
                        scenario_id=scenario_id,
                    )
            except Exception as exc:
                messagebox.showerror("Не вдалося згенерувати розклад", str(exc))
                return
            status_var.set(
                f"Генерацію завершено. Створено: {len(result.created_entries)} | "
                f"Нерозміщено занять: {sum(result.unscheduled_sessions.values())}"
            )
            if result.diagnostics:
                details = "\n".join(f"[{item.code}] {item.message}" for item in result.diagnostics[:12])
                messagebox.showwarning("Діагностика конфліктів", details)
            on_load_week()

        def on_validate() -> None:
            try:
                period_id = parse_period_id()
                scenario_id = selected_scenario_id()
                with session_scope() as session:
                    report = ScheduleValidationController(session=session).validate_schedule(
                        period_id,
                        scenario_id=scenario_id,
                    )
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

        def load_policy() -> None:
            try:
                with session_scope() as session:
                    policy = SchedulerController(session=session).get_policy(company_id=company_id)
            except Exception as exc:
                messagebox.showerror("Політика генерації", str(exc))
                return
            policy_max_sessions_var.set("" if policy.max_sessions_per_day is None else str(policy.max_sessions_per_day))
            policy_max_consecutive_var.set("" if policy.max_consecutive_blocks is None else str(policy.max_consecutive_blocks))
            policy_no_gaps_var.set(bool(policy.enforce_no_gaps))
            reverse_map = {value: label for label, value in policy_time_pref_options.items()}
            normalized_pref = policy.time_preference if isinstance(policy.time_preference, TimePreference) else TimePreference.BALANCED
            policy_time_pref_var.set(reverse_map.get(normalized_pref, "Баланс"))
            policy_weight_time_var.set(str(policy.weight_time_preference))
            policy_weight_compact_var.set(str(policy.weight_compactness))
            policy_weight_building_var.set(str(policy.weight_building_transition))

        def on_save_policy() -> None:
            try:
                max_sessions = parse_optional_positive_int(policy_max_sessions_var.get(), field_name="Макс пар/день")
                max_consecutive = parse_optional_positive_int(policy_max_consecutive_var.get(), field_name="Макс підряд блоків")
                pref_label = policy_time_pref_var.get().strip() or "Баланс"
                if pref_label not in policy_time_pref_options:
                    raise ValueError("Оберіть коректну часову перевагу.")
                weight_time = parse_non_negative_int(policy_weight_time_var.get(), field_name="W час")
                weight_compact = parse_non_negative_int(policy_weight_compact_var.get(), field_name="W компактність")
                weight_building = parse_non_negative_int(policy_weight_building_var.get(), field_name="W переходи")
                with session_scope() as session:
                    SchedulerController(session=session).update_policy(
                        company_id=company_id,
                        max_sessions_per_day=max_sessions,
                        max_consecutive_blocks=max_consecutive,
                        enforce_no_gaps=bool(policy_no_gaps_var.get()),
                        time_preference=policy_time_pref_options[pref_label].value,
                        weight_time_preference=weight_time,
                        weight_compactness=weight_compact,
                        weight_building_transition=weight_building,
                    )
            except Exception as exc:
                messagebox.showerror("Політика генерації", str(exc))
                return
            status_var.set("Політику генерації збережено.")

        def on_check_feasibility() -> None:
            try:
                period_id = parse_period_id()
                scenario_id = selected_scenario_id()
                with session_scope() as session:
                    report = SchedulerController(session=session).analyze_feasibility(
                        calendar_period_id=period_id,
                        replace_existing=True,
                        scenario_id=scenario_id,
                    )
            except Exception as exc:
                messagebox.showerror("Перевірка здійсненності", str(exc))
                return
            if report.is_feasible:
                messagebox.showinfo("Перевірка здійсненності", "Ознак нерозв'язності не знайдено.")
                status_var.set("Перевірка здійсненності успішна.")
                return
            details = "\n".join(f"[{issue.code}] {issue.message}" for issue in report.issues[:10])
            messagebox.showwarning("Перевірка здійсненності", details)
            status_var.set(f"Знайдено ризиків: {len(report.issues)}")

        def on_add_subject() -> None:
            try:
                name = subject_name_var.get().strip()
                if not name:
                    raise ValueError("Вкажіть назву предмета.")
                duration = int(subject_duration_var.get().strip())
                sessions_total = int(subject_sessions_var.get().strip())
                max_per_week = int(subject_max_week_var.get().strip())
                teacher_id = selected_teacher_resource_id()
                target_mode = selected_subject_target()
                room_type = selected_room_type()
                min_capacity = parse_optional_positive_int(subject_min_capacity_var.get(), field_name="Мін. місткість")
                needs_projector = bool(subject_needs_projector_var.get())
                fixed_room_id = selected_fixed_room_id()

                with session_scope() as session:
                    req_controller = RequirementController(session=session)
                    resource_controller = ResourceController(session=session)
                    requirement = req_controller.create_requirement(
                        name=name,
                        duration_blocks=duration,
                        sessions_total=sessions_total,
                        max_per_week=max_per_week,
                        company_id=company_id,
                        room_type=room_type,
                        min_capacity=min_capacity,
                        needs_projector=needs_projector,
                        fixed_room_id=fixed_room_id,
                    )
                    req_controller.assign_resource(requirement.id, teacher_id, "TEACHER")

                    if target_mode == "STREAM":
                        stream_id = selected_subject_stream_id()
                        stream_groups = resource_controller.list_resources(
                            resource_type=ResourceType.GROUP,
                            company_id=company_id,
                            stream_id=stream_id,
                        )
                        if not stream_groups:
                            raise ValueError("У вибраному потоці немає жодної групи.")
                        for group in stream_groups:
                            req_controller.assign_resource(requirement.id, group.id, "GROUP")
                    else:
                        group_id = selected_subject_group_id()
                        req_controller.assign_resource(requirement.id, group_id, "GROUP")
            except Exception as exc:
                messagebox.showerror("Не вдалося додати предмет", str(exc))
                return
            load_requirements()
            target_label = "потоку" if selected_subject_target() == "STREAM" else "групи"
            status_var.set(f"Предмет '{name}' додано для {target_label}.")

        def on_add_blackout() -> None:
            try:
                selected_blackout_scope()
                resource_id = selected_blackout_resource_id()
                starts_at = parse_datetime_input(blackout_start_var.get(), field_name="Початок")
                ends_at = parse_datetime_input(blackout_end_var.get(), field_name="Кінець")
                if ends_at <= starts_at:
                    raise ValueError("Кінець blackout має бути пізніше за початок.")
                title = blackout_title_var.get().strip() or None
                with session_scope() as session:
                    ResourceController(session=session).create_blackout(
                        resource_id=resource_id,
                        starts_at=starts_at,
                        ends_at=ends_at,
                        title=title,
                    )
            except Exception as exc:
                messagebox.showerror("Не вдалося додати blackout", str(exc))
                return
            load_blackouts()
            load_coverage_dashboard()
            status_var.set("Blackout додано.")

        def on_add_blackout_batch() -> None:
            try:
                selected_blackout_scope()
                resource_id = selected_blackout_resource_id()
                start_day = parse_date_input(blackout_batch_start_date_var.get(), field_name="Початок пакета")
                end_day = parse_date_input(blackout_batch_end_date_var.get(), field_name="Кінець пакета")
                if end_day < start_day:
                    raise ValueError("Кінець пакета має бути не раніше початку.")
                start_clock = parse_time_input(blackout_batch_start_time_var.get(), field_name="Час початку")
                end_clock = parse_time_input(blackout_batch_end_time_var.get(), field_name="Час кінця")
                weekdays = parse_weekdays(blackout_batch_weekdays_var.get())
                title = blackout_title_var.get().strip() or None

                intervals: list[tuple[datetime, datetime, str | None]] = []
                current_day = start_day
                while current_day <= end_day:
                    if current_day.isoweekday() in weekdays:
                        starts_at = datetime.combine(current_day, start_clock)
                        ends_at = datetime.combine(current_day, end_clock)
                        if ends_at <= starts_at:
                            raise ValueError("Час кінця blackout має бути пізніше за початок.")
                        intervals.append((starts_at, ends_at, title))
                    current_day += timedelta(days=1)
                if not intervals:
                    raise ValueError("За обраним діапазоном і днями тижня не згенеровано жодного blackout.")

                with session_scope() as session:
                    created = ResourceController(session=session).create_blackouts_batch(
                        resource_id=resource_id,
                        intervals=intervals,
                    )
            except Exception as exc:
                messagebox.showerror("Batch blackout", str(exc))
                return
            load_blackouts()
            load_coverage_dashboard()
            status_var.set(f"Додано blackout пакет: {len(created)} записів.")

        def on_delete_blackout() -> None:
            selected = blackout_table.selection()
            if not selected:
                messagebox.showwarning("Видалення blackout", "Оберіть blackout у списку.")
                return
            blackout_id = int(selected[0])
            try:
                with session_scope() as session:
                    deleted = ResourceController(session=session).delete_blackout(blackout_id=blackout_id)
                    if not deleted:
                        raise ValueError("Blackout не знайдено або вже видалено.")
            except Exception as exc:
                messagebox.showerror("Не вдалося видалити blackout", str(exc))
                return
            load_blackouts()
            load_coverage_dashboard()
            status_var.set("Blackout видалено.")

        def on_add_manual_entry() -> None:
            try:
                period_id = parse_period_id()
                scenario_id = selected_scenario_id()
                requirement_id = selected_manual_requirement_id()
                day = date.fromisoformat(manual_date_var.get().strip())
                order_in_day = int(manual_order_var.get().strip())
                if order_in_day <= 0:
                    raise ValueError("Номер блоку має бути більшим за 0.")
                room_resource_id = selected_manual_room_resource_id()
                with session_scope() as session:
                    SchedulerController(session=session).create_manual_entry(
                        calendar_period_id=period_id,
                        scenario_id=scenario_id,
                        requirement_id=requirement_id,
                        day=day,
                        order_in_day=order_in_day,
                        room_resource_id=room_resource_id,
                        is_locked=bool(manual_lock_var.get()),
                    )
            except Exception as exc:
                messagebox.showerror("Ручний слот", str(exc))
                return
            on_load_week()
            status_var.set("Ручний слот додано.")

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
            text="Здійсненність",
            command=on_check_feasibility,
            primary=False,
            width=140,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._motion_button(
            buttons,
            text="Створити A/B",
            command=on_create_scenarios_ab,
            primary=False,
            width=140,
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

        blackout_add_button.configure(command=on_add_blackout)
        blackout_batch_button.configure(command=on_add_blackout_batch)
        blackout_delete_button.configure(command=on_delete_blackout)
        blackout_reload_button.configure(command=load_blackouts)
        coverage_refresh_button.configure(command=load_coverage_dashboard)
        scenario_compare_button.configure(command=on_compare_scenarios)
        scenario_publish_button.configure(command=on_publish_scenario)
        policy_save_button.configure(command=on_save_policy)
        manual_add_button.configure(command=on_add_manual_entry)
        requirements_refresh_button.configure(command=load_requirements)
        requirements_edit_button.configure(command=open_requirement_edit_modal)
        requirements_delete_button.configure(command=on_delete_requirement)

        load_reference_data()
        load_policy()
        load_blackouts()
        load_requirements()
        load_coverage_dashboard()
        subject_target_box.bind("<<ComboboxSelected>>", lambda _e: refresh_subject_target_controls(), add="+")
        blackout_scope_box.bind("<<ComboboxSelected>>", lambda _e: refresh_blackout_resource_choices(), add="+")
        period_box.bind("<<ComboboxSelected>>", lambda _e: on_period_changed(), add="+")
        scenario_box.bind("<<ComboboxSelected>>", lambda _e: on_load_week(), add="+")
        requirements_table.bind("<Double-1>", lambda _e: open_requirement_edit_modal(), add="+")
        if period_var.get():
            on_load_week()


    def _build_company_curriculum_view(self, parent: ttk.Frame, company_id: int) -> None:
        CompanyCurriculumTab(
            parent=parent,
            company_id=company_id,
            theme=self.theme,
            motion_button_factory=self._motion_button,
        ).build()


    def _build_company_groups_view(self, parent: ttk.Frame, company_id: int) -> None:
        group_state: dict[str, int | str | None] = {"id": None, "name": None}
        browse_state: dict[str, int | str | None] = {
            "level": "departments",
            "department_id": None,
            "specialty_id": None,
        }
        structure_state: dict[str, object] = {
            "departments": [],
            "specialties": [],
            "courses": [],
            "streams": [],
            "department_by_id": {},
            "specialty_by_id": {},
            "course_by_id": {},
            "stream_by_id": {},
        }
        course_filter_var = tk.StringVar(value="Усі курси")
        stream_filter_var = tk.StringVar(value="Усі потоки")
    
        def subgroup_short_name(full_name: str) -> str:
            marker = "::"
            if marker not in full_name:
                return full_name
            return full_name.split(marker, maxsplit=1)[1]

        def parse_selected_prefixed_id(raw: str) -> int | None:
            value = raw.strip()
            if not value or "|" not in value:
                return None
            try:
                return int(value.split("|", maxsplit=1)[0].strip())
            except ValueError:
                return None

        def parse_optional_positive_int(raw: str, *, field_name: str) -> int | None:
            value = raw.strip()
            if not value:
                return None
            try:
                parsed = int(value)
            except ValueError as exc:
                raise ValueError(f"Поле '{field_name}' має бути цілим числом.") from exc
            if parsed <= 0:
                raise ValueError(f"Поле '{field_name}' має бути більше нуля.")
            return parsed
    
        content = ttk.Frame(parent, style="Card.TFrame")
        content.pack(fill=tk.BOTH, expand=True)
    
        main_view = ttk.Frame(content, style="Card.TFrame")
        detail_view = ttk.Frame(content, style="Card.TFrame")
        for frame in (main_view, detail_view):
            frame.pack(fill=tk.BOTH, expand=True)
            frame.pack_forget()
    
        header = ttk.Frame(main_view, style="Card.TFrame")
        header.pack(fill=tk.X, pady=(0, 8))
        header_actions = ttk.Frame(header, style="Card.TFrame")
        header_actions.pack(side=tk.RIGHT)
        add_group_button = self._motion_button(
            header_actions,
            text="+ Група",
            command=lambda: open_create_group_modal(),
            primary=True,
            width=128,
        )
        add_stream_button = self._motion_button(
            header_actions,
            text="+ Потік",
            command=lambda: open_create_stream_modal(),
            primary=False,
            width=110,
        )
        add_course_button = self._motion_button(
            header_actions,
            text="+ Курс",
            command=lambda: open_create_course_modal(),
            primary=False,
            width=110,
        )
        add_specialty_button = self._motion_button(
            header_actions,
            text="+ Спеціальність",
            command=lambda: open_create_specialty_modal(),
            primary=False,
            width=150,
        )
        add_department_button = self._motion_button(
            header_actions,
            text="+ Кафедра",
            command=lambda: open_create_department_modal(),
            primary=False,
            width=128,
        )
        titles = ttk.Frame(header, style="Card.TFrame")
        titles.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(titles, text="Групи", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            titles,
            text="Ієрархія: кафедра → спеціальність → група. Усередині груп працюють фільтри за курсом і потоком.",
            style="CardSubtle.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        hierarchy_nav = ttk.Frame(main_view, style="Card.TFrame")
        hierarchy_nav.pack(fill=tk.X, pady=(0, 6))
        hierarchy_back_button = HoverCircleIconButton(
            hierarchy_nav,
            text="←",
            command=lambda: None,
            diameter=44,
            canvas_bg=self.theme.SURFACE,
            icon_color=self.theme.TEXT_PRIMARY,
            hover_bg=self.theme.SECONDARY_HOVER,
            hover_icon_color=self.theme.TEXT_PRIMARY,
            pressed_bg=self.theme.SECONDARY_PRESSED,
        )
        hierarchy_back_button.pack(side=tk.LEFT)
        hierarchy_path_var = tk.StringVar(value="Кафедри")
        ttk.Label(hierarchy_nav, textvariable=hierarchy_path_var, style="CardSubtle.TLabel").pack(
            side=tk.LEFT,
            padx=(10, 0),
            pady=(6, 0),
        )

        group_filters = ttk.Frame(main_view, style="Card.TFrame")
        group_filters.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(group_filters, text="Фільтри груп:", style="CardSubtle.TLabel").pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(group_filters, text="Курс", style="Card.TLabel").pack(side=tk.LEFT)
        course_filter_box = ttk.Combobox(
            group_filters,
            textvariable=course_filter_var,
            state="readonly",
            width=26,
        )
        course_filter_box.pack(side=tk.LEFT, padx=(8, 12))
        ttk.Label(group_filters, text="Потік", style="Card.TLabel").pack(side=tk.LEFT)
        stream_filter_box = ttk.Combobox(
            group_filters,
            textvariable=stream_filter_var,
            state="readonly",
            width=26,
        )
        stream_filter_box.pack(side=tk.LEFT, padx=(8, 0))

        cards_scroll_wrap = ttk.Frame(main_view, style="Card.TFrame")
        cards_scroll_wrap.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        cards_canvas = tk.Canvas(
            cards_scroll_wrap,
            bg=self.theme.SURFACE,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        cards_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cards_scroll = ttk.Scrollbar(
            cards_scroll_wrap,
            orient=tk.VERTICAL,
            command=cards_canvas.yview,
            style="App.Vertical.TScrollbar",
        )
        cards_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        cards_canvas.configure(yscrollcommand=cards_scroll.set)

        cards_container = ttk.Frame(cards_canvas, style="Card.TFrame")
        cards_window = cards_canvas.create_window((0, 0), anchor="nw", window=cards_container)

        def _sync_cards_scroll(_event=None) -> None:
            cards_canvas.configure(scrollregion=cards_canvas.bbox("all"))
            cards_canvas.itemconfigure(cards_window, width=cards_canvas.winfo_width())

        cards_container.bind("<Configure>", _sync_cards_scroll)
        cards_canvas.bind("<Configure>", _sync_cards_scroll)
    
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
        detail_actions = ttk.Frame(detail_nav, style="Card.TFrame")
        detail_actions.pack(side=tk.RIGHT)
        reassign_stream_button = self._motion_button(
            detail_actions,
            text="Змінити курс/потік",
            command=lambda: open_reassign_group_stream_modal(),
            primary=False,
            width=188,
            height=38,
        )
        reassign_stream_button.pack(side=tk.RIGHT)
        detail_meta_var = tk.StringVar(value="")
        detail_subtitle = ttk.Label(
            detail_body,
            textvariable=detail_meta_var,
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
        subgroup_tree = ttk.Treeview(
            subgroup_tree_wrap,
            show="tree headings",
            height=14,
            selectmode="browse",
        )
        subgroup_tree.heading("#0", text="Підгрупи та учасники", anchor="w")
        subgroup_tree.column("#0", anchor="w", minwidth=280, width=460, stretch=True)
        subgroup_tree.tag_configure(
            "bucket",
            font=("Segoe UI", 10, "bold"),
            background=self.theme.SURFACE_ALT,
            foreground=self.theme.TEXT_PRIMARY,
        )
        subgroup_tree.tag_configure(
            "participant",
            font=("Segoe UI", 10),
            foreground=self.theme.TEXT_PRIMARY,
        )
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

        filter_sync_state = {"busy": False}

        def selected_department_id() -> int | None:
            value = browse_state.get("department_id")
            return int(value) if isinstance(value, int) else None

        def selected_specialty_id() -> int | None:
            value = browse_state.get("specialty_id")
            return int(value) if isinstance(value, int) else None

        def selected_course_id() -> int | None:
            return parse_selected_prefixed_id(course_filter_var.get())

        def selected_stream_id() -> int | None:
            return parse_selected_prefixed_id(stream_filter_var.get())

        def compute_main_columns(width: int) -> int:
            return 4

        def compute_main_card_width(width: int, columns: int) -> int:
            spacing_per_card = 12
            usable_width = max(320, int(width) - 8)
            raw_width = (usable_width - (columns * spacing_per_card)) // max(1, columns)
            return max(140, min(420, raw_width))

        def refresh_header_actions() -> None:
            for widget in (add_group_button, add_stream_button, add_course_button, add_specialty_button, add_department_button):
                widget.pack_forget()
            level = str(browse_state["level"])
            if level == "departments":
                add_department_button.pack(side=tk.RIGHT)
            elif level == "specialties":
                add_specialty_button.pack(side=tk.RIGHT)
            else:
                add_group_button.pack(side=tk.RIGHT)
                add_stream_button.pack(side=tk.RIGHT, padx=(0, 6))
                add_course_button.pack(side=tk.RIGHT, padx=(0, 6))
        def refresh_hierarchy_nav() -> None:
            level = str(browse_state["level"])
            department = structure_state["department_by_id"].get(selected_department_id())
            specialty = structure_state["specialty_by_id"].get(selected_specialty_id())

            if level == "departments":
                hierarchy_path_var.set("Кафедри")
                hierarchy_back_button.pack_forget()
            elif level == "specialties":
                dep_name = department.name if department is not None else "Кафедра"
                hierarchy_path_var.set(f"Кафедри / {dep_name}")
                if not hierarchy_back_button.winfo_ismapped():
                    hierarchy_back_button.pack(side=tk.LEFT)
            else:
                dep_name = department.name if department is not None else "Кафедра"
                spec_name = specialty.code or specialty.name if specialty is not None else "Спеціальність"
                hierarchy_path_var.set(f"Кафедри / {dep_name} / {spec_name}")
                if not hierarchy_back_button.winfo_ismapped():
                    hierarchy_back_button.pack(side=tk.LEFT)

        def refresh_group_filter_options() -> None:
            specialty_id = selected_specialty_id()
            all_courses = [item for item in structure_state["courses"] if specialty_id is None or item.specialty_id == specialty_id]
            current_course = selected_course_id()
            allowed_course_ids = {item.id for item in all_courses}
            if current_course not in allowed_course_ids:
                current_course = None

            all_streams = [
                item
                for item in structure_state["streams"]
                if (specialty_id is None or item.specialty_id == specialty_id)
                and (current_course is None or item.course_id == current_course)
            ]
            current_stream = selected_stream_id()
            allowed_stream_ids = {item.id for item in all_streams}
            if current_stream not in allowed_stream_ids:
                current_stream = None

            course_values = [
                f"{item.id} | {item.code} — {item.name}" if item.code else f"{item.id} | {item.name}"
                for item in all_courses
            ]
            stream_values = [
                f"{item.id} | {item.name}{f' • набір {item.admission_year}' if item.admission_year is not None else ''}"
                for item in all_streams
            ]

            filter_sync_state["busy"] = True
            course_filter_box["values"] = ["Усі курси"] + course_values
            stream_filter_box["values"] = ["Усі потоки"] + stream_values
            if current_course is None:
                course_filter_var.set("Усі курси")
            else:
                course = structure_state["course_by_id"][current_course]
                course_filter_var.set(f"{course.id} | {course.code} — {course.name}" if course.code else f"{course.id} | {course.name}")
            if current_stream is None:
                stream_filter_var.set("Усі потоки")
            else:
                stream = structure_state["stream_by_id"][current_stream]
                year_suffix = f" • набір {stream.admission_year}" if stream.admission_year is not None else ""
                stream_filter_var.set(f"{stream.id} | {stream.name}{year_suffix}")
            filter_sync_state["busy"] = False

        def load_structure_state() -> None:
            with session_scope() as session:
                academic = AcademicController(session=session)
                departments = academic.list_departments(company_id=company_id, include_archived=False)
                specialties = academic.list_specialties(company_id=company_id, include_archived=False)
                courses = academic.list_courses(company_id=company_id, include_archived=False)
                streams = academic.list_streams(company_id=company_id, include_archived=False)

            structure_state["departments"] = departments
            structure_state["specialties"] = specialties
            structure_state["courses"] = courses
            structure_state["streams"] = streams
            structure_state["department_by_id"] = {item.id: item for item in departments}
            structure_state["specialty_by_id"] = {item.id: item for item in specialties}
            structure_state["course_by_id"] = {item.id: item for item in courses}
            structure_state["stream_by_id"] = {item.id: item for item in streams}

            if selected_department_id() not in structure_state["department_by_id"]:
                browse_state["department_id"] = None
                browse_state["specialty_id"] = None
                browse_state["level"] = "departments"
            elif selected_specialty_id() not in structure_state["specialty_by_id"]:
                browse_state["specialty_id"] = None
                browse_state["level"] = "specialties"

        def set_hierarchy_level(level: str, *, department_id: int | None = None, specialty_id: int | None = None) -> None:
            previous_level = str(browse_state["level"])
            previous_department_id = selected_department_id()
            previous_specialty_id = selected_specialty_id()
            browse_state["level"] = level
            browse_state["department_id"] = department_id
            browse_state["specialty_id"] = specialty_id
            if (
                previous_level != level
                or previous_department_id != department_id
                or previous_specialty_id != specialty_id
            ):
                cards_canvas.yview_moveto(0.0)
        def on_hierarchy_back() -> None:
            level = str(browse_state["level"])
            if level == "groups":
                department_id = selected_department_id()
                if department_id is None:
                    specialty_id = selected_specialty_id()
                    if specialty_id is not None:
                        specialty = structure_state["specialty_by_id"].get(specialty_id)
                        if specialty is not None:
                            department_id = specialty.department_id
                set_hierarchy_level("specialties", department_id=department_id, specialty_id=None)
            elif level == "specialties":
                set_hierarchy_level("departments", department_id=None, specialty_id=None)
            render_main_cards()

        def on_course_filter_change(_event=None) -> None:
            if filter_sync_state["busy"] or str(browse_state["level"]) != "groups":
                return
            refresh_group_filter_options()
            render_main_cards()

        def on_stream_filter_change(_event=None) -> None:
            if filter_sync_state["busy"] or str(browse_state["level"]) != "groups":
                return
            render_main_cards()

        def open_create_department_modal() -> None:
            modal = tk.Toplevel(self.root)
            modal.title("Нова кафедра")
            modal.transient(self.root)
            modal.resizable(False, False)
            modal.grab_set()

            shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
            shell.pack(fill=tk.BOTH, expand=True)
            ttk.Label(shell, text="Створення кафедри", style="CardTitle.TLabel").pack(anchor="w")

            name_var = tk.StringVar(value="")
            short_name_var = tk.StringVar(value="")

            ttk.Label(shell, text="Назва", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
            name_entry = ttk.Entry(shell, textvariable=name_var, width=44)
            name_entry.pack(fill=tk.X, pady=(6, 8))
            ttk.Label(shell, text="Скорочення (опціонально)", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=short_name_var, width=24).pack(fill=tk.X, pady=(6, 12))

            footer = ttk.Frame(shell, style="Card.TFrame")
            footer.pack(fill=tk.X)

            def on_submit_department() -> None:
                clean_name = name_var.get().strip()
                if not clean_name:
                    messagebox.showerror("Некоректні дані", "Назва кафедри обов'язкова.", parent=modal)
                    return
                try:
                    with session_scope() as session:
                        created = AcademicController(session=session).create_department(
                            name=clean_name,
                            short_name=short_name_var.get().strip() or None,
                            company_id=company_id,
                        )
                except IntegrityError:
                    messagebox.showerror("Не вдалося створити кафедру", "Кафедра з такою назвою або скороченням вже існує.", parent=modal)
                    return
                except Exception as exc:
                    messagebox.showerror("Не вдалося створити кафедру", str(exc), parent=modal)
                    return

                modal.destroy()
                load_structure_state()
                set_hierarchy_level("specialties", department_id=created.id, specialty_id=None)
                render_main_cards()

            self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
            self._motion_button(footer, text="Створити", command=on_submit_department, primary=True, width=130).pack(
                side=tk.RIGHT,
                padx=(0, 8),
            )
            name_entry.focus_set()

        def open_create_specialty_modal() -> None:
            with session_scope() as session:
                departments = AcademicController(session=session).list_departments(company_id=company_id, include_archived=False)
            if not departments:
                messagebox.showerror("Спеціальність", "Спочатку створіть кафедру.", parent=self.root)
                return

            modal = tk.Toplevel(self.root)
            modal.title("Нова спеціальність")
            modal.transient(self.root)
            modal.resizable(False, False)
            modal.grab_set()

            shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
            shell.pack(fill=tk.BOTH, expand=True)
            ttk.Label(shell, text="Створення спеціальності", style="CardTitle.TLabel").pack(anchor="w")

            department_values = [
                f"{item.id} | {item.short_name} — {item.name}" if item.short_name else f"{item.id} | {item.name}"
                for item in departments
            ]
            department_var = tk.StringVar(value=department_values[0])
            current_department_id = selected_department_id()
            if current_department_id is not None:
                for value in department_values:
                    if value.startswith(f"{current_department_id} |"):
                        department_var.set(value)
                        break
            name_var = tk.StringVar(value="")
            code_var = tk.StringVar(value="")
            duration_var = tk.StringVar(value="")
            degree_var = tk.StringVar(value="Бакалавр")
            degree_code_by_label = {
                "Бакалавр": "BACHELOR",
                "Магістр": "MASTER",
                "Доктор": "PHD",
                "Інше": "OTHER",
            }

            ttk.Label(shell, text="Кафедра", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
            ttk.Combobox(shell, textvariable=department_var, values=department_values, state="readonly", width=46).pack(
                fill=tk.X,
                pady=(6, 8),
            )
            ttk.Label(shell, text="Назва", style="Card.TLabel").pack(anchor="w")
            name_entry = ttk.Entry(shell, textvariable=name_var, width=46)
            name_entry.pack(fill=tk.X, pady=(6, 8))
            ttk.Label(shell, text="Код (опціонально)", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=code_var, width=26).pack(fill=tk.X, pady=(6, 8))
            ttk.Label(shell, text="Рівень", style="Card.TLabel").pack(anchor="w")
            ttk.Combobox(shell, textvariable=degree_var, values=list(degree_code_by_label.keys()), state="readonly", width=18).pack(
                fill=tk.X,
                pady=(6, 8),
            )
            ttk.Label(shell, text="Тривалість (років, опціонально)", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=duration_var, width=12).pack(fill=tk.X, pady=(6, 12))

            footer = ttk.Frame(shell, style="Card.TFrame")
            footer.pack(fill=tk.X)

            def on_submit_specialty() -> None:
                specialty_name = name_var.get().strip()
                if not specialty_name:
                    messagebox.showerror("Некоректні дані", "Назва спеціальності обов'язкова.", parent=modal)
                    return
                department_id = parse_selected_prefixed_id(department_var.get())
                if department_id is None:
                    messagebox.showerror("Некоректні дані", "Оберіть кафедру зі списку.", parent=modal)
                    return
                try:
                    duration_years = parse_optional_positive_int(duration_var.get(), field_name="Тривалість")
                    with session_scope() as session:
                        created = AcademicController(session=session).create_specialty(
                            department_id=department_id,
                            name=specialty_name,
                            code=code_var.get().strip() or None,
                            degree_level=degree_code_by_label[degree_var.get()],
                            duration_years=duration_years,
                            company_id=company_id,
                        )
                except IntegrityError:
                    messagebox.showerror("Не вдалося створити спеціальність", "Спеціальність з такою назвою або кодом вже існує.", parent=modal)
                    return
                except Exception as exc:
                    messagebox.showerror("Не вдалося створити спеціальність", str(exc), parent=modal)
                    return

                modal.destroy()
                load_structure_state()
                set_hierarchy_level("groups", department_id=department_id, specialty_id=created.id)
                course_filter_var.set("Усі курси")
                stream_filter_var.set("Усі потоки")
                render_main_cards()

            self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
            self._motion_button(footer, text="Створити", command=on_submit_specialty, primary=True, width=130).pack(
                side=tk.RIGHT,
                padx=(0, 8),
            )
            name_entry.focus_set()

        def open_create_course_modal() -> None:
            with session_scope() as session:
                specialties_with_departments = AcademicController(session=session).list_specialties_with_departments(company_id=company_id)
            if not specialties_with_departments:
                messagebox.showerror("Курс", "Спочатку створіть спеціальність.", parent=self.root)
                return

            modal = tk.Toplevel(self.root)
            modal.title("Новий курс")
            modal.transient(self.root)
            modal.resizable(False, False)
            modal.grab_set()

            shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
            shell.pack(fill=tk.BOTH, expand=True)
            ttk.Label(shell, text="Створення курсу", style="CardTitle.TLabel").pack(anchor="w")

            specialty_values = []
            for specialty, department in specialties_with_departments:
                dep_label = department.short_name or department.name
                specialty_values.append(f"{specialty.id} | {specialty.name} ({dep_label})")
            specialty_var = tk.StringVar(value=specialty_values[0])
            current_specialty_id = selected_specialty_id()
            if current_specialty_id is not None:
                for value in specialty_values:
                    if value.startswith(f"{current_specialty_id} |"):
                        specialty_var.set(value)
                        break
            name_var = tk.StringVar(value="")
            code_var = tk.StringVar(value="")
            study_year_var = tk.StringVar(value="")

            ttk.Label(shell, text="Спеціальність", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
            ttk.Combobox(shell, textvariable=specialty_var, values=specialty_values, state="readonly", width=48).pack(
                fill=tk.X,
                pady=(6, 8),
            )
            ttk.Label(shell, text="Назва курсу", style="Card.TLabel").pack(anchor="w")
            name_entry = ttk.Entry(shell, textvariable=name_var, width=38)
            name_entry.pack(fill=tk.X, pady=(6, 8))
            ttk.Label(shell, text="Код (опціонально)", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=code_var, width=26).pack(fill=tk.X, pady=(6, 8))
            ttk.Label(shell, text="Номер курсу (опціонально)", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=study_year_var, width=12).pack(fill=tk.X, pady=(6, 12))

            footer = ttk.Frame(shell, style="Card.TFrame")
            footer.pack(fill=tk.X)

            def on_submit_course() -> None:
                course_name = name_var.get().strip()
                if not course_name:
                    messagebox.showerror("Некоректні дані", "Назва курсу обов'язкова.", parent=modal)
                    return
                specialty_id = parse_selected_prefixed_id(specialty_var.get())
                if specialty_id is None:
                    messagebox.showerror("Некоректні дані", "Оберіть спеціальність зі списку.", parent=modal)
                    return
                try:
                    study_year = parse_optional_positive_int(study_year_var.get(), field_name="Номер курсу")
                    with session_scope() as session:
                        created = AcademicController(session=session).create_course(
                            specialty_id=specialty_id,
                            name=course_name,
                            code=code_var.get().strip() or None,
                            study_year=study_year,
                            company_id=company_id,
                        )
                except IntegrityError:
                    messagebox.showerror("Не вдалося створити курс", "Курс із такою назвою або кодом уже існує.", parent=modal)
                    return
                except Exception as exc:
                    messagebox.showerror("Не вдалося створити курс", str(exc), parent=modal)
                    return

                modal.destroy()
                load_structure_state()
                specialty = structure_state["specialty_by_id"].get(created.specialty_id)
                department = structure_state["department_by_id"].get(specialty.department_id) if specialty is not None else None
                set_hierarchy_level(
                    "groups",
                    department_id=department.id if department is not None else selected_department_id(),
                    specialty_id=created.specialty_id,
                )
                course_filter_var.set(f"{created.id} | {created.code} — {created.name}" if created.code else f"{created.id} | {created.name}")
                stream_filter_var.set("Усі потоки")
                render_main_cards()

            self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
            self._motion_button(footer, text="Створити", command=on_submit_course, primary=True, width=130).pack(
                side=tk.RIGHT,
                padx=(0, 8),
            )
            name_entry.focus_set()

        def open_create_stream_modal() -> None:
            with session_scope() as session:
                academic_controller = AcademicController(session=session)
                courses = academic_controller.list_courses(
                    company_id=company_id,
                    specialty_id=selected_specialty_id(),
                    include_archived=False,
                )
                specialties = academic_controller.list_specialties(company_id=company_id, include_archived=True)
                departments = academic_controller.list_departments(company_id=company_id, include_archived=True)
            if not courses:
                messagebox.showerror("Потік", "Спочатку створіть курс (спеціальність → курс).", parent=self.root)
                return

            modal = tk.Toplevel(self.root)
            modal.title("Новий потік")
            modal.transient(self.root)
            modal.resizable(False, False)
            modal.grab_set()

            shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
            shell.pack(fill=tk.BOTH, expand=True)
            ttk.Label(shell, text="Створення потоку", style="CardTitle.TLabel").pack(anchor="w")

            specialty_by_id = {item.id: item for item in specialties}
            department_by_id = {item.id: item for item in departments}
            course_values = []
            for course in courses:
                specialty = specialty_by_id.get(course.specialty_id)
                department = department_by_id.get(specialty.department_id) if specialty is not None else None
                dep_label = (department.short_name or department.name) if department is not None else "Кафедра?"
                spec_label = (specialty.code or specialty.name) if specialty is not None else "Спеціальність?"
                year_label = f" • {course.study_year} курс" if course.study_year is not None else ""
                course_values.append(f"{course.id} | {course.name} ({dep_label} / {spec_label}{year_label})")
            course_var = tk.StringVar(value=course_values[0])
            name_var = tk.StringVar(value="")
            admission_year_var = tk.StringVar(value="")
            graduation_year_var = tk.StringVar(value="")
            study_year_var = tk.StringVar(value="")

            ttk.Label(shell, text="Курс", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
            ttk.Combobox(shell, textvariable=course_var, values=course_values, state="readonly", width=58).pack(
                fill=tk.X,
                pady=(6, 8),
            )
            ttk.Label(shell, text="Назва потоку", style="Card.TLabel").pack(anchor="w")
            name_entry = ttk.Entry(shell, textvariable=name_var, width=36)
            name_entry.pack(fill=tk.X, pady=(6, 8))
            ttk.Label(shell, text="Рік набору (опціонально)", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=admission_year_var, width=12).pack(fill=tk.X, pady=(6, 8))
            ttk.Label(shell, text="Очікуваний рік випуску (опціонально)", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=graduation_year_var, width=12).pack(fill=tk.X, pady=(6, 8))
            ttk.Label(shell, text="Поточний курс (опціонально)", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=study_year_var, width=12).pack(fill=tk.X, pady=(6, 12))

            footer = ttk.Frame(shell, style="Card.TFrame")
            footer.pack(fill=tk.X)

            def on_submit_stream() -> None:
                stream_name = name_var.get().strip()
                if not stream_name:
                    messagebox.showerror("Некоректні дані", "Назва потоку обов'язкова.", parent=modal)
                    return
                course_id = parse_selected_prefixed_id(course_var.get())
                if course_id is None:
                    messagebox.showerror("Некоректні дані", "Оберіть курс зі списку.", parent=modal)
                    return
                try:
                    admission_year = parse_optional_positive_int(admission_year_var.get(), field_name="Рік набору")
                    graduation_year = parse_optional_positive_int(graduation_year_var.get(), field_name="Рік випуску")
                    study_year = parse_optional_positive_int(study_year_var.get(), field_name="Поточний курс")
                    with session_scope() as session:
                        created = AcademicController(session=session).create_stream(
                            course_id=course_id,
                            name=stream_name,
                            admission_year=admission_year,
                            expected_graduation_year=graduation_year,
                            study_year=study_year,
                            company_id=company_id,
                        )
                except IntegrityError:
                    messagebox.showerror("Не вдалося створити потік", "Потік з такою назвою вже існує для цього курсу.", parent=modal)
                    return
                except Exception as exc:
                    messagebox.showerror("Не вдалося створити потік", str(exc), parent=modal)
                    return

                modal.destroy()
                load_structure_state()
                stream_filter_var.set(f"{created.id} | {created.name}")
                render_main_cards()

            self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
            self._motion_button(footer, text="Створити", command=on_submit_stream, primary=True, width=130).pack(
                side=tk.RIGHT,
                padx=(0, 8),
            )
            name_entry.focus_set()

        def open_main_view() -> None:
            group_state["id"] = None
            group_state["name"] = None
            detail_view.pack_forget()
            main_view.pack(fill=tk.BOTH, expand=True)
            render_main_cards()
    
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
                render_main_cards()

        cards_layout_state = {"columns": 1, "card_width": 260}

        def refresh_cards_layout() -> bool:
            viewport_width = cards_canvas.winfo_width()
            if viewport_width <= 1:
                viewport_width = cards_scroll_wrap.winfo_width()
            if viewport_width <= 1:
                viewport_width = max(1, main_view.winfo_width() - 24)
            columns = compute_main_columns(viewport_width)
            card_width = compute_main_card_width(viewport_width, columns)
            if cards_layout_state["columns"] == columns and cards_layout_state["card_width"] == card_width:
                return False
            cards_layout_state["columns"] = columns
            cards_layout_state["card_width"] = card_width
            return True

        def clear_cards_container() -> None:
            for child in cards_container.winfo_children():
                child.destroy()

        def apply_card_grid_columns(columns: int) -> None:
            for col in range(4):
                cards_container.grid_columnconfigure(col, weight=1 if col < columns else 0, uniform="group-card-col")

        def card_wrap_width() -> int:
            return max(160, int(cards_layout_state["card_width"]) - 34)

        def render_empty_main(text: str) -> None:
            clear_cards_container()
            empty = ttk.Frame(cards_container, style="Card.TFrame")
            empty.grid(row=0, column=0, sticky="w", padx=8, pady=8)
            ttk.Label(
                empty,
                text=text,
                style="CardSubtle.TLabel",
                wraplength=max(260, cards_canvas.winfo_width() - 36),
                justify=tk.LEFT,
            ).pack(anchor="w")

        def render_department_cards() -> None:
            departments = sorted(structure_state["departments"], key=lambda item: (item.name.lower(), item.id))
            if not departments:
                render_empty_main("Поки що немає кафедр. Створи першу кафедру.")
                return

            specialties = structure_state["specialties"]
            courses = structure_state["courses"]
            streams = structure_state["streams"]
            dep_id_by_spec_id = {item.id: item.department_id for item in specialties}
            spec_id_by_course_id = {item.id: item.specialty_id for item in courses}
            course_id_by_stream_id = {item.id: item.course_id for item in streams}

            specialty_count_by_dep: dict[int, int] = {}
            course_count_by_dep: dict[int, int] = {}
            stream_count_by_dep: dict[int, int] = {}
            for specialty in specialties:
                specialty_count_by_dep[specialty.department_id] = specialty_count_by_dep.get(specialty.department_id, 0) + 1
            for course in courses:
                dep_id = dep_id_by_spec_id.get(course.specialty_id)
                if dep_id is None:
                    continue
                course_count_by_dep[dep_id] = course_count_by_dep.get(dep_id, 0) + 1
            for stream in streams:
                if stream.course_id is None:
                    continue
                spec_id = spec_id_by_course_id.get(stream.course_id)
                dep_id = dep_id_by_spec_id.get(spec_id) if spec_id is not None else None
                if dep_id is None:
                    continue
                stream_count_by_dep[dep_id] = stream_count_by_dep.get(dep_id, 0) + 1

            clear_cards_container()
            columns = cards_layout_state["columns"]
            card_width = cards_layout_state["card_width"]
            wrap = card_wrap_width()
            apply_card_grid_columns(columns)
            for index, department in enumerate(departments):
                row = index // columns
                column = index % columns
                card = RoundedMotionCard(
                    cards_container,
                    bg_color=self.theme.SURFACE,
                    card_color=self.theme.SURFACE_ALT,
                    shadow_color=self.theme.SHADOW_SOFT,
                    radius=16,
                    padding=4,
                    shadow_offset=4,
                    motion_enabled=True,
                    width=card_width,
                    height=188,
                )
                card.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
                title = ttk.Label(
                    card.content,
                    text=department.name,
                    style="CardAltTitle.TLabel",
                    wraplength=wrap,
                    justify=tk.LEFT,
                )
                title.pack(anchor="w", pady=(4, 2))
                subtitle = ttk.Label(
                    card.content,
                    text=(
                        f"Спеціальностей: {specialty_count_by_dep.get(department.id, 0)} | "
                        f"Курсів: {course_count_by_dep.get(department.id, 0)} | "
                        f"Потоків: {stream_count_by_dep.get(department.id, 0)}"
                    ),
                    style="CardAltSubtle.TLabel",
                    wraplength=wrap,
                    justify=tk.LEFT,
                )
                subtitle.pack(anchor="w")
                short_name = department.short_name or "Без скорочення"
                hint = ttk.Label(
                    card.content,
                    text=f"Скорочення: {short_name}",
                    style="CardAltSubtle.TLabel",
                    wraplength=wrap,
                    justify=tk.LEFT,
                )
                hint.pack(anchor="w", pady=(3, 0))

                def on_card_resize(event: tk.Event, labels: tuple[ttk.Label, ...] = (title, subtitle, hint)) -> None:
                    line_wrap = max(120, event.width - 24)
                    for label in labels:
                        label.configure(wraplength=line_wrap)

                card.content.bind("<Configure>", on_card_resize, add="+")
                for widget in (card, card.canvas, card.content, title, subtitle, hint):
                    widget.bind(
                        "<Button-1>",
                        lambda _e, dep_id=department.id: (
                            set_hierarchy_level("specialties", department_id=dep_id, specialty_id=None),
                            render_main_cards(),
                        ),
                    )

        def render_specialty_cards() -> None:
            department_id = selected_department_id()
            if department_id is None:
                set_hierarchy_level("departments", department_id=None, specialty_id=None)
                render_main_cards()
                return
            specialties = [
                item
                for item in structure_state["specialties"]
                if item.department_id == department_id
            ]
            specialties.sort(key=lambda item: (item.name.lower(), item.id))
            if not specialties:
                render_empty_main("У цій кафедрі ще немає спеціальностей.")
                return

            courses = structure_state["courses"]
            streams = structure_state["streams"]
            course_count_by_spec: dict[int, int] = {}
            stream_count_by_spec: dict[int, int] = {}
            for course in courses:
                course_count_by_spec[course.specialty_id] = course_count_by_spec.get(course.specialty_id, 0) + 1
            for stream in streams:
                if stream.course_id is None:
                    continue
                course = structure_state["course_by_id"].get(stream.course_id)
                if course is None:
                    continue
                stream_count_by_spec[course.specialty_id] = stream_count_by_spec.get(course.specialty_id, 0) + 1

            clear_cards_container()
            columns = cards_layout_state["columns"]
            card_width = cards_layout_state["card_width"]
            wrap = card_wrap_width()
            apply_card_grid_columns(columns)
            for index, specialty in enumerate(specialties):
                row = index // columns
                column = index % columns
                card = RoundedMotionCard(
                    cards_container,
                    bg_color=self.theme.SURFACE,
                    card_color=self.theme.SURFACE_ALT,
                    shadow_color=self.theme.SHADOW_SOFT,
                    radius=16,
                    padding=4,
                    shadow_offset=4,
                    motion_enabled=True,
                    width=card_width,
                    height=180,
                )
                card.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
                title_text = f"{specialty.code} • {specialty.name}" if specialty.code else specialty.name
                title = ttk.Label(
                    card.content,
                    text=title_text,
                    style="CardAltTitle.TLabel",
                    wraplength=wrap,
                    justify=tk.LEFT,
                )
                title.pack(anchor="w", pady=(4, 2))
                stats = ttk.Label(
                    card.content,
                    text=f"Курсів: {course_count_by_spec.get(specialty.id, 0)} • Потоків: {stream_count_by_spec.get(specialty.id, 0)}",
                    style="CardAltSubtle.TLabel",
                    wraplength=wrap,
                    justify=tk.LEFT,
                )
                stats.pack(anchor="w")
                degree = specialty.degree_level or "OTHER"
                detail = ttk.Label(
                    card.content,
                    text=f"Рівень: {degree}",
                    style="CardAltSubtle.TLabel",
                    wraplength=wrap,
                    justify=tk.LEFT,
                )
                detail.pack(anchor="w", pady=(3, 0))

                def on_card_resize(event: tk.Event, labels: tuple[ttk.Label, ...] = (title, stats, detail)) -> None:
                    line_wrap = max(120, event.width - 24)
                    for label in labels:
                        label.configure(wraplength=line_wrap)

                card.content.bind("<Configure>", on_card_resize, add="+")
                for widget in (card, card.canvas, card.content, title, stats, detail):
                    widget.bind(
                        "<Button-1>",
                        lambda _e, spec_id=specialty.id: (
                            set_hierarchy_level("groups", department_id=department_id, specialty_id=spec_id),
                            course_filter_var.set("Усі курси"),
                            stream_filter_var.set("Усі потоки"),
                            render_main_cards(),
                        ),
                    )

        def load_group_cards_data() -> list[tuple[int, str, int, str]]:
            specialty_id = selected_specialty_id()
            if specialty_id is None:
                return []
            course_id_filter = selected_course_id()
            stream_id_filter = selected_stream_id()

            all_streams = [item for item in structure_state["streams"] if item.specialty_id == specialty_id]
            if course_id_filter is not None:
                all_streams = [item for item in all_streams if item.course_id == course_id_filter]
            allowed_stream_ids = {item.id for item in all_streams}
            if stream_id_filter is not None:
                allowed_stream_ids = {stream_id_filter} if stream_id_filter in allowed_stream_ids else set()

            with session_scope() as session:
                auth_controller = AuthController(session=session)
                resource_controller = ResourceController(session=session)
                groups = resource_controller.list_resources(
                    resource_type=ResourceType.GROUP,
                    company_id=company_id,
                )
                groups = [item for item in groups if item.stream_id in allowed_stream_ids]

                result: list[tuple[int, str, int, str]] = []
                for group in groups:
                    subgroups = resource_controller.list_subgroups(group_id=group.id, company_id=company_id)
                    users = auth_controller.list_group_users(
                        company_id=company_id,
                        group_id=group.id,
                        subgroup_ids=[item.id for item in subgroups],
                    )
                    stream_label = "Без потоку"
                    stream = structure_state["stream_by_id"].get(group.stream_id)
                    if stream is not None:
                        course = structure_state["course_by_id"].get(stream.course_id) if stream.course_id is not None else None
                        course_name = course.code or course.name if course is not None else "Курс?"
                        stream_label = f"{course_name} • {stream.name}"
                    result.append((group.id, group.name, len(users), stream_label))
            result.sort(key=lambda item: (item[1].lower(), item[0]))
            return result

        def render_group_cards() -> None:
            try:
                groups = load_group_cards_data()
            except Exception as exc:
                messagebox.showerror("Помилка завантаження груп", str(exc))
                return

            if not groups:
                render_empty_main("У цій спеціальності ще немає груп за обраними фільтрами.")
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

            clear_cards_container()
            columns = cards_layout_state["columns"]
            card_width = cards_layout_state["card_width"]
            wrap = card_wrap_width()
            apply_card_grid_columns(columns)
            for index, (group_id, group_name, user_count, stream_label) in enumerate(groups):
                row = index // columns
                column = index % columns
                card = RoundedMotionCard(
                    cards_container,
                    bg_color=self.theme.SURFACE,
                    card_color=self.theme.SURFACE_ALT,
                    shadow_color=self.theme.SHADOW_SOFT,
                    radius=16,
                    padding=4,
                    shadow_offset=4,
                    motion_enabled=True,
                    width=card_width,
                    height=176,
                )
                card.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
                title = ttk.Label(
                    card.content,
                    text=group_name,
                    style="CardAltTitle.TLabel",
                    wraplength=wrap,
                    justify=tk.LEFT,
                )
                title.pack(anchor="w", pady=(4, 2))
                meta = ttk.Label(
                    card.content,
                    text=stream_label,
                    style="CardAltSubtle.TLabel",
                    wraplength=wrap,
                    justify=tk.LEFT,
                )
                meta.pack(anchor="w")
                count = ttk.Label(
                    card.content,
                    text=f"Учасників: {user_count}",
                    style="CardAltSubtle.TLabel",
                    wraplength=wrap,
                    justify=tk.LEFT,
                )
                count.pack(anchor="w", pady=(2, 0))

                def on_card_resize(event: tk.Event, labels: tuple[ttk.Label, ...] = (title, meta, count)) -> None:
                    line_wrap = max(120, event.width - 24)
                    for label in labels:
                        label.configure(wraplength=line_wrap)

                card.content.bind("<Configure>", on_card_resize, add="+")
                for widget in (card, card.canvas, card.content, title, meta, count):
                    widget.bind("<Button-1>", lambda _e, gid=group_id, gname=group_name: open_group_view(gid, gname))
                    widget.bind("<Button-3>", lambda e, gid=group_id, gname=group_name: on_card_context(e, gid, gname))

        def render_main_cards(_event=None, *, reload_structure: bool = True) -> None:
            if reload_structure:
                load_structure_state()
            refresh_cards_layout()
            refresh_header_actions()
            refresh_hierarchy_nav()

            level = str(browse_state["level"])
            if level == "groups":
                group_filters.pack(fill=tk.X, pady=(0, 8))
                refresh_group_filter_options()
                render_group_cards()
            else:
                group_filters.pack_forget()
                if level == "specialties":
                    render_specialty_cards()
                else:
                    render_department_cards()
            _sync_cards_scroll()

        def on_cards_resize(_event=None) -> None:
            _sync_cards_scroll()
            if not refresh_cards_layout():
                return
            render_main_cards(reload_structure=False)
    
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

            counts_by_subgroup_id: dict[int | None, int] = {None: 0}
            for subgroup_id in current_subgroups_by_id:
                counts_by_subgroup_id[subgroup_id] = 0
            for user in users:
                subgroup_id = user.subgroup_id if user.subgroup_id in current_subgroups_by_id else None
                counts_by_subgroup_id[subgroup_id] = counts_by_subgroup_id.get(subgroup_id, 0) + 1

            unassigned_iid = "sg_none"
            subgroup_tree.insert(
                "",
                tk.END,
                iid=unassigned_iid,
                text=f"Без підгрупи [{counts_by_subgroup_id.get(None, 0)}]",
                open=True,
                tags=("bucket",),
            )
            tree_subgroup_id_by_iid[unassigned_iid] = None

            for subgroup in current_subgroups_by_id.values():
                iid = f"sg_{subgroup.id}"
                subgroup_tree.insert(
                    "",
                    tk.END,
                    iid=iid,
                    text=f"Підгрупа: {subgroup_short_name(subgroup.name)} [{counts_by_subgroup_id.get(subgroup.id, 0)}]",
                    open=True,
                    tags=("bucket",),
                )
                tree_subgroup_id_by_iid[iid] = subgroup.id

            for user in users:
                parent_iid = unassigned_iid
                if user.subgroup_id is not None and user.subgroup_id in current_subgroups_by_id:
                    parent_iid = f"sg_{user.subgroup_id}"
                subgroup_tree.insert(
                    parent_iid,
                    tk.END,
                    iid=f"user_{user.id}",
                    text=f"Учасник: {user.username}",
                    tags=("participant",),
                )

        def load_group_detail() -> None:
            nonlocal current_users_by_id, current_subgroups_by_id

            group_id = group_state["id"]
            if group_id is None:
                return
            with session_scope() as session:
                auth_controller = AuthController(session=session)
                resource_controller = ResourceController(session=session)
                academic_controller = AcademicController(session=session)
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
                stream = academic_controller.get_stream(group.stream_id) if getattr(group, "stream_id", None) is not None else None
                course = (
                    academic_controller.get_course(stream.course_id)
                    if stream is not None and getattr(stream, "course_id", None) is not None
                    else None
                )
                specialty = (
                    academic_controller.get_specialty(course.specialty_id if course is not None else stream.specialty_id)
                    if stream is not None
                    else None
                )
                department = (
                    academic_controller.get_department(specialty.department_id)
                    if specialty is not None
                    else None
                )

            current_subgroups_by_id = {item.id: item for item in subgroups}
            current_users_by_id = {item.id: item for item in users}

            structure_parts: list[str] = []
            if department is not None:
                structure_parts.append(department.short_name or department.name)
            if specialty is not None:
                structure_parts.append(specialty.code or specialty.name)
            if course is not None:
                structure_parts.append(course.code or course.name)
            if stream is not None:
                structure_parts.append(stream.name)
            structure_prefix = " → ".join(structure_parts) if structure_parts else "Без структури потоку"
            detail_meta_var.set(
                f"{structure_prefix}. Додавай учасників за логіном і перетягуй їх між підгрупами."
            )

            render_participant_cards(users)
            render_subgroup_tree(users)

            available_usernames = [item.username for item in available_users if item.id not in current_users_by_id]
            participant_input_box["values"] = available_usernames
            if participant_username_var.get().strip() not in available_usernames:
                participant_username_var.set("")

        def open_reassign_group_stream_modal() -> None:
            group_id = group_state["id"]
            if group_id is None:
                return

            with session_scope() as session:
                resource_controller = ResourceController(session=session)
                academic_controller = AcademicController(session=session)
                group = resource_controller.get_resource(int(group_id))
                if group is None or group.type != ResourceType.GROUP:
                    messagebox.showerror("Помилка", "Групу не знайдено.")
                    open_main_view()
                    return
                streams = academic_controller.list_streams(company_id=company_id, include_archived=True)
                courses = academic_controller.list_courses(company_id=company_id, include_archived=True)
                specialties = academic_controller.list_specialties(company_id=company_id, include_archived=True)

            if not streams:
                messagebox.showerror("Курс/потік", "Немає доступних потоків для переназначення.", parent=self.root)
                return

            course_by_id = {item.id: item for item in courses}
            specialty_by_id = {item.id: item for item in specialties}
            stream_by_id = {item.id: item for item in streams}

            stream_labels_by_course_id: dict[int | None, list[str]] = {}
            stream_id_by_label: dict[str, int] = {}
            for stream in streams:
                course = course_by_id.get(stream.course_id) if stream.course_id is not None else None
                course_name = (course.code or course.name) if course is not None else "Без курсу"
                year_suffix = f" • набір {stream.admission_year}" if stream.admission_year is not None else ""
                label = f"{stream.id} | {course_name} • {stream.name}{year_suffix}"
                stream_id_by_label[label] = stream.id
                stream_labels_by_course_id.setdefault(stream.course_id, []).append(label)

            course_values: list[str] = []
            course_id_by_label: dict[str, int | None] = {}
            for course_id in sorted(stream_labels_by_course_id.keys(), key=lambda value: (value is None, value or 0)):
                if course_id is None:
                    label = "Без курсу"
                else:
                    course = course_by_id.get(course_id)
                    if course is None:
                        label = f"{course_id} | Курс"
                    else:
                        specialty = specialty_by_id.get(course.specialty_id)
                        specialty_prefix = f"{specialty.code} / " if specialty is not None and specialty.code else ""
                        course_label = f"{course.code} — {course.name}" if course.code else course.name
                        label = f"{course.id} | {specialty_prefix}{course_label}"
                course_values.append(label)
                course_id_by_label[label] = course_id

            if not course_values:
                messagebox.showerror("Курс/потік", "Немає доступних курсів для переназначення.", parent=self.root)
                return

            current_stream = stream_by_id.get(group.stream_id) if group.stream_id is not None else None
            current_course_id = current_stream.course_id if current_stream is not None else None
            current_stream_label = None
            if current_stream is not None:
                for label, stream_id in stream_id_by_label.items():
                    if stream_id == current_stream.id:
                        current_stream_label = label
                        break

            modal = tk.Toplevel(self.root)
            modal.title("Переназначення курсу та потоку")
            modal.transient(self.root)
            modal.resizable(False, False)
            modal.grab_set()

            shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
            shell.pack(fill=tk.BOTH, expand=True)
            ttk.Label(shell, text="Переназначення групи", style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(
                shell,
                text=f"Група: {group.name}",
                style="CardSubtle.TLabel",
            ).pack(anchor="w", pady=(2, 0))

            course_var = tk.StringVar()
            stream_var = tk.StringVar()

            ttk.Label(shell, text="Курс", style="Card.TLabel").pack(anchor="w", pady=(10, 0))
            course_box = ttk.Combobox(
                shell,
                textvariable=course_var,
                values=course_values,
                state="readonly",
                width=58,
            )
            course_box.pack(fill=tk.X, pady=(6, 8))

            ttk.Label(shell, text="Потік", style="Card.TLabel").pack(anchor="w")
            stream_box = ttk.Combobox(
                shell,
                textvariable=stream_var,
                values=[],
                state="readonly",
                width=58,
            )
            stream_box.pack(fill=tk.X, pady=(6, 10))

            stream_hint_var = tk.StringVar(value="")
            ttk.Label(shell, textvariable=stream_hint_var, style="CardSubtle.TLabel").pack(anchor="w")

            def _refresh_stream_values(*_args) -> None:
                selected_course_id = course_id_by_label.get(course_var.get().strip())
                values = stream_labels_by_course_id.get(selected_course_id, [])
                stream_box["values"] = values
                if stream_var.get().strip() not in values:
                    if current_stream_label is not None and current_stream_label in values:
                        stream_var.set(current_stream_label)
                    elif values:
                        stream_var.set(values[0])
                    else:
                        stream_var.set("")
                stream_hint_var.set(f"Доступно потоків: {len(values)}")

            initial_course_label = None
            for label, course_id in course_id_by_label.items():
                if course_id == current_course_id:
                    initial_course_label = label
                    break
            course_var.set(initial_course_label or course_values[0])
            _refresh_stream_values()
            course_box.bind("<<ComboboxSelected>>", _refresh_stream_values, add="+")

            footer = ttk.Frame(shell, style="Card.TFrame")
            footer.pack(fill=tk.X, pady=(10, 0))

            def on_submit_reassign_stream() -> None:
                selected_stream_id = stream_id_by_label.get(stream_var.get().strip())
                if selected_stream_id is None:
                    messagebox.showerror("Некоректні дані", "Оберіть потік зі списку.", parent=modal)
                    return
                try:
                    with session_scope() as session:
                        ResourceController(session=session).update_resource(
                            int(group_id),
                            stream_id=int(selected_stream_id),
                        )
                except Exception as exc:
                    messagebox.showerror("Не вдалося переназначити потік", str(exc), parent=modal)
                    return

                modal.destroy()
                load_group_detail()
                render_group_cards()

            self._motion_button(footer, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
            self._motion_button(footer, text="Зберегти", command=on_submit_reassign_stream, primary=True, width=130).pack(
                side=tk.RIGHT,
                padx=(0, 8),
            )

            modal.update_idletasks()
            modal.geometry(f"+{self.root.winfo_rootx() + 230}+{self.root.winfo_rooty() + 130}")

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

            subgroup_resource = current_subgroups_by_id.get(subgroup_id)
            subgroup_name = subgroup_short_name(subgroup_resource.name) if subgroup_resource is not None else f"#{subgroup_id}"
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
                auth_controller = AuthController(session=session)
                academic_controller = AcademicController(session=session)
                personal_users = auth_controller.list_available_personal_users_for_company(
                    company_id=company_id
                )
                streams = academic_controller.list_streams(company_id=company_id, include_archived=False)
                courses = academic_controller.list_courses(company_id=company_id, include_archived=True)
                specialties = academic_controller.list_specialties(company_id=company_id, include_archived=True)
            if not streams:
                messagebox.showerror("Створення групи", "Спочатку створіть потік (кафедра → спеціальність → курс → потік).")
                return
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

            course_by_id = {item.id: item for item in courses}
            specialty_by_id = {item.id: item for item in specialties}
            stream_values = []
            for item in streams:
                course = course_by_id.get(getattr(item, "course_id", None))
                specialty = specialty_by_id.get(course.specialty_id) if course is not None else specialty_by_id.get(item.specialty_id)
                spec_label = f"{specialty.code} — " if specialty is not None and specialty.code else ""
                course_label = f"{(course.code or course.name)} • " if course is not None else ""
                year_suffix = f" • набір {item.admission_year}" if item.admission_year is not None else ""
                stream_values.append(f"{item.id} | {spec_label}{course_label}{item.name}{year_suffix}")
            stream_var = tk.StringVar(value=stream_values[0])

            stream_row = ttk.Frame(root, style="Card.TFrame")
            stream_row.pack(fill=tk.X, pady=(0, 10))
            ttk.Label(stream_row, text="Потік", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Combobox(stream_row, textvariable=stream_var, values=stream_values, width=34, state="readonly").pack(
                side=tk.LEFT,
                padx=(8, 0),
            )
    
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
            tree = ttk.Treeview(
                tree_container,
                show="tree headings",
                height=10,
                selectmode="browse",
            )
            tree.heading("#0", text="Підгрупи та учасники", anchor="w")
            tree.column("#0", anchor="w", minwidth=240, width=360, stretch=True)
            tree.tag_configure(
                "bucket",
                font=("Segoe UI", 10, "bold"),
                background=self.theme.SURFACE_ALT,
                foreground=self.theme.TEXT_PRIMARY,
            )
            tree.tag_configure(
                "participant",
                font=("Segoe UI", 10),
                foreground=self.theme.TEXT_PRIMARY,
            )
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
            tree.insert("", tk.END, iid=unassigned_iid, text="Без підгрупи [0]", open=True, tags=("bucket",))
            subgroup_iid_by_name: dict[str, str] = {}
            subgroup_name_by_iid: dict[str, str] = {}
            added_users: dict[int, str] = {}
            assignment_by_user_id: dict[int, str | None] = {}
            drag_state: dict[str, str | bool | None] = {"item": None, "active": False}

            def refresh_tree_bucket_labels() -> None:
                tree.item(unassigned_iid, text=f"Без підгрупи [{len(tree.get_children(unassigned_iid))}]")
                for subgroup_name, subgroup_iid in subgroup_iid_by_name.items():
                    tree.item(subgroup_iid, text=f"Підгрупа: {subgroup_name} [{len(tree.get_children(subgroup_iid))}]")
    
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
                tree.insert(unassigned_iid, tk.END, iid=item_iid, text=f"Учасник: {user.username}", tags=("participant",))
                added_users[user.id] = user.username
                assignment_by_user_id[user.id] = None
                participant_var.set("")
                refresh_suggestions()
                refresh_tree_bucket_labels()
    
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
                refresh_tree_bucket_labels()
    
            def add_subgroup() -> None:
                name = subgroup_var.get().strip()
                if not name:
                    messagebox.showerror("Помилка", "Вкажи назву підгрупи.", parent=modal)
                    return
                if name in subgroup_iid_by_name:
                    return
                iid = f"sg_{len(subgroup_iid_by_name) + 1}_{uuid4().hex[:4]}"
                tree.insert("", tk.END, iid=iid, text=f"Підгрупа: {name} [0]", open=True, tags=("bucket",))
                subgroup_iid_by_name[name] = iid
                subgroup_name_by_iid[iid] = name
                subgroup_var.set("")
                refresh_tree_bucket_labels()
    
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
                refresh_tree_bucket_labels()
    
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
                refresh_tree_bucket_labels()
    
            def save_group() -> None:
                group_name = group_name_var.get().strip()
                if not group_name:
                    messagebox.showerror("Некоректні дані", "Введи назву групи.", parent=modal)
                    return
                stream_id = parse_selected_prefixed_id(stream_var.get())
                if stream_id is None:
                    messagebox.showerror("Некоректні дані", "Обери потік зі списку.", parent=modal)
                    return
                try:
                    with session_scope() as session:
                        resource_controller = ResourceController(session=session)
                        auth_controller = AuthController(session=session)
                        group = resource_controller.create_resource(
                            name=group_name,
                            resource_type=ResourceType.GROUP,
                            company_id=company_id,
                            stream_id=stream_id,
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
            refresh_tree_bucket_labels()

        course_filter_box.bind("<<ComboboxSelected>>", on_course_filter_change, add="+")
        stream_filter_box.bind("<<ComboboxSelected>>", on_stream_filter_change, add="+")
        cards_canvas.bind("<Configure>", on_cards_resize, add="+")
        main_view.bind("<Map>", lambda _event: on_cards_resize(), add="+")

        hierarchy_back_button.command = on_hierarchy_back
        back_button.command = open_main_view
        set_hierarchy_level("departments", department_id=None, specialty_id=None)
        open_main_view()

    def _build_company_rooms_view(self, parent: ttk.Frame, company_id: int) -> None:
        buildings_state: dict[str, list[object]] = {"items": []}
        columns_state = {"value": 4}
        selected_building = {"item": None}
        rooms_state: dict[str, list[object]] = {"items": []}
        room_booking_state: dict[int, object] = {}
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
        detail_header.pack(fill=tk.X, pady=(0, 6))
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

        detail_actions = ttk.Frame(detail_view, style="Card.TFrame")
        detail_actions.pack(fill=tk.X, pady=(0, 8))

        room_search_var = tk.StringVar(value="")
        room_type_filter_var = tk.StringVar(value="Усі")
        room_min_capacity_var = tk.StringVar(value="")
        room_department_filter_var = tk.StringVar(value="Усі кафедри")
        room_projector_filter_var = tk.StringVar(value="Усі")
        room_projector_filter_options: list[tuple[str, bool | None]] = [
            ("Усі", None),
            ("Є проєктор", True),
            ("Немає проєктора", False),
        ]
        room_projector_filter_by_label = {label: value for label, value in room_projector_filter_options}
        room_department_label_by_id: dict[int, str] = {}
        room_department_id_by_label: dict[str, int] = {}
        room_status_all_var = tk.BooleanVar(value=True)
        room_status_active_var = tk.BooleanVar(value=True)
        room_status_archived_var = tk.BooleanVar(value=True)
        room_status_booked_var = tk.BooleanVar(value=True)
        room_filter_sync_state = {"busy": False}
        room_filter_reload_job = {"id": None}
        rooms_count_var = tk.StringVar(value="Аудиторій: 0")

        detail_body = ttk.Frame(detail_view, style="Card.TFrame")
        detail_body.pack(fill=tk.BOTH, expand=True)

        rooms_header = ttk.Frame(detail_body, style="Card.TFrame")
        rooms_header.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(rooms_header, text="Аудиторії", style="CardTitle.TLabel").pack(side=tk.LEFT)
        ttk.Label(rooms_header, textvariable=rooms_count_var, style="CardSubtle.TLabel").pack(side=tk.LEFT, padx=(12, 0), pady=(4, 0))

        filters_shell = ttk.Frame(detail_body, style="Card.TFrame", padding=(2, 2, 2, 2))
        filters_shell.pack(fill=tk.X, pady=(0, 8))
        filters_shell.grid_columnconfigure(1, weight=1)

        ttk.Label(filters_shell, text="Пошук", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        room_search_entry = ttk.Entry(filters_shell, textvariable=room_search_var)
        room_search_entry.grid(row=0, column=1, sticky="ew", padx=(8, 12))

        ttk.Label(filters_shell, text="Тип", style="Card.TLabel").grid(row=0, column=2, sticky="w")
        room_type_box = ttk.Combobox(
            filters_shell,
            textvariable=room_type_filter_var,
            values=[label for label, _ in room_type_options],
            state="readonly",
            width=16,
        )
        room_type_box.grid(row=0, column=3, sticky="w", padx=(8, 12))
        ttk.Label(filters_shell, text="Мін. місткість", style="Card.TLabel").grid(row=0, column=4, sticky="w")
        room_capacity_entry = ttk.Entry(filters_shell, textvariable=room_min_capacity_var, width=8)
        room_capacity_entry.grid(row=0, column=5, sticky="w", padx=(8, 12))
        ttk.Label(filters_shell, text="Кафедра", style="Card.TLabel").grid(row=0, column=6, sticky="w")
        room_department_box = ttk.Combobox(
            filters_shell,
            textvariable=room_department_filter_var,
            state="readonly",
            width=24,
        )
        room_department_box.grid(row=0, column=7, sticky="w", padx=(8, 12))
        ttk.Label(filters_shell, text="Проєктор", style="Card.TLabel").grid(row=0, column=8, sticky="w")
        room_projector_box = ttk.Combobox(
            filters_shell,
            textvariable=room_projector_filter_var,
            values=[label for label, _ in room_projector_filter_options],
            state="readonly",
            width=18,
        )
        room_projector_box.grid(row=0, column=9, sticky="w", padx=(8, 12))

        status_wrap = ttk.Frame(filters_shell, style="Card.TFrame")
        status_wrap.grid(row=1, column=0, columnspan=11, sticky="ew", pady=(12, 0))
        ttk.Label(status_wrap, text="Статус:", style="CardSubtle.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        status_buttons_wrap = ttk.Frame(status_wrap, style="Card.TFrame")
        status_buttons_wrap.pack(side=tk.LEFT, fill=tk.X, expand=True)
        status_chip_specs: list[tuple[str, str, tk.BooleanVar, int]] = [
            ("all", "Усі", room_status_all_var, 74),
            ("active", "Активні", room_status_active_var, 94),
            ("archived", "Архівні", room_status_archived_var, 90),
            ("booked", "Бронь", room_status_booked_var, 82),
        ]
        status_chip_buttons: dict[str, RoundedMotionButton] = {}
        for key, label, variable, width in status_chip_specs:
            chip_button = self._motion_button(
                status_buttons_wrap,
                text=label,
                command=lambda var=variable: var.set(not bool(var.get())),
                primary=False,
                width=width,
                height=30,
            )
            chip_button.pack(side=tk.LEFT, padx=(0, 6))
            status_chip_buttons[key] = chip_button

        def refresh_status_chips() -> None:
            for key, label, variable, _width in status_chip_specs:
                chip_button = status_chip_buttons[key]
                active = bool(variable.get())
                if active:
                    chip_button.fill = self.theme.ACCENT
                    chip_button.hover_fill = self.theme.ACCENT_HOVER
                    chip_button.pressed_fill = self.theme.ACCENT_PRESSED
                    chip_button.text_color = self.theme.TEXT_LIGHT
                    chip_button.shadow_color = self.theme.SHADOW_SOFT
                    chip_button.set_text(f"✓ {label}")
                else:
                    chip_button.fill = self.theme.SURFACE_ALT
                    chip_button.hover_fill = self.theme.SECONDARY_HOVER
                    chip_button.pressed_fill = self.theme.SECONDARY_PRESSED
                    chip_button.text_color = self.theme.TEXT_PRIMARY
                    chip_button.shadow_color = self.theme.SHADOW_SOFT
                    chip_button.set_text(label)

        def on_filter_panel_resize(_event=None) -> None:
            width = max(1, filters_shell.winfo_width())
            compact = width < 1240
            if compact:
                filters_shell.grid_columnconfigure(1, weight=0)
                room_search_entry.grid_configure(columnspan=1)
                room_search_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 12), pady=(6, 0))
                room_type_box.grid(row=1, column=2, sticky="w", padx=(8, 12), pady=(6, 0))
                room_capacity_entry.grid(row=1, column=4, sticky="w", padx=(8, 12), pady=(6, 0))
                room_department_box.grid_configure(row=1, column=6, sticky="w", padx=(8, 12), pady=(6, 0))
                room_projector_box.grid_configure(row=1, column=8, sticky="w", padx=(8, 12), pady=(6, 0))
                reset_filters_button.grid_configure(row=1, column=10, sticky="e", padx=(0, 0), pady=(6, 0))
                status_wrap.grid_configure(row=2, column=0, columnspan=11, pady=(10, 0))
            else:
                filters_shell.grid_columnconfigure(1, weight=1)
                room_search_entry.grid_configure(row=0, column=1, columnspan=1, sticky="ew", padx=(8, 12), pady=(0, 0))
                room_type_box.grid_configure(row=0, column=3, sticky="w", padx=(8, 12), pady=(0, 0))
                room_capacity_entry.grid_configure(row=0, column=5, sticky="w", padx=(8, 12), pady=(0, 0))
                room_department_box.grid_configure(row=0, column=7, sticky="w", padx=(8, 12), pady=(0, 0))
                room_projector_box.grid_configure(row=0, column=9, sticky="w", padx=(8, 12), pady=(0, 0))
                reset_filters_button.grid_configure(row=0, column=10, sticky="e", padx=(0, 0), pady=(0, 0))
                status_wrap.grid_configure(row=1, column=0, columnspan=11, pady=(12, 0))

        rooms_table_wrap = ttk.Frame(detail_body, style="Card.TFrame")
        rooms_table_wrap.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        rooms_table = ttk.Treeview(
            rooms_table_wrap,
            columns=("name", "type", "capacity", "floor", "department", "projector", "status"),
            show="headings",
            height=18,
        )
        rooms_table.heading("name", text="Назва")
        rooms_table.heading("type", text="Тип")
        rooms_table.heading("capacity", text="Місткість")
        rooms_table.heading("floor", text="Поверх")
        rooms_table.heading("department", text="Кафедра")
        rooms_table.heading("projector", text="Проєктор")
        rooms_table.heading("status", text="Статус")
        rooms_table.column("name", width=280, anchor="w")
        rooms_table.column("type", width=150, anchor="center")
        rooms_table.column("capacity", width=110, anchor="center")
        rooms_table.column("floor", width=110, anchor="center")
        rooms_table.column("department", width=170, anchor="center")
        rooms_table.column("projector", width=110, anchor="center")
        rooms_table.column("status", width=200, anchor="center")
        rooms_table.tag_configure("room_archived", background="#f4e8ef")
        rooms_table.tag_configure("room_booked", background="#e8f0ff")
        rooms_table.tag_configure("room_archived_booked", background="#efe6f8")
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
            room_filter_sync_state["busy"] = True
            room_search_var.set("")
            room_type_filter_var.set("Усі")
            room_min_capacity_var.set("")
            room_department_filter_var.set("Усі кафедри")
            room_projector_filter_var.set("Усі")
            room_status_all_var.set(True)
            room_status_active_var.set(True)
            room_status_archived_var.set(True)
            room_status_booked_var.set(True)
            room_filter_sync_state["busy"] = False
            load_room_departments()
            refresh_status_chips()
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

        def parse_datetime_input(raw: str, *, field_name: str) -> datetime:
            value = raw.strip()
            if not value:
                raise ValueError(f"Поле '{field_name}' обов'язкове.")
            for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            try:
                return datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValueError(
                    f"Поле '{field_name}' має бути у форматі YYYY-MM-DD HH:MM або DD.MM.YYYY HH:MM."
                ) from exc

        def load_room_departments() -> None:
            with session_scope() as session:
                departments = AcademicController(session=session).list_departments(
                    company_id=company_id,
                    include_archived=False,
                )
            room_department_label_by_id.clear()
            room_department_id_by_label.clear()
            values = ["Усі кафедри"]
            for department in departments:
                label_name = department.short_name or department.name
                label = f"{department.id} | {label_name}"
                room_department_label_by_id[department.id] = label_name
                room_department_id_by_label[label] = department.id
                values.append(label)
            room_department_box["values"] = values
            if room_department_filter_var.get() not in values:
                room_department_filter_var.set("Усі кафедри")

        def selected_room_department_id() -> int | None:
            return room_department_id_by_label.get(room_department_filter_var.get().strip())

        def room_department_display_value(department_id: int | None) -> str:
            if department_id is None:
                return "Не вказано"
            name = room_department_label_by_id.get(department_id)
            if not name:
                return "Не вказано"
            return f"{department_id} | {name}"

        def parse_room_department_selection(raw: str) -> int | None:
            value = raw.strip()
            if not value or value == "Не вказано":
                return None
            department_id = room_department_id_by_label.get(value)
            if department_id is None:
                raise ValueError("Оберіть кафедру зі списку або 'Не вказано'.")
            return department_id

        def schedule_room_filter_reload(delay_ms: int = 220) -> None:
            if room_filter_sync_state["busy"]:
                return
            job_id = room_filter_reload_job["id"]
            if job_id is not None:
                try:
                    self.root.after_cancel(job_id)
                except ValueError:
                    pass
                room_filter_reload_job["id"] = None

            def _execute_reload() -> None:
                room_filter_reload_job["id"] = None
                load_rooms()

            room_filter_reload_job["id"] = self.root.after(delay_ms, _execute_reload)

        def on_room_status_all_changed(*_args) -> None:
            if room_filter_sync_state["busy"]:
                return
            value = bool(room_status_all_var.get())
            room_filter_sync_state["busy"] = True
            room_status_active_var.set(value)
            room_status_archived_var.set(value)
            room_status_booked_var.set(value)
            room_filter_sync_state["busy"] = False
            refresh_status_chips()
            schedule_room_filter_reload(delay_ms=0)

        def on_room_status_partial_changed(*_args) -> None:
            if room_filter_sync_state["busy"]:
                return
            all_selected = bool(room_status_active_var.get()) and bool(room_status_archived_var.get()) and bool(
                room_status_booked_var.get()
            )
            room_filter_sync_state["busy"] = True
            room_status_all_var.set(all_selected)
            room_filter_sync_state["busy"] = False
            refresh_status_chips()
            schedule_room_filter_reload(delay_ms=0)

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
            now = datetime.utcnow()
            for room in items:
                booking = room_booking_state.get(int(room.id))
                is_booked = booking is not None
                if is_booked:
                    starts_at = booking.starts_at
                    ends_at = booking.ends_at
                    if starts_at <= now <= ends_at:
                        status_text = f"Заброньована до {ends_at.strftime('%d.%m %H:%M')}"
                    else:
                        status_text = f"Бронь з {starts_at.strftime('%d.%m %H:%M')}"
                else:
                    status_text = "Активна"
                if bool(room.is_archived):
                    status_text = "Архівна" if not is_booked else f"Архівна • {status_text}"

                row_tags: tuple[str, ...] = ()
                if bool(room.is_archived) and is_booked:
                    row_tags = ("room_archived_booked",)
                elif bool(room.is_archived):
                    row_tags = ("room_archived",)
                elif is_booked:
                    row_tags = ("room_booked",)

                rooms_table.insert(
                    "",
                    tk.END,
                    iid=str(room.id),
                    values=(
                        str(room.name),
                        room_type_label_by_enum.get(room.room_type, "Інше"),
                        "" if room.capacity is None else str(room.capacity),
                        "" if room.floor is None else str(room.floor),
                        room_department_label_by_id.get(room.home_department_id, "—") if room.home_department_id is not None else "—",
                        "Так" if bool(room.has_projector) else "Ні",
                        status_text,
                    ),
                    tags=row_tags,
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

            min_capacity = None
            raw_capacity = room_min_capacity_var.get().strip()
            if raw_capacity:
                if not raw_capacity.isdigit():
                    return
                min_capacity = int(raw_capacity)
            home_department_id = selected_room_department_id()
            selected_projector_label = room_projector_filter_var.get().strip() or "Усі"
            if selected_projector_label not in room_projector_filter_by_label:
                messagebox.showerror("Некоректний фільтр", "Невідомий стан фільтра проєктора.", parent=self.root)
                return
            has_projector_filter = room_projector_filter_by_label[selected_projector_label]

            with session_scope() as session:
                controller = RoomController(session=session)
                rooms = controller.list_rooms(
                    building_id=building.id,
                    include_archived=True,
                    search=room_search_var.get().strip() or None,
                    room_type=room_type_filter,
                    min_capacity=min_capacity,
                    has_projector=has_projector_filter,
                    home_department_id=home_department_id,
                )
                room_booking_state.clear()
                room_booking_state.update(
                    controller.upcoming_booking_map([int(room.id) for room in rooms])
                )

            show_active = bool(room_status_active_var.get())
            show_archived = bool(room_status_archived_var.get())
            show_booked = bool(room_status_booked_var.get())

            filtered_rooms: list[object] = []
            for room in rooms:
                room_id = int(room.id)
                is_archived = bool(room.is_archived)
                is_booked = room_id in room_booking_state
                include_room = (
                    (show_active and (not is_archived and not is_booked))
                    or (show_archived and is_archived)
                    or (show_booked and is_booked)
                )
                if include_room:
                    filtered_rooms.append(room)

            rooms_state["items"] = filtered_rooms
            render_rooms()
            refresh_room_action_state()

        def open_room_modal(room=None) -> None:
            building = selected_building["item"]
            if building is None:
                messagebox.showerror("Аудиторія", "Спочатку виберіть корпус.", parent=self.root)
                return
            load_room_departments()

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
            has_projector_var = tk.BooleanVar(value=bool(room.has_projector) if is_edit else False)
            department_values = ["Не вказано"] + list(room_department_id_by_label.keys())
            department_var = tk.StringVar(value=room_department_display_value(room.home_department_id) if is_edit else "Не вказано")

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

            dep_row = ttk.Frame(shell, style="Card.TFrame")
            dep_row.pack(fill=tk.X, pady=(0, 12))
            ttk.Label(dep_row, text="Кафедра", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Combobox(
                dep_row,
                textvariable=department_var,
                values=department_values,
                state="readonly",
                width=32,
            ).pack(side=tk.LEFT, padx=(8, 0))

            projector_row = ttk.Frame(shell, style="Card.TFrame")
            projector_row.pack(fill=tk.X, pady=(0, 12))
            ttk.Checkbutton(
                projector_row,
                text="Є проєктор",
                variable=has_projector_var,
            ).pack(anchor="w")

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
                    department_id = parse_room_department_selection(department_var.get())
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
                                has_projector=bool(has_projector_var.get()),
                                home_department_id=department_id,
                                is_archived=False,
                            )
                        else:
                            controller.create_room(
                                building_id=building.id,
                                name=clean_name,
                                room_type=selected_type,
                                capacity=capacity,
                                floor=floor,
                                has_projector=bool(has_projector_var.get()),
                                home_department_id=department_id,
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

        def toggle_archive_selected_room() -> None:
            room = get_selected_room()
            if room is None:
                messagebox.showerror("Статус аудиторії", "Оберіть аудиторію у списку.", parent=self.root)
                return

            is_archived = bool(room.is_archived)
            action_title = "Розархівування аудиторії" if is_archived else "Архівація аудиторії"
            question = (
                f"Розархівувати аудиторію '{room.name}'?"
                if is_archived
                else f"Архівувати аудиторію '{room.name}'?"
            )
            if not messagebox.askyesno(action_title, question, parent=self.root):
                return

            with session_scope() as session:
                controller = RoomController(session=session)
                if is_archived:
                    controller.unarchive_room(room.id)
                else:
                    controller.archive_room(room.id)
            load_rooms()

        def open_book_room_modal(room=None) -> None:
            target = room if room is not None else get_selected_room()
            if target is None:
                messagebox.showerror("Бронювання аудиторії", "Оберіть аудиторію у списку.", parent=self.root)
                return
            if bool(target.is_archived):
                messagebox.showerror(
                    "Бронювання аудиторії",
                    "Архівовану аудиторію не можна забронювати. Спочатку розархівуйте її.",
                    parent=self.root,
                )
                return

            now = datetime.now().replace(second=0, microsecond=0)
            default_start = now + timedelta(minutes=30 - (now.minute % 30 or 30))
            default_end = default_start + timedelta(hours=1)

            modal = tk.Toplevel(self.root)
            modal.title("Бронювання аудиторії")
            modal.transient(self.root)
            modal.resizable(False, False)
            modal.grab_set()

            shell = ttk.Frame(modal, style="Card.TFrame", padding=14)
            shell.pack(fill=tk.BOTH, expand=True)
            ttk.Label(shell, text="Бронювання аудиторії", style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(shell, text=f"Аудиторія: {target.name}", style="CardSubtle.TLabel").pack(anchor="w", pady=(2, 10))

            title_var = tk.StringVar(value="")
            starts_var = tk.StringVar(value=default_start.strftime("%Y-%m-%d %H:%M"))
            ends_var = tk.StringVar(value=default_end.strftime("%Y-%m-%d %H:%M"))

            ttk.Label(shell, text="Назва / примітка", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=title_var, width=42).pack(fill=tk.X, pady=(6, 10))
            ttk.Label(shell, text="Початок", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=starts_var, width=24).pack(fill=tk.X, pady=(6, 10))
            ttk.Label(shell, text="Кінець", style="Card.TLabel").pack(anchor="w")
            ttk.Entry(shell, textvariable=ends_var, width=24).pack(fill=tk.X, pady=(6, 4))
            ttk.Label(
                shell,
                text="Формат: YYYY-MM-DD HH:MM або DD.MM.YYYY HH:MM",
                style="CardSubtle.TLabel",
            ).pack(anchor="w", pady=(0, 10))

            actions = ttk.Frame(shell, style="Card.TFrame")
            actions.pack(fill=tk.X)

            def on_submit_booking() -> None:
                try:
                    starts_at = parse_datetime_input(starts_var.get(), field_name="Початок")
                    ends_at = parse_datetime_input(ends_var.get(), field_name="Кінець")
                except ValueError as exc:
                    messagebox.showerror("Некоректні дані", str(exc), parent=modal)
                    return

                try:
                    with session_scope() as session:
                        controller = RoomController(session=session)
                        controller.create_room_booking(
                            room_id=int(target.id),
                            starts_at=starts_at,
                            ends_at=ends_at,
                            title=title_var.get().strip() or None,
                        )
                except Exception as exc:
                    messagebox.showerror("Бронювання аудиторії", str(exc), parent=modal)
                    return

                modal.destroy()
                load_rooms()

            self._motion_button(actions, text="Скасувати", command=modal.destroy, primary=False, width=130).pack(side=tk.RIGHT)
            self._motion_button(actions, text="Забронювати", command=on_submit_booking, primary=True, width=130).pack(
                side=tk.RIGHT,
                padx=(0, 8),
            )

            modal.update_idletasks()
            modal.geometry(f"+{self.root.winfo_rootx() + 250}+{self.root.winfo_rooty() + 130}")

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
            load_room_departments()

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
            mode_buttons: dict[str, tk.Button] = {}

            tabs_shell = ttk.Frame(shell, style="Card.TFrame")
            tabs_shell.pack(fill=tk.X, pady=(0, 8))
            tabs_shell.grid_columnconfigure(0, weight=1)
            tabs_shell.grid_columnconfigure(1, weight=1)

            def set_bulk_mode(mode: str) -> None:
                mode_var.set(mode)
                refresh_mode_tabs()
                render_mode_panel()

            def refresh_mode_tabs() -> None:
                active_mode = mode_var.get()
                for mode_name, button in mode_buttons.items():
                    is_active = mode_name == active_mode
                    button.configure(
                        bg=self.theme.ACCENT if is_active else self.theme.SURFACE_ALT,
                        fg=self.theme.TEXT_LIGHT if is_active else self.theme.TEXT_PRIMARY,
                        activebackground=self.theme.ACCENT_HOVER if is_active else self.theme.SECONDARY_HOVER,
                        activeforeground=self.theme.TEXT_LIGHT if is_active else self.theme.TEXT_PRIMARY,
                        relief=tk.FLAT,
                        bd=0,
                        cursor="hand2",
                    )

            def make_tab_button(*, label: str, mode: str, column: int) -> None:
                button = tk.Button(
                    tabs_shell,
                    text=label,
                    font=("Segoe UI", 10, "bold"),
                    padx=12,
                    pady=8,
                    command=lambda m=mode: set_bulk_mode(m),
                )
                button.grid(row=0, column=column, sticky="ew", padx=(0, 6) if column == 0 else (6, 0))
                mode_buttons[mode] = button

            make_tab_button(label="Діапазон", mode="range", column=0)
            make_tab_button(label="Список", mode="list", column=1)

            prefix_var = tk.StringVar(value=f"{building.name}-")
            start_var = tk.StringVar(value="101")
            end_var = tk.StringVar(value="120")
            step_var = tk.StringVar(value="1")
            exclude_var = tk.StringVar(value="")

            mode_panel = ttk.Frame(shell, style="Card.TFrame")
            mode_panel.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            range_panel = ttk.Frame(mode_panel, style="Card.TFrame")
            list_panel = ttk.Frame(mode_panel, style="Card.TFrame")

            list_text = tk.Text(
                list_panel,
                height=8,
                width=48,
                bg=self.theme.SURFACE_ALT,
                fg=self.theme.TEXT_PRIMARY,
                insertbackground=self.theme.TEXT_PRIMARY,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=self.theme.BORDER,
                highlightcolor=self.theme.ACCENT,
            )

            grid = ttk.Frame(range_panel, style="Card.TFrame")
            grid.pack(fill=tk.X)
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

            ttk.Label(list_panel, text="Список назв: одна назва аудиторії на рядок", style="CardSubtle.TLabel").pack(anchor="w")
            list_text.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

            def render_mode_panel() -> None:
                range_panel.pack_forget()
                list_panel.pack_forget()
                if mode_var.get() == "list":
                    list_panel.pack(fill=tk.BOTH, expand=True)
                else:
                    range_panel.pack(fill=tk.X)

            refresh_mode_tabs()
            render_mode_panel()

            settings_row = ttk.Frame(shell, style="Card.TFrame")
            settings_row.pack(fill=tk.X, pady=(0, 10))
            type_var = tk.StringVar(value="Клас")
            capacity_var = tk.StringVar(value="")
            floor_var = tk.StringVar(value="")
            bulk_has_projector_var = tk.BooleanVar(value=False)
            bulk_department_values = ["Не вказано"] + list(room_department_id_by_label.keys())
            bulk_department_var = tk.StringVar(value="Не вказано")
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
            ttk.Checkbutton(
                settings_row,
                text="Проєктор",
                variable=bulk_has_projector_var,
            ).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Label(settings_row, text="Кафедра", style="Card.TLabel").pack(side=tk.LEFT)
            ttk.Combobox(
                settings_row,
                textvariable=bulk_department_var,
                values=bulk_department_values,
                state="readonly",
                width=22,
            ).pack(side=tk.LEFT, padx=(6, 10))
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
                    home_department_id = parse_room_department_selection(bulk_department_var.get())
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
                            has_projector=bool(bulk_has_projector_var.get()),
                            home_department_id=home_department_id,
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
            room_filter_sync_state["busy"] = True
            room_search_var.set("")
            room_type_filter_var.set("Усі")
            room_min_capacity_var.set("")
            room_department_filter_var.set("Усі кафедри")
            room_projector_filter_var.set("Усі")
            room_status_all_var.set(True)
            room_status_active_var.set(True)
            room_status_archived_var.set(True)
            room_status_booked_var.set(True)
            room_filter_sync_state["busy"] = False
            refresh_status_chips()
            load_rooms()

        room_action_buttons: list[object] = []

        button_new_room = self._motion_button(
            detail_actions,
            text="+ Нова аудиторія",
            command=lambda: open_room_modal(room=None),
            primary=True,
            width=138,
            height=38,
        )
        room_action_buttons.append(button_new_room)
        button_bulk_create = self._motion_button(
            detail_actions,
            text="+ Масове додавання",
            command=open_bulk_create_rooms_modal,
            primary=False,
            width=152,
            height=38,
        )
        room_action_buttons.append(button_bulk_create)
        button_edit_room = self._motion_button(
            detail_actions,
            text="Редагувати",
            command=lambda: open_room_modal(room=get_selected_room()) if get_selected_room() is not None else messagebox.showerror(
                "Редагування аудиторії",
                "Оберіть аудиторію у списку.",
                parent=self.root,
            ),
            primary=False,
            width=112,
            height=38,
        )
        room_action_buttons.append(button_edit_room)
        archive_toggle_button = self._motion_button(
            detail_actions,
            text="Архівувати",
            command=toggle_archive_selected_room,
            primary=False,
            width=124,
            height=38,
        )
        room_action_buttons.append(archive_toggle_button)
        button_book_room = self._motion_button(
            detail_actions,
            text="Забронювати",
            command=lambda: open_book_room_modal(room=None),
            primary=False,
            width=124,
            height=38,
        )
        room_action_buttons.append(button_book_room)
        button_delete_room = self._motion_button(
            detail_actions,
            text="Видалити",
            command=delete_selected_room,
            primary=False,
            width=108,
            height=38,
            fill="#e11d48",
            hover_fill="#be123c",
            pressed_fill="#9f1239",
            text_color=self.theme.TEXT_LIGHT,
        )
        room_action_buttons.append(button_delete_room)

        def relayout_room_actions(_event=None) -> None:
            width = max(1, detail_actions.winfo_width())
            if width >= 860:
                columns = 6
            elif width >= 740:
                columns = 5
            elif width >= 610:
                columns = 4
            elif width >= 470:
                columns = 3
            elif width >= 340:
                columns = 2
            else:
                columns = 1
            max_columns = 6
            for col in range(max_columns):
                if col < columns:
                    detail_actions.grid_columnconfigure(col, weight=1, uniform="room-action-col")
                else:
                    detail_actions.grid_columnconfigure(col, weight=0, uniform="")
            for index, button in enumerate(room_action_buttons):
                row = index // columns
                col = index % columns
                button.grid(row=row, column=col, sticky="ew", padx=4, pady=4)

        def refresh_room_action_state(_event=None) -> None:
            room = get_selected_room()
            if room is not None and bool(room.is_archived):
                archive_toggle_button.set_text("Розархівувати")
            else:
                archive_toggle_button.set_text("Архівувати")

        room_context_menu = tk.Menu(self.root, tearoff=0)

        def on_rooms_table_context_menu(event: tk.Event) -> str:
            row_id = rooms_table.identify_row(event.y)
            if not row_id:
                return "break"
            rooms_table.selection_set(row_id)
            refresh_room_action_state()

            room = get_selected_room()
            if room is None:
                return "break"

            room_context_menu.delete(0, tk.END)
            room_context_menu.add_command(label="Редагувати", command=lambda: open_room_modal(room=room))
            room_context_menu.add_command(
                label="Розархівувати" if bool(room.is_archived) else "Архівувати",
                command=toggle_archive_selected_room,
            )
            room_context_menu.add_command(label="Забронювати", command=lambda: open_book_room_modal(room=room))
            room_context_menu.add_separator()
            room_context_menu.add_command(label="Видалити", command=delete_selected_room)
            room_context_menu.tk_popup(event.x_root, event.y_root)
            room_context_menu.grab_release()
            return "break"

        reset_filters_button = self._motion_button(
            filters_shell,
            text="Скинути",
            command=on_reset_room_filters,
            primary=False,
            width=108,
            height=34,
        )
        on_filter_panel_resize()
        refresh_status_chips()

        room_search_var.trace_add("write", lambda *_args: schedule_room_filter_reload())
        room_min_capacity_var.trace_add("write", lambda *_args: schedule_room_filter_reload())
        room_status_all_var.trace_add("write", on_room_status_all_changed)
        room_status_active_var.trace_add("write", on_room_status_partial_changed)
        room_status_archived_var.trace_add("write", on_room_status_partial_changed)
        room_status_booked_var.trace_add("write", on_room_status_partial_changed)
        room_type_box.bind("<<ComboboxSelected>>", lambda _e: load_rooms(), add="+")
        room_department_box.bind("<<ComboboxSelected>>", lambda _e: load_rooms(), add="+")
        room_projector_box.bind("<<ComboboxSelected>>", lambda _e: load_rooms(), add="+")
        filters_shell.bind("<Configure>", on_filter_panel_resize, add="+")
        detail_actions.bind("<Configure>", relayout_room_actions, add="+")
        relayout_room_actions()

        rooms_table.bind("<<TreeviewSelect>>", refresh_room_action_state, add="+")
        rooms_table.bind("<Button-3>", on_rooms_table_context_menu, add="+")

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
