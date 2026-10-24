"""Skill forecasts: demand index, damped momentum, volatility, scenarios (SPEC 5.1).

Input is one skill's entry from a snapshot (`counts`, `shares`, `exposure`)
plus the snapshot's `months`. Output is a SkillForecast dict
(contracts/README.md).

Pipeline per skill: smooth -> fit a trend (annual log growth g, standard error s) -> damp noisy
trends toward the all-skill average (shrinkage) -> apply the AI scenario in log space -> label.
"""

from __future__ import annotations

import math

from engine import config


def epsilon(total_posts: list[int]) -> float:
    """The small share added before taking logs: EPSILON_POSTS relative to the average thread size.

    One constant for every month (SPEC 5.1), so a skill that is never mentioned shows no trend
    even when the monthly threads grow or shrink. With no usable thread sizes, behaves as if the
    average thread had one post, so ln() is still defined.
    """
    average = sum(total_posts) / len(total_posts) if total_posts else 0
    return config.EPSILON_POSTS / average if average > 0 else config.EPSILON_POSTS


def smooth(shares: list[float], window: int = config.SMOOTHING_MONTHS) -> list[float]:
    """Trailing rolling mean; the first values use as many months as exist so far."""
    out = []
    for i in range(len(shares)):
        chunk = shares[max(0, i - window + 1): i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def demand_index(smoothed: list[float]) -> list[float]:
    """Rebase so the first month = 100 (the sparkline on the Skill Market).

    If the skill only appears later, rebase on its first non-zero month; earlier months show 0.
    """
    base = next((v for v in smoothed if v > 0), None)
    if base is None:
        return [0.0] * len(smoothed)
    return [100 * v / base for v in smoothed]


def _ols_slope(y: list[float]) -> tuple[float, float]:
    """Slope of y on 0..n-1 and its standard error, n - 2 degrees of freedom (SPEC 5.1).

    Closed form: the slope of a flat series is exactly 0 (its standard error can still be a tiny
    rounding value, which is why tests compare with a small absolute tolerance).
    """
    n = len(y)
    x_mean = (n - 1) / 2
    y_mean = sum(y) / n
    sxx = sum((i - x_mean) ** 2 for i in range(n))
    b = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(y)) / sxx
    a = y_mean - b * x_mean
    rss = sum((v - (a + b * i)) ** 2 for i, v in enumerate(y))
    se = math.sqrt(rss / (n - 2) / sxx)
    return b, se


def trend(smoothed: list[float], total_posts: list[int]) -> tuple[float, float]:
    """Annual log growth g = 12 b and its standard error s = 12 SE_b * SE_INFLATION.

    SE_INFLATION corrects the plain OLS standard error, which is too small because the smoothed points are not independent (SPEC 5.1).
    OLS of ln(smoothed + epsilon) on the month index over the last MOMENTUM_WINDOW_MONTHS.
    With fewer than MIN_HISTORY_MONTHS there is no trend to fit: returns (0, 0).
    """
    n = min(config.MOMENTUM_WINDOW_MONTHS, len(smoothed))
    if n < config.MIN_HISTORY_MONTHS:
        return 0.0, 0.0
    eps = epsilon(total_posts)
    b, se = _ols_slope([math.log(s + eps) for s in smoothed[-n:]])
    return 12 * b, 12 * se * config.SE_INFLATION


def momentum(smoothed: list[float], total_posts: list[int]) -> tuple[float, float, float]:
    """The raw (undamped) annual growth (r, r_low, r_high): r = e^g - 1, interval g -/+ INTERVAL_Z * s.

    Not used by forecast_all (it works on trend() and damps it); kept as the plain fitted trend. The interval
    uses trend()'s s, so it already includes SE_INFLATION.
    """
    g, s = trend(smoothed, total_posts)
    half = config.INTERVAL_Z * s
    return math.exp(g) - 1, math.exp(g - half) - 1, math.exp(g + half) - 1


def shrinkage_prior(estimates: list[tuple[float, float]]) -> dict | None:
    """Average growth `mu` and between-skill spread `tau2` of well-observed skills (SPEC 5.1).

    `estimates` are (g, s) of the reference skills. Fewer than SHRINK_MIN_SKILLS -> None (no damping).
    DerSimonian-Laird: s* = max(s, SE_FLOOR), w = 1/s*^2, mu0 = sum(w g)/sum(w), Q = sum(w (g - mu0)^2),
    tau2_DL = max(0, (Q - (k - 1)) / (sum(w) - sum(w^2)/sum(w))), tau2 = max(tau2_DL, TAU_FLOOR^2),
    mu = sum(g / (s*^2 + tau2)) / sum(1 / (s*^2 + tau2)).
    """
    k = len(estimates)
    if k < config.SHRINK_MIN_SKILLS:
        return None
    g = [e[0] for e in estimates]
    s_star = [max(e[1], config.SE_FLOOR) for e in estimates]
    w = [1 / s ** 2 for s in s_star]
    w_sum = sum(w)
    mu0 = sum(wi * gi for wi, gi in zip(w, g)) / w_sum
    q = sum(wi * (gi - mu0) ** 2 for wi, gi in zip(w, g))
    tau2_dl = max(0.0, (q - (k - 1)) / (w_sum - sum(wi ** 2 for wi in w) / w_sum))
    tau2 = max(tau2_dl, config.TAU_FLOOR ** 2)
    w2 = [1 / (s ** 2 + tau2) for s in s_star]
    mu = sum(wi * gi for wi, gi in zip(w2, g)) / sum(w2)
    return {"k": k, "mu": mu, "tau2_dl": tau2_dl, "tau2": tau2}


