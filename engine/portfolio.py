"""Portfolio metrics for a set of skills (SPEC 5.2). Lane A."""

from __future__ import annotations


def weights(skills: list[dict]) -> dict[str, float]:
    """[{skill_id, level}] -> {skill_id: level / sum(levels)}."""
    raise NotImplementedError("lane A")


def covariance(snapshot: dict, skill_ids: list[str]) -> list[list[float]]:
    """Annualised covariance of monthly changes in ln(smoothed share + eps), shrunk toward the diagonal.

    Same epsilon (forecast.epsilon) and 24-month window as forecast.volatility (SPEC 5.1/5.2), so a
    one-skill portfolio has volatility equal to that skill's volatility.
    """
    raise NotImplementedError("lane A")


def metrics(skill_weights: dict[str, float], forecasts: dict[str, dict], cov: list[list[float]], risk_tolerance: str) -> dict:
    """PortfolioMetrics: growth, ai_exposure, volatility, diversification, readiness."""
    raise NotImplementedError("lane A")
