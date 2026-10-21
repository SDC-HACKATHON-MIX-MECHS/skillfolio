"""Pins every rule in docs/SPEC.md section 5.3 (role matching) to numbers.

Golden values in tests/fixtures/golden_matching.json come from tests/fixtures/independent_matching.py, which
does not import the engine. Illustrative fixture data only (the roles are made up, built on snapshot_30m).
"""

import copy
import json
from pathlib import Path

import pytest

from engine import config, forecast, matching

FIXTURES = Path(__file__).parent / "fixtures"
GOLD = json.loads((FIXTURES / "golden_matching.json").read_text(encoding="utf-8"))
SNAP = json.loads((FIXTURES / "snapshot_30m.json").read_text(encoding="utf-8"))
ROLES, ROLE_SKILLS = GOLD["roles"], GOLD["role_skills"]
DATE = "2026-01-01"
CASES = list(GOLD["cases"].items())
KEYS = {"role_id", "title", "match_pct", "role_growth", "ai_exposure", "sdg_overlap", "rank_score",
        "contributions", "gaps", "sdgs", "citations"}


def forecasts(scenario):
    return forecast.forecast_all(SNAP, scenario)


def check_match(actual, expected, label):
    for key in ("match_pct", "role_growth", "sdg_overlap", "rank_score"):
        assert actual[key] == pytest.approx(expected[key], rel=1e-7, abs=1e-9), f"{label}.{key}"
    for key in ("contributions", "gaps"):
        assert [c["skill_id"] for c in actual[key]] == [c["skill_id"] for c in expected[key]], f"{label}.{key} order"
        for a, e in zip(actual[key], expected[key]):
            assert a == pytest.approx(e, rel=1e-7, abs=1e-9), f"{label}.{key}"


@pytest.mark.parametrize("name,case", CASES)
def test_every_role_matches_the_independent_numbers(name, case):
    fc = forecasts(case["scenario"])
    for role_id, expected in case["matches"].items():
        role = next(r for r in ROLES if r["role_id"] == role_id)
        m = matching.match_role(role, ROLE_SKILLS, case["user_levels"], fc, case["user_sdgs"], DATE)
        assert set(m) == KEYS
        check_match(m, expected, f"{name}/{role_id}")
        assert m["title"] == role["title"] and m["ai_exposure"] == role["ai_exposure"] and m["sdgs"] == role["sdgs"]


@pytest.mark.parametrize("name,case", CASES)
def test_ranking_matches_the_independent_order(name, case):
    ranked = matching.rank_roles(ROLES, ROLE_SKILLS, case["user_levels"], forecasts(case["scenario"]), case["user_sdgs"], DATE)
    assert [m["role_id"] for m in ranked] == case["ranking"]
    scores = [m["rank_score"] for m in ranked]
    assert scores == sorted(scores, reverse=True)
    for m in ranked:
        check_match(m, case["matches"][m["role_id"]], f"{name}/{m['role_id']}")


def test_ranking_excludes_origin_roles_and_roles_without_skills_but_match_role_still_scores_origin():
    case = GOLD["cases"]["full_profile/moderate"]
    ranked = {m["role_id"] for m in matching.rank_roles(ROLES, ROLE_SKILLS, case["user_levels"], forecasts("moderate"), [], DATE)}
    assert "r_origin" not in ranked and "r_empty" not in ranked and len(ranked) == 6
    origin = next(r for r in ROLES if r["role_id"] == "r_origin")
    assert matching.match_role(origin, ROLE_SKILLS, case["user_levels"], forecasts("moderate"), [], DATE)["match_pct"] == pytest.approx(1.0)


def _role(rid):
    return {"role_id": rid, "title": rid, "role_type": "future", "ai_exposure": 0.1, "sdgs": []}


def _row(rid, skill):
    return {"role_id": rid, "skill_id": skill, "weight": 1, "required_level": 1}


def test_ties_are_broken_by_role_id_whatever_the_input_order():
    fc = {"s": {"projected": 0.0}}
    rows = [_row(r, "s") for r in ("c", "a", "b")]
    for order in (("c", "a", "b"), ("a", "b", "c"), ("b", "c", "a")):
        out = matching.rank_roles([_role(r) for r in order], rows, {"s": 1}, fc, [], DATE)
        assert [m["role_id"] for m in out] == ["a", "b", "c"]


