"""Scratch-only pytest plugin: applies one source mutation to engine/portfolio.py in memory (MUT=<name>)."""

import os

import _mutcheck

from engine import portfolio

M = {
    # --- weights ---
    "empty_profile_allowed": ("if not skills:", "if False:"),
    "duplicate_skill_allowed": ("if skill_id in levels:", "if False:"),
    "level_0_allowed": ("level not in (1, 2, 3)", "level not in (0, 1, 2, 3)"),
    "level_4_allowed": ("level not in (1, 2, 3)", "level not in (1, 2, 3, 4)"),
    "bool_level_allowed": ("isinstance(level, bool) or ", ""),
    "weights_equal": ("level / total for skill_id, level in levels.items()", "1 / len(levels) for skill_id, level in levels.items()"),
    "weights_divided_by_max": ("total = sum(levels.values())", "total = max(levels.values())"),
    # --- covariance ---
    "cov_duplicates_allowed": ("if len(set(skill_ids)) != len(skill_ids):", "if False:"),
    "cov_ragged_allowed": ("if len({len(c) for c in changes}) > 1:", "if False:"),
    "cov_needs_3_changes": ("if count < 2:", "if count < 3:"),
    "cov_needs_1_change": ("if count < 2:", "if count < 1:"),
    "cov_population_not_sample": ("/ (count - 1)", "/ count"),
    "cov_not_annualised": ("value = 12 * sum(", "value = 1 * sum("),
    "cov_annualised_11": ("value = 12 * sum(", "value = 11 * sum("),
    "cov_not_centred": ("(a - means[i]) * (b - means[j])", "a * b"),
    "cov_no_shrinkage": ("            if i != j:\n                value *= keep\n", "            pass\n"),
    "cov_shrinks_diagonal_too": ("            if i != j:\n                value *= keep\n", "            value *= keep\n"),
    "cov_keep_is_shrinkage": ("keep = 1 - config.COVARIANCE_SHRINKAGE", "keep = config.COVARIANCE_SHRINKAGE"),
    "cov_window_12": ("[-config.VOLATILITY_WINDOW_MONTHS:]", "[-12:]"),
    "cov_window_25": ("[-config.VOLATILITY_WINDOW_MONTHS:]", "[-25:]"),
    "cov_window_whole_series": ("[-config.VOLATILITY_WINDOW_MONTHS:]", "[:]"),
    "cov_not_smoothed": ('forecast.smooth(series["shares"])', 'series["shares"]'),
    "cov_wrong_eps": ('forecast.epsilon([m["total_posts"] for m in snapshot["months"]])', "forecast.epsilon([])"),
    "cov_fixed_eps": ('forecast.epsilon([m["total_posts"] for m in snapshot["months"]])', "0.001"),
    "cov_log_without_eps": ("math.log(v + eps)", "math.log(v + 0.001)"),
    "cov_not_symmetric": ("cov[i][j] = cov[j][i] = value", "cov[i][j] = value"),
    "cov_skips_diagonal": ("for j in range(i, n):", "for j in range(i + 1, n):"),
    "cov_changes_over_two_months": ("[b - a for a, b in zip(logs, logs[1:])]", "[b - a for a, b in zip(logs, logs[2:])]"),
    "changes_finite_unchecked": ('if not all(math.isfinite(x) for c in changes for x in c):', "if False:"),
    "metrics_finite_unchecked": ("if not all(math.isfinite(x) for x in numbers):", "if False:"),
    "metrics_cov_finite_unchecked": ("numbers = [cov_value for row in cov for cov_value in row]", "numbers = []"),
    "metrics_projected_finite_unchecked": ('numbers += [forecasts[i]["projected"] for i in ids]', "pass"),
    "metrics_exposure_finite_unchecked": ('numbers += [forecasts[i]["exposure"] for i in ids if forecasts[i]["exposure"] is not None]', "pass"),
    # --- config bypass (the value must come from config.py) ---
    "hc_vol_window": ("config.VOLATILITY_WINDOW_MONTHS", "24"),
    "hc_shrinkage": ("config.COVARIANCE_SHRINKAGE", "0.5"),
    "hc_gamma": ("config.RISK_AVERSION[risk_tolerance]", '{"low": 0.75, "medium": 0.375, "high": 0.125}[risk_tolerance]'),
    "hc_cap": ("config.THIN_GROWTH_CAP", "0.05"),
    # --- metrics ---
    "gamma_always_medium": ("config.RISK_AVERSION[risk_tolerance]", 'config.RISK_AVERSION["medium"]'),
    "weights_unchecked": ("if not ids or abs(sum(w) - 1) > 1e-9:", "if not ids:"),
    "empty_weights_allowed": ("if not ids or abs(sum(w) - 1) > 1e-9:", "if abs(sum(w) - 1) > 1e-9 and ids:"),
    "cov_shape_unchecked": ("if len(cov) != len(ids) or any(len(row) != len(ids) for row in cov):", "if False:"),
    "cov_columns_unchecked": ("if len(cov) != len(ids) or any(len(row) != len(ids) for row in cov):", "if len(cov) != len(ids):"),
    "thin_not_capped": ('if f["thin_data"]:', "if False:"),
    "solid_also_capped": ('if f["thin_data"]:', "if True:"),
    "cap_upper_only": ("r = max(-cap, min(cap, r))", "r = min(cap, r)"),
    "cap_lower_only": ("r = max(-cap, min(cap, r))", "r = max(-cap, r)"),
    "thin_zeroed_not_capped": ("r = max(-cap, min(cap, r))", "r = 0.0"),
    "growth_equal_weights": ("growth += weight * r", "growth += r / len(ids)"),
    "growth_uses_momentum": ('r = f["projected"]', 'r = f["momentum"]'),
    "exposure_drops_zero": ('if forecasts[i]["exposure"] is not None]', 'if forecasts[i]["exposure"]]', 2),
    "exposure_not_renormalised": ("/ sum(weight for weight, _ in known) if known", "/ 1 if known"),
    "exposure_none_becomes_zero": ("if known else None", "if known else 0.0"),
    "exposure_unknown_as_zero": ('known = [(weight, forecasts[i]["exposure"]) for i, weight in zip(ids, w) if forecasts[i]["exposure"] is not None]',
                                 'known = [(weight, forecasts[i]["exposure"] or 0.0) for i, weight in zip(ids, w)]'),
    "variance_diagonal_only": ("for i in range(len(ids)) for j in range(len(ids)))", "for i in range(len(ids)) for j in range(len(ids)) if i == j)"),
    "volatility_is_variance": ("volatility = math.sqrt(max(0.0, variance))", "volatility = variance"),
    "readiness_penalty_not_halved": ("growth - gamma / 2 * volatility ** 2", "growth - gamma * volatility ** 2"),
    "readiness_penalty_linear": ("growth - gamma / 2 * volatility ** 2", "growth - gamma / 2 * volatility"),
    "readiness_adds_penalty": ("growth - gamma / 2 * volatility ** 2", "growth + gamma / 2 * volatility ** 2"),
    "readiness_no_penalty": ("growth - gamma / 2 * volatility ** 2", "growth"),
    "diversification_linear": ('"diversification": 1 - sum(weight ** 2 for weight in w)', '"diversification": 1 - sum(weight for weight in w) / len(w)'),
    "diversification_no_one": ('"diversification": 1 - sum(weight ** 2 for weight in w)', '"diversification": sum(weight ** 2 for weight in w)'),
    # --- contract surface ---
    "key_growth": ('"growth": growth,', '"expected_growth": growth,'),
    "key_ai_exposure": ('"ai_exposure": exposure,', '"exposure": exposure,'),
    "key_volatility": ('"volatility": volatility,', '"vol": volatility,'),
    "key_readiness": ('"readiness": growth', '"score": growth'),
}

MUTANTS = dict(M)


TARGET = portfolio


def _apply(name):
    _mutcheck.apply(TARGET, MUTANTS, name)


_name = os.environ.get("MUT")
if _name:
    _apply(_name)
