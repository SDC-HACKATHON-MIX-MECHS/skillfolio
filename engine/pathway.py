"""Reskilling plan = portfolio rebalancing (SPEC 5.4).

Given what the user knows and a target role, pick courses one at a time: each round takes the course that
helps most per hour, applies it (the skill's level rises), and repeats while hours (and money) remain.
"Helps" means more readiness and a better match with the target role.
"""

from __future__ import annotations

import math

from engine import config, matching, portfolio


def _check_budget(value, name: str, allow_none: bool = False):
    if value is None and allow_none:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite number of at least 0, got {value!r}")
    return value


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _check_courses(courses: list[dict]) -> None:
    seen = set()
    for course in courses:
        missing = [key for key in ("course_id", "skill_id", "hours", "level_out", "cost_rm", "title", "provider", "url", "hrdc_claimable") if key not in course]
        if missing:
            raise ValueError(f"course {course.get('course_id')!r} is missing {missing}")
        cid = course["course_id"]
        if cid in seen:
            raise ValueError(f"course {cid!r} appears more than once")
        seen.add(cid)
        if not (_is_number(course["hours"]) and course["hours"] >= config.MIN_COURSE_HOURS):
            raise ValueError(f"course {cid!r} needs hours of at least {config.MIN_COURSE_HOURS}, got {course['hours']!r}")
        if not _is_number(course["cost_rm"]) or course["cost_rm"] < 0:
            raise ValueError(f"course {cid!r} needs a finite cost_rm of at least 0, got {course['cost_rm']!r}")
        level_out = course["level_out"]
        if isinstance(level_out, bool) or not isinstance(level_out, int) or level_out not in (1, 2, 3):
            raise ValueError(f"course {cid!r} must end at level 1, 2 or 3, got {level_out!r}")
        if course.get("prereq_skill_id"):
            if "prereq_level" not in course or not _is_number(course["prereq_level"]) or not 1 <= course["prereq_level"] <= 3:
                raise ValueError(f"course {cid!r} has a prerequisite skill but prereq_level is not a number from 1 to 3: {course.get('prereq_level')!r}")
    if len({type(course["course_id"]) for course in courses}) > 1:
        raise ValueError("course_id values must all be the same type (all text or all numbers): ties are broken by course_id")


