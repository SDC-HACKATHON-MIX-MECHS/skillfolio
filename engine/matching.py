"""Role matching and ranking (SPEC 5.3). Lane A.

A role is a bundle of skills, each with an importance weight and a required level. The match is how much
of that bundle the user covers; the rank score also rewards roles built from growing skills and roles that
share the user's SDGs. Every match returns its working (contributions, gaps, citations), so the UI never
has to show a black box.
"""

from __future__ import annotations

import math

from engine import config

_ROLE_SKILL_SOURCES = {"onet_in_demand": "onet_tech", "onet_hot": "onet_tech"}  # role_skills.csv flags -> snapshot source ids


def _validate(rows: list[dict], user_levels: dict[str, int]) -> None:
    seen = set()
    for row in rows:
        if row["skill_id"] in seen:
            raise ValueError(f"role {row['role_id']!r} lists skill {row['skill_id']!r} more than once")
        seen.add(row["skill_id"])
        if any(isinstance(row[k], bool) or row[k] not in (1, 2, 3) for k in ("weight", "required_level")):
            raise ValueError(f"weight and required_level must be 1, 2 or 3 ({row['role_id']!r}/{row['skill_id']!r})")
    for skill_id, level in user_levels.items():
        if isinstance(level, bool) or level not in (0, 1, 2, 3):
            raise ValueError(f"level for {skill_id!r} must be 0, 1, 2 or 3, got {level!r}")


def _citations(role: dict, rows: list[dict], snapshot_date: str) -> list[dict]:
    ids = ["hn_whoishiring", role.get("exposure_source") or "aei_job_exposure"]
    ids += [_ROLE_SKILL_SOURCES.get(row.get("source"), row.get("source")) for row in rows]
    unique = list(dict.fromkeys(i for i in ids if i))
    return [{"source_id": i, "snapshot_date": snapshot_date} for i in unique]


def match_role(role: dict, role_skills: list[dict], user_levels: dict[str, int], forecasts: dict[str, dict], user_sdgs: list[int], snapshot_date: str) -> dict:
    """One Match dict: match_pct, role_growth, ai_exposure, sdg_overlap, rank_score,
    contributions, gaps, sdgs, citations (shape in contracts/README.md).

    Uses the rows of `role_skills` that belong to this role. A role without skills cannot be scored (ValueError).
    Role growth averages the skills' `projected` growth by importance, with a thin-data skill counting for at
    most +/-THIN_GROWTH_CAP (as in the portfolio) and a skill without a forecast counting as 0.
    """
    rows = [r for r in role_skills if r["role_id"] == role["role_id"]]
    if not rows:
        raise ValueError(f"role {role['role_id']!r} has no skills in role_skills")
    _validate(rows, user_levels)
    total_weight = sum(r["weight"] for r in rows)
    cap = config.THIN_GROWTH_CAP
    match_terms, growth_terms = [], []     # summed with fsum, so the result does not depend on the row order
    contributions, gaps = [], []
    for row in rows:
        level = user_levels.get(row["skill_id"], 0)
        credit = min(level / row["required_level"], 1.0)
        match_terms.append(row["weight"] * credit / total_weight)
        forecast = forecasts.get(row["skill_id"])
        if forecast is not None:
            projected = forecast["projected"]
            if not math.isfinite(projected):
                raise ValueError(f"projected growth for {row['skill_id']!r} is not a finite number")
            if forecast.get("thin_data", False):
                projected = max(-cap, min(cap, projected))
            growth_terms.append(row["weight"] / total_weight * projected)
        if credit > 0:
            contributions.append({"skill_id": row["skill_id"], "weight": row["weight"], "user_level": level,
                                  "required_level": row["required_level"], "credit": credit})
        if level < row["required_level"]:
            gaps.append({"skill_id": row["skill_id"], "weight": row["weight"], "user_level": level,
                         "required_level": row["required_level"]})
    contributions.sort(key=lambda c: (-c["weight"], -c["credit"], c["skill_id"]))
    gaps.sort(key=lambda g: (-g["weight"], -g["required_level"], g["skill_id"]))
    match, growth = math.fsum(match_terms), math.fsum(growth_terms)
    wanted = set(user_sdgs)
    overlap = len(set(role["sdgs"]) & wanted) / max(1, len(wanted))
    return {
        "role_id": role["role_id"],
        "title": role["title"],
        "match_pct": match,
        "role_growth": growth,
        "ai_exposure": role["ai_exposure"],
        "sdg_overlap": overlap,
        "rank_score": match * (1 + growth) * (1 + config.SDG_TILT_ALPHA * overlap),
        "contributions": contributions,
        "gaps": gaps,
        "sdgs": list(role["sdgs"]),
        "citations": _citations(role, rows, snapshot_date),
    }


def rank_roles(roles: list[dict], role_skills: list[dict], user_levels: dict[str, int], forecasts: dict[str, dict], user_sdgs: list[int], snapshot_date: str) -> list[dict]:
    """Matches for every `future` role that has skills, sorted by rank_score (highest first).

    Ties go to the higher match_pct, then the smaller role_id, so the order never depends on input order
    (match and growth are summed exactly, so the same skills in another row order give the same numbers).
    Two roles with the same id are an error.
    A role with no skill rows cannot be scored and is left out rather than shown with a made-up zero.
    """
    ids = [role["role_id"] for role in roles]
    if len(set(ids)) != len(ids):
        raise ValueError("role ids must be unique")
    has_skills = {r["role_id"] for r in role_skills}
    matches = [match_role(role, role_skills, user_levels, forecasts, user_sdgs, snapshot_date)
               for role in roles if role["role_type"] == "future" and role["role_id"] in has_skills]
    matches.sort(key=lambda m: (-m["rank_score"], -m["match_pct"], m["role_id"]))
    return matches
