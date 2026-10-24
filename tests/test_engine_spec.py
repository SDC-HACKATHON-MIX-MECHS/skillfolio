"""Acceptance tests for the engine (SPEC 5)."""

import json

import pytest

from engine import forecast, matching, pathway, portfolio, sdg
from engine.data import EXAMPLE_SNAPSHOT



@pytest.fixture
def example():
    return json.loads(EXAMPLE_SNAPSHOT.read_text(encoding="utf-8"))


def test_smooth_uses_trailing_mean():
    assert forecast.smooth([1, 2, 3, 4], window=3) == pytest.approx([1, 1.5, 2, 3])


def test_demand_index_rebases_to_100():
    assert forecast.demand_index([2, 4, 1]) == pytest.approx([100, 200, 50])


def test_momentum_sign_follows_trend(example):
    totals = [m["total_posts"] for m in example["months"]]
    for skill, expected in [("rising_skill", 1), ("falling_skill", -1)]:
        r, low, high = forecast.momentum(forecast.smooth(example["skills"][skill]["shares"]), totals)
        assert r * expected > 0 and low <= r <= high
    r, _, _ = forecast.momentum(forecast.smooth(example["skills"]["flat_skill"]["shares"]), totals)
    assert r == pytest.approx(0, abs=1e-9)


def test_trajectory_labels():
    assert forecast.trajectory(0.06, 0.20) == "rising"
    assert forecast.trajectory(-0.30, -0.06) == "declining"
    assert forecast.trajectory(-0.10, 0.10) == "stable"
    # the whole interval must clear the 5% threshold, not just its midpoint
    assert forecast.trajectory(0.03, 0.20) == "stable"
    assert forecast.trajectory(-0.20, -0.03) == "stable"
    # strictly beyond the threshold: exactly 5% is still stable
    assert forecast.trajectory(0.05, 0.20) == "stable"
    assert forecast.trajectory(-0.20, -0.05) == "stable"


def test_volatility_is_zero_for_a_flat_series(example):
    flat = forecast.smooth(example["skills"]["flat_skill"]["shares"])
    rising = forecast.smooth(example["skills"]["rising_skill"]["shares"])
    eps = forecast.epsilon([m["total_posts"] for m in example["months"]])
    assert forecast.volatility(flat, eps) == pytest.approx(0, abs=1e-12)
    assert forecast.volatility(rising, eps) > 0


def test_fast_scenario_penalises_exposed_skills(example):
    moderate = forecast.forecast_all(example, "moderate")
    fast = forecast.forecast_all(example, "fast")
    # falling_skill has the highest exposure (0.7), rising_skill the lowest (0.2)
    assert fast["falling_skill"]["projected"] < moderate["falling_skill"]["projected"]
    assert fast["rising_skill"]["projected"] > moderate["rising_skill"]["projected"]
    assert all(f["is_estimate"] for f in fast.values())


def test_thin_data_flag_and_missing_exposure(example):
    snap = json.loads(json.dumps(example))
    snap["skills"]["rare_skill"] = {
        "counts": [1, 0, 2, 1, 0, 1], "shares": [0.005, 0.0, 0.01, 0.005, 0.0, 0.005],
        "exposure": None, "exposure_n_occupations": 0, "exposure_method": None,
    }
    moderate = forecast.forecast_all(snap, "moderate")
    fast = forecast.forecast_all(snap, "fast")
    assert moderate["rare_skill"]["thin_data"] is True
    assert moderate["flat_skill"]["thin_data"] is False
    # unknown exposure: no scenario shift for that skill...
    assert fast["rare_skill"]["exposure"] is None
    assert fast["rare_skill"]["projected"] == pytest.approx(moderate["rare_skill"]["projected"])
    # ...and it must not drag the average exposure used for every other skill
    assert fast["falling_skill"]["projected"] == pytest.approx(forecast.forecast_all(example, "fast")["falling_skill"]["projected"])


# The golden numbers for the example snapshot moved to tests/fixtures/golden_example.json and are checked
# in tests/test_forecast_golden.py (test_golden_example_snapshot), next to the other independent goldens.