def plan(user_levels: dict[str, int], target_role: dict, role_skills: list[dict], courses: list[dict], forecasts: dict[str, dict], snapshot: dict, risk_tolerance: str, hours_budget: float, *, budget_rm: float | None = None) -> dict:
    """Greedy plan within hours_budget (and budget_rm when given).

    Each round, among courses that teach a gap skill of the target role, raise it above the user's current
    level, have a series in the snapshot, fit the remaining hours (and RM) and have their prerequisite met by
    the CURRENT levels, pick the highest (readiness gain + PATHWAY_MATCH_BETA * match gain) / hours. Exact ties go
    to the lower cost, then the smaller course_id. Apply it, repeat. Stop when no candidate is
    left or the best score is not above 0 (a step that does not help is not recommended).

    `user_levels` are skill levels 1..3 (a 0 means "does not have it" and is ignored; booleans are rejected); every
    skill must have a series in the snapshot and a forecast. Bad course rows raise ValueError (see _check_courses).
    Budget comparisons allow config.BUDGET_TOLERANCE so decimal hours that fit exactly are accepted. Returns {"steps": [PathwayStep...], "before": PortfolioMetrics + match_pct,
    "after": PortfolioMetrics + match_pct, "hours_used": float, "cost_used": float}.
    Only courses from `courses` (courses.csv) may appear.
    """
    _check_budget(hours_budget, "hours_budget")
    _check_budget(budget_rm, "budget_rm", allow_none=True)
    if risk_tolerance not in config.RISK_AVERSION:
        raise ValueError(f"risk_tolerance must be one of {list(config.RISK_AVERSION)}, got {risk_tolerance!r}")
    for skill_id, level in user_levels.items():
        if isinstance(level, bool):                                    # False == 0 would otherwise read as "does not have it"
            raise ValueError(f"level for {skill_id!r} must be 1, 2 or 3, got {level!r}")
    levels = {skill_id: level for skill_id, level in user_levels.items() if level != 0}
    portfolio.weights([{"skill_id": s, "level": lv} for s, lv in levels.items()])        # levels 1..3, not empty
    missing = [s for s in levels if s not in snapshot["skills"]]
    if missing:
        raise ValueError(f"skills without a series in the snapshot: {missing}")
    rows = [row for row in role_skills if row["role_id"] == target_role["role_id"]]
    if not rows:
        raise ValueError(f"role {target_role['role_id']!r} has no skills in role_skills")
    required = {row["skill_id"]: row["required_level"] for row in rows}
    _check_courses(courses)
    levels = {s: int(lv) for s, lv in levels.items()}
    needs_series = set(levels) | {c["skill_id"] for c in courses if c["skill_id"] in snapshot["skills"]}
    no_forecast = sorted(s for s in needs_series if s not in forecasts)
    if no_forecast:
        raise ValueError(f"skills without a forecast: {no_forecast}")
    beta = config.PATHWAY_MATCH_BETA
    tol = config.BUDGET_TOLERANCE
    cache: dict[tuple, tuple[dict, float]] = {}

    def evaluate(state: dict[str, int]) -> tuple[dict, float]:
        key = tuple(sorted(state.items()))                    # skill-id order: the output must not depend on how the caller ordered user_levels
        if key not in cache:
            weights = portfolio.weights([{"skill_id": s, "level": lv} for s, lv in key])
            metrics = portfolio.metrics(weights, forecasts, portfolio.covariance(snapshot, list(weights)), risk_tolerance)
            match = matching.match_role(target_role, role_skills, state, forecasts, [], snapshot["snapshot_date"])["match_pct"]
            cache[key] = (metrics, match)
        return cache[key]

    before_metrics, before_match = evaluate(levels)
    steps, hours_used, cost_used = [], 0.0, 0.0
    while True:
        now_metrics, now_match = evaluate(levels)
        best = None
        for course in courses:
            skill = course["skill_id"]
            if skill not in snapshot["skills"] or skill not in required:
                continue
            current = levels.get(skill, 0)
            if current >= required[skill] or course["level_out"] <= current:
                continue
            if course["hours"] > hours_budget - hours_used + tol:          # tolerance: 0.9h + 0.8h fits 1.7h
                continue
            if budget_rm is not None and course["cost_rm"] > budget_rm - cost_used + tol:
                continue
            if course.get("prereq_skill_id") and levels.get(course["prereq_skill_id"], 0) < course["prereq_level"]:
                continue
            new_metrics, new_match = evaluate({**levels, skill: course["level_out"]})
            gain = ((new_metrics["readiness"] - now_metrics["readiness"]) + beta * (new_match - now_match)) / course["hours"]
            rank = (-gain, course["cost_rm"], course["course_id"])
            if best is None or rank < best[0]:
                best = (rank, course, gain, current)
        if best is None or best[2] <= 0:
            break
        _, course, gain, current = best
        levels[course["skill_id"]] = course["level_out"]
        hours_used += course["hours"]
        cost_used += course["cost_rm"]
        steps.append({
            "order": len(steps) + 1,
            "course_id": course["course_id"],
            "title": course["title"],
            "provider": course["provider"],
            "skill_id": course["skill_id"],
            "level_before": current,
            "level_out": course["level_out"],
            "hours": course["hours"],
            "cost_rm": course["cost_rm"],
            "url": course["url"],
            "hrdc_claimable": course["hrdc_claimable"],
            "gain_per_hour": gain,
            "cumulative_hours": hours_used,
            "cumulative_cost_rm": cost_used,
        })
    after_metrics, after_match = evaluate(levels)
    return {
        "steps": steps,
        "before": {**before_metrics, "match_pct": before_match},
        "after": {**after_metrics, "match_pct": after_match},
        "hours_used": hours_used,
        "cost_used": cost_used,
    }