def test_equal_rank_scores_go_to_the_higher_match_before_the_role_id():
    # "z": match 1.0, growth 0 -> score 1.0.  "a": match 0.5 and growth +1.0 -> score 1.0.  Same score; z has the higher match.
    fc = {"s": {"projected": 0.0}, "t": {"projected": 0.0}, "u": {"projected": 2.0}}
    rows = [_row("z", "s"), _row("a", "s"), _row("a", "u")]
    out = matching.rank_roles([_role("a"), _role("z")], rows, {"s": 1}, fc, [], DATE)
    assert out[0]["rank_score"] == pytest.approx(out[1]["rank_score"])
    assert [m["role_id"] for m in out] == ["z", "a"]


def _two_skill_role(**kw):
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": [9]}
    rows = [{"role_id": "r", "skill_id": "x", "weight": 3, "required_level": 2},
            {"role_id": "r", "skill_id": "y", "weight": 1, "required_level": 1}]
    return role, rows


def test_match_pct_is_a_weighted_average_of_capped_credit():
    role, rows = _two_skill_role()
    fc = {"x": {"projected": 0.0}, "y": {"projected": 0.0}}
    for levels, expected in [({}, 0.0), ({"x": 1}, 3 * 0.5 / 4), ({"x": 2}, 3 / 4), ({"x": 3}, 3 / 4),
                             ({"x": 3, "y": 3}, 1.0), ({"y": 1}, 1 / 4), ({"x": 0, "y": 0}, 0.0)]:
        assert matching.match_role(role, rows, levels, fc, [], DATE)["match_pct"] == pytest.approx(expected), levels


def test_contributions_and_gaps_content_and_order():
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": []}
    rows = [{"role_id": "r", "skill_id": s, "weight": w, "required_level": q} for s, w, q in
            [("e", 1, 3), ("d", 2, 2), ("c", 2, 3), ("b", 2, 3), ("a", 3, 1), ("f", 3, 2)]]
    fc = {}
    out = matching.match_role(role, rows, {"a": 1, "d": 1, "e": 2, "f": 2}, fc, [], DATE)
    # gaps: weight desc, then required level desc, then skill id; a is fully met, f is met (2 of 2)
    assert [g["skill_id"] for g in out["gaps"]] == ["b", "c", "d", "e"]
    assert out["gaps"][2] == {"skill_id": "d", "weight": 2, "user_level": 1, "required_level": 2}   # a partly met skill is also a gap
    assert out["gaps"][0]["user_level"] == 0                                                          # a missing skill has level 0
    # contributions: only skills with credit > 0; weight desc, then credit desc, then skill id
    assert [c["skill_id"] for c in out["contributions"]] == ["a", "f", "d", "e"]
    assert out["contributions"][2] == {"skill_id": "d", "weight": 2, "user_level": 1, "required_level": 2, "credit": 0.5}
    assert out["contributions"][0]["credit"] == 1.0


def test_equal_weight_and_credit_are_ordered_by_skill_id_whatever_the_row_order():
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": []}
    rows = [{"role_id": "r", "skill_id": s, "weight": 2, "required_level": 2} for s in ("c", "a", "b")]
    out = matching.match_role(role, rows, {"c": 1, "a": 1, "b": 1}, {}, [], DATE)
    assert [c["skill_id"] for c in out["contributions"]] == ["a", "b", "c"]
    assert [g["skill_id"] for g in out["gaps"]] == ["a", "b", "c"]


def test_contribution_order_prefers_higher_credit_at_equal_weight():
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": []}
    rows = [{"role_id": "r", "skill_id": "a", "weight": 2, "required_level": 3},
            {"role_id": "r", "skill_id": "b", "weight": 2, "required_level": 2}]
    out = matching.match_role(role, rows, {"a": 1, "b": 2}, {}, [], DATE)
    assert [c["skill_id"] for c in out["contributions"]] == ["b", "a"]


