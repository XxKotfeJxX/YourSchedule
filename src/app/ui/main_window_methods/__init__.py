from __future__ import annotations

from pathlib import Path


_METHOD_PARTS: dict[str, list[str]] = {
    "_build_company_groups_view__impl": [
        "_build_company_groups_view__impl_parts/part_01.pyfrag",
        "_build_company_groups_view__impl_parts/part_02.pyfrag",
        "_build_company_groups_view__impl_parts/part_03.pyfrag",
    ],
    "_build_company_rooms_view__impl": [
        "_build_company_rooms_view__impl_parts/part_01.pyfrag",
        "_build_company_rooms_view__impl_parts/part_02.pyfrag",
    ],
    "_build_company_schedule_view__impl": [
        "_build_company_schedule_view__impl_parts/part_01.pyfrag",
        "_build_company_schedule_view__impl_parts/part_02.pyfrag",
        "_build_company_schedule_view__impl_parts/part_03.pyfrag",
        "_build_company_schedule_view__impl_parts/part_04.pyfrag",
        "_build_company_schedule_view__impl_parts/part_05.pyfrag",
        "_build_company_schedule_view__impl_parts/part_06.pyfrag",
    ],
    "_build_company_settings_profile_tab__impl": [
        "_build_company_settings_profile_tab__impl.py",
    ],
    "_build_company_settings_view__impl": [
        "_build_company_settings_view__impl.py",
    ],
    "_show_company_dashboard__impl": [
        "_show_company_dashboard__impl.py",
    ],
    "_show_personal_dashboard__impl": [
        "_show_personal_dashboard__impl.py",
    ],
}


def ensure_main_window_method_impls(namespace: dict[str, object]) -> None:
    if all(name in namespace for name in _METHOD_PARTS):
        return
    base_dir = Path(__file__).resolve().parent
    for impl_name, relative_paths in _METHOD_PARTS.items():
        source = ""
        for relative_path in relative_paths:
            source += (base_dir / relative_path).read_text(encoding="utf-8")
        if source and not source.endswith("\n"):
            source += "\n"
        origin = str(base_dir / relative_paths[0]) if relative_paths else str(base_dir)
        exec(compile(source, origin, "exec"), namespace, namespace)
        if impl_name not in namespace:
            raise RuntimeError(f"Failed to load method implementation: {impl_name}")
