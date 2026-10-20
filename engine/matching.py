"""Role matching and ranking (SPEC 5.3). Lane A."""

from __future__ import annotations


def match_role(role: dict, role_skills: list[dict], user_levels: dict[str, int], forecasts: dict[str, dict], user_sdgs: list[int], snapshot_date: str) -> dict:
    """One Match dict: match_pct, role_growth, ai_exposure, sdg_overlap, rank_score,
    contributions, gaps, sdgs, citations (shape in contracts/README.md)."""
    raise NotImplementedError("lane A")


def rank_roles(roles: list[dict], role_skills: list[dict], user_levels: dict[str, int], forecasts: dict[str, dict], user_sdgs: list[int], snapshot_date: str) -> list[dict]:
    """Matches for every `future` role, sorted by rank_score (highest first)."""
    raise NotImplementedError("lane A")
