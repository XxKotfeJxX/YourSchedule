# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _on_plan_select__impl(self) -> None:
    plan_id = self._selected_listbox_id(self.plan_listbox, self._plan_ids)
    self._selected_plan_id = plan_id
    self._selected_component_id = None
    self._selected_assignment_id = None
    if plan_id is None:
        self._load_components(None)
        return
    with session_scope() as session:
        plan = CurriculumController(session=session).get_plan(plan_id)
    if plan is None:
        self._load_components(None)
        return

    self.plan_name_var.set(plan.name)
    self.plan_semester_var.set("" if plan.semester is None else str(plan.semester))
    self.plan_specialty_var.set(self._format_optional_ref(plan.specialty_id, "specialty"))
    self.plan_course_var.set(self._format_optional_ref(plan.course_id, "course"))
    self.plan_stream_var.set(
        "" if plan.stream_id is None else f"{plan.stream_id} | {self._stream_name_by_id.get(plan.stream_id, f'Потік #{plan.stream_id}')}"
    )
    self._load_components(plan_id)
