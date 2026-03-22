from __future__ import annotations

from pathlib import Path


_METHOD_PARTS: dict[str, list[str]] = {
    "_build_blackout_reservations__impl": [
        "_build_blackout_reservations__impl.py",
    ],
    "_build_day_order_bounds__impl": [
        "_build_day_order_bounds__impl.py",
    ],
    "_build_existing_session_counts__impl": [
        "_build_existing_session_counts__impl.py",
    ],
    "_build_requirement_block_reservations__impl": [
        "_build_requirement_block_reservations__impl.py",
    ],
    "_build_resource_day_states__impl": [
        "_build_resource_day_states__impl.py",
    ],
    "_build_resource_reservations__impl": [
        "_build_resource_reservations__impl.py",
    ],
    "_build_room_default_resource_map__impl": [
        "_build_room_default_resource_map__impl.py",
    ],
    "_build_room_options_by_requirement__impl": [
        "_build_room_options_by_requirement__impl.py",
    ],
    "_build_weekly_usage__impl": [
        "_build_weekly_usage__impl.py",
    ],
    "_collect_blackout_resource_ids__impl": [
        "_collect_blackout_resource_ids__impl.py",
    ],
    "_diagnose_hard_constraint_violation__impl": [
        "_diagnose_hard_constraint_violation__impl.py",
    ],
    "_diagnose_requirement_failures__impl": [
        "_diagnose_requirement_failures__impl.py",
    ],
    "_ensure_entry_in_period__impl": [
        "_ensure_entry_in_period__impl.py",
    ],
    "_first_conflicting_resource__impl": [
        "_first_conflicting_resource__impl.py",
    ],
    "_gap_count__impl": [
        "_gap_count__impl.py",
    ],
    "_generate_candidates__impl": [
        "_generate_candidates__impl.py",
    ],
    "_has_resource_conflict__impl": [
        "_has_resource_conflict__impl.py",
    ],
    "_load_blackouts__impl": [
        "_load_blackouts__impl.py",
    ],
    "_load_requirements__impl": [
        "_load_requirements__impl.py",
    ],
    "_load_teaching_blocks__impl": [
        "_load_teaching_blocks__impl.py",
    ],
    "_longest_streak__impl": [
        "_longest_streak__impl.py",
    ],
    "_pick_available_room__impl": [
        "_pick_available_room__impl.py",
    ],
    "_prepare_manual_slot__impl": [
        "_prepare_manual_slot__impl.py",
    ],
    "_reserve_candidate_day_state__impl": [
        "_reserve_candidate_day_state__impl.py",
    ],
    "_resolve_block_ids__impl": [
        "_resolve_block_ids__impl.py",
    ],
    "_resolve_policy__impl": [
        "_resolve_policy__impl.py",
    ],
    "_room_matches_requirement__impl": [
        "_room_matches_requirement__impl.py",
    ],
    "_score_candidate__impl": [
        "_score_candidate__impl.py",
    ],
    "_sort_requirements_by_difficulty__impl": [
        "_sort_requirements_by_difficulty__impl.py",
    ],
    "_validate_scenario_context__impl": [
        "_validate_scenario_context__impl.py",
    ],
    "_violates_hard_constraints__impl": [
        "_violates_hard_constraints__impl.py",
    ],
    "_week_key__impl": [
        "_week_key__impl.py",
    ],
    "analyze_feasibility__impl": [
        "analyze_feasibility__impl.py",
    ],
    "build_coverage_dashboard__impl": [
        "build_coverage_dashboard__impl.py",
    ],
    "build_schedule__impl": [
        "build_schedule__impl.py",
    ],
    "create_manual_entry__impl": [
        "create_manual_entry__impl.py",
    ],
    "delete_schedule_entry__impl": [
        "delete_schedule_entry__impl.py",
    ],
    "get_policy__impl": [
        "get_policy__impl.py",
    ],
    "list_schedule_entries__impl": [
        "list_schedule_entries__impl.py",
    ],
    "set_schedule_entry_lock__impl": [
        "set_schedule_entry_lock__impl.py",
    ],
    "update_manual_entry__impl": [
        "update_manual_entry__impl.py",
    ],
    "update_policy__impl": [
        "update_policy__impl.py",
    ],
}


def ensure_greedy_scheduler_method_impls(namespace: dict[str, object]) -> None:
    if all(name in namespace for name in _METHOD_PARTS):
        return
    base_dir = Path(__file__).resolve().parent
    for impl_name, relative_paths in _METHOD_PARTS.items():
        source = ""
        for relative_path in relative_paths:
            source += (base_dir / relative_path).read_text(encoding="utf-8")
        if source and not source.endswith("\n"):
            source += "\n"
        origin = str(base_dir / relative_paths[0]) if relative_paths else str(base_dir)
        exec(compile(source, origin, "exec"), namespace, namespace)
        if impl_name not in namespace:
            raise RuntimeError(f"Failed to load method implementation: {impl_name}")
