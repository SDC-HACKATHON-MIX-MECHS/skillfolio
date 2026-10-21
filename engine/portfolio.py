"""Portfolio metrics for a set of skills (SPEC 5.2). Lane A.

The user's skills are weighted by self-rated level. From each skill's forecast and the covariance of
the skills' monthly demand changes we get expected growth, AI exposure, volatility, diversification
and one headline Readiness score.
"""

from __future__ import annotations

import math

from engine import config, forecast


def weights(skills: list[dict]) -> dict[str, float]:
    """[{skill_id, level}] -> {skill_id: level / sum(levels)}, in the order given.

    Levels are 1, 2 or 3. An empty profile, an unknown level or a repeated skill is an error: the
    scoring needs a real portfolio, and a silent guess would hide a data problem.
    """
    if not skills:
        raise ValueError("a portfolio needs at least one skill")
    levels: dict[str, int] = {}
    for entry in skills:
        skill_id, level = entry["skill_id"], entry["level"]
        if skill_id in levels:
            raise ValueError(f"skill {skill_id!r} appears more than once")
        if isinstance(level, bool) or level not in (1, 2, 3):
            raise ValueError(f"level for {skill_id!r} must be 1, 2 or 3, got {level!r}")
        levels[skill_id] = int(level)
    total = sum(levels.values())
    return {skill_id: level / total for skill_id, level in levels.items()}


def _monthly_changes(series: dict, eps: float) -> list[float]:
    """Month-on-month change in ln(smoothed share + eps) over the volatility window (as forecast.volatility)."""
    window = forecast.smooth(series["shares"])[-config.VOLATILITY_WINDOW_MONTHS:]
    logs = [math.log(v + eps) for v in window]
    return [b - a for a, b in zip(logs, logs[1:])]


def covariance(snapshot: dict, skill_ids: list[str]) -> list[list[float]]:
    """Annualised covariance of monthly changes in ln(smoothed share + eps), shrunk toward the diagonal.

    Same epsilon (forecast.epsilon) and 24-month window as forecast.volatility (SPEC 5.1/5.2), so a
    one-skill portfolio has volatility equal to that skill's volatility. Sample covariance (divide by
    the number of changes - 1) times 12; off-diagonal entries are then multiplied by
    (1 - COVARIANCE_SHRINKAGE). Fewer than 2 changes -> all zeros. Row and column order follow `skill_ids`.
    """
    if len(set(skill_ids)) != len(skill_ids):
        raise ValueError("skill_ids must not repeat")
    eps = forecast.epsilon([m["total_posts"] for m in snapshot["months"]])
    changes = [_monthly_changes(snapshot["skills"][skill_id], eps) for skill_id in skill_ids]
    if len({len(c) for c in changes}) > 1:
        raise ValueError("skills have series of different lengths")
    if not all(math.isfinite(x) for c in changes for x in c):
        raise ValueError("a share is not a finite number")
    n = len(skill_ids)
    count = len(changes[0]) if n else 0
    if count < 2:
        return [[0.0] * n for _ in range(n)]
    means = [sum(c) / count for c in changes]
    keep = 1 - config.COVARIANCE_SHRINKAGE
    cov = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            value = 12 * sum((a - means[i]) * (b - means[j]) for a, b in zip(changes[i], changes[j])) / (count - 1)
            if i != j:
                value *= keep
            cov[i][j] = cov[j][i] = value
    return cov


def metrics(skill_weights: dict[str, float], forecasts: dict[str, dict], cov: list[list[float]], risk_tolerance: str) -> dict:
    """PortfolioMetrics: growth, ai_exposure, volatility, diversification, readiness.

    `cov` rows and columns follow the key order of `skill_weights`. Growth is the weighted `projected`
    growth, except that a thin-data skill counts for at most +/-THIN_GROWTH_CAP (a number we cannot
    trust must not move the headline). AI exposure averages only the skills whose exposure is known
    (weights renormalised) and is None when none is. Readiness = growth - gamma/2 * volatility^2.
    """
    gamma = config.RISK_AVERSION[risk_tolerance]
    ids = list(skill_weights)
    w = [skill_weights[i] for i in ids]
    if not ids or abs(sum(w) - 1) > 1e-9:
        raise ValueError("weights must be non-empty and sum to 1")
    if len(cov) != len(ids) or any(len(row) != len(ids) for row in cov):
        raise ValueError("covariance must be a square matrix with one row per skill, in weight order")
    numbers = [cov_value for row in cov for cov_value in row]
    numbers += [forecasts[i]["projected"] for i in ids]
    numbers += [forecasts[i]["exposure"] for i in ids if forecasts[i]["exposure"] is not None]
    if not all(math.isfinite(x) for x in numbers):
        raise ValueError("covariance, projected growth and exposure must be finite numbers")
    cap = config.THIN_GROWTH_CAP
    growth = 0.0
    for skill_id, weight in zip(ids, w):
        f = forecasts[skill_id]
        r = f["projected"]
        if f["thin_data"]:
            r = max(-cap, min(cap, r))
        growth += weight * r
    known = [(weight, forecasts[i]["exposure"]) for i, weight in zip(ids, w) if forecasts[i]["exposure"] is not None]
    exposure = sum(weight * e for weight, e in known) / sum(weight for weight, _ in known) if known else None
    variance = sum(w[i] * cov[i][j] * w[j] for i in range(len(ids)) for j in range(len(ids)))
    volatility = math.sqrt(max(0.0, variance))
    return {
        "growth": growth,
        "ai_exposure": exposure,
        "volatility": volatility,
        "diversification": 1 - sum(weight ** 2 for weight in w),
        "readiness": growth - gamma / 2 * volatility ** 2,
    }