def _snapshot(totals, skills):
    return {"months": [{"month": f"m{i}", "total_posts": t} for i, t in enumerate(totals)], "skills": skills}


def test_zero_post_skill_shows_no_trend_when_threads_shrink():
    totals = [400 - 8 * i for i in range(25)]  # monthly threads shrink 400 -> 208
    # exposures far from the average, so the fast scenario shifts "never" by more than the 5% threshold
    snap = _snapshot(totals, {
        "never": {"counts": [0] * 25, "shares": [0.0] * 25, "exposure": 0.9},
        "steady": {"counts": [20] * 25, "shares": [20 / t for t in totals], "exposure": 0.1},
    })
    for scenario in ("moderate", "fast"):
        f = forecast.forecast_all(snap, scenario)["never"]
        assert f["momentum"] == pytest.approx(0, abs=1e-9)
        assert f["volatility"] == pytest.approx(0, abs=1e-9)
        assert f["trajectory"] == "stable" and f["thin_data"] is True


@pytest.mark.parametrize("n_months", [1, 2])
def test_short_history_is_stable_and_flagged(n_months):
    snap = _snapshot([200] * n_months, {
        "exposed": {"counts": [40] * n_months, "shares": [0.2] * n_months, "exposure": 0.7},
        "sheltered": {"counts": [40] * n_months, "shares": [0.2] * n_months, "exposure": 0.2},
    })
    for f in forecast.forecast_all(snap, "fast").values():
        assert f["history_months"] == n_months
        assert f["thin_data"] is True       # too little history to trust
        assert f["trajectory"] == "stable"  # the scenario alone must not decide the label
        # no history -> placeholders: no trend, and no scenario shift either
        for key in ("momentum", "momentum_low", "momentum_high", "projected", "projected_low", "projected_high"):
            assert f[key] == 0.0, key


def test_empty_series_does_not_crash():
    f = forecast.forecast_all(_snapshot([], {"x": {"counts": [], "shares": [], "exposure": 0}}), "moderate")["x"]
    assert f["history_months"] == 0 and f["thin_data"] is True and f["trajectory"] == "stable"
    assert f["index"] == [] and isinstance(f["exposure"], float)


def test_thin_data_cutoff_is_a_mean_below_3_posts_per_month(example):
    exactly_3 = {"counts": [6, 0, 6, 0, 6, 0], "shares": [0.03, 0.0, 0.03, 0.0, 0.03, 0.0], "exposure": 0.4}
    just_under = {"counts": [3, 3, 3, 3, 3, 2], "shares": [0.015] * 5 + [0.01], "exposure": 0.4}
    out = forecast.forecast_all({"months": example["months"], "skills": {"a": exactly_3, "b": just_under}}, "moderate")
    assert out["a"]["thin_data"] is False  # mean 3.0 is enough, even with empty months
    assert out["b"]["thin_data"] is True   # mean 2.83


def test_forecast_skill_rejects_unknown_scenario(example):
    no_exposure = dict(example["skills"]["flat_skill"], exposure=None)  # no lambda lookup needed, must still reject
    with pytest.raises(KeyError):
        forecast.forecast_skill("flat_skill", no_exposure, example["months"], 0.4, "slow")


def test_portfolio_weights_follow_levels():
    w = portfolio.weights([{"skill_id": "a", "level": 3}, {"skill_id": "b", "level": 1}])
    assert w == pytest.approx({"a": 0.75, "b": 0.25})


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


def test_skill_sdgs_baseline_plus_heavily_weighted_roles():
    roles = [{"role_id": "green", "sdgs": [7, 13]}, {"role_id": "light", "sdgs": [16]}]
    role_skills = [
        {"role_id": "green", "skill_id": "s", "weight": 3, "required_level": 2},
        {"role_id": "light", "skill_id": "s", "weight": 1, "required_level": 1},
    ]
    assert sorted(sdg.skill_sdgs("s", roles, role_skills)) == [4, 7, 13]   # weight-1 role doesn't count
    assert sdg.skill_sdgs("other", roles, role_skills) == [4]
