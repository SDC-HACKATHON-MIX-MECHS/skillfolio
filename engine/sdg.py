"""SDG lens (SPEC 5.5). Lane A, with SDG data from lane D."""

from __future__ import annotations


def skill_sdgs(skill_id: str, roles: list[dict], role_skills: list[dict]) -> list[int]:
    """BASELINE_SKILL_SDG plus the SDGs of every role that weights this skill >= ROLE_SDG_MIN_WEIGHT."""
    raise NotImplementedError("lane A")


def impact_allocation(skill_weights: dict[str, float], roles: list[dict], role_skills: list[dict]) -> dict[int, float]:
    """Share of portfolio weight linked to each SDG (for the donut chart)."""
    raise NotImplementedError("lane A")
