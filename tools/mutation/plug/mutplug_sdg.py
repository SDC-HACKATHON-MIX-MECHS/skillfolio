"""Scratch-only pytest plugin: applies one source mutation to engine/sdg.py in memory (MUT=<name>)."""

import os

import _mutcheck

from engine import sdg

M = {
    'baseline_missing': ('[config.BASELINE_SKILL_SDG] + sorted(found - {config.BASELINE_SKILL_SDG})', 'sorted(found)'),
    'baseline_last': ('[config.BASELINE_SKILL_SDG] + sorted(found - {config.BASELINE_SKILL_SDG})', 'sorted(found - {config.BASELINE_SKILL_SDG}) + [config.BASELINE_SKILL_SDG]'),
    'baseline_repeated': ('sorted(found - {config.BASELINE_SKILL_SDG})', 'sorted(found)'),
    'others_descending': ('sorted(found - {config.BASELINE_SKILL_SDG})', 'sorted(found - {config.BASELINE_SKILL_SDG}, reverse=True)'),
    'threshold_exclusive': ('row["weight"] >= config.ROLE_SDG_MIN_WEIGHT', 'row["weight"] > config.ROLE_SDG_MIN_WEIGHT'),
    'threshold_3': ('row["weight"] >= config.ROLE_SDG_MIN_WEIGHT', 'row["weight"] >= 3'),
    'threshold_any_weight': ('row["weight"] >= config.ROLE_SDG_MIN_WEIGHT', 'row["weight"] >= 1'),
    'hc_threshold': ('config.ROLE_SDG_MIN_WEIGHT', '2'),
    'hc_baseline': ('config.BASELINE_SKILL_SDG', '4', 2),
    'unknown_roles_not_ignored': (' and row["role_id"] in by_role', ''),
    'other_skills_rows_used': ('if row["skill_id"] == skill_id and ', 'if '),
    'only_future_style_roles': ('by_role = {role["role_id"]: role["sdgs"] for role in roles}', 'by_role = {role["role_id"]: role["sdgs"] for role in roles if role.get("role_type") != "origin"}'),
    'negative_weights_allowed': ('not all(w >= 0 for w in weights)', 'False'),
    'weights_sum_unchecked': (' or abs(sum(weights) - 1) > 1e-9', ''),
    'weights_sum_tolerance_loose': ('abs(sum(weights) - 1) > 1e-9', 'abs(sum(weights) - 1) > 1e-3'),
    'weights_sum_tolerance_exact': ('abs(sum(weights) - 1) > 1e-9', 'abs(sum(weights) - 1) > 1e-15'),
    'no_split': ('weight / len(sdgs)', 'weight'),
    'split_by_one_more': ('weight / len(sdgs)', 'weight / (len(sdgs) + 1)'),
    'split_ignores_baseline': ('weight / len(sdgs)', 'weight / max(1, len(sdgs) - 1)'),
    'inexact_sum': ('math.fsum(parts)', '__import__("functools").reduce(lambda a, b: a + b, parts, 0.0)'),
    'sorted_ascending_share': ('key=lambda item: (-item[1], item[0])', 'key=lambda item: (item[1], item[0])'),
    'ties_descending_sdg': ('key=lambda item: (-item[1], item[0])', 'key=lambda item: (-item[1], -item[0])'),
    'no_tiebreak': ('key=lambda item: (-item[1], item[0])', 'key=lambda item: -item[1]'),
    'sorted_by_sdg_only': ('key=lambda item: (-item[1], item[0])', 'key=lambda item: item[0]'),
    'zero_weights_listed': ('        if weight == 0:\n            continue', '        if False:\n            continue'),
    'zero_weight_rejected': ('not all(w >= 0 for w in weights)', 'not all(w > 0 for w in weights)'),
    'bool_weights_allowed': ('any(isinstance(w, bool) for w in weights) or ', ''),
    'weights_tol_1e-6': ('abs(sum(weights) - 1) > 1e-9', 'abs(sum(weights) - 1) > 1e-6'),
}

MUTANTS = dict(M)


TARGET = sdg


def _apply(name):
    _mutcheck.apply(TARGET, MUTANTS, name)


_name = os.environ.get("MUT")
if _name:
    _apply(_name)
