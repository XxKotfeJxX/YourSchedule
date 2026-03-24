# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _delete_component__impl(self) -> None:
    if self._selected_component_id is None:
        messagebox.showerror("Помилка валідації", "Спочатку вибери компонент.")
        return
    if not messagebox.askyesno("Видалення компонента", "Видалити вибраний компонент і всі призначення?"):
        return
    component_id = self._selected_component_id
    try:
        with session_scope() as session:
            CurriculumController(session=session).delete_component(component_id, delete_requirements=True)
    except Exception as exc:
        messagebox.showerror("Помилка", str(exc))
        return
    if self._selected_plan_id is not None:
        self._load_components(self._selected_plan_id)
    self._set_status(f"Компонент #{component_id} видалено.")
