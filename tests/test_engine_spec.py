"""Acceptance tests for lane A (SPEC 5). Marked xfail until the engine is implemented:
once a function exists, its tests must pass for real."""

import json

import pytest

from engine import forecast, matching, pathway, portfolio, sdg
from engine.data import EXAMPLE_SNAPSHOT

todo = pytest.mark.xfail(raises=NotImplementedError, reason="lane A: not implemented yet", strict=False)


@pytest.fixture
def example():
    return json.loads(EXAMPLE_SNAPSHOT.read_text(encoding="utf-8"))


@todo
def test_smooth_uses_trailing_mean():
    assert forecast.smooth([1, 2, 3, 4], window=3) == pytest.approx([1, 1.5, 2, 3])


@todo
def test_demand_index_rebases_to_100():
    assert forecast.demand_index([2, 4, 1]) == pytest.approx([100, 200, 50])


@todo
def test_momentum_sign_follows_trend(example):
    totals = [m["total_posts"] for m in example["months"]]
    for skill, expected in [("rising_skill", 1), ("falling_skill", -1)]:
        r, low, high = forecast.momentum(forecast.smooth(example["skills"][skill]["shares"]), totals)
        assert r * expected > 0 and low <= r <= high
    r, _, _ = forecast.momentum(forecast.smooth(example["skills"]["flat_skill"]["shares"]), totals)
    assert r == pytest.approx(0, abs=1e-9)


@todo
def test_trajectory_labels():
    assert forecast.trajectory(0.06, 0.20) == "rising"
    assert forecast.trajectory(-0.30, -0.06) == "declining"
    assert forecast.trajectory(-0.10, 0.10) == "stable"
    # the whole interval must clear the 5% threshold, not just its midpoint
    assert forecast.trajectory(0.03, 0.20) == "stable"
    assert forecast.trajectory(-0.20, -0.03) == "stable"


@todo
def test_volatility_is_zero_for_a_flat_series(example):
    flat = forecast.smooth(example["skills"]["flat_skill"]["shares"])
    rising = forecast.smooth(example["skills"]["rising_skill"]["shares"])
    assert forecast.volatility(flat) == pytest.approx(0, abs=1e-12)
    assert forecast.volatility(rising) > 0


@todo
def test_fast_scenario_penalises_exposed_skills(example):
    moderate = forecast.forecast_all(example, "moderate")
    fast = forecast.forecast_all(example, "fast")
    # falling_skill has the highest exposure (0.7), rising_skill the lowest (0.2)
    assert fast["falling_skill"]["projected"] < moderate["falling_skill"]["projected"]
    assert fast["rising_skill"]["projected"] > moderate["rising_skill"]["projected"]
    assert all(f["is_estimate"] for f in fast.values())


@todo
def test_portfolio_weights_follow_levels():
    w = portfolio.weights([{"skill_id": "a", "level": 3}, {"skill_id": "b", "level": 1}])
    assert w == pytest.approx({"a": 0.75, "b": 0.25})


@todo
def test_match_pct_formula():
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": [9]}
    role_skills = [
        {"role_id": "r", "skill_id": "x", "weight": 3, "required_level": 2},
        {"role_id": "r", "skill_id": "y", "weight": 1, "required_level": 1},
    ]
    forecasts = {"x": {"projected": 0.1}, "y": {"projected": 0.0}}
    m = matching.match_role(role, role_skills, {"x": 1}, forecasts, [9], "2026-01-01")
    assert m["match_pct"] == pytest.approx((3 * 0.5 + 0) / 4)
    assert [g["skill_id"] for g in m["gaps"]] == ["x", "y"]
    assert m["citations"], "every match must cite its sources"


@todo
def test_match_caps_credit_and_builds_rank_score():
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": [9]}
    role_skills = [
        {"role_id": "r", "skill_id": "x", "weight": 3, "required_level": 2},
        {"role_id": "r", "skill_id": "y", "weight": 1, "required_level": 1},
    ]
    forecasts = {"x": {"projected": 0.1}, "y": {"projected": 0.0}}
    m = matching.match_role(role, role_skills, {"x": 3}, forecasts, [9], "2026-01-01")
    assert m["match_pct"] == pytest.approx(3 / 4)            # level 3 vs required 2 earns full credit, not more
    assert m["role_growth"] == pytest.approx(0.75 * 0.1)     # importance-weighted projected growth
    assert m["sdg_overlap"] == pytest.approx(1.0)
    assert m["rank_score"] == pytest.approx(0.75 * 1.075 * 1.15)


@todo
def test_plan_stays_in_budget_and_catalogue(example):
    from engine.data import ROOT
    import csv

    with open(ROOT / "contracts" / "examples" / "courses.example.csv", encoding="utf-8") as f:
        courses = [dict(r, level_out=int(r["level_out"]), hours=float(r["hours"]), cost_rm=float(r["cost_rm"]),
                        prereq_level=int(r["prereq_level"]) if r["prereq_level"] else None) for r in csv.DictReader(f)]
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": [9]}
    role_skills = [{"role_id": "r", "skill_id": "rising_skill", "weight": 3, "required_level": 3}]
    forecasts = forecast.forecast_all(example, "moderate")
    result = pathway.plan({"flat_skill": 2}, role, role_skills, courses, forecasts, example, "medium", hours_budget=15)
    assert result["hours_used"] <= 15
    assert {s["course_id"] for s in result["steps"]} <= {c["course_id"] for c in courses}
    # course 1 (10 h) fits and closes part of the gap; course 2 needs 20 h and course 1 first
    assert [s["course_id"] for s in result["steps"]] == ["example_course_1"]
    assert result["after"]["match_pct"] > result["before"]["match_pct"]


@todo
def test_skill_sdgs_baseline_plus_heavily_weighted_roles():
    roles = [{"role_id": "green", "sdgs": [7, 13]}, {"role_id": "light", "sdgs": [16]}]
    role_skills = [
        {"role_id": "green", "skill_id": "s", "weight": 3, "required_level": 2},
        {"role_id": "light", "skill_id": "s", "weight": 1, "required_level": 1},
    ]
    assert sorted(sdg.skill_sdgs("s", roles, role_skills)) == [4, 7, 13]   # weight-1 role doesn't count
    assert sdg.skill_sdgs("other", roles, role_skills) == [4]
