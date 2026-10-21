"""Pins engine.pathway.plan (SPEC 5.4, the greedy reskilling plan) to numbers and to its documented behaviour.

Golden values in tests/fixtures/golden_pathway.json come from tests/fixtures/independent_pathway.py, which does not
import the engine. Roles, courses and the snapshot are illustrative fixtures (snapshot_30m + independent_matching roles).
"""

import copy
import json
from pathlib import Path

import pytest

from engine import config, forecast, pathway

FIXTURES = Path(__file__).parent / "fixtures"
GOLD = json.loads((FIXTURES / "golden_pathway.json").read_text(encoding="utf-8"))
MATCHING = json.loads((FIXTURES / "golden_matching.json").read_text(encoding="utf-8"))
SNAP = json.loads((FIXTURES / "snapshot_30m.json").read_text(encoding="utf-8"))
ROLES = {r["role_id"]: r for r in MATCHING["roles"]}
ROLE_SKILLS = MATCHING["role_skills"]
COURSES = GOLD["courses"]
CASES = list(GOLD["cases"].items())
STEP_KEYS = {"order", "course_id", "title", "provider", "skill_id", "level_before", "level_out", "hours", "cost_rm", "url",
             "hrdc_claimable", "gain_per_hour", "cumulative_hours", "cumulative_cost_rm"}
METRIC_KEYS = {"growth", "ai_exposure", "volatility", "diversification", "readiness", "match_pct"}


def run(case, courses=None, **overrides):
    i = case["input"]
    scenario_forecasts = forecast.forecast_all(SNAP, i["scenario"])
    kwargs = dict(budget_rm=i["rm"])
    kwargs.update(overrides)
    pool = [c for c in (courses if courses is not None else COURSES) if not i.get("only") or c["course_id"] in i["only"]]
    return pathway.plan(i["levels"], ROLES[i["target"]], ROLE_SKILLS, pool, scenario_forecasts, SNAP, i["risk"], i["hours"], **kwargs)


def close(actual, expected, label):
    if expected is None:
        assert actual is None, label
    else:
        assert actual == pytest.approx(expected, rel=1e-7, abs=1e-9), label


def test_the_golden_beta_is_the_configured_one():
    assert GOLD["beta"] == config.PATHWAY_MATCH_BETA


@pytest.mark.parametrize("name,case", CASES)
def test_the_plan_matches_the_independent_numbers(name, case):
    out, expected = run(case), case["plan"]
    assert set(out) == {"steps", "before", "after", "hours_used", "cost_used"}
    assert [s["course_id"] for s in out["steps"]] == [s["course_id"] for s in expected["steps"]], name
    for actual, want in zip(out["steps"], expected["steps"]):
        assert set(actual) == STEP_KEYS
        for key in ("order", "skill_id", "level_before", "level_out", "hours", "cost_rm", "title", "provider", "url", "hrdc_claimable"):
            assert actual[key] == want[key], f"{name}/{want['course_id']}.{key}"
        for key in ("gain_per_hour", "cumulative_hours", "cumulative_cost_rm"):
            close(actual[key], want[key], f"{name}/{want['course_id']}.{key}")
    for side in ("before", "after"):
        assert set(out[side]) == METRIC_KEYS
        for key, value in expected[side].items():
            close(out[side][key], value, f"{name}.{side}.{key}")
    close(out["hours_used"], expected["hours_used"], name)
    close(out["cost_used"], expected["cost_used"], name)


@pytest.mark.parametrize("name,case", CASES)
def test_the_plan_respects_the_budgets_the_catalogue_and_is_plain_json(name, case):
    out = run(case)
    i = case["input"]
    assert out["hours_used"] <= i["hours"] + 1e-9
    if i["rm"] is not None:
        assert out["cost_used"] <= i["rm"] + 1e-9
    assert {s["course_id"] for s in out["steps"]} <= {c["course_id"] for c in COURSES}
    assert [s["order"] for s in out["steps"]] == list(range(1, len(out["steps"]) + 1))
    assert all(s["gain_per_hour"] > 0 for s in out["steps"])
    assert json.loads(json.dumps(out)) == out
    if not out["steps"]:
        assert out["before"] == out["after"] and out["hours_used"] == 0 and out["cost_used"] == 0


def test_a_course_is_only_taken_if_it_helps_the_target_role_and_the_snapshot_can_score_it():
    out = run(GOLD["cases"]["ops_plenty_of_hours"])
    taken = {s["course_id"] for s in out["steps"]}
    assert not taken & {"c_other", "c_noisy", "c_ghost", "c_low"}      # not a gap skill / unscoreable skill / does not raise the level
    assert out["after"]["match_pct"] == pytest.approx(1.0)


