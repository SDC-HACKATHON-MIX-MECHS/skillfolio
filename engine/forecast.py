"""Skill forecasts: demand index, momentum, volatility, scenarios (SPEC 5.1). Lane A.

Input is one skill's entry from a snapshot (`counts`, `shares`, `exposure`)
plus the snapshot's `months`. Output is a SkillForecast dict
(contracts/README.md).
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


def momentum(smoothed: list[float], total_posts: list[int]) -> tuple[float, float, float]:
    """Annualised trend over the last MOMENTUM_WINDOW_MONTHS.

    OLS of ln(smoothed + epsilon) on the month index -> slope b and its standard error.
    Returns (r, r_low, r_high) where r = e^(12b) - 1 and the interval uses INTERVAL_Z.
    With fewer than MIN_HISTORY_MONTHS there is no trend to fit: returns (0, 0, 0) and
    forecast_skill marks the skill as thin data with a "stable" label.
    """
    n = min(config.MOMENTUM_WINDOW_MONTHS, len(smoothed))
    if n < config.MIN_HISTORY_MONTHS:
        return 0.0, 0.0, 0.0
    eps = epsilon(total_posts)
    y = [math.log(s + eps) for s in smoothed[-n:]]
    b, se = _ols_slope(y)
    annual = lambda slope: math.exp(12 * slope) - 1
    half = config.INTERVAL_Z * se
    return annual(b), annual(b - half), annual(b + half)


def volatility(smoothed: list[float], eps: float) -> float:
    """Sample std dev of month-on-month change in ln(smoothed + eps), times sqrt(12).

    Uses the last VOLATILITY_WINDOW_MONTHS smoothed values. `eps` must be the same
    epsilon(total_posts) that momentum uses; a zero share needs eps > 0.
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


def forecast_skill(skill_id: str, series: dict, months: list[dict], mean_exposure: float, scenario: str) -> dict:
    """Build one SkillForecast. projected = momentum - lambda_s * (exposure - mean_exposure).

    A skill with unknown exposure gets no scenario shift. Thin data means fewer than
    MIN_HISTORY_MONTHS of history, or fewer than THIN_DATA_MIN_MEAN_COUNT posts a month on
    average (over all months). Thin skills are always labelled "stable": a number we cannot
    trust must not become a headline. With too little history the trend and the scenario
    shift are both zero placeholders.
    """
    if scenario not in config.SCENARIOS:
        raise KeyError(f"unknown scenario {scenario!r}; expected one of {list(config.SCENARIOS)}")
    totals = [m["total_posts"] for m in months]
    counts = series["counts"]
    history = len(series["shares"])
    smoothed = smooth(series["shares"])
    r, r_low, r_high = momentum(smoothed, totals)
    exposure = None if series.get("exposure") is None else float(series["exposure"])
    enough_history = history >= config.MIN_HISTORY_MONTHS
    shift = 0.0
    if exposure is not None and enough_history:
        shift = config.SCENARIOS[scenario]["lambda"] * (exposure - mean_exposure)
    mean_count = sum(counts) / len(counts) if counts else 0.0
    thin = not enough_history or mean_count < config.THIN_DATA_MIN_MEAN_COUNT
    return {
        "skill_id": skill_id,
        "scenario": scenario,
        "momentum": r,
        "momentum_low": r_low,
        "momentum_high": r_high,
        "volatility": volatility(smoothed, epsilon(totals)),
        "exposure": exposure,
        "projected": r - shift,
        "projected_low": r_low - shift,
        "projected_high": r_high - shift,
        "trajectory": "stable" if thin else trajectory(r_low - shift, r_high - shift),
        "thin_data": thin,
        "history_months": history,
        "is_estimate": True,
        "index": demand_index(smoothed),
    }


def forecast_all(snapshot: dict, scenario: str = config.DEFAULT_SCENARIO) -> dict[str, dict]:
    """SkillForecast for every skill in the snapshot, keyed by skill_id."""
    if scenario not in config.SCENARIOS:
        raise KeyError(f"unknown scenario {scenario!r}; expected one of {list(config.SCENARIOS)}")
    known = [s["exposure"] for s in snapshot["skills"].values() if s.get("exposure") is not None]
    mean_exposure = sum(known) / len(known) if known else 0.0
    return {
        skill_id: forecast_skill(skill_id, series, snapshot["months"], mean_exposure, scenario)
        for skill_id, series in snapshot["skills"].items()
    }
