def _create_component__impl(self) -> None:
    if self._selected_plan_id is None:
        messagebox.showerror("Помилка валідації", "Спочатку вибери план.")
        return
    subject_id = self._parse_prefixed_id(self.component_subject_var.get())
    if subject_id is None:
        messagebox.showerror("Помилка валідації", "Вибери предмет.")
        return
    try:
        with session_scope() as session:
            CurriculumController(session=session).create_component(
                plan_id=self._selected_plan_id,
                subject_id=subject_id,
                component_type=PlanComponentType(self.component_type_var.get().strip().upper()),
                duration_blocks=int(self.component_duration_var.get().strip()),
                sessions_total=int(self.component_sessions_var.get().strip()),
                max_per_week=int(self.component_max_per_week_var.get().strip()),
                notes=self.component_notes_var.get().strip() or None,
            )
    except Exception as exc:
        messagebox.showerror("Помилка", str(exc))
        return
    self._load_components(self._selected_plan_id)
    self._set_status(f"Компонент додано до плану #{self._selected_plan_id}.")
