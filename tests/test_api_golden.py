"""Pins engine.api.analyse (the app's single front door) to numbers and to its documented behaviour.

Golden values in tests/fixtures/golden_api.json come from tests/fixtures/independent_api.py, which does not import the
engine. Roles and role skills are the illustrative fixtures from independent_matching (snapshot_30m).
"""

import copy
import json
from pathlib import Path

import pytest

from engine import api, config, forecast

FIXTURES = Path(__file__).parent / "fixtures"
GOLD = json.loads((FIXTURES / "golden_api.json").read_text(encoding="utf-8"))
MATCHING = json.loads((FIXTURES / "golden_matching.json").read_text(encoding="utf-8"))
SNAP = json.loads((FIXTURES / "snapshot_30m.json").read_text(encoding="utf-8"))
ROLES, ROLE_SKILLS = MATCHING["roles"], MATCHING["role_skills"]
CASES = list(GOLD["cases"].items())
KEYS = {"profile_id", "scenario", "snapshot_date", "skills", "dropped_skills", "portfolio", "matches", "sdg_allocation", "forecasts", "warnings"}


def run(case):
    return api.analyse(GOLD["profiles"][case["profile"]], SNAP, case["scenario"], roles=ROLES, role_skills=ROLE_SKILLS)


def call(profile, scenario="moderate", role_skills=ROLE_SKILLS):
    return api.analyse(profile, SNAP, scenario, roles=ROLES, role_skills=role_skills)


def close(actual, expected, label):
    if expected is None:
        assert actual is None, label
    else:
        assert actual == pytest.approx(expected, rel=1e-7, abs=1e-9), label


def test_the_golden_top_n_is_the_configured_one():
    assert GOLD["top_n"] == config.TOP_N_ROLES


@pytest.mark.parametrize("name,case", CASES)
def test_everything_matches_the_independent_numbers(name, case):
    out = run(case)
    assert set(out) == KEYS
    assert out["scenario"] == case["scenario"] and out["snapshot_date"] == SNAP["snapshot_date"]
    assert out["profile_id"] == GOLD["profiles"][case["profile"]]["profile_id"]
    assert out["dropped_skills"] == case["dropped"]
    assert [s["skill_id"] for s in out["skills"]] == [s["skill_id"] for s in case["skills"]]
    for actual, expected in zip(out["skills"], case["skills"]):
        assert set(actual) == {"skill_id", "level", "weight", "projected", "thin_data", "exposure", "sdgs"}
        for key in ("level", "thin_data", "sdgs"):
            assert actual[key] == expected[key], f"{name}/{expected['skill_id']}.{key}"
        for key in ("weight", "projected", "exposure"):
            close(actual[key], expected[key], f"{name}/{expected['skill_id']}.{key}")
    assert set(out["portfolio"]) == set(case["portfolio"])
    for key, value in case["portfolio"].items():
        close(out["portfolio"][key], value, f"{name}.portfolio.{key}")
    assert [r["sdg"] for r in out["sdg_allocation"]] == [s for s, _ in case["sdg"]]
    assert [r["share"] for r in out["sdg_allocation"]] == pytest.approx([v for _, v in case["sdg"]], rel=1e-9)
    assert [m["role_id"] for m in out["matches"]] == case["match_ids"]
    for m in out["matches"]:
        expected = case["matches"][m["role_id"]]
        for key in ("match_pct", "role_growth", "sdg_overlap", "rank_score"):
            close(m[key], expected[key], f"{name}/{m['role_id']}.{key}")
        for key in ("contributions", "gaps"):
            assert [c["skill_id"] for c in m[key]] == [c["skill_id"] for c in expected[key]]
        assert m["citations"] and m["citations"][0]["snapshot_date"] == SNAP["snapshot_date"]


@pytest.mark.parametrize("name,case", CASES)
def test_the_output_is_plain_json_and_forecasts_are_the_engines(name, case):
    out = run(case)
    assert json.loads(json.dumps(out)) == out
    assert out["forecasts"] == forecast.forecast_all(SNAP, case["scenario"])
    assert out["warnings"] == []


