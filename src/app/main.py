from __future__ import annotations

import argparse
import tkinter as tk

from app.config.database import init_db
from app.ui import ScheduleMainWindow


def main() -> None:
    parser = argparse.ArgumentParser(description="Academic Schedule Generator")
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
    print("Database schema initialized.")

    if args.init_only:
        return

    try:
        window = ScheduleMainWindow()
        window.run()
    except tk.TclError as exc:
        print(
            "Unable to start Tkinter UI. "
            "If you run in Docker/headless mode use: python -m app.main --init-only"
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
