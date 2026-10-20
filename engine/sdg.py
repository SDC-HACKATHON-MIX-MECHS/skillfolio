"""SDG lens (SPEC 5.5). Lane A, with SDG data from lane D.

Every skill supports SDG 4 (decent jobs through relevant skills) and inherits the SDGs of each role that
leans on it. A portfolio's impact allocation says which SDGs its skills are linked to, as shares that sum to 1.
"""

from __future__ import annotations

import math

from engine import config


def skill_sdgs(skill_id: str, roles: list[dict], role_skills: list[dict]) -> list[int]:
    """BASELINE_SKILL_SDG plus the SDGs of every role that weights this skill >= ROLE_SDG_MIN_WEIGHT.

    Origin roles count too. Rows that name a role missing from `roles` are ignored. The baseline comes
    first, then the other SDGs in ascending order, each once.
    """
    by_role = {role["role_id"]: role["sdgs"] for role in roles}
    found = {
        sdg
        for row in role_skills
        if row["skill_id"] == skill_id and row["weight"] >= config.ROLE_SDG_MIN_WEIGHT and row["role_id"] in by_role
        for sdg in by_role[row["role_id"]]
    }
    return [config.BASELINE_SKILL_SDG] + sorted(found - {config.BASELINE_SKILL_SDG})


def impact_allocation(skill_weights: dict[str, float], roles: list[dict], role_skills: list[dict]) -> dict[int, float]:
    """Share of portfolio weight linked to each SDG (for the donut chart); the shares sum to 1.

    A skill's weight is split equally across that skill's SDGs and each SDG adds up the pieces it
    receives. Because every skill carries SDG 4, SDG 4 is always one of the larger slices. The result is
    ordered by share (high to low), then SDG number. Skills with weight 0 add nothing. The weights must be
    non-negative numbers (not bools) that sum to 1 (NaN fails the non-negative test, and an infinite weight
    fails the sum test).
    """
    weights = list(skill_weights.values())
    if any(isinstance(w, bool) for w in weights) or not all(w >= 0 for w in weights) or abs(sum(weights) - 1) > 1e-9:       # an empty portfolio sums to 0, so it fails too
        raise ValueError("weights must be non-negative and sum to 1 (and not empty)")
    pieces: dict[int, list[float]] = {}
    for skill_id, weight in skill_weights.items():
        if weight == 0:
            continue                       # a skill with no weight links to nothing, so it adds no (empty) slices
        sdgs = skill_sdgs(skill_id, roles, role_skills)
        for sdg in sdgs:
            pieces.setdefault(sdg, []).append(weight / len(sdgs))
    shares = {sdg: math.fsum(parts) for sdg, parts in pieces.items()}   # exact sums: row order cannot change a tie
    return dict(sorted(shares.items(), key=lambda item: (-item[1], item[0])))
