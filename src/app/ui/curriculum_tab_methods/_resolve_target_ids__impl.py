# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _resolve_target_ids__impl(self, target_type: PlanTargetType) -> tuple[int | None, int | None]:
    if target_type == PlanTargetType.STREAM:
        stream_id = self._parse_prefixed_id(self.assignment_stream_var.get())
        if stream_id is None:
            raise ValueError("Вибери потік для цілі.")
        return stream_id, None
    if target_type == PlanTargetType.GROUP:
        target_id = self._parse_prefixed_id(self.assignment_group_var.get())
        if target_id is None:
            raise ValueError("Вибери групу для цілі.")
        return None, target_id
    target_id = self._parse_prefixed_id(self.assignment_subgroup_var.get())
    if target_id is None:
        raise ValueError("Вибери підгрупу для цілі.")
    return None, target_id
