def _update_plan__impl(self) -> None:
    if self._selected_plan_id is None:
        messagebox.showerror("Помилка валідації", "Спочатку вибери план.")
        return
    name = self.plan_name_var.get().strip()
    if not name:
        messagebox.showerror("Помилка валідації", "Назва плану обов'язкова.")
        return
    try:
        semester = self._parse_optional_positive_int(self.plan_semester_var.get())
        with session_scope() as session:
            CurriculumController(session=session).update_plan(
                self._selected_plan_id,
                name=name,
                specialty_id=self._parse_prefixed_id(self.plan_specialty_var.get()),
                course_id=self._parse_prefixed_id(self.plan_course_var.get()),
                stream_id=self._parse_prefixed_id(self.plan_stream_var.get()),
                semester=semester,
            )
    except IntegrityError:
        messagebox.showerror("Конфлікт", "План з такою назвою вже існує.")
        return
    except Exception as exc:
        messagebox.showerror("Помилка", str(exc))
        return
    self._load_plans()
    self._set_status(f"План #{self._selected_plan_id} оновлено.")