def shrink(g: float, s: float, prior: dict | None) -> tuple[float, float]:
    """Damp a trend toward the prior mean: B = tau2 / (tau2 + s^2), g' = mu + B (g - mu), s' = s sqrt(B).

    Uses the skill's own (unfloored) s, so a skill with s = 0 is left exactly as it is.
    No prior -> unchanged.
    """
    if prior is None:
        return g, s
    b = prior["tau2"] / (prior["tau2"] + s * s)
    return prior["mu"] + b * (g - prior["mu"]), s * math.sqrt(b)


def volatility(smoothed: list[float], eps: float) -> float:
    """Sample std dev of month-on-month change in ln(smoothed + eps), times sqrt(12).

    Uses the last VOLATILITY_WINDOW_MONTHS smoothed values. `eps` must be the same
    epsilon(total_posts) that the trend uses; a zero share needs eps > 0.
    """
    window = smoothed[-config.VOLATILITY_WINDOW_MONTHS:]
    if any(v + eps <= 0 for v in window):
        raise ValueError("a zero share needs eps > 0 (use epsilon(total_posts))")
    logs = [math.log(v + eps) for v in window]
    changes = [b - a for a, b in zip(logs, logs[1:])]
    if len(changes) < 2:
        return 0.0
    mean = sum(changes) / len(changes)
    variance = sum((c - mean) ** 2 for c in changes) / (len(changes) - 1)
    return math.sqrt(variance) * math.sqrt(12)


def trajectory(projected_low: float, projected_high: float) -> str:
    """'rising' if low > +TREND_THRESHOLD, 'declining' if high < -TREND_THRESHOLD, else 'stable'."""
    if projected_low > config.TREND_THRESHOLD:
        return "rising"
    if projected_high < -config.TREND_THRESHOLD:
        return "declining"
    return "stable"


def _is_thin(series: dict) -> bool:
    """Too little history, or fewer than THIN_DATA_MIN_MEAN_COUNT posts a month over all months."""
    counts = series["counts"]
    mean_count = sum(counts) / len(counts) if counts else 0.0
    return len(series["shares"]) < config.MIN_HISTORY_MONTHS or mean_count < config.THIN_DATA_MIN_MEAN_COUNT


def forecast_skill(skill_id: str, series: dict, months: list[dict], mean_exposure: float, scenario: str,
                   prior: dict | None = None) -> dict:
    """Build one SkillForecast.

    The trend is damped with `prior` (None = not damped), then the scenario shifts it in log space:
    projected = e^(g' - lambda_s * (exposure - mean_exposure)) - 1. A skill with unknown exposure gets
    no scenario shift. Thin data means fewer than MIN_HISTORY_MONTHS of history, or fewer than
    THIN_DATA_MIN_MEAN_COUNT posts a month on average (over all months). Thin skills are always
    labelled "stable": a number we cannot trust must not become a headline. With too little history
    the trend and the scenario shift are both zero placeholders.
    """
    if scenario not in config.SCENARIOS:
        raise KeyError(f"unknown scenario {scenario!r}; expected one of {list(config.SCENARIOS)}")
    totals = [m["total_posts"] for m in months]
    history = len(series["shares"])
    smoothed = smooth(series["shares"])
    g, s = trend(smoothed, totals)
    enough_history = history >= config.MIN_HISTORY_MONTHS
    g_damped, s_damped = shrink(g, s, prior) if enough_history else (g, s)
    half = config.INTERVAL_Z * s_damped
    exposure = None if series.get("exposure") is None else float(series["exposure"])
    delta = 0.0
    if exposure is not None and enough_history:
        delta = config.SCENARIOS[scenario]["lambda"] * (exposure - mean_exposure)
    thin = _is_thin(series)
    projected_low = math.exp(g_damped - half - delta) - 1
    projected_high = math.exp(g_damped + half - delta) - 1
    return {
        "skill_id": skill_id,
        "scenario": scenario,
        "momentum": math.exp(g_damped) - 1,
        "momentum_low": math.exp(g_damped - half) - 1,
        "momentum_high": math.exp(g_damped + half) - 1,
        "momentum_raw": math.exp(g) - 1,
        "volatility": volatility(smoothed, epsilon(totals)),
        "exposure": exposure,
        "projected": math.exp(g_damped - delta) - 1,
        "projected_low": projected_low,
        "projected_high": projected_high,
        "trajectory": "stable" if thin else trajectory(projected_low, projected_high),
        "thin_data": thin,
        "history_months": history,
        "is_estimate": True,
        "index": demand_index(smoothed),
    }


def prior_for_snapshot(snapshot: dict) -> dict | None:
    """The shrinkage prior from a snapshot's reference skills (enough history and not thin data)."""
    totals = [m["total_posts"] for m in snapshot["months"]]
    reference = []
    for series in snapshot["skills"].values():
        if len(series["shares"]) >= config.MIN_HISTORY_MONTHS and not _is_thin(series):
            reference.append(trend(smooth(series["shares"]), totals))
    return shrinkage_prior(reference)


def forecast_all(snapshot: dict, scenario: str = config.DEFAULT_SCENARIO) -> dict[str, dict]:
    """SkillForecast for every skill in the snapshot, keyed by skill_id."""
    if scenario not in config.SCENARIOS:
        raise KeyError(f"unknown scenario {scenario!r}; expected one of {list(config.SCENARIOS)}")
    known = [s["exposure"] for s in snapshot["skills"].values() if s.get("exposure") is not None]
    mean_exposure = sum(known) / len(known) if known else 0.0
    prior = prior_for_snapshot(snapshot)
    return {
        skill_id: forecast_skill(skill_id, series, snapshot["months"], mean_exposure, scenario, prior)
        for skill_id, series in snapshot["skills"].items()
    }