def test_sdg_shares_sum_to_one_and_are_ordered_and_rows_are_plain_dicts():
    out = run(GOLD["cases"]["full_profile/moderate"])
    rows = out["sdg_allocation"]
    assert sum(r["share"] for r in rows) == pytest.approx(1.0)
    assert [(-r["share"], r["sdg"]) for r in rows] == sorted((-r["share"], r["sdg"]) for r in rows)
    assert all(set(r) == {"sdg", "share"} and isinstance(r["sdg"], int) for r in rows)


def test_unknown_profile_skills_are_dropped_and_reported_not_scored(caplog):
    case = GOLD["cases"]["unknown_skill_dropped/moderate"]
    with caplog.at_level("WARNING"):
        out = run(case)
    assert out["dropped_skills"] == ["ghost_skill"]
    assert [s["skill_id"] for s in out["skills"]] == ["u_turn", "sparse"]
    assert sum(s["weight"] for s in out["skills"]) == pytest.approx(1.0)
    assert "ghost_skill" in caplog.text


def test_profiles_with_no_scorable_skill_or_a_bad_level_are_errors():
    base = dict(GOLD["profiles"]["full_profile"])
    for skills in ([], [{"skill_id": "nope", "level": 2}]):
        with pytest.raises(ValueError):
            call(dict(base, skills=skills))
    for level in (0, 4, 1.5, True):
        with pytest.raises(ValueError):
            call(dict(base, skills=[{"skill_id": "u_turn", "level": level}]))
    with pytest.raises(ValueError):
        call(dict(base, skills=[{"skill_id": "u_turn", "level": 1}, {"skill_id": "u_turn", "level": 2}]))
    with pytest.raises(ValueError):
        call(dict(base, risk_tolerance="reckless"))
    with pytest.raises(KeyError):
        call(base, "slow")


def test_missing_risk_defaults_to_medium_and_missing_sdgs_to_none():
    base = {k: v for k, v in GOLD["profiles"]["full_profile"].items() if k not in ("risk_tolerance", "sdg_interests")}
    out = call(base)
    assert out == call(dict(base, risk_tolerance="medium", sdg_interests=[]))
    assert all(m["sdg_overlap"] == 0 for m in out["matches"])
    assert out["portfolio"]["readiness"] != call(dict(base, risk_tolerance="low"))["portfolio"]["readiness"]


def test_no_role_skills_means_no_matches_and_a_warning_instead_of_garbage():
    out = call(GOLD["profiles"]["full_profile"], role_skills=[])
    assert out["matches"] == [] and len(out["warnings"]) == 1 and "role_skills" in out["warnings"][0]
    assert out["portfolio"]["growth"] != 0 and out["sdg_allocation"]


def test_top_n_comes_from_config(monkeypatch):
    case = GOLD["cases"]["full_profile/moderate"]
    monkeypatch.setattr(config, "TOP_N_ROLES", 2)
    assert [m["role_id"] for m in run(case)["matches"]] == case["match_ids"][:2]


def test_the_scenario_moves_growth_but_not_risk_diversification_or_gaps():
    a, b = (run(GOLD["cases"][f"full_profile/{s}"]) for s in ("moderate", "fast"))
    assert a["portfolio"]["growth"] != pytest.approx(b["portfolio"]["growth"])
    for key in ("volatility", "diversification", "ai_exposure"):
        assert a["portfolio"][key] == b["portfolio"][key]
    assert a["sdg_allocation"] == b["sdg_allocation"]
    by = lambda o: {m["role_id"]: m for m in o["matches"]}
    assert all(by(a)[r]["gaps"] == by(b)[r]["gaps"] for r in by(a) if r in by(b))


def test_inputs_are_not_changed():
    case = GOLD["cases"]["unknown_skill_dropped/fast"]
    before = copy.deepcopy((GOLD["profiles"], SNAP, ROLES, ROLE_SKILLS))
    run(case)
    assert (GOLD["profiles"], SNAP, ROLES, ROLE_SKILLS) == before


def test_thin_skills_are_flagged_in_the_skill_rows():
    out = run(GOLD["cases"]["unknown_skill_dropped/moderate"])
    assert {s["skill_id"]: s["thin_data"] for s in out["skills"]} == {"u_turn": False, "sparse": True}


