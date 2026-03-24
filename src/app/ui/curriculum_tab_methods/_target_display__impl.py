# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _target_display__impl(self, target_type: PlanTargetType, stream_id: int | None, target_resource_id: int | None) -> str:
    if target_type == PlanTargetType.STREAM:
        return f"ПОТІК: {self._stream_name_by_id.get(stream_id or 0, f'#{stream_id}')}"
    if target_type == PlanTargetType.GROUP:
        return f"ГРУПА: {self._group_name_by_id.get(target_resource_id or 0, f'#{target_resource_id}')}"
    return f"ПІДГРУПА: {self._subgroup_name_by_id.get(target_resource_id or 0, f'#{target_resource_id}')}"
