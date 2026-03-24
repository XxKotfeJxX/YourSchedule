# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _load_components__impl(self, plan_id: int | None) -> None:
    if self.component_tree is None:
        return
    self._component_ids_by_iid.clear()
    for iid in self.component_tree.get_children():
        self.component_tree.delete(iid)
    self._selected_component_id = None
    self._selected_assignment_id = None
    if plan_id is None:
        self._load_assignments(None)
        return
    with session_scope() as session:
        components = CurriculumController(session=session).list_components(plan_id=plan_id)
    for item in components:
        iid = self.component_tree.insert(
            "",
            tk.END,
            values=(
                item.id,
                self._subject_name_by_id.get(item.subject_id, f"Предмет #{item.subject_id}"),
                item.component_type.value,
                item.duration_blocks,
                item.sessions_total,
                item.max_per_week,
            ),
        )
        self._component_ids_by_iid[iid] = item.id
    self._load_assignments(None)
