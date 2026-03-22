from __future__ import annotations

from pathlib import Path


_METHOD_PARTS: dict[str, list[str]] = {
    "_build_blackout_reservations__impl": [
        "_build_blackout_reservations__impl.pyfrag",
    ],
    "_build_day_order_bounds__impl": [
        "_build_day_order_bounds__impl.pyfrag",
    ],
    "_build_existing_session_counts__impl": [
        "_build_existing_session_counts__impl.pyfrag",
    ],
    "_build_requirement_block_reservations__impl": [
        "_build_requirement_block_reservations__impl.pyfrag",
    ],
    "_build_resource_day_states__impl": [
        "_build_resource_day_states__impl.pyfrag",
    ],
    "_build_resource_reservations__impl": [
        "_build_resource_reservations__impl.pyfrag",
    ],
    "_build_room_default_resource_map__impl": [
        "_build_room_default_resource_map__impl.pyfrag",
    ],
    "_build_room_options_by_requirement__impl": [
        "_build_room_options_by_requirement__impl.pyfrag",
    ],
    "_build_weekly_usage__impl": [
        "_build_weekly_usage__impl.pyfrag",
    ],
    "_collect_blackout_resource_ids__impl": [
        "_collect_blackout_resource_ids__impl.pyfrag",
    ],
    "_diagnose_hard_constraint_violation__impl": [
        "_diagnose_hard_constraint_violation__impl.pyfrag",
    ],
    "_diagnose_requirement_failures__impl": [
        "_diagnose_requirement_failures__impl.pyfrag",
    ],
    "_ensure_entry_in_period__impl": [
        "_ensure_entry_in_period__impl.pyfrag",
    ],
    "_first_conflicting_resource__impl": [
        "_first_conflicting_resource__impl.pyfrag",
    ],
    "_gap_count__impl": [
        "_gap_count__impl.pyfrag",
    ],
    "_generate_candidates__impl": [
        "_generate_candidates__impl.pyfrag",
    ],
    "_has_resource_conflict__impl": [
        "_has_resource_conflict__impl.pyfrag",
    ],
    "_load_blackouts__impl": [
        "_load_blackouts__impl.pyfrag",
    ],
    "_load_requirements__impl": [
        "_load_requirements__impl.pyfrag",
    ],
    "_load_teaching_blocks__impl": [
        "_load_teaching_blocks__impl.pyfrag",
    ],
    "_longest_streak__impl": [
        "_longest_streak__impl.pyfrag",
    ],
    "_pick_available_room__impl": [
        "_pick_available_room__impl.pyfrag",
    ],
    "_prepare_manual_slot__impl": [
        "_prepare_manual_slot__impl.pyfrag",
    ],
    "_reserve_candidate_day_state__impl": [
        "_reserve_candidate_day_state__impl.pyfrag",
    ],
    "_resolve_block_ids__impl": [
        "_resolve_block_ids__impl.pyfrag",
    ],
    "_resolve_policy__impl": [
        "_resolve_policy__impl.pyfrag",
    ],
    "_room_matches_requirement__impl": [
        "_room_matches_requirement__impl.pyfrag",
    ],
    "_score_candidate__impl": [
        "_score_candidate__impl.pyfrag",
    ],
    "_sort_requirements_by_difficulty__impl": [
        "_sort_requirements_by_difficulty__impl.pyfrag",
    ],
    "_validate_scenario_context__impl": [
        "_validate_scenario_context__impl.pyfrag",
    ],
    "_violates_hard_constraints__impl": [
        "_violates_hard_constraints__impl.pyfrag",
    ],
    "_week_key__impl": [
        "_week_key__impl.pyfrag",
    ],
    "analyze_feasibility__impl": [
        "analyze_feasibility__impl.pyfrag",
    ],
    "build_coverage_dashboard__impl": [
        "build_coverage_dashboard__impl.pyfrag",
    ],
    "build_schedule__impl": [
        "build_schedule__impl.pyfrag",
    ],
    "create_manual_entry__impl": [
        "create_manual_entry__impl.pyfrag",
    ],
    "delete_schedule_entry__impl": [
        "delete_schedule_entry__impl.pyfrag",
    ],
    "get_policy__impl": [
        "get_policy__impl.pyfrag",
    ],
    "list_schedule_entries__impl": [
        "list_schedule_entries__impl.pyfrag",
    ],
    "set_schedule_entry_lock__impl": [
        "set_schedule_entry_lock__impl.pyfrag",
    ],
    "update_manual_entry__impl": [
        "update_manual_entry__impl.pyfrag",
    ],
    "update_policy__impl": [
        "update_policy__impl.pyfrag",
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
