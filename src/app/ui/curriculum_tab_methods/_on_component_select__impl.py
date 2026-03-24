def _on_component_select__impl(self) -> None:
    if self.component_tree is None:
        return
    selected = self.component_tree.selection()
    if not selected:
        self._selected_component_id = None
        self._load_assignments(None)
        return
    component_id = self._component_ids_by_iid.get(selected[0])
    self._selected_component_id = component_id
    self._selected_assignment_id = None
    if component_id is None:
        self._load_assignments(None)
        return
    with session_scope() as session:
        component = CurriculumController(session=session).get_component(component_id)
    if component is None:
        self._load_assignments(None)
        return
    self.component_subject_var.set(
        f"{component.subject_id} | {self._subject_name_by_id.get(component.subject_id, f'Предмет #{component.subject_id}')}"
    )
    self.component_type_var.set(component.component_type.value)
    self.component_duration_var.set(str(component.duration_blocks))
    self.component_sessions_var.set(str(component.sessions_total))
    self.component_max_per_week_var.set(str(component.max_per_week))
    self.component_notes_var.set(component.notes or "")
    self._load_assignments(component_id)
