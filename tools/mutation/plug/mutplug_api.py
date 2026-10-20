"""Scratch-only pytest plugin: applies one source mutation to engine/api.py in memory (MUT=<name>)."""

import os

from engine import api

M = {
    # --- profile handling ---
    "risk_required": ('profile.get("risk_tolerance", DEFAULT_RISK)', 'profile["risk_tolerance"]'),
    "default_risk_low": ('DEFAULT_RISK = "medium"', 'DEFAULT_RISK = "low"'),
    "default_risk_high": ('DEFAULT_RISK = "medium"', 'DEFAULT_RISK = "high"'),
    "risk_unchecked": ("if risk not in config.RISK_AVERSION:", "if False:"),
    "risk_ignored": ("portfolio.metrics(weights, forecasts, cov, risk)", 'portfolio.metrics(weights, forecasts, cov, "medium")'),
    "roles_arg_ignored": ("data.load_roles() if roles is None else roles", "data.load_roles()"),
    "role_skills_arg_ignored": ("data.load_role_skills() if role_skills is None else role_skills", "data.load_role_skills()"),
    "empty_role_skills_replaced_by_data": ("data.load_role_skills() if role_skills is None else role_skills", "data.load_role_skills() if not role_skills else role_skills"),
    "empty_roles_replaced_by_data": ("data.load_roles() if roles is None else roles", "data.load_roles() if not roles else roles"),
    # --- guardrail ---
    "nothing_is_known": ('known = set(snapshot["skills"])', "known = set()"),
    "everything_is_known": ('known = set(snapshot["skills"])', 'known = set(snapshot["skills"]) | {e["skill_id"] for e in profile["skills"]}'),
    "guardrail_skipped": ('kept = guardrails.keep_known(profile["skills"], "skill_id", known)', 'kept = profile["skills"]'),
    "dropped_lists_the_kept": ('if entry["skill_id"] not in known]', 'if entry["skill_id"] in known]'),
    "dropped_always_empty": ('if entry["skill_id"] not in known]', "if False]"),
    "level_not_int": ('int(entry["level"])', 'entry["level"]'),
    # --- engine calls ---
    "scenario_ignored": ("forecast.forecast_all(snapshot, scenario)", "forecast.forecast_all(snapshot)"),
    "covariance_wrong_order": ("portfolio.covariance(snapshot, list(weights))", "portfolio.covariance(snapshot, sorted(weights))"),
    "matches_use_weights_not_levels": ("matching.rank_roles(roles, role_skills, levels, forecasts,", "matching.rank_roles(roles, role_skills, weights, forecasts,"),
    "sdg_interests_ignored": ('profile.get("sdg_interests", [])', "[]"),
    "sdg_interests_required": ('profile.get("sdg_interests", [])', 'profile["sdg_interests"]'),
    "match_snapshot_date_blank": ('profile.get("sdg_interests", []), snapshot["snapshot_date"])', 'profile.get("sdg_interests", []), "")'),
    "top_n_hardcoded": ("matches[:config.TOP_N_ROLES]", "matches[:5]"),
    "top_n_off_by_one": ("matches[:config.TOP_N_ROLES]", "matches[:config.TOP_N_ROLES - 1]"),
    "top_n_missing": ("        matches = matches[:config.TOP_N_ROLES]\n", "        pass\n"),
    "no_warning_when_no_role_skills": ('        warnings.append("role_skills has no rows, so roles cannot be matched yet")\n', "        pass\n"),
    "always_warns": ("    if role_skills:\n", "    warnings.append('x')\n    if role_skills:\n"),
    "matches_when_no_role_skills_flipped": ("    if role_skills:\n", "    if not role_skills:\n"),
    "allocation_uses_levels": ("sdg.impact_allocation(weights, roles, role_skills)", "sdg.impact_allocation(levels, roles, role_skills)"),
    # --- output shape ---
    "key_profile_id": ('"profile_id": profile.get("profile_id"),', '"id": profile.get("profile_id"),'),
    "key_scenario": ('"scenario": scenario,', '"scenario": "moderate",'),
    "key_snapshot_date": ('"snapshot_date": snapshot["snapshot_date"],', '"snapshot_date": "",'),
    "key_portfolio": ('"portfolio": metrics,', '"metrics": metrics,'),
    "key_matches": ('"matches": matches,', '"roles": matches,'),
    "key_forecasts": ('"forecasts": forecasts,', '"forecasts": {},'),
    "key_warnings": ('"warnings": warnings,', '"warnings": [],'),
    "key_dropped": ('"dropped_skills": dropped,', '"dropped": dropped,'),
    "row_projected_is_momentum": ('"projected": forecasts[skill_id]["projected"],', '"projected": forecasts[skill_id]["momentum"],'),
    "row_thin_wrong": ('"thin_data": forecasts[skill_id]["thin_data"],', '"thin_data": False,'),
    "row_exposure_wrong": ('"exposure": forecasts[skill_id]["exposure"],', '"exposure": None,'),
    "row_weight_is_level": ('"weight": weight,', '"weight": levels[skill_id],'),
    "row_sdgs_baseline_only": ('"sdgs": sdg.skill_sdgs(skill_id, roles, role_skills),', '"sdgs": [config.BASELINE_SKILL_SDG],'),
    "allocation_rows_key_names": ('{"sdg": number, "share": share}', '{"sdg": number, "weight": share}'),
    "allocation_unordered": ("for number, share in allocation.items()]", "for number, share in sorted(allocation.items())]"),
    'skills_shape_unchecked': ('if not isinstance(skills, list) or any(not isinstance(e, dict) or "skill_id" not in e or "level" not in e for e in skills):', 'if False:'),
    'skills_entries_unchecked': (' or any(not isinstance(e, dict) or "skill_id" not in e or "level" not in e for e in skills)', ''),
    'risk_type_unchecked': ('not isinstance(risk, str) or risk not in config.RISK_AVERSION', 'risk not in config.RISK_AVERSION'),
    'interests_none_rejected': ('interests = [] if interests is None else interests', 'interests = interests'),
    'interests_unchecked': ('if not isinstance(interests, list) or any(', 'if False and any('),
    'interests_bool_allowed': ('isinstance(n, bool) or not isinstance(n, int)', 'not isinstance(n, int)'),
    'interests_range_16': ('n not in SDG_NUMBERS', 'n not in range(1, 17)'),
    'interests_range_zero_ok': ('n not in SDG_NUMBERS', 'n not in range(0, 18)'),
    'interests_range_18_ok': ('n not in SDG_NUMBERS', 'n not in range(1, 19)'),
    'interests_truncated': ('profile.get("sdg_interests")', 'profile.get("sdg_interests") and profile.get("sdg_interests")[:3]'),
    'snapshot_date_unchecked': ('if "snapshot_date" not in snapshot:', 'if False:'),
    'all_levels_unchecked': ('    portfolio.weights(profile["skills"])', '    pass'),
    'all_dropped_allowed': ('    if not kept:\n', '    if False:\n'),
    'all_dropped_message_generic': ('f"none of the profile\'s skills is in the snapshot (dropped: {dropped})"', '"a portfolio needs at least one skill"'),
    'no_future_roles_no_warning': ('    elif not matches:\n        warnings.append("no future role has skills listed in role_skills, so nothing can be matched")\n', '    elif False:\n        pass\n'),
    'top_n_default_frozen': ('top_n = config.TOP_N_ROLES if top_n is CONFIGURED else top_n', 'top_n = 5 if top_n is CONFIGURED else top_n'),
    'top_n_none_means_config': ('matches = matches if top_n is None else matches[:top_n]', 'matches = matches[:config.TOP_N_ROLES] if top_n is None else matches[:top_n]'),
    'top_n_zero_means_all': ('matches = matches if top_n is None else matches[:top_n]', 'matches = matches if not top_n else matches[:top_n]'),
    'snapshot_mutated': ('    known = set(snapshot["skills"])', '    snapshot.setdefault("_seen", True)\n    known = set(snapshot["skills"])'),
    'dropped_sorted': ('dropped = [entry["skill_id"] for entry in profile["skills"] if entry["skill_id"] not in known]', 'dropped = sorted(entry["skill_id"] for entry in profile["skills"] if entry["skill_id"] not in known)'),
    'levels_include_dropped': ('levels = {entry["skill_id"]: int(entry["level"]) for entry in kept}', 'levels = {entry["skill_id"]: int(entry["level"]) for entry in profile["skills"]}'),
    'profile_id_blank_default': ('profile.get("profile_id")', 'profile.get("profile_id", "")'),
}

MUTANTS = dict(M)


def _apply(name):
    old, new = MUTANTS[name]
    path = api.__file__
    src = open(path, encoding="utf-8").read()
    assert src.count(old) >= 1, f"mutation target not found for {name}"
    exec(compile(src.replace(old, new), path, "exec"), api.__dict__)


_name = os.environ.get("MUT")
if _name:
    _apply(_name)