def test_role_growth_is_importance_weighted_and_thin_skills_are_capped():
    role, rows = _two_skill_role()
    cap = config.THIN_GROWTH_CAP
    solid = {"x": {"projected": 0.40, "thin_data": False}, "y": {"projected": -0.20, "thin_data": False}}
    assert matching.match_role(role, rows, {}, solid, [], DATE)["role_growth"] == pytest.approx(0.75 * 0.40 + 0.25 * -0.20)
    thin = {"x": {"projected": 3.0, "thin_data": True}, "y": {"projected": -3.0, "thin_data": True}}
    assert matching.match_role(role, rows, {}, thin, [], DATE)["role_growth"] == pytest.approx(0.75 * cap - 0.25 * cap)
    inside = {"x": {"projected": cap / 2, "thin_data": True}, "y": {"projected": 0.0, "thin_data": True}}
    assert matching.match_role(role, rows, {}, inside, [], DATE)["role_growth"] == pytest.approx(0.75 * cap / 2)
    mixed = {"x": {"projected": 3.0, "thin_data": True}, "y": {"projected": 3.0, "thin_data": False}}
    assert matching.match_role(role, rows, {}, mixed, [], DATE)["role_growth"] == pytest.approx(0.75 * cap + 0.25 * 3.0)


def test_a_skill_without_a_forecast_counts_as_zero_growth_and_keeps_its_weight():
    role, rows = _two_skill_role()
    only_y = {"y": {"projected": 0.8}}
    assert matching.match_role(role, rows, {}, only_y, [], DATE)["role_growth"] == pytest.approx(0.25 * 0.8)


def test_sdg_overlap_uses_sets_and_divides_by_the_users_distinct_sdgs():
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": [9, 8, 8]}
    rows = [{"role_id": "r", "skill_id": "x", "weight": 1, "required_level": 1}]
    fc = {"x": {"projected": 0.0}}
    overlap = lambda sdgs: matching.match_role(role, rows, {"x": 1}, fc, sdgs, DATE)["sdg_overlap"]
    assert overlap([]) == 0.0
    assert overlap([9]) == 1.0
    assert overlap([9, 8]) == 1.0
    assert overlap([9, 8, 3, 4]) == pytest.approx(0.5)
    assert overlap([9, 9, 9, 3]) == pytest.approx(0.5)      # repeats count once
    assert overlap([1, 2]) == 0.0


def test_rank_score_uses_the_configured_sdg_tilt(monkeypatch):
    role, rows = _two_skill_role()
    fc = {"x": {"projected": 0.2}, "y": {"projected": 0.0}}
    base = matching.match_role(role, rows, {"x": 2, "y": 1}, fc, [9, 3], DATE)
    assert base["rank_score"] == pytest.approx(1.0 * (1 + 0.15) * (1 + 0.15 * 0.5))
    monkeypatch.setattr(config, "SDG_TILT_ALPHA", 0.4)
    assert matching.match_role(role, rows, {"x": 2, "y": 1}, fc, [9, 3], DATE)["rank_score"] == pytest.approx(1.15 * (1 + 0.4 * 0.5))


def test_thin_cap_comes_from_config(monkeypatch):
    role, rows = _two_skill_role()
    monkeypatch.setattr(config, "THIN_GROWTH_CAP", 0.2)
    fc = {"x": {"projected": 1.0, "thin_data": True}, "y": {"projected": 0.0}}
    assert matching.match_role(role, rows, {}, fc, [], DATE)["role_growth"] == pytest.approx(0.75 * 0.2)


def test_citations_list_every_source_once_with_the_snapshot_date():
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": [], "exposure_source": "aei_job_exposure"}
    rows = [{"role_id": "r", "skill_id": "x", "weight": 1, "required_level": 1, "source": "onet_in_demand"},
            {"role_id": "r", "skill_id": "y", "weight": 1, "required_level": 1, "source": "onet_hot"},
            {"role_id": "r", "skill_id": "z", "weight": 1, "required_level": 1, "source": "curated_by_team"},
            {"role_id": "r", "skill_id": "w", "weight": 1, "required_level": 1}]
    out = matching.match_role(role, rows, {}, {}, [], "2026-10-20")["citations"]
    assert out == [{"source_id": "hn_whoishiring", "snapshot_date": "2026-10-20"},
                   {"source_id": "aei_job_exposure", "snapshot_date": "2026-10-20"},
                   {"source_id": "onet_tech", "snapshot_date": "2026-10-20"},
                   {"source_id": "curated_by_team", "snapshot_date": "2026-10-20"}]
    bare = matching.match_role({"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": None, "sdgs": []},
                               [{"role_id": "r", "skill_id": "x", "weight": 1, "required_level": 1}], {}, {}, [], "d")["citations"]
    assert [c["source_id"] for c in bare] == ["hn_whoishiring", "aei_job_exposure"]
    other = dict(role, exposure_source="another_source")
    assert matching.match_role(other, rows[:1], {}, {}, [], "d")["citations"][1]["source_id"] == "another_source"


