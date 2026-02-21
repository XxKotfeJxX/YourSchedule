from __future__ import annotations

import tkinter as tk


def _rounded_rect_points(x1: int, y1: int, x2: int, y2: int, radius: int) -> list[int]:
    radius = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    return [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]


class RoundedMotionCard(tk.Frame):
    def __init__(
        self,
        master,
        *,
        bg_color: str,
        card_color: str,
        shadow_color: str = "#d6dee8",
        radius: int = 18,
        padding: int = 16,
        shadow_offset: int = 5,
        motion_enabled: bool = True,
        width: int | None = None,
        height: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            width=width or 0,
            height=height or 0,
            **kwargs,
        )
        self.bg_color = bg_color
        self.card_color = card_color
        self.shadow_color = shadow_color
        self.radius = radius
        self.padding = padding
        self.base_shadow_offset = shadow_offset
        self.motion_enabled = motion_enabled
        self.current_lift = 0
        self.target_lift = 0
        self._animating = False

        if width is not None or height is not None:
            # Respect explicit widget size for shells (e.g., auth card), do not shrink to children.
            self.pack_propagate(False)
            self.grid_propagate(False)

        self.canvas = tk.Canvas(
            self,
            bg=bg_color,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            width=width or 0,
            height=height or 0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.content = tk.Frame(self.canvas, bg=card_color, bd=0, highlightthickness=0)
        self._content_window = self.canvas.create_window(0, 0, anchor="nw", window=self.content)

        self.canvas.bind("<Configure>", self._on_configure)
        if self.motion_enabled:
            for widget in (self, self.canvas, self.content):
                widget.bind("<Enter>", self._on_enter, add="+")
                widget.bind("<Leave>", self._on_leave, add="+")

        self._draw()

    def _on_configure(self, _event=None) -> None:
        self._draw()

    def _on_enter(self, _event=None) -> None:
        self.target_lift = -2
        self._animate()

    def _on_leave(self, _event=None) -> None:
        self.target_lift = 0
        self._animate()

    def _animate(self) -> None:
        if self._animating:
            return
        self._animating = True
        self.after(0, self._animate_step)

    def _animate_step(self) -> None:
        diff = self.target_lift - self.current_lift
        if abs(diff) < 0.2:
            self.current_lift = self.target_lift
            self._draw()
            self._animating = False
            return
        self.current_lift += diff * 0.35
        self._draw()
        self.after(16, self._animate_step)

    def _draw(self) -> None:
        width = max(2, self.canvas.winfo_width())
        height = max(2, self.canvas.winfo_height())
        pad = self.padding
        lift = int(round(self.current_lift))
        shadow_offset = self.base_shadow_offset + max(0, -lift)

        self.canvas.delete("shape")
        if width <= pad * 2 or height <= pad * 2:
            return

        x1, y1 = pad, pad + lift
        x2, y2 = width - pad, height - pad + lift
        sx1, sy1 = x1, y1 + shadow_offset
        sx2, sy2 = x2, y2 + shadow_offset

        self.canvas.create_polygon(
            _rounded_rect_points(sx1, sy1, sx2, sy2, self.radius),
            smooth=True,
            splinesteps=20,
            fill=self.shadow_color,
            outline="",
            tags="shape",
        )
        self.canvas.create_polygon(
            _rounded_rect_points(x1, y1, x2, y2, self.radius),
            smooth=True,
            splinesteps=20,
            fill=self.card_color,
            outline="",
            tags="shape",
        )
        inner_pad = 14
        self.canvas.coords(self._content_window, x1 + inner_pad, y1 + inner_pad)
        self.canvas.itemconfigure(
            self._content_window,
            width=max(1, (x2 - x1) - inner_pad * 2),
            height=max(1, (y2 - y1) - inner_pad * 2),
        )


class RoundedMotionButton(tk.Canvas):
    def __init__(
        self,
        master,
        *,
        text: str,
        command,
        width: int = 170,
        height: int = 42,
        radius: int = 12,
        fill: str = "#0f766e",
        hover_fill: str = "#115e59",
        pressed_fill: str = "#0e5b56",
        text_color: str = "#f8fbff",
        shadow_color: str = "#cfd8e3",
        canvas_bg: str = "#ffffff",
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            bg=canvas_bg,
            cursor="hand2",
        )
        self.command = command
        self.radius = radius
        self.fill = fill
        self.hover_fill = hover_fill
        self.pressed_fill = pressed_fill
        self.text_color = text_color
        self.shadow_color = shadow_color
        self._state = "normal"
        self._lift = 0

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", self._on_resize)

        self._text = text
        self._draw()

    def set_text(self, text: str) -> None:
        self._text = text
        self._draw()

    def _on_resize(self, _event=None) -> None:
        self._draw()

    def _on_enter(self, _event=None) -> None:
        self._state = "hover"
        self._lift = -1
        self._draw()

    def _on_leave(self, _event=None) -> None:
        self._state = "normal"
        self._lift = 0
        self._draw()

    def _on_press(self, _event=None) -> None:
        self._state = "pressed"
        self._lift = 0
        self._draw()

    def _on_release(self, event=None) -> None:
        if event is None:
            return
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        self._state = "hover" if inside else "normal"
        self._lift = -1 if inside else 0
        self._draw()
        if inside and self.command is not None:
            self.command()

    def _draw(self) -> None:
        width = max(2, self.winfo_width())
        height = max(2, self.winfo_height())
        pad = 3
        lift = self._lift
        shadow_offset = 3 + max(0, -lift)
        x1, y1 = pad, pad + lift
        x2, y2 = width - pad, height - pad + lift

        if self._state == "pressed":
            color = self.pressed_fill
        elif self._state == "hover":
            color = self.hover_fill
        else:
            color = self.fill

        self.delete("all")
        self.create_polygon(
            _rounded_rect_points(x1, y1 + shadow_offset, x2, y2 + shadow_offset, self.radius),
            smooth=True,
            splinesteps=20,
            fill=self.shadow_color,
            outline="",
        )
        self.create_polygon(
            _rounded_rect_points(x1, y1, x2, y2, self.radius),
            smooth=True,
            splinesteps=20,
            fill=color,
            outline="",
        )
        self.create_text(
            width // 2,
            height // 2 + lift,
            text=self._text,
            fill=self.text_color,
            font=("Segoe UI", 10, "bold"),
        )
