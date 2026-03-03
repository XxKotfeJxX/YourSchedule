from __future__ import annotations

import argparse
import io
import os
import sys

from app.config.database import init_db


def _configure_console_utf8() -> None:
    """Best-effort UTF-8 console setup (especially for Windows)."""
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)
            kernel32.SetConsoleCP(65001)
        except Exception:
            pass

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
            continue
        except Exception:
            pass
        try:
            buffer = stream.buffer
        except Exception:
            continue
        setattr(
            sys,
            stream_name,
            io.TextIOWrapper(
                buffer,
                encoding="utf-8",
                errors="replace",
                line_buffering=True,
            ),
        )


def main() -> None:
    _configure_console_utf8()

    parser = argparse.ArgumentParser(description="Запуск застосунку розкладу")
    parser.add_argument(
        "--init-only",
        action="store_true",
        help="Initialize database schema and exit.",
    )
    parser.add_argument(
        "--reset-schema",
        action="store_true",
        help="Drop all tables and recreate schema.",
    )
    args = parser.parse_args()

    init_db(reset_schema=args.reset_schema)
    print("Схему бази даних ініціалізовано.")

    if args.init_only:
        return

    try:
        import tkinter as tk
    except Exception as exc:
        print(
            "Не вдалося запустити Tkinter-інтерфейс. "
            "Якщо запускаєш у Docker/headless режимі, використай: python -m app.main --init-only"
        )
        raise SystemExit(1) from exc

    try:
        from app.ui import ScheduleMainWindow

        window = ScheduleMainWindow()
        window.run()
    except tk.TclError as exc:
        print(
            "Не вдалося запустити Tkinter-інтерфейс. "
            "Якщо запускаєш у Docker/headless режимі, використай: python -m app.main --init-only"
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
