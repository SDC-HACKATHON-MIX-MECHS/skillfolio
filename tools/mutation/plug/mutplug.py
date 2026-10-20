"""Scratch-only pytest plugin: applies one source mutation to engine/forecast.py in memory (MUT=<name>)."""

import os

from engine import config, forecast

M = {
    # --- shrinkage ---
    "shrink_off": ("g_damped, s_damped = shrink(g, s, prior) if enough_history else (g, s)", "g_damped, s_damped = g, s"),
    "shrink_applied_without_history": ("g_damped, s_damped = shrink(g, s, prior) if enough_history else (g, s)", "g_damped, s_damped = shrink(g, s, prior)"),
    "prior_never_used": ("prior = prior_for_snapshot(snapshot)", "prior = None"),
    "B_uses_floored_s": ('b = prior["tau2"] / (prior["tau2"] + s * s)', 'b = prior["tau2"] / (prior["tau2"] + max(s, config.SE_FLOOR) ** 2)'),
    "B_linear_s": ('b = prior["tau2"] / (prior["tau2"] + s * s)', 'b = prior["tau2"] / (prior["tau2"] + s)'),
    "B_inverted": ('b = prior["tau2"] / (prior["tau2"] + s * s)', 'b = (s * s) / (prior["tau2"] + s * s)'),
    "s_not_scaled": ('s * math.sqrt(b)', 's'),
    "s_scaled_by_B": ('s * math.sqrt(b)', 's * b'),
    "pull_toward_zero": ('return prior["mu"] + b * (g - prior["mu"]), s * math.sqrt(b)', 'return b * g, s * math.sqrt(b)'),
    "full_pull_to_mean": ('return prior["mu"] + b * (g - prior["mu"]), s * math.sqrt(b)', 'return prior["mu"], s * math.sqrt(b)'),
    # --- prior estimation ---
    "min_skills_4": ("if k < config.SHRINK_MIN_SKILLS:", "if k < 4:"),
    "min_skills_6": ("if k < config.SHRINK_MIN_SKILLS:", "if k < 6:"),
    "min_skills_le": ("if k < config.SHRINK_MIN_SKILLS:", "if k <= config.SHRINK_MIN_SKILLS:"),
    "se_floor_off": ("s_star = [max(e[1], config.SE_FLOOR) for e in estimates]", "s_star = [max(e[1], 1e-9) for e in estimates]"),
    "se_floor_0_01": ("s_star = [max(e[1], config.SE_FLOOR) for e in estimates]", "s_star = [max(e[1], 0.01) for e in estimates]"),
    "se_floor_0_1": ("s_star = [max(e[1], config.SE_FLOOR) for e in estimates]", "s_star = [max(e[1], 0.1) for e in estimates]"),
    "tau_floor_off": ("tau2 = max(tau2_dl, config.TAU_FLOOR ** 2)", "tau2 = max(tau2_dl, 1e-9)"),
    "tau_floor_not_squared": ("tau2 = max(tau2_dl, config.TAU_FLOOR ** 2)", "tau2 = max(tau2_dl, config.TAU_FLOOR)"),
    "dl_q_minus_k": ("(q - (k - 1))", "(q - k)"),
    "dl_denominator_plain": ("(w_sum - sum(wi ** 2 for wi in w) / w_sum)", "w_sum"),
    "mu_fixed_effect": ("mu = sum(wi * gi for wi, gi in zip(w2, g)) / sum(w2)", "mu = mu0"),
    "mu_unweighted": ("mu = sum(wi * gi for wi, gi in zip(w2, g)) / sum(w2)", "mu = sum(g) / k"),
    "weights_not_squared": ("w = [1 / s ** 2 for s in s_star]", "w = [1 / s for s in s_star]"),
    "w2_without_tau": ("w2 = [1 / (s ** 2 + tau2) for s in s_star]", "w2 = [1 / s ** 2 for s in s_star]"),
    "reference_includes_thin": ('if len(series["shares"]) >= config.MIN_HISTORY_MONTHS and not _is_thin(series):', 'if len(series["shares"]) >= config.MIN_HISTORY_MONTHS:'),
    "reference_needs_no_history": ('if len(series["shares"]) >= config.MIN_HISTORY_MONTHS and not _is_thin(series):', 'if not _is_thin(series):'),
    "reference_only_rising": ('if len(series["shares"]) >= config.MIN_HISTORY_MONTHS and not _is_thin(series):', 'if len(series["shares"]) >= config.MIN_HISTORY_MONTHS and not _is_thin(series) and sum(series["counts"][-3:]) >= sum(series["counts"][:3]):'),
    # --- scenario in log space ---
    "scenario_linear_projected": ('"projected": math.exp(g_damped - delta) - 1,', '"projected": math.exp(g_damped) - 1 - delta,'),
    "scenario_linear_low": ("projected_low = math.exp(g_damped - half - delta) - 1", "projected_low = math.exp(g_damped - half) - 1 - delta"),
    "scenario_linear_high": ("projected_high = math.exp(g_damped + half - delta) - 1", "projected_high = math.exp(g_damped + half) - 1 - delta"),
    "scenario_sign_flipped": ('delta = config.SCENARIOS[scenario]["lambda"] * (exposure - mean_exposure)', 'delta = config.SCENARIOS[scenario]["lambda"] * (mean_exposure - exposure)'),
    "scenario_not_centred": ('delta = config.SCENARIOS[scenario]["lambda"] * (exposure - mean_exposure)', 'delta = config.SCENARIOS[scenario]["lambda"] * exposure'),
    "scenario_hits_momentum": ('"momentum": math.exp(g_damped) - 1,', '"momentum": math.exp(g_damped - delta) - 1,'),
    "scenario_ignores_interval_low": ("projected_low = math.exp(g_damped - half - delta) - 1", "projected_low = math.exp(g_damped - half) - 1"),
    "shift_applied_without_history": ("if exposure is not None and enough_history:", "if exposure is not None:"),
    "shift_guard_ge4": ("if exposure is not None and enough_history:", "if exposure is not None and history >= 4:"),
    "interval_uses_raw_s": ("half = config.INTERVAL_Z * s_damped", "half = config.INTERVAL_Z * s"),
    "momentum_raw_is_damped": ('"momentum_raw": math.exp(g) - 1,', '"momentum_raw": math.exp(g_damped) - 1,'),
    "label_from_momentum_interval": ("trajectory(projected_low, projected_high)", "trajectory(math.exp(g_damped - half) - 1, math.exp(g_damped + half) - 1)"),
    "label_from_point_estimate": ("trajectory(projected_low, projected_high)", "trajectory(math.exp(g_damped - delta) - 1, projected_high)"),
    "label_from_point_estimate_high": ("trajectory(projected_low, projected_high)", "trajectory(projected_low, math.exp(g_damped - delta) - 1)"),
    "label_from_point_both": ("trajectory(projected_low, projected_high)", "trajectory(math.exp(g_damped - delta) - 1, math.exp(g_damped - delta) - 1)"),
    "label_ignores_thin": ('"stable" if thin else trajectory(projected_low, projected_high)', "trajectory(projected_low, projected_high)"),
    "trend_not_annualised": ("return 12 * b, 12 * se", "return b, se"),
    "trend_se_not_annualised": ("return 12 * b, 12 * se", "return 12 * b, se"),
    "mean_exposure_includes_none_as_zero": ("mean_exposure = sum(known) / len(known) if known else 0.0", "mean_exposure = sum(known) / (len(known) + 1) if known else 0.0"),
    # --- thin data / history (kept from earlier rounds) ---
    "thin_cutoff_2_9": ("mean_count < config.THIN_DATA_MIN_MEAN_COUNT", "mean_count < 2.9"),
    "thin_cutoff_le_3": ("mean_count < config.THIN_DATA_MIN_MEAN_COUNT", "mean_count <= config.THIN_DATA_MIN_MEAN_COUNT"),
    "thin_mean_over_nonzero": ("mean_count = sum(counts) / len(counts) if counts else 0.0", "nz = [c for c in counts if c]; mean_count = sum(nz) / len(nz) if nz else 0.0"),
    "history_guard_4_in_trend": ("if n < config.MIN_HISTORY_MONTHS:", "if n < 4:"),
    "traj_ge": ("if projected_low > config.TREND_THRESHOLD:", "if projected_low >= config.TREND_THRESHOLD:"),
    "unknown_exposure_offset": ("    delta = 0.0\n", "    delta = 0.01 if exposure is None else 0.0\n"),
    # --- config bypass ---
    "hc_min_skills": ("config.SHRINK_MIN_SKILLS", "5"),
    "hc_se_floor": ("config.SE_FLOOR", "0.05"),
    "hc_tau_floor": ("config.TAU_FLOOR", "0.10"),
    "hc_lambda": ('config.SCENARIOS[scenario]["lambda"]', '{"moderate": 0.5, "fast": 1.5}[scenario]'),
    "hc_interval_z": ("config.INTERVAL_Z", "1.28"),
    "hc_momentum_window": ("config.MOMENTUM_WINDOW_MONTHS", "12"),
    "hc_vol_window": ("config.VOLATILITY_WINDOW_MONTHS", "24"),
    "hc_min_history": ("config.MIN_HISTORY_MONTHS", "3"),
    "hc_trend_threshold": ("config.TREND_THRESHOLD", "0.05"),
    "hc_thin_cutoff": ("config.THIN_DATA_MIN_MEAN_COUNT", "3"),
    "hc_epsilon_posts": ("config.EPSILON_POSTS", "0.5"),
    # --- contract surface ---
    "skill_id_wrong": ('"skill_id": skill_id,', '"skill_id": "x",'),
    "scenario_field_wrong": ('"scenario": scenario,', '"scenario": "moderate",'),
    "default_scenario_fast": ("scenario: str = config.DEFAULT_SCENARIO", "scenario: str = 'fast'"),
    "is_estimate_int": ('"is_estimate": True,', '"is_estimate": 1,'),
}

MUTANTS = {k: v for k, v in M.items()}


def _apply(name):
    old, new = MUTANTS[name]
    path = forecast.__file__
    src = open(path, encoding="utf-8").read()
    assert src.count(old) >= 1, f"mutation target not found for {name}"
    exec(compile(src.replace(old, new), path, "exec"), forecast.__dict__)


_name = os.environ.get("MUT")
if _name:
    _apply(_name)
