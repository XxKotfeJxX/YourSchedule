from __future__ import annotations

from calendar import monthrange
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
from app.controllers.curriculum_controller import CurriculumController
from app.controllers.requirement_controller import RequirementController
from app.controllers.resource_controller import ResourceController
from app.controllers.room_controller import RoomController
from app.controllers.schedule_validation_controller import ScheduleValidationController
from app.controllers.schedule_view_controller import ScheduleViewController
from app.controllers.scheduler_controller import SchedulerController
from app.controllers.template_controller import TemplateController
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
from app.ui.main_window_methods import ensure_main_window_method_impls



ensure_main_window_method_impls(globals())

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

    def _dismiss_combobox_popdowns(self, scope: tk.Widget) -> None:
        stack: list[tk.Widget] = [scope]
        while stack:
            widget = stack.pop()
            try:
                if str(widget.winfo_class()) == "TCombobox":
                    try:
                        self.root.tk.call("ttk::combobox::Unpost", str(widget))
                    except tk.TclError:
                        pass
                stack.extend(widget.winfo_children())
            except tk.TclError:
                continue

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

    def _show_company_dashboard(self, *args, **kwargs):
        return _show_company_dashboard__impl(self, *args, **kwargs)


    def _build_company_schedule_view(self, *args, **kwargs):
        return _build_company_schedule_view__impl(self, *args, **kwargs)



    def _build_company_curriculum_view(self, parent: ttk.Frame, company_id: int) -> None:
        CompanyCurriculumTab(
            parent=parent,
            company_id=company_id,
            theme=self.theme,
            motion_button_factory=self._motion_button,
        ).build()


    def _build_company_groups_view(self, *args, **kwargs):
        return _build_company_groups_view__impl(self, *args, **kwargs)


    def _build_company_rooms_view(self, *args, **kwargs):
        return _build_company_rooms_view__impl(self, *args, **kwargs)


    def _build_company_settings_view(self, *args, **kwargs):
        return _build_company_settings_view__impl(self, *args, **kwargs)


    def _build_company_settings_profile_tab(self, *args, **kwargs):
        return _build_company_settings_profile_tab__impl(self, *args, **kwargs)


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

    def _show_personal_dashboard(self, *args, **kwargs):
        return _show_personal_dashboard__impl(self, *args, **kwargs)


