# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _load_plans__impl(self) -> None:
    if self.plan_listbox is None:
        return
    selected_id = self._selected_listbox_id(self.plan_listbox, self._plan_ids)
    with session_scope() as session:
        plans = CurriculumController(session=session).list_plans(
            company_id=self.company_id,
            include_archived=False,
        )
    plans = sorted(plans, key=lambda item: item.name.casefold())

    self._plan_ids = [item.id for item in plans]
    self.plan_listbox.delete(0, tk.END)
    for item in plans:
        sem_suffix = f" (семестр {item.semester})" if item.semester is not None else ""
        self.plan_listbox.insert(tk.END, f"  {item.name}{sem_suffix}")

    if selected_id is not None and selected_id in self._plan_ids:
        idx = self._plan_ids.index(selected_id)
        self.plan_listbox.selection_set(idx)
        self.plan_listbox.see(idx)
        self._on_plan_select()
    else:
        self._selected_plan_id = None
        self._load_components(None)
