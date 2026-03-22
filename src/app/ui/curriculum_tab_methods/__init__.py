from __future__ import annotations

from pathlib import Path


_METHOD_PARTS: dict[str, list[str]] = {
    "_build_assignments_editor__impl": [
        "_build_assignments_editor__impl.py",
    ],
    "_build_components_editor__impl": [
        "_build_components_editor__impl.py",
    ],
    "_build_plan_editor__impl": [
        "_build_plan_editor__impl.py",
    ],
    "_build_plans_tab__impl": [
        "_build_plans_tab__impl.py",
    ],
    "_create_assignment__impl": [
        "_create_assignment__impl.py",
    ],
    "_create_component__impl": [
        "_create_component__impl.py",
    ],
    "_create_plan__impl": [
        "_create_plan__impl.py",
    ],
    "_delete_assignment__impl": [
        "_delete_assignment__impl.py",
    ],
    "_delete_component__impl": [
        "_delete_component__impl.py",
    ],
    "_delete_plan__impl": [
        "_delete_plan__impl.py",
    ],
    "_format_optional_ref__impl": [
        "_format_optional_ref__impl.py",
    ],
    "_load_assignments__impl": [
        "_load_assignments__impl.py",
    ],
    "_load_components__impl": [
        "_load_components__impl.py",
    ],
    "_load_plan_reference_data__impl": [
        "_load_plan_reference_data__impl.py",
    ],
    "_load_plans__impl": [
        "_load_plans__impl.py",
    ],
    "_on_assignment_select__impl": [
        "_on_assignment_select__impl.py",
    ],
    "_on_component_select__impl": [
        "_on_component_select__impl.py",
    ],
    "_on_plan_select__impl": [
        "_on_plan_select__impl.py",
    ],
    "_refresh_assignment_target_controls__impl": [
        "_refresh_assignment_target_controls__impl.py",
    ],
    "_resolve_target_ids__impl": [
        "_resolve_target_ids__impl.py",
    ],
    "_sync_assignment__impl": [
        "_sync_assignment__impl.py",
    ],
    "_sync_plan__impl": [
        "_sync_plan__impl.py",
    ],
    "_target_display__impl": [
        "_target_display__impl.py",
    ],
    "_update_assignment__impl": [
        "_update_assignment__impl.py",
    ],
    "_update_component__impl": [
        "_update_component__impl.py",
    ],
    "_update_plan__impl": [
        "_update_plan__impl.py",
    ],
}


def ensure_curriculum_tab_method_impls(namespace: dict[str, object]) -> None:
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
