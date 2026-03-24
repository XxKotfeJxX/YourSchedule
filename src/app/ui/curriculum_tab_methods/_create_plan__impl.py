# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _create_plan__impl(self) -> None:
    name = self.plan_name_var.get().strip()
    if not name:
        messagebox.showerror("Помилка валідації", "Назва плану обов'язкова.")
        return
    try:
        semester = self._parse_optional_positive_int(self.plan_semester_var.get())
        with session_scope() as session:
            CurriculumController(session=session).create_plan(
                name=name,
                company_id=self.company_id,
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
    self._set_status(f"План '{name}' створено.")
