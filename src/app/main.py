from __future__ import annotations

import argparse

from app.config.database import init_db


def main() -> None:
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
