def _load_plan_reference_data__impl(self) -> None:
    with session_scope() as session:
        academic = AcademicController(session=session)
        resources = ResourceController(session=session)
        curriculum = CurriculumController(session=session)

        specialties = academic.list_specialties(company_id=self.company_id, include_archived=False)
        courses = academic.list_courses(company_id=self.company_id, include_archived=False)
        streams = academic.list_streams(company_id=self.company_id, include_archived=False)
        teachers = resources.list_resources(resource_type=ResourceType.TEACHER, company_id=self.company_id)
        groups = resources.list_resources(resource_type=ResourceType.GROUP, company_id=self.company_id)
        subgroups = resources.list_resources(resource_type=ResourceType.SUBGROUP, company_id=self.company_id)
        subjects = curriculum.list_subjects(company_id=self.company_id, include_archived=False)

    self._subject_name_by_id = {item.id: item.name for item in subjects}
    self._teacher_name_by_id = {item.id: item.name for item in teachers}
    self._stream_name_by_id = {item.id: item.name for item in streams}
    self._group_name_by_id = {item.id: item.name for item in groups}
    self._subgroup_name_by_id = {item.id: item.name for item in subgroups}

    specialty_values = [""] + [f"{item.id} | {item.name}" for item in specialties]
    course_values = [""] + [f"{item.id} | {item.name}" for item in courses]
    stream_values = [""] + [f"{item.id} | {item.name}" for item in streams]
    teacher_values = [f"{item.id} | {item.name}" for item in teachers]
    subject_values = [f"{item.id} | {item.name}" for item in subjects]
    group_values = [""] + [f"{item.id} | {item.name}" for item in groups]
    subgroup_values = [""] + [f"{item.id} | {item.name}" for item in subgroups]

    self._set_combobox_values(self.plan_specialty_box, self.plan_specialty_var, specialty_values)
    self._set_combobox_values(self.plan_course_box, self.plan_course_var, course_values)
    self._set_combobox_values(self.plan_stream_box, self.plan_stream_var, stream_values)
    self._set_combobox_values(self.component_subject_box, self.component_subject_var, subject_values, allow_empty=False)
    self._set_combobox_values(self.assignment_teacher_box, self.assignment_teacher_var, teacher_values, allow_empty=False)
    self._set_combobox_values(self.assignment_stream_box, self.assignment_stream_var, stream_values)
    self._set_combobox_values(self.assignment_group_box, self.assignment_group_var, group_values)
    self._set_combobox_values(self.assignment_subgroup_box, self.assignment_subgroup_var, subgroup_values)
