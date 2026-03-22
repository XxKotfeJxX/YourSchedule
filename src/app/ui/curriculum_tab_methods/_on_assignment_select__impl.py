def _on_assignment_select__impl(self) -> None:
    if self.assignment_tree is None:
        return
    selected = self.assignment_tree.selection()
    if not selected:
        self._selected_assignment_id = None
        return
    assignment_id = self._assignment_ids_by_iid.get(selected[0])
    self._selected_assignment_id = assignment_id
    if assignment_id is None:
        return
    with session_scope() as session:
        assignment = CurriculumController(session=session).get_assignment(assignment_id)
    if assignment is None:
        return
    self.assignment_teacher_var.set(
        f"{assignment.teacher_resource_id} | {self._teacher_name_by_id.get(assignment.teacher_resource_id, f'Викладач #{assignment.teacher_resource_id}')}"
    )
    self.assignment_target_type_var.set(assignment.target_type.value)
    self.assignment_stream_var.set("")
    self.assignment_group_var.set("")
    self.assignment_subgroup_var.set("")
    if assignment.stream_id is not None:
        self.assignment_stream_var.set(
            f"{assignment.stream_id} | {self._stream_name_by_id.get(assignment.stream_id, f'Потік #{assignment.stream_id}')}"
        )
    if assignment.target_type == PlanTargetType.GROUP and assignment.target_resource_id is not None:
        self.assignment_group_var.set(
            f"{assignment.target_resource_id} | {self._group_name_by_id.get(assignment.target_resource_id, f'Група #{assignment.target_resource_id}')}"
        )
    if assignment.target_type == PlanTargetType.SUBGROUP and assignment.target_resource_id is not None:
        self.assignment_subgroup_var.set(
            f"{assignment.target_resource_id} | {self._subgroup_name_by_id.get(assignment.target_resource_id, f'Підгрупа #{assignment.target_resource_id}')}"
        )
    self.assignment_sessions_var.set(str(assignment.sessions_total))
    self.assignment_max_per_week_var.set(str(assignment.max_per_week))
    self._refresh_assignment_target_controls()