def test_later_steps_see_the_levels_earlier_steps_created():
    steps = run(GOLD["cases"]["ops_plenty_of_hours"])["steps"]
    ids = [s["course_id"] for s in steps]
    assert ids.index("c_up2") < ids.index("c_up3") and ids.index("c_a_down1") < ids.index("c_down2")     # prerequisites came first
    assert [s["level_before"] for s in steps if s["skill_id"] == "shift_up"] == [1, 2]


def test_exact_ties_go_to_the_lower_cost_then_the_smaller_id_and_fewer_hours_still_wins_on_score():
    case = GOLD["cases"]["tie_break_only_two"]
    assert [s["course_id"] for s in run(case)["steps"]] == ["c_a_down1"]
    reversed_pool = list(reversed(COURSES))
    assert [s["course_id"] for s in run(case, courses=reversed_pool)["steps"]] == ["c_a_down1"]
    # same score per hour but different hours/cost: build two courses whose difference is only cost
    open_case = dict(case, input=dict(case["input"], only=None))                 # the extra courses below are not in the "only" list
    base = dict(next(c for c in COURSES if c["course_id"] == "c_down1"))
    cheap, dear = dict(base, course_id="z_cheap", cost_rm=0), dict(base, course_id="a_dear", cost_rm=10)
    assert [s["course_id"] for s in run(open_case, courses=[dear, cheap])["steps"]] == ["z_cheap"]
    longer = dict(base, course_id="a_long", hours=7)
    assert [s["course_id"] for s in run(open_case, courses=[longer, base])["steps"]] == ["c_down1"]


def test_the_budget_checks_are_inclusive():
    assert [s["course_id"] for s in run(GOLD["cases"]["exact_hours_fit"])["steps"]] == ["c_down1"]
    assert run(GOLD["cases"]["one_hour_short"])["steps"] == []
    assert [s["course_id"] for s in run(GOLD["cases"]["exact_rm_fit"])["steps"]] == ["c_unk1"]
    assert run(GOLD["cases"]["rm_one_short"])["steps"] == []
    free = run(GOLD["cases"]["exact_rm_fit"], budget_rm=None)                 # no RM limit given: cost is reported, not limited
    assert free["cost_used"] == 50


def test_a_prerequisite_on_another_skill_needs_that_skills_current_level():
    assert run(GOLD["cases"]["prereq_on_other_skill_unmet"])["steps"] == []
    assert [s["course_id"] for s in run(GOLD["cases"]["prereq_on_other_skill_met"])["steps"]] == ["c_cross_prereq"]


def test_csv_style_courses_with_empty_prerequisites_work():
    as_csv = [dict(c, prereq_skill_id=c["prereq_skill_id"] or "", prereq_level=c["prereq_level"]) for c in COURSES]
    case = GOLD["cases"]["ops_plenty_of_hours"]
    assert [s["course_id"] for s in run(case, courses=as_csv)["steps"]] == [s["course_id"] for s in case["plan"]["steps"]]
    none_style = [dict(c, prereq_skill_id=None) if not c["prereq_skill_id"] else c for c in COURSES]
    assert [s["course_id"] for s in run(case, courses=none_style)["steps"]] == [s["course_id"] for s in case["plan"]["steps"]]


def test_a_step_that_does_not_help_is_not_recommended_and_zero_budget_does_nothing():
    case = GOLD["cases"]["ops_fast_medium"]                      # every available course lowers readiness more than it adds match
    out = run(case)
    assert out["steps"] == [] and out["before"] == out["after"]
    assert run(GOLD["cases"]["ops_zero_hours"])["steps"] == []
    assert run(GOLD["cases"]["nothing_to_learn"])["steps"] == []         # every gap skill is already at the required level


def test_scenario_and_risk_change_the_choice_through_the_forecasts_and_gamma():
    a = run(GOLD["cases"]["ops_tight_hours"])
    b = run(dict(GOLD["cases"]["ops_tight_hours"], input=dict(GOLD["cases"]["ops_tight_hours"]["input"], risk="high")))
    assert a["before"]["readiness"] != b["before"]["readiness"] and a["before"]["growth"] == b["before"]["growth"]


def test_inputs_are_not_changed():
    case = GOLD["cases"]["ops_plenty_of_hours"]
    before = copy.deepcopy((case, COURSES, ROLES, ROLE_SKILLS))
    run(case)
    assert (case, COURSES, ROLES, ROLE_SKILLS) == before


def _plan(levels=None, hours=50, role="r_ops", **kw):
    fc = forecast.forecast_all(SNAP, "moderate")
    return pathway.plan({"shift_up": 1} if levels is None else levels, ROLES[role], ROLE_SKILLS, kw.pop("courses", COURSES), fc, SNAP, kw.pop("risk", "low"), hours, **kw)


@pytest.mark.parametrize("hours", [-1, float("nan"), float("inf"), True, "10"])
def test_bad_hours_budgets_are_errors(hours):
    with pytest.raises(ValueError):
        _plan(hours=hours)


