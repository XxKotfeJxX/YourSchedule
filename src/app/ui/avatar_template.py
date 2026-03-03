from __future__ import annotations

import tkinter as tk


def draw_default_company_avatar(
    canvas: tk.Canvas,
    *,
    x: int,
    y: int,
    size: int,
    circle_fill: str,
    building_fill: str,
    window_fill: str,
    outline: str,
) -> None:
    radius = size // 2
    canvas.create_oval(
        x - radius,
        y - radius,
        x + radius,
        y + radius,
        fill=circle_fill,
        outline=outline,
        width=2,
    )

    # Building base.
    body_w = int(size * 0.48)
    body_h = int(size * 0.42)
    body_x1 = x - body_w // 2
    body_y1 = y - body_h // 2 + int(size * 0.12)
    body_x2 = body_x1 + body_w
    body_y2 = body_y1 + body_h
    canvas.create_rectangle(
        body_x1,
        body_y1,
        body_x2,
        body_y2,
        fill=building_fill,
        outline="",
    )

    # Roof.
    roof_h = int(size * 0.2)
    canvas.create_polygon(
        body_x1 - int(size * 0.04),
        body_y1,
        x,
        body_y1 - roof_h,
        body_x2 + int(size * 0.04),
        body_y1,
        fill=building_fill,
        outline="",
    )

    # Door.
    door_w = int(size * 0.1)
    door_h = int(size * 0.16)
    canvas.create_rectangle(
        x - door_w // 2,
        body_y2 - door_h,
        x + door_w // 2,
        body_y2,
        fill=window_fill,
        outline="",
    )

    # Windows.
    window_w = int(size * 0.08)
    window_h = int(size * 0.07)
    spacing_x = int(size * 0.11)
    for row in range(2):
        for col in (-1, 1):
            cx = x + col * spacing_x
            cy = body_y1 + int(size * 0.1) + row * int(size * 0.11)
            canvas.create_rectangle(
                cx - window_w // 2,
                cy - window_h // 2,
                cx + window_w // 2,
                cy + window_h // 2,
                fill=window_fill,
                outline="",
            )

