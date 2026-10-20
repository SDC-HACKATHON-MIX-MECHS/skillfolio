"""Scratch-only pytest plugin: applies one source mutation to engine/matching.py in memory (MUT=<name>)."""

import os

from engine import matching

M = {
    # --- validation ---
    "duplicate_rows_allowed": ('if row["skill_id"] in seen:', "if False:"),
    "weight_unchecked": ('row["weight"] not in (1, 2, 3) or ', ""),
    "weight_4_allowed": ('row["weight"] not in (1, 2, 3)', 'row["weight"] not in (1, 2, 3, 4)'),
    "weight_0_allowed": ('row["weight"] not in (1, 2, 3)', 'row["weight"] not in (0, 1, 2, 3)'),
    "required_level_unchecked": (' or row["required_level"] not in (1, 2, 3)', ""),
    "required_level_4_allowed": ('row["required_level"] not in (1, 2, 3)', 'row["required_level"] not in (1, 2, 3, 4)'),
    "validation_skipped": ("    _validate(rows, user_levels)\n", "    pass\n"),
    "user_level_4_allowed": ("level not in (0, 1, 2, 3)", "level not in (0, 1, 2, 3, 4)"),
    "user_level_0_rejected": ("level not in (0, 1, 2, 3)", "level not in (1, 2, 3)"),
    "user_level_negative_allowed": ("level not in (0, 1, 2, 3)", "level not in (-1, 0, 1, 2, 3)"),
    "user_level_bool_allowed": ("isinstance(level, bool) or ", ""),
    "empty_role_allowed": ("    if not rows:\n", "    if False:\n"),
    "other_roles_rows_used": ('if r["role_id"] == role["role_id"]]', "if True]"),
    # --- match ---
    "credit_uncapped": ('credit = min(level / row["required_level"], 1.0)', 'credit = level / row["required_level"]'),
    "credit_all_or_nothing": ('credit = min(level / row["required_level"], 1.0)', 'credit = 1.0 if level >= row["required_level"] else 0.0'),
    "credit_over_three": ('credit = min(level / row["required_level"], 1.0)', "credit = min(level / 3, 1.0)"),
    "match_unweighted": ('match += row["weight"] * credit / total_weight', "match += credit / len(rows)"),
    "total_weight_is_count": ("total_weight = sum(r[\"weight\"] for r in rows)", "total_weight = len(rows)"),
    "total_weight_is_max": ("total_weight = sum(r[\"weight\"] for r in rows)", "total_weight = max(r[\"weight\"] for r in rows)"),
    # --- role growth ---
    "growth_unweighted": ('growth += row["weight"] / total_weight * projected', "growth += projected / len(rows)"),
    "growth_not_normalised": ('growth += row["weight"] / total_weight * projected', 'growth += row["weight"] * projected'),
    "growth_uses_momentum": ('projected = forecast["projected"]', 'projected = forecast["momentum"]'),
    "missing_forecast_is_an_error": ("forecast = forecasts.get(row[\"skill_id\"])", "forecast = forecasts[row[\"skill_id\"]]"),
    "thin_not_capped": ('if forecast.get("thin_data", False):', "if False:"),
    "solid_also_capped": ('if forecast.get("thin_data", False):', "if True:"),
    "thin_flag_required": ('forecast.get("thin_data", False)', 'forecast["thin_data"]'),
    "thin_flag_defaults_to_thin": ('forecast.get("thin_data", False)', 'forecast.get("thin_data", True)'),
    "cap_upper_only": ("projected = max(-cap, min(cap, projected))", "projected = min(cap, projected)"),
    "cap_lower_only": ("projected = max(-cap, min(cap, projected))", "projected = max(-cap, projected)"),
    "thin_zeroed": ("projected = max(-cap, min(cap, projected))", "projected = 0.0"),
    "hc_cap": ("config.THIN_GROWTH_CAP", "0.05"),
    # --- contributions and gaps ---
    "contribution_when_credit_ge_0": ("if credit > 0:", "if credit >= 0:"),
    "contribution_always_full": ('"required_level": row["required_level"], "credit": credit}', '"required_level": row["required_level"], "credit": 1.0}'),
    "gap_only_when_missing": ('if level < row["required_level"]:', "if level == 0:"),
    "gap_when_level_le_required": ('if level < row["required_level"]:', 'if level <= row["required_level"]:'),
    "contributions_by_weight_asc": ('key=lambda c: (-c["weight"], -c["credit"], c["skill_id"])', 'key=lambda c: (c["weight"], -c["credit"], c["skill_id"])'),
    "contributions_no_credit_order": ('key=lambda c: (-c["weight"], -c["credit"], c["skill_id"])', 'key=lambda c: (-c["weight"], c["skill_id"])'),
    "contributions_credit_asc": ('key=lambda c: (-c["weight"], -c["credit"], c["skill_id"])', 'key=lambda c: (-c["weight"], c["credit"], c["skill_id"])'),
    "contributions_no_weight_order": ('key=lambda c: (-c["weight"], -c["credit"], c["skill_id"])', 'key=lambda c: (-c["credit"], c["skill_id"])'),
    "contributions_no_id_tiebreak": ('key=lambda c: (-c["weight"], -c["credit"], c["skill_id"])', 'key=lambda c: (-c["weight"], -c["credit"])'),
    "contributions_id_desc": ('key=lambda c: (-c["weight"], -c["credit"], c["skill_id"])', 'key=lambda c: (-c["weight"], -c["credit"], [-ord(ch) for ch in c["skill_id"]])'),
    "gaps_by_weight_asc": ('key=lambda g: (-g["weight"], -g["required_level"], g["skill_id"])', 'key=lambda g: (g["weight"], -g["required_level"], g["skill_id"])'),
    "gaps_no_required_order": ('key=lambda g: (-g["weight"], -g["required_level"], g["skill_id"])', 'key=lambda g: (-g["weight"], g["skill_id"])'),
    "gaps_required_asc": ('key=lambda g: (-g["weight"], -g["required_level"], g["skill_id"])', 'key=lambda g: (-g["weight"], g["required_level"], g["skill_id"])'),
    "gaps_no_weight_order": ('key=lambda g: (-g["weight"], -g["required_level"], g["skill_id"])', 'key=lambda g: (-g["required_level"], g["skill_id"])'),
    "gaps_no_id_tiebreak": ('key=lambda g: (-g["weight"], -g["required_level"], g["skill_id"])', 'key=lambda g: (-g["weight"], -g["required_level"])'),
    "gaps_id_desc": ('key=lambda g: (-g["weight"], -g["required_level"], g["skill_id"])', 'key=lambda g: (-g["weight"], -g["required_level"], [-ord(ch) for ch in g["skill_id"]])'),
    # --- SDG overlap and rank score ---
    "overlap_counts_repeats_in_role": ('len(set(role["sdgs"]) & wanted)', 'len([s for s in role["sdgs"] if s in wanted])'),
    "overlap_divides_by_role_sdgs": ('/ max(1, len(wanted))', '/ max(1, len(set(role["sdgs"])))'),
    "overlap_counts_repeats_in_user": ("wanted = set(user_sdgs)", "wanted = list(user_sdgs)"),
    "overlap_divides_by_one": ("/ max(1, len(wanted))", "/ 1"),
    "overlap_no_zero_guard": ("/ max(1, len(wanted))", "/ len(wanted)"),
    "rank_without_growth": ("match * (1 + growth) * (1 + config.SDG_TILT_ALPHA * overlap)", "match * (1 + config.SDG_TILT_ALPHA * overlap)"),
    "rank_without_sdg": ("match * (1 + growth) * (1 + config.SDG_TILT_ALPHA * overlap)", "match * (1 + growth)"),
    "rank_growth_not_one_plus": ("match * (1 + growth) * (1 + config.SDG_TILT_ALPHA * overlap)", "match * growth * (1 + config.SDG_TILT_ALPHA * overlap)"),
    "rank_sdg_not_one_plus": ("match * (1 + growth) * (1 + config.SDG_TILT_ALPHA * overlap)", "match * (1 + growth) * (config.SDG_TILT_ALPHA * overlap)"),
    "rank_additive": ("match * (1 + growth) * (1 + config.SDG_TILT_ALPHA * overlap)", "match + growth + config.SDG_TILT_ALPHA * overlap"),
    "hc_alpha": ("config.SDG_TILT_ALPHA", "0.15"),
    # --- added after verifier round 9 ---
    'nonfinite_unchecked': ('if not math.isfinite(projected):', 'if False:'),
    'nonfinite_checked_after_cap': ('            if not math.isfinite(projected):\n                raise ValueError(f"projected growth for {row[\'skill_id\']!r} is not a finite number")\n            if forecast.get("thin_data", False):\n                projected = max(-cap, min(cap, projected))\n', '            if forecast.get("thin_data", False):\n                projected = max(-cap, min(cap, projected))\n            if not math.isfinite(projected):\n                raise ValueError(\'x\')\n'),
    'match_not_exact_sum': ('math.fsum(match_terms)', '__import__("functools").reduce(lambda a, b: a + b, match_terms, 0.0)'),
    'growth_not_exact_sum': ('math.fsum(growth_terms)', '__import__("functools").reduce(lambda a, b: a + b, growth_terms, 0.0)'),
    'duplicate_roles_allowed': ('if len(set(ids)) != len(ids):', 'if False:'),
    'bool_weight_allowed': ('isinstance(row[k], bool) or ', ''),
    'overlap_rounded': ('len(set(role["sdgs"]) & wanted) / max(1, len(wanted))', 'round(len(set(role["sdgs"]) & wanted) / max(1, len(wanted)), 2)'),
    'growth_floored_in_rank': ('match * (1 + growth) *', 'match * (1 + max(growth, 0.0)) *'),
    'sdgs_aliased': ('"sdgs": list(role["sdgs"]),', '"sdgs": role["sdgs"],'),
    'levels_mutated': ('level = user_levels.get(row["skill_id"], 0)', 'level = user_levels.setdefault(row["skill_id"], 0)'),
    'other_role_types_ranked': ('role["role_type"] == "future" and', 'role["role_type"] != "origin" and'),
    'unknown_skill_levels_unchecked': ('    for skill_id, level in user_levels.items():', '    for skill_id, level in {}.items():'),
    # --- contract surface ---
    "key_match_pct": ('"match_pct": match,', '"match": match,'),
    "key_role_growth": ('"role_growth": growth,', '"growth": growth,'),
    "key_sdg_overlap": ('"sdg_overlap": overlap,', '"overlap": overlap,'),
    "key_rank_score": ('"rank_score": match', '"score": match'),
    "role_title_wrong": ('"title": role["title"],', '"title": role["role_id"],'),
    "ai_exposure_wrong": ('"ai_exposure": role["ai_exposure"],', '"ai_exposure": growth,'),
    "sdgs_is_user_sdgs": ('"sdgs": list(role["sdgs"]),', '"sdgs": list(user_sdgs),'),
    # --- citations ---
    "citations_not_deduplicated": ("unique = list(dict.fromkeys(i for i in ids if i))", "unique = list(ids)"),
    "citations_keep_empty": ("unique = list(dict.fromkeys(i for i in ids if i))", "unique = list(dict.fromkeys(ids))"),
    "citations_exposure_source_unfallbacked": ('role.get("exposure_source") or "aei_job_exposure"', 'role.get("exposure_source")'),
    "citations_exposure_source_ignored": ('role.get("exposure_source") or "aei_job_exposure"', '"aei_job_exposure"'),
    "citations_no_trend_source": ('ids = ["hn_whoishiring", ', "ids = ["),
    "citations_wrong_trend_source": ('"hn_whoishiring"', '"hn"'),
    "citations_raw_row_source": ("_ROLE_SKILL_SOURCES.get(row.get(\"source\"), row.get(\"source\"))", 'row.get("source")'),
    "citations_hot_unmapped": ('"onet_hot": "onet_tech"', '"onet_hot": "onet_hot"'),
    "citations_in_demand_unmapped": ('"onet_in_demand": "onet_tech"', '"onet_in_demand": "onet_in_demand"'),
    "citations_no_date": ('"snapshot_date": snapshot_date}', '"snapshot_date": ""}'),
    # --- ranking ---
    "rank_includes_origin_roles": ('role["role_type"] == "future" and role["role_id"] in has_skills', 'role["role_id"] in has_skills'),
    "rank_includes_roles_without_skills": ('role["role_type"] == "future" and role["role_id"] in has_skills', 'role["role_type"] == "future"'),
    "rank_ascending": ('key=lambda m: (-m["rank_score"], -m["match_pct"], m["role_id"])', 'key=lambda m: (m["rank_score"], -m["match_pct"], m["role_id"])'),
    "rank_no_match_tiebreak": ('key=lambda m: (-m["rank_score"], -m["match_pct"], m["role_id"])', 'key=lambda m: (-m["rank_score"], m["role_id"])'),
    "rank_match_tiebreak_asc": ('key=lambda m: (-m["rank_score"], -m["match_pct"], m["role_id"])', 'key=lambda m: (-m["rank_score"], m["match_pct"], m["role_id"])'),
    "rank_no_id_tiebreak": ('key=lambda m: (-m["rank_score"], -m["match_pct"], m["role_id"])', 'key=lambda m: (-m["rank_score"], -m["match_pct"])'),
    "rank_by_match_only": ('key=lambda m: (-m["rank_score"], -m["match_pct"], m["role_id"])', 'key=lambda m: (-m["match_pct"], m["role_id"])'),
}

MUTANTS = dict(M)


def _apply(name):
    old, new = MUTANTS[name]
    path = matching.__file__
    src = open(path, encoding="utf-8").read()
    assert src.count(old) >= 1, f"mutation target not found for {name}"
    exec(compile(src.replace(old, new), path, "exec"), matching.__dict__)


_name = os.environ.get("MUT")
if _name:
    _apply(_name)
