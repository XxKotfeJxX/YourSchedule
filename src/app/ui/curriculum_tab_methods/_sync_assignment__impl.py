# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _sync_assignment__impl(self) -> None:
    if self._selected_assignment_id is None:
        messagebox.showerror("Помилка валідації", "Спочатку вибери призначення.")
        return
    assignment_id = self._selected_assignment_id
    try:
        with session_scope() as session:
            CurriculumController(session=session).sync_assignment_requirement(assignment_id)
    except Exception as exc:
        messagebox.showerror("Помилка", str(exc))
        return
    if self._selected_component_id is not None:
        self._load_assignments(self._selected_component_id)
    self._set_status(f"Призначення #{assignment_id} синхронізовано.")
