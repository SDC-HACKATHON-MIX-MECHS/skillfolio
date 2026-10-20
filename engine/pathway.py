"""Reskilling plan = portfolio rebalancing (SPEC 5.4). Lane A."""

from __future__ import annotations


def plan(user_levels: dict[str, int], target_role: dict, role_skills: list[dict], courses: list[dict], forecasts: dict[str, dict], snapshot: dict, risk_tolerance: str, hours_budget: float) -> dict:
    """Greedy plan within hours_budget.

    Each round: among courses that teach a gap skill of the target role, fit the
    remaining hours and have their prerequisite met, pick the highest
    (readiness gain + PATHWAY_MATCH_BETA * match gain) / hours. Apply it, repeat.

    Returns {"steps": [PathwayStep...], "before": PortfolioMetrics + match_pct,
             "after": PortfolioMetrics + match_pct, "hours_used": float}.
    Only courses from courses.csv may appear.
    """
    raise NotImplementedError("lane A")