def test_only_this_roles_rows_are_used_and_inputs_are_not_changed():
    role = ROLES[1]
    case = GOLD["cases"]["full_profile/moderate"]
    fc = forecasts("moderate")
    snapshot = (copy.deepcopy(ROLES), copy.deepcopy(ROLE_SKILLS), copy.deepcopy(case["user_levels"]), copy.deepcopy(fc))
    mixed = matching.match_role(role, ROLE_SKILLS, case["user_levels"], fc, [9], DATE)
    only_own = matching.match_role(role, [r for r in ROLE_SKILLS if r["role_id"] == role["role_id"]], case["user_levels"], fc, [9], DATE)
    assert mixed == only_own
    assert (ROLES, ROLE_SKILLS, case["user_levels"], fc) == snapshot


@pytest.mark.parametrize("bad_row", [
    {"role_id": "r", "skill_id": "x", "weight": 0, "required_level": 1},
    {"role_id": "r", "skill_id": "x", "weight": 4, "required_level": 1},
    {"role_id": "r", "skill_id": "x", "weight": 1, "required_level": 0},
    {"role_id": "r", "skill_id": "x", "weight": 1, "required_level": 4},
    {"role_id": "r", "skill_id": "x", "weight": None, "required_level": 1},
])
def test_bad_role_skill_rows_are_rejected(bad_row):
    role, _ = _two_skill_role()
    with pytest.raises(ValueError):
        matching.match_role(role, [bad_row], {}, {}, [], DATE)


def test_duplicate_role_skill_rows_user_levels_and_empty_roles_are_rejected():
    role, rows = _two_skill_role()
    with pytest.raises(ValueError):
        matching.match_role(role, rows + [dict(rows[0])], {}, {}, [], DATE)
    for bad in (-1, 4, True, 1.5):
        with pytest.raises(ValueError):
            matching.match_role(role, rows, {"x": bad}, {}, [], DATE)
    with pytest.raises(ValueError):
        matching.match_role(role, [], {}, {}, [], DATE)
    with pytest.raises(ValueError):
        matching.match_role(role, [dict(rows[0], role_id="other")], {}, {}, [], DATE)
    out = matching.match_role(role, rows, {"x": 0}, {}, [], DATE)           # level 0 is the same as absent
    assert out == matching.match_role(role, rows, {}, {}, [], DATE)


def test_the_scenario_moves_growth_and_rank_but_not_match_or_gaps():
    case = GOLD["cases"]["full_profile/moderate"]
    a = matching.rank_roles(ROLES, ROLE_SKILLS, case["user_levels"], forecasts("moderate"), case["user_sdgs"], DATE)
    b = matching.rank_roles(ROLES, ROLE_SKILLS, case["user_levels"], forecasts("fast"), case["user_sdgs"], DATE)
    by_id = lambda ms: {m["role_id"]: m for m in ms}
    for rid, m in by_id(a).items():
        assert m["match_pct"] == by_id(b)[rid]["match_pct"] and m["gaps"] == by_id(b)[rid]["gaps"]
    assert any(m["role_growth"] != pytest.approx(by_id(b)[rid]["role_growth"]) for rid, m in by_id(a).items())


def test_non_finite_growth_is_an_error_not_a_silent_ranking_bug():
    role, rows = _two_skill_role()
    for projected in (float("nan"), float("inf"), float("-inf")):
        for thin in (False, True):          # a thin skill's NaN must not be clamped into +5% either
            with pytest.raises(ValueError):
                matching.match_role(role, rows, {}, {"x": {"projected": projected, "thin_data": thin}}, [], DATE)
    matching.match_role(role, rows, {}, {"x": {"projected": 0.1}}, [], DATE)


# (weight, required level, user level) per skill, plus projected growth. Found by search: with a plain running
# total (total += term), these row sets give a last-digit different match (first) or growth (second) in some orders.
NOISY_MATCH = ([(3, 2, 1), (2, 2, 1), (1, 2, 0), (3, 2, 3), (1, 3, 3)], [0.0] * 5)
NOISY_GROWTH = ([(3, 2, 2), (3, 3, 0), (2, 1, 0), (1, 1, 2), (2, 1, 3)], [0.14, 0.17, -0.39, -0.18, -0.12])