@pytest.mark.parametrize("profile_id", ["aina", "ravi"])
@pytest.mark.parametrize("scenario", ["moderate", "fast"])
def test_the_sample_profiles_run_on_the_real_snapshot_and_repo_data(profile_id, scenario):
    from engine import data
    snapshot = json.loads((FIXTURES / "real_snapshot_2026-10-20.json").read_text(encoding="utf-8"))
    out = api.analyse(data.load_profile(profile_id), snapshot, scenario)
    assert out["dropped_skills"] == [] and len(out["skills"]) >= 5
    assert json.loads(json.dumps(out)) == out
    assert len(out["matches"]) <= config.TOP_N_ROLES
    if not data.load_role_skills():
        assert out["matches"] == [] and out["warnings"]
    assert sum(r["share"] for r in out["sdg_allocation"]) == pytest.approx(1.0)


def test_explicit_empty_roles_and_role_skills_are_respected_even_if_the_repo_has_data(monkeypatch):
    monkeypatch.setattr(api.data, "load_role_skills", lambda: ROLE_SKILLS)
    monkeypatch.setattr(api.data, "load_roles", lambda: ROLES)
    profile = GOLD["profiles"]["full_profile"]
    assert api.analyse(profile, SNAP, "moderate", roles=ROLES, role_skills=[])["matches"] == []
    assert api.analyse(profile, SNAP, "moderate", roles=[], role_skills=ROLE_SKILLS)["matches"] == []
    from_data = api.analyse(profile, SNAP, "moderate")                       # None means: read data/
    assert [m["role_id"] for m in from_data["matches"]] == GOLD["cases"]["full_profile/moderate"]["match_ids"]


def test_levels_are_reported_as_integers():
    profile = dict(GOLD["profiles"]["full_profile"], skills=[{"skill_id": "u_turn", "level": 2.0}, {"skill_id": "shift_up", "level": 1}])
    levels = [s["level"] for s in call(profile)["skills"]]
    assert levels == [2, 1] and all(type(v) is int for v in levels)



def test_a_fresh_snapshot_and_profile_are_not_changed_by_a_call():
    snap = json.loads((FIXTURES / "snapshot_30m.json").read_text(encoding="utf-8"))      # fresh copies, so earlier tests cannot hide a change
    profile = copy.deepcopy(GOLD["profiles"]["unknown_skill_dropped"])
    roles, rows = copy.deepcopy(ROLES), copy.deepcopy(ROLE_SKILLS)
    api.analyse(profile, snap, "fast", roles=roles, role_skills=rows)
    assert snap == json.loads((FIXTURES / "snapshot_30m.json").read_text(encoding="utf-8"))
    assert (profile, roles, rows) == (GOLD["profiles"]["unknown_skill_dropped"], ROLES, ROLE_SKILLS)


def test_many_sdg_interests_all_count():
    profile = dict(GOLD["profiles"]["full_profile"], sdg_interests=[9, 8, 10, 7, 13])
    by = {m["role_id"]: m for m in call(profile)["matches"]}
    assert by["r_data"]["sdg_overlap"] == pytest.approx(2 / 5)          # SDGs 9 and 8 of the five
    assert call(dict(profile, sdg_interests=[9, 8, 10, 7, 13, 9]))["matches"][0]["sdg_overlap"] == by[call(profile)["matches"][0]["role_id"]]["sdg_overlap"]


@pytest.mark.parametrize("bad", [["8", "13"], "8", [8, True], [0], [18], [8.0], {8}, 8])
def test_sdg_interests_must_be_a_list_of_goal_numbers(bad):
    with pytest.raises(ValueError):
        call(dict(GOLD["profiles"]["full_profile"], sdg_interests=bad))


def test_none_means_no_interests_and_all_17_goals_are_valid():
    base = GOLD["profiles"]["full_profile"]
    assert call(dict(base, sdg_interests=None)) == call(dict(base, sdg_interests=[]))
    call(dict(base, sdg_interests=list(range(1, 18))))


