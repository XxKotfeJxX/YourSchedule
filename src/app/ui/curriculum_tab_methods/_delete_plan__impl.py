def _delete_plan__impl(self) -> None:
    if self._selected_plan_id is None:
        messagebox.showerror("Помилка валідації", "Спочатку вибери план.")
        return
    if not messagebox.askyesno("Видалення плану", "Видалити вибраний план разом з компонентами та призначеннями?"):
        return
    plan_id = self._selected_plan_id
    try:
        with session_scope() as session:
            CurriculumController(session=session).delete_plan(plan_id, delete_requirements=True)
    except Exception as exc:
        messagebox.showerror("Помилка", str(exc))
        return
    self._selected_plan_id = None
    self._selected_component_id = None
    self._selected_assignment_id = None
    self._load_plans()
    self._set_status(f"План #{plan_id} видалено.")
