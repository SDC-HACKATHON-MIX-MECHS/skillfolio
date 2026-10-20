"""Skill forecasts: demand index, momentum, volatility, scenarios (SPEC 5.1). Lane A.

Input is one skill's entry from a snapshot (`counts`, `shares`, `exposure`)
plus the snapshot's `months`. Output is a SkillForecast dict
(contracts/README.md).
"""

from __future__ import annotations

from engine import config


def smooth(shares: list[float], window: int = config.SMOOTHING_MONTHS) -> list[float]:
    """Trailing rolling mean; the first values use as many months as exist so far."""
    raise NotImplementedError("lane A")


def demand_index(smoothed: list[float]) -> list[float]:
    """Rebase so the first month = 100 (the sparkline on the Skill Market)."""
    raise NotImplementedError("lane A")


def momentum(smoothed: list[float], total_posts: list[int]) -> tuple[float, float, float]:
    """Annualised trend over the last MOMENTUM_WINDOW_MONTHS.

    OLS of ln(smoothed + eps) on the month index -> slope b and its standard error.
    Returns (r, r_low, r_high) where r = e^(12b) - 1 and the interval uses INTERVAL_Z.
    eps = 0.5 / total_posts for each month, so zero months don't break the log.
    """
    raise NotImplementedError("lane A")


def volatility(smoothed: list[float]) -> float:
    """Std dev of month-on-month log change over VOLATILITY_WINDOW_MONTHS, times sqrt(12)."""
    raise NotImplementedError("lane A")


def trajectory(projected_low: float, projected_high: float) -> str:
    """'rising' if low > +TREND_THRESHOLD, 'declining' if high < -TREND_THRESHOLD, else 'stable'."""
    raise NotImplementedError("lane A")


def forecast_skill(skill_id: str, series: dict, months: list[dict], mean_exposure: float, scenario: str) -> dict:
    """Build one SkillForecast. projected = momentum - lambda_s * (exposure - mean_exposure)."""
    raise NotImplementedError("lane A")


def forecast_all(snapshot: dict, scenario: str = config.DEFAULT_SCENARIO) -> dict[str, dict]:
    """SkillForecast for every skill in the snapshot, keyed by skill_id."""
    raise NotImplementedError("lane A")
