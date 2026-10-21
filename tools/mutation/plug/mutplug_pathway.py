"""Scratch-only pytest plugin: applies one source mutation to engine/pathway.py in memory (MUT=<name>)."""

import os

import _mutcheck

from engine import pathway

M = {
    # --- validation ---
    "bool_budget_allowed": ("isinstance(value, bool) or ", ""),
    "budget_type_unchecked": ("not isinstance(value, (int, float)) or ", ""),
    "budget_nonfinite_allowed": (" or not math.isfinite(value)", ""),
    "negative_budget_allowed": (" or value < 0:", ":"),
    "hours_budget_unchecked": ('    _check_budget(hours_budget, "hours_budget")\n', "    pass\n"),
    "rm_budget_unchecked": ('    _check_budget(budget_rm, "budget_rm", allow_none=True)\n', "    pass\n"),
    "none_rm_rejected": ("    if value is None and allow_none:\n        return None\n", ""),
    "risk_unchecked": ("    if risk_tolerance not in config.RISK_AVERSION:\n", "    if False:\n"),
    "zero_levels_kept": ("if level != 0}", "if True}"),
    "snapshot_membership_unchecked": ('    if missing:\n        raise ValueError(f"skills without a series', '    if False:\n        raise ValueError(f"skills without a series'),
    "course_checks_skipped": ("    _check_courses(courses)\n", "    pass\n"),
    "duplicate_courses_allowed": ("        if cid in seen:\n", "        if False:\n"),
    "min_hours_is_just_positive": (">= config.MIN_COURSE_HOURS)", "> 0)"),
    "min_hours_boundary_exclusive": (">= config.MIN_COURSE_HOURS)", "> config.MIN_COURSE_HOURS)"),
    "course_hours_unchecked": ("        if not (_is_number(course[\"hours\"]) and course[\"hours\"] >= config.MIN_COURSE_HOURS):\n", "        if False:\n"),
    "level_out_4_allowed": ("level_out not in (1, 2, 3):", "level_out not in (1, 2, 3, 4):"),
    "level_out_unchecked": ("        if isinstance(level_out, bool) or not isinstance(level_out, int) or level_out not in (1, 2, 3):\n", "        if False:\n"),
    "level_out_bool_allowed": ("isinstance(level_out, bool) or ", ""),
    "level_out_float_allowed": ("not isinstance(level_out, int) or ", ""),
    "number_bool_allowed": (" and not isinstance(value, bool) and", " and"),
    "number_nonfinite_allowed": (" and math.isfinite(value)\n", "\n"),
    "cost_rm_unchecked": ("        if not _is_number(course[\"cost_rm\"]) or course[\"cost_rm\"] < 0:\n", "        if False:\n"),
    "cost_rm_negative_allowed": (" or course[\"cost_rm\"] < 0:", ":"),
    "cost_rm_key_not_required": ('"hours", "level_out", "cost_rm", "title"', '"hours", "level_out", "title"'),
    "course_keys_unchecked": ("        if missing:\n            raise ValueError(f\"course", "        if False:\n            raise ValueError(f\"course"),
    "prereq_level_unchecked": (' or not _is_number(course["prereq_level"]) or not 1 <= course["prereq_level"] <= 3:', ":"),
    "prereq_range_unchecked": (' or not 1 <= course["prereq_level"] <= 3:', ":"),
    "prereq_range_4_allowed": ('course["prereq_level"] <= 3', 'course["prereq_level"] <= 4'),
    "prereq_range_0_allowed": ('1 <= course["prereq_level"]', '0 <= course["prereq_level"]'),
    "display_keys_not_required": ('"title", "provider", "url", "hrdc_claimable")', '"title")'),
    "prereq_level_key_not_required": ('"prereq_level" not in course or ', ""),
    "prereq_checked_without_prereq_skill": ('        if course.get("prereq_skill_id"):\n            if "prereq_level"', '        if True:\n            if "prereq_level"'),
    "mixed_course_id_types_allowed": ("for course in courses}) > 1:", "for course in courses}) > 9:"),
    "bool_user_levels_allowed": ("        if isinstance(level, bool):", "        if False:"),
    "no_forecast_unchecked": ("    if no_forecast:\n", "    if False:\n"),
    "course_skills_need_no_forecast": (" | {c[\"skill_id\"] for c in courses if c[\"skill_id\"] in snapshot[\"skills\"]}", ""),
    "unscoreable_course_skills_need_forecast": (' for c in courses if c["skill_id"] in snapshot["skills"]}', " for c in courses}"),
    "levels_not_int": ("levels = {s: int(lv) for s, lv in levels.items()}", "levels = dict(levels)"),
    # --- candidate filters ---
    "unscoreable_courses_allowed": ('skill not in snapshot["skills"] or ', ""),
    "non_gap_courses_allowed": (' or skill not in required', ""),
    "met_skills_still_trained": ("current >= required[skill]", "current > required[skill]"),
    "non_raising_courses_allowed": (' or course["level_out"] <= current', ""),
    "hours_budget_ignored": ('course["hours"] > hours_budget - hours_used + tol', "False"),
    "hours_not_cumulative": ('course["hours"] > hours_budget - hours_used + tol', 'course["hours"] > hours_budget + tol'),
    "hours_tolerance_removed": ('course["hours"] > hours_budget - hours_used + tol', 'course["hours"] > hours_budget - hours_used'),
    "hours_tolerance_subtracted": ('course["hours"] > hours_budget - hours_used + tol', 'course["hours"] > hours_budget - hours_used - tol'),
    "rm_not_cumulative": ('course["cost_rm"] > budget_rm - cost_used + tol', 'course["cost_rm"] > budget_rm + tol'),
    "rm_tolerance_removed": ('course["cost_rm"] > budget_rm - cost_used + tol', 'course["cost_rm"] > budget_rm - cost_used'),
    "hours_exclusive": ('course["hours"] > hours_budget - hours_used + tol', 'course["hours"] >= hours_budget - hours_used + tol'),
    "rm_exclusive": ('course["cost_rm"] > budget_rm - cost_used + tol', 'course["cost_rm"] >= budget_rm - cost_used + tol'),
    "tolerance_far_too_big": ("tol = config.BUDGET_TOLERANCE", "tol = 0.5"),
    "tolerance_too_small": ("tol = config.BUDGET_TOLERANCE", "tol = 1e-15"),
    "rm_ignored": ("            if budget_rm is not None and course[\"cost_rm\"] > budget_rm - cost_used + tol:\n                continue\n", ""),
    "prereq_ignored": ("            if course.get(\"prereq_skill_id\") and levels.get(course[\"prereq_skill_id\"], 0) < course[\"prereq_level\"]:\n                continue\n", ""),
    "prereq_exclusive": ('< course["prereq_level"]', '<= course["prereq_level"]'),
    "prereq_from_start_levels": ('levels.get(course["prereq_skill_id"], 0)', 'user_levels.get(course["prereq_skill_id"], 0)'),
    "prereq_on_the_courses_own_skill_only": ('levels.get(course["prereq_skill_id"], 0)', 'levels.get(course["skill_id"], 0)'),
    # --- scoring and choice ---
    "gain_sign_flipped": ('(new_metrics["readiness"] - now_metrics["readiness"])', '(now_metrics["readiness"] - new_metrics["readiness"])'),
    "match_gain_sign_flipped": ("beta * (new_match - now_match)", "beta * (now_match - new_match)"),
    "no_match_term": (' + beta * (new_match - now_match)) / course["hours"]', ") / course[\"hours\"]"),
    "no_readiness_term": ('((new_metrics["readiness"] - now_metrics["readiness"]) + beta * (new_match - now_match))', "(beta * (new_match - now_match))"),
    "beta_ignored": ("beta * (new_match - now_match)", "(new_match - now_match)"),
    "hc_beta": ("config.PATHWAY_MATCH_BETA", "1.0"),
    "gain_not_per_hour": (' / course["hours"]\n            rank', "\n            rank"),
    "gain_per_hour_squared": (' / course["hours"]\n            rank', ' / course["hours"] ** 2\n            rank'),
    "match_gain_from_start": ("new_match - now_match", "new_match - before_match"),
    "readiness_gain_from_start": ('new_metrics["readiness"] - now_metrics["readiness"]', 'new_metrics["readiness"] - before_metrics["readiness"]'),
    "lowest_gain_wins": ('rank = (-gain, course["cost_rm"]', 'rank = (gain, course["cost_rm"]'),
    "ties_prefer_dearer": ('rank = (-gain, course["cost_rm"], course["course_id"])', 'rank = (-gain, -course["cost_rm"], course["course_id"])'),
    "ties_ignore_cost": ('rank = (-gain, course["cost_rm"], course["course_id"])', 'rank = (-gain, course["course_id"])'),
    "ties_no_id": ('rank = (-gain, course["cost_rm"], course["course_id"])', 'rank = (-gain, course["cost_rm"])'),
    "ties_id_descending": ('rank = (-gain, course["cost_rm"], course["course_id"])', 'rank = (-gain, course["cost_rm"], [-ord(c) for c in course["course_id"]])'),
    "stops_only_below_zero": ("if best is None or best[2] <= 0:", "if best is None or best[2] < 0:"),
    "never_stops_on_losses": ("if best is None or best[2] <= 0:", "if best is None:"),
    "stops_below_threshold": ("if best is None or best[2] <= 0:", "if best is None or best[2] <= 0.001:"),
    # --- applying a step ---
    "level_rises_by_one": ('levels[course["skill_id"]] = course["level_out"]', 'levels[course["skill_id"]] = levels.get(course["skill_id"], 0) + 1'),
    "level_jumps_to_required": ('levels[course["skill_id"]] = course["level_out"]', 'levels[course["skill_id"]] = required[course["skill_id"]]'),
    "level_not_applied": ('        levels[course["skill_id"]] = course["level_out"]\n', ""),
    "hours_not_summed": ('        hours_used += course["hours"]\n', ""),
    "cost_not_summed": ('        cost_used += course["cost_rm"]\n', ""),
    "evaluation_ignores_new_levels": ("new_metrics, new_match = evaluate({**levels, skill: course[\"level_out\"]})", "new_metrics, new_match = evaluate({**levels})"),
    # --- evaluation ---
    "risk_fixed": ("portfolio.covariance(snapshot, list(weights)), risk_tolerance)", 'portfolio.covariance(snapshot, list(weights)), "medium")'),
    "covariance_in_wrong_order": ("portfolio.covariance(snapshot, list(weights))", "portfolio.covariance(snapshot, list(reversed(list(weights))))"),
    "cache_ignores_levels": ("        key = tuple(sorted(state.items()))", "        key = ()"),
    "weights_in_caller_order": ("for s, lv in key])", "for s, lv in state.items()])"),
    # --- output ---
    "key_steps": ('"steps": steps,', '"plan": steps,'),
    "before_is_after": ('"before": {**before_metrics, "match_pct": before_match},', '"before": {**after_metrics, "match_pct": after_match},'),
    "after_is_before": ('"after": {**after_metrics, "match_pct": after_match},', '"after": {**before_metrics, "match_pct": before_match},'),
    "match_key_renamed": ('"after": {**after_metrics, "match_pct": after_match},', '"after": {**after_metrics, "match": after_match},'),
    "hours_used_zero": ('"hours_used": hours_used,', '"hours_used": 0,'),
    "cost_used_zero": ('"cost_used": cost_used,', '"cost_used": 0,'),
    "step_order_zero_based": ('"order": len(steps) + 1,', '"order": len(steps),'),
    "step_level_before_wrong": ('"level_before": current,', '"level_before": 0,'),
    "step_level_out_wrong": ('"level_out": course["level_out"],', '"level_out": required[course["skill_id"]],'),
    "step_gain_wrong": ('"gain_per_hour": gain,', '"gain_per_hour": gain * course["hours"],'),
    "step_cumulative_hours_wrong": ('"cumulative_hours": hours_used,', '"cumulative_hours": course["hours"],'),
    "step_cumulative_cost_wrong": ('"cumulative_cost_rm": cost_used,', '"cumulative_cost_rm": course["cost_rm"],'),
    "step_url_missing": ('"url": course["url"],', '"url": "",'),
    "step_title_wrong": ('"title": course["title"],', '"title": course["course_id"],'),
    "step_provider_wrong": ('"provider": course["provider"],', '"provider": "",'),
    "step_hrdc_wrong": ('"hrdc_claimable": course["hrdc_claimable"],', '"hrdc_claimable": "unknown",'),
}

MUTANTS = dict(M)


TARGET = pathway


def _apply(name):
    _mutcheck.apply(TARGET, MUTANTS, name)


_name = os.environ.get("MUT")
if _name:
    _apply(_name)
