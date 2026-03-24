# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _format_optional_ref__impl(self, value: int | None, kind: str) -> str:
    if value is None:
        return ""
    with session_scope() as session:
        academic = AcademicController(session=session)
        if kind == "specialty":
            item = academic.get_specialty(value)
        elif kind == "course":
            item = academic.get_course(value)
        else:
            item = None
    label = item.name if item is not None else f"{kind.capitalize()} #{value}"
    return f"{value} | {label}"
