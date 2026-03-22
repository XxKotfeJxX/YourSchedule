from __future__ import annotations

from pathlib import Path


_METHOD_PARTS: dict[str, list[str]] = {
    "open_edit_dialog__impl": [
        "open_edit_dialog__impl_parts/part_01.pyfrag",
        "open_edit_dialog__impl_parts/part_02.pyfrag",
    ],
}


def ensure_week_template_workflow_method_impls(namespace: dict[str, object]) -> None:
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