@pytest.mark.parametrize("profile", [
    {"risk_tolerance": "low"},                                                    # no skills key
    {"skills": None}, {"skills": "u_turn"}, {"skills": [None]}, {"skills": ["u_turn"]},
    {"skills": [{"skill_id": "u_turn"}]}, {"skills": [{"level": 2}]},
])
def test_malformed_profiles_get_a_clear_value_error(profile):
    with pytest.raises(ValueError, match="skills"):
        call(profile)


def test_risk_must_be_a_known_string():
    base = GOLD["profiles"]["full_profile"]
    for bad in (None, ["low"], 3, "LOW"):
        with pytest.raises(ValueError, match="risk_tolerance"):
            call(dict(base, risk_tolerance=bad))


def test_a_snapshot_without_a_date_is_an_error_even_with_no_role_skills():
    snap = {k: v for k, v in SNAP.items() if k != "snapshot_date"}
    with pytest.raises(ValueError, match="snapshot_date"):
        api.analyse(GOLD["profiles"]["full_profile"], snap, "moderate", roles=ROLES, role_skills=[])


def test_when_every_skill_is_unknown_the_error_says_they_were_dropped():
    with pytest.raises(ValueError, match="none of the profile.*zz_a.*zz_b"):
        call(dict(GOLD["profiles"]["full_profile"], skills=[{"skill_id": "zz_a", "level": 2}, {"skill_id": "zz_b", "level": 1}]))


def test_levels_are_checked_for_dropped_skills_too_and_dropped_ids_keep_profile_order():
    base = GOLD["profiles"]["full_profile"]
    with pytest.raises(ValueError):
        call(dict(base, skills=[{"skill_id": "u_turn", "level": 2}, {"skill_id": "zz_a", "level": 9}]))
    with pytest.raises(ValueError):
        call(dict(base, skills=[{"skill_id": "u_turn", "level": 2}, {"skill_id": "zz_a", "level": 1}, {"skill_id": "zz_a", "level": 1}]))
    out = call(dict(base, skills=[{"skill_id": "zz_z", "level": 2}, {"skill_id": "u_turn", "level": 2}, {"skill_id": "zz_a", "level": 1}]))
    assert out["dropped_skills"] == ["zz_z", "zz_a"]


def test_a_dropped_skill_earns_no_match_credit_even_if_a_role_needs_it():
    # r_ghost needs skill "ghost" (weight 2) and u_turn (weight 2); "ghost" has no series in the snapshot
    profile = dict(GOLD["profiles"]["full_profile"], skills=[{"skill_id": "ghost", "level": 3}, {"skill_id": "u_turn", "level": 3}])
    out = call(profile)
    assert out["dropped_skills"] == ["ghost"]
    ghost = next(m for m in out["matches"] if m["role_id"] == "r_ghost")
    assert ghost["match_pct"] == pytest.approx(0.5) and [g["skill_id"] for g in ghost["gaps"]] == ["ghost"]


def test_profile_id_is_none_when_absent_and_top_n_can_be_all_or_few():
    base = {k: v for k, v in GOLD["profiles"]["full_profile"].items() if k != "profile_id"}
    assert call(base)["profile_id"] is None
    profile = GOLD["profiles"]["full_profile"]
    every = api.analyse(profile, SNAP, "moderate", roles=ROLES, role_skills=ROLE_SKILLS, top_n=None)["matches"]
    assert len(every) == 6 > config.TOP_N_ROLES                                   # all future roles that have skills
    assert [m["role_id"] for m in every[:5]] == [m["role_id"] for m in call(profile)["matches"]]
    two = api.analyse(profile, SNAP, "moderate", roles=ROLES, role_skills=ROLE_SKILLS, top_n=2)["matches"]
    assert [m["role_id"] for m in two] == [m["role_id"] for m in every[:2]]
    assert api.analyse(profile, SNAP, "moderate", roles=ROLES, role_skills=ROLE_SKILLS, top_n=0)["matches"] == []


def test_role_skills_with_no_future_role_to_match_warn_instead_of_showing_nothing():
    out = api.analyse(GOLD["profiles"]["full_profile"], SNAP, "moderate", roles=[], role_skills=ROLE_SKILLS)
    assert out["matches"] == [] and len(out["warnings"]) == 1 and "future role" in out["warnings"][0]
