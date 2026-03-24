# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _load_assignments__impl(self, component_id: int | None) -> None:
    if self.assignment_tree is None:
        return
    self._assignment_ids_by_iid.clear()
    for iid in self.assignment_tree.get_children():
        self.assignment_tree.delete(iid)
    self._selected_assignment_id = None
    if component_id is None:
        return
    with session_scope() as session:
        assignments = CurriculumController(session=session).list_assignments(component_id=component_id)
    for item in assignments:
        iid = self.assignment_tree.insert(
            "",
            tk.END,
            values=(
                item.id,
                self._teacher_name_by_id.get(item.teacher_resource_id, f"Викладач #{item.teacher_resource_id}"),
                self._target_display(item.target_type, item.stream_id, item.target_resource_id),
                item.sessions_total,
                item.max_per_week,
                item.requirement_id or "",
            ),
        )
        self._assignment_ids_by_iid[iid] = item.id
