# NOTE: This implementation module is executed via the parent module loader.
# Importing the parent symbols keeps static analyzers (Pylance/Pyright) in sync.
from app.ui.curriculum_tab import *  # noqa: F401,F403

def _build_plan_editor__impl(self, parent: ttk.Frame) -> None:
    plan_editor = ttk.Frame(parent, style="Card.TFrame")
    plan_editor.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    plan_editor.grid_columnconfigure(0, weight=1)
    plan_editor.grid_columnconfigure(1, weight=1)
    plan_editor.grid_columnconfigure(2, weight=1)

    ttk.Label(plan_editor, text="Параметри плану", style="Card.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

    ttk.Label(plan_editor, text="Назва").grid(row=1, column=0, sticky="w")
    ttk.Entry(plan_editor, textvariable=self.plan_name_var).grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
    ttk.Label(plan_editor, text="Семестр").grid(row=1, column=1, sticky="w")
    ttk.Entry(plan_editor, textvariable=self.plan_semester_var).grid(row=2, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))

    ttk.Label(plan_editor, text="Потік").grid(row=1, column=2, sticky="w")
    self.plan_stream_box = ttk.Combobox(plan_editor, textvariable=self.plan_stream_var, state="readonly")
    self.plan_stream_box.grid(row=2, column=2, sticky="ew", pady=(2, 4))

    ttk.Label(plan_editor, text="Спеціальність").grid(row=3, column=0, sticky="w")
    self.plan_specialty_box = ttk.Combobox(plan_editor, textvariable=self.plan_specialty_var, state="readonly")
    self.plan_specialty_box.grid(row=4, column=0, sticky="ew", padx=(0, 8), pady=(2, 4))
    ttk.Label(plan_editor, text="Курс").grid(row=3, column=1, sticky="w")
    self.plan_course_box = ttk.Combobox(plan_editor, textvariable=self.plan_course_var, state="readonly")
    self.plan_course_box.grid(row=4, column=1, sticky="ew", padx=(0, 8), pady=(2, 4))

    buttons = ttk.Frame(plan_editor, style="Card.TFrame")
    buttons.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(2, 0))
    self._grid_action_buttons(
        parent=buttons,
        items=[
            ("Створити", self._create_plan, True),
            ("Змінити", self._update_plan, False),
            ("Видалити", self._delete_plan, False),
            ("Синхр. план", self._sync_plan, False),
        ],
        columns=2,
        width=118,
        height=34,
    )
