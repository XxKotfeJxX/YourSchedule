# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _update_assignment__impl(self) -> None:
    if self._selected_assignment_id is None:
        messagebox.showerror("Помилка валідації", "Спочатку вибери призначення.")
        return
    teacher_id = self._parse_prefixed_id(self.assignment_teacher_var.get())
    if teacher_id is None:
        messagebox.showerror("Помилка валідації", "Вибери викладача.")
        return
    try:
        target_type = PlanTargetType(self.assignment_target_type_var.get().strip().upper())
        stream_id, target_resource_id = self._resolve_target_ids(target_type)
        with session_scope() as session:
            controller = CurriculumController(session=session)
            controller.update_assignment(
                self._selected_assignment_id,
                teacher_resource_id=teacher_id,
                target_type=target_type,
                target_resource_id=target_resource_id,
                stream_id=stream_id,
                sessions_total=self._parse_optional_positive_int(self.assignment_sessions_var.get()),
                max_per_week=self._parse_optional_positive_int(self.assignment_max_per_week_var.get()),
            )
            controller.sync_assignment_requirement(self._selected_assignment_id)
    except Exception as exc:
        messagebox.showerror("Помилка", str(exc))
        return
    if self._selected_component_id is not None:
        self._load_assignments(self._selected_component_id)
    self._set_status("Призначення оновлено і синхронізовано.")
