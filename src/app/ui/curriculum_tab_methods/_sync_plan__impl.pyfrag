def _sync_plan__impl(self) -> None:
    if self._selected_plan_id is None:
        messagebox.showerror("Помилка валідації", "Спочатку вибери план.")
        return
    try:
        with session_scope() as session:
            synced = CurriculumController(session=session).sync_plan_requirements(self._selected_plan_id)
    except Exception as exc:
        messagebox.showerror("Помилка", str(exc))
        return
    self._load_assignments(self._selected_component_id)
    self._set_status(f"Синхронізовано {len(synced)} призначень для плану #{self._selected_plan_id}.")
