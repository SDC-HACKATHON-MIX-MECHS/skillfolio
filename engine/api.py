"""The app's single front door: one call returns everything a page needs.

`analyse(profile, snapshot, scenario)` runs the whole engine for one learner: skill forecasts, portfolio
metrics, the top role matches and the SDG allocation. The result is plain JSON (dicts, lists, numbers,
strings, None), so a page can show it, cache it, or `st.json` it. Pages call this and read the result
(shape in contracts/README.md, "Analysis").
"""

from __future__ import annotations

from engine import config, data, forecast, guardrails, matching, portfolio, sdg

DEFAULT_RISK = "medium"
SDG_NUMBERS = range(1, 18)          # the 17 Sustainable Development Goals
CONFIGURED = object()               # default for top_n: read config.TOP_N_ROLES when called (not when defined)


def _check_profile(profile: dict) -> tuple[str, list[int]]:
    """Validate the parts of the profile the engine reads; return (risk tolerance, SDG interests)."""
    skills = profile.get("skills")
    if not isinstance(skills, list) or any(not isinstance(e, dict) or "skill_id" not in e or "level" not in e for e in skills):
        raise ValueError("profile needs a 'skills' list of {skill_id, level} entries")
    risk = profile.get("risk_tolerance", DEFAULT_RISK)
    if not isinstance(risk, str) or risk not in config.RISK_AVERSION:
        raise ValueError(f"risk_tolerance must be one of {list(config.RISK_AVERSION)}, got {risk!r}")
    interests = profile.get("sdg_interests")
    interests = [] if interests is None else interests
    if not isinstance(interests, list) or any(isinstance(n, bool) or not isinstance(n, int) or n not in SDG_NUMBERS for n in interests):
        raise ValueError(f"sdg_interests must be a list of SDG numbers 1 to 17, got {interests!r}")
    return risk, interests


def analyse(profile: dict, snapshot: dict, scenario: str = config.DEFAULT_SCENARIO, *, roles: list[dict] | None = None,
            role_skills: list[dict] | None = None, top_n: int | None | object = CONFIGURED) -> dict:
    """Score one profile on one snapshot under one AI scenario.

    Every profile skill's level must be 1..3 with no repeats. Skills the snapshot has no series for are then
    dropped (logged by the guardrail and listed in `dropped_skills`) and the weights renormalised over the
    rest; if none is left that is an error. A malformed profile, an unknown `risk_tolerance`, SDG interests
    that are not numbers 1..17, a snapshot without `snapshot_date` and an unknown scenario are errors too.
    `risk_tolerance` defaults to "medium" and `sdg_interests` to none. `roles` and `role_skills` default to
    data/roles.csv and data/role_skills.csv. `matches` holds the best `top_n` roles (default config.TOP_N_ROLES; None = all of them).
    When nothing can be matched, `matches` is empty and `warnings` says why instead of showing made-up matches.
    """
    if scenario not in config.SCENARIOS:
        raise KeyError(f"unknown scenario {scenario!r}; expected one of {list(config.SCENARIOS)}")
    if "snapshot_date" not in snapshot:
        raise ValueError("snapshot has no snapshot_date")
    risk, interests = _check_profile(profile)
    roles = data.load_roles() if roles is None else roles
    role_skills = data.load_role_skills() if role_skills is None else role_skills

    portfolio.weights(profile["skills"])                       # checks levels and repeats for every entry, dropped or not
    known = set(snapshot["skills"])
    kept = guardrails.keep_known(profile["skills"], "skill_id", known)
    dropped = [entry["skill_id"] for entry in profile["skills"] if entry["skill_id"] not in known]
    if not kept:
        raise ValueError(f"none of the profile's skills is in the snapshot (dropped: {dropped})")
    weights = portfolio.weights(kept)
    levels = {entry["skill_id"]: int(entry["level"]) for entry in kept}

    forecasts = forecast.forecast_all(snapshot, scenario)
    cov = portfolio.covariance(snapshot, list(weights))
    metrics = portfolio.metrics(weights, forecasts, cov, risk)

    warnings = []
    matches = matching.rank_roles(roles, role_skills, levels, forecasts, interests, snapshot["snapshot_date"])
    if not role_skills:
        warnings.append("role_skills has no rows, so roles cannot be matched yet")
    elif not matches:
        warnings.append("no future role has skills listed in role_skills, so nothing can be matched")
    top_n = config.TOP_N_ROLES if top_n is CONFIGURED else top_n
    matches = matches if top_n is None else matches[:top_n]
    allocation = sdg.impact_allocation(weights, roles, role_skills)

    return {
        "profile_id": profile.get("profile_id"),
        "scenario": scenario,
        "snapshot_date": snapshot["snapshot_date"],
        "skills": [
            {
                "skill_id": skill_id,
                "level": levels[skill_id],
                "weight": weight,
                "projected": forecasts[skill_id]["projected"],
                "thin_data": forecasts[skill_id]["thin_data"],
                "exposure": forecasts[skill_id]["exposure"],
                "sdgs": sdg.skill_sdgs(skill_id, roles, role_skills),
            }
            for skill_id, weight in weights.items()
        ],
        "dropped_skills": dropped,
        "portfolio": metrics,
        "matches": matches,
        "sdg_allocation": [{"sdg": number, "share": share} for number, share in allocation.items()],
        "forecasts": forecasts,
        "warnings": warnings,
    }