def test_bad_inputs_are_errors():
    with pytest.raises(ValueError):
        _plan(budget_rm=-1)
    with pytest.raises(ValueError):
        _plan(budget_rm=float("nan"))
    with pytest.raises(ValueError):
        _plan(risk="reckless")
    with pytest.raises(ValueError):
        _plan(levels={})                                          # nothing to build a portfolio from
    with pytest.raises(ValueError):
        _plan(levels={"shift_up": 5})
    with pytest.raises(ValueError):
        _plan(levels={"not_in_snapshot": 2})
    with pytest.raises(ValueError):
        _plan(role="r_empty")                                     # the role has no skills listed
    with pytest.raises(ValueError):
        _plan(courses=COURSES + [dict(COURSES[0])])               # the same course id twice


def test_level_zero_means_the_user_does_not_have_the_skill():
    assert _plan(levels={"shift_up": 1, "shift_down": 0}) == _plan(levels={"shift_up": 1})


def test_beta_comes_from_config(monkeypatch):
    base = _plan(hours=100)
    monkeypatch.setattr(config, "PATHWAY_MATCH_BETA", 0.0)
    only_readiness = _plan(hours=100)
    assert base["steps"] != only_readiness["steps"] or base["after"] != only_readiness["after"]
    monkeypatch.setattr(config, "PATHWAY_MATCH_BETA", 100.0)
    assert _plan(hours=100)["after"]["match_pct"] >= base["after"]["match_pct"]


def test_the_real_course_catalogue_works_with_the_real_snapshot():
    from engine import data
    snap = json.loads((FIXTURES / "real_snapshot_2026-10-20.json").read_text(encoding="utf-8"))
    courses = data.load_courses()
    assert len(courses) >= 50
    fc = forecast.forecast_all(snap, "moderate")
    role = {"role_id": "demo", "title": "Demo", "role_type": "future", "ai_exposure": 0.3, "sdgs": [9]}
    rows = [{"role_id": "demo", "skill_id": s, "weight": 3, "required_level": 3} for s in ("python", "sql", "excel", "statistics")]
    out = pathway.plan({"excel": 3, "sql": 2}, role, rows, courses, fc, snap, "medium", 120)
    assert out["hours_used"] <= 120 and {s["course_id"] for s in out["steps"]} <= {c["course_id"] for c in courses}
    assert json.loads(json.dumps(out)) == out
    assert all(s["url"].startswith("http") for s in out["steps"])


@pytest.mark.parametrize("change", [dict(hours=0), dict(hours=-3), dict(hours=float("nan")), dict(hours=float("inf")), dict(hours="6"),
                                    dict(level_out=0), dict(level_out=4), dict(level_out=None)])
def test_malformed_courses_are_errors(change):
    field = "level_out" if "level_out" in change else "hours"
    other = next(c for c in COURSES if c["course_id"] == "c_other")            # not a gap skill: only validation can catch it
    bad = dict(other, **{field: change[field]})
    with pytest.raises(ValueError):
        _plan(courses=[c for c in COURSES if c is not other] + [bad])


def test_float_levels_are_reported_as_ints_and_cost_is_cumulative_in_the_output():
    out = _plan(levels={"shift_up": 1.0, "u_turn": 2.0}, hours=100)
    assert out["steps"] and all(type(s["level_before"]) is int and type(s["level_out"]) is int for s in out["steps"])
    assert out["steps"][-1]["cumulative_cost_rm"] == out["cost_used"] == sum(s["cost_rm"] for s in out["steps"])
    assert out["steps"][-1]["cumulative_hours"] == out["hours_used"] == sum(s["hours"] for s in out["steps"])


def test_each_step_carries_its_courses_own_details():
    by_id = {c["course_id"]: c for c in COURSES}
    steps = run(GOLD["cases"]["ops_plenty_of_hours"])["steps"]
    assert {s["hrdc_claimable"] for s in steps} == {"yes", "unknown"}
    for s in steps:
        c = by_id[s["course_id"]]
        assert (s["title"], s["provider"], s["url"], s["hrdc_claimable"], s["hours"], s["cost_rm"]) == (c["title"], c["provider"], c["url"], c["hrdc_claimable"], c["hours"], c["cost_rm"])


def test_a_step_with_exactly_zero_gain_is_not_recommended(monkeypatch):
    monkeypatch.setattr(config, "PATHWAY_MATCH_BETA", 0.0)                                  # the match term vanishes ...
    flat = {"growth": 0.0, "ai_exposure": 0.0, "volatility": 0.0, "diversification": 0.0, "readiness": 0.0}
    monkeypatch.setattr(pathway.portfolio, "metrics", lambda *a, **k: dict(flat))        # ... and readiness never changes: gain is exactly 0
    out = _plan(hours=100)
    assert out["steps"] == [] and out["before"] == out["after"]
