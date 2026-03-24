# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _refresh_assignment_target_controls__impl(self) -> None:
    raw = self.assignment_target_type_var.get().strip().upper()
    try:
        target_type = PlanTargetType(raw)
    except ValueError:
        target_type = PlanTargetType.STREAM
        self.assignment_target_type_var.set(target_type.value)
    if self.assignment_stream_box is not None:
        self.assignment_stream_box.configure(state="readonly" if target_type == PlanTargetType.STREAM else "disabled")
    if self.assignment_group_box is not None:
        self.assignment_group_box.configure(state="readonly" if target_type == PlanTargetType.GROUP else "disabled")
    if self.assignment_subgroup_box is not None:
        self.assignment_subgroup_box.configure(state="readonly" if target_type == PlanTargetType.SUBGROUP else "disabled")