@pytest.mark.parametrize("rows_and_growth", [NOISY_MATCH, NOISY_GROWTH], ids=["match", "growth"])
def test_row_order_cannot_change_the_numbers_so_ties_follow_the_documented_rule(rows_and_growth):
    import itertools
    spec, projected = rows_and_growth
    skills = [(f"s{i}", w, q) for i, (w, q, _) in enumerate(spec)]
    levels = {f"s{i}": lvl for i, (_, _, lvl) in enumerate(spec)}
    fc = {f"s{i}": {"projected": p} for i, p in enumerate(projected)}
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": [9]}
    results = set()
    for perm in itertools.permutations(skills):
        rows = [{"role_id": "r", "skill_id": s, "weight": w, "required_level": q} for s, w, q in perm]
        m = matching.match_role(role, rows, levels, fc, [9], DATE)
        results.add((m["match_pct"], m["role_growth"], m["rank_score"]))
    assert len(results) == 1               # bit-for-bit identical in every one of the 120 orders


def test_duplicate_role_ids_are_rejected_and_unknown_role_types_are_not_ranked():
    with pytest.raises(ValueError):
        matching.rank_roles([_role("a"), _role("a")], [_row("a", "s")], {"s": 1}, {}, [], DATE)
    other = dict(_role("b"), role_type="other")
    out = matching.rank_roles([_role("a"), other], [_row("a", "s"), _row("b", "s")], {"s": 1}, {}, [], DATE)
    assert [m["role_id"] for m in out] == ["a"]


def test_bool_and_non_numeric_weights_are_rejected():
    role, _ = _two_skill_role()
    for bad in (True, "2", None):
        with pytest.raises(ValueError):
            matching.match_role(role, [{"role_id": "r", "skill_id": "x", "weight": bad, "required_level": 1}], {}, {}, [], DATE)
        with pytest.raises(ValueError):
            matching.match_role(role, [{"role_id": "r", "skill_id": "x", "weight": 1, "required_level": bad}], {}, {}, [], DATE)


def test_sdg_overlap_is_not_rounded_and_negative_growth_lowers_the_rank():
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": [9, 8]}
    rows = [{"role_id": "r", "skill_id": "x", "weight": 1, "required_level": 1}]
    out = matching.match_role(role, rows, {"x": 1}, {"x": {"projected": -0.3}}, [9, 3, 4], DATE)
    assert out["sdg_overlap"] == 1 / 3                              # exactly, not 0.33
    assert out["rank_score"] == pytest.approx(1.0 * 0.7 * (1 + 0.15 / 3), rel=1e-12)


def test_inputs_are_not_changed_and_returned_lists_are_copies():
    role = {"role_id": "r", "title": "R", "role_type": "future", "ai_exposure": 0.3, "sdgs": [9]}
    rows = [{"role_id": "r", "skill_id": "x", "weight": 1, "required_level": 1}]
    levels, sdgs, fc = {"x": 1}, [9, 3], {"x": {"projected": 0.1}}
    before = copy.deepcopy((role, rows, levels, sdgs, fc))
    out = matching.match_role(role, rows, levels, fc, sdgs, DATE)
    out["sdgs"].append(99)
    out["contributions"][0]["credit"] = 0
    assert (role, rows, levels, sdgs, fc) == before
    assert matching.match_role(role, rows, levels, fc, sdgs, DATE)["sdgs"] == [9]
    levels_without_y = {"x": 1}
    matching.match_role(role, rows + [{"role_id": "r", "skill_id": "y", "weight": 1, "required_level": 1}], levels_without_y, fc, [], DATE)
    assert levels_without_y == {"x": 1}


def test_user_levels_for_skills_outside_the_role_are_ignored_but_must_still_be_valid():
    role, rows = _two_skill_role()
    fc = {"x": {"projected": 0.0}, "y": {"projected": 0.0}}
    assert matching.match_role(role, rows, {"x": 2, "elsewhere": 3}, fc, [], DATE)["match_pct"] == pytest.approx(3 / 4)
    with pytest.raises(ValueError):
        matching.match_role(role, rows, {"x": 2, "elsewhere": 9}, fc, [], DATE)
