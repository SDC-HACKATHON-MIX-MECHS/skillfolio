"""Pins every rule in docs/SPEC.md section 5.5 (SDG lens) to numbers.

Golden values in tests/fixtures/golden_sdg.json come from tests/fixtures/independent_sdg.py, which does not import the engine.
"""

import copy
import json
from pathlib import Path

import pytest

from engine import config, sdg

GOLD = json.loads((Path(__file__).parent / "fixtures" / "golden_sdg.json").read_text(encoding="utf-8"))
ROLES, ROLE_SKILLS = GOLD["roles"], GOLD["role_skills"]


def test_config_matches_the_goldens():
    assert config.BASELINE_SKILL_SDG == GOLD["baseline"] and config.ROLE_SDG_MIN_WEIGHT == GOLD["min_weight"]


@pytest.mark.parametrize("skill", list(GOLD["skill_sdgs"]))
def test_skill_sdgs_match_the_independent_numbers(skill):
    assert sdg.skill_sdgs(skill, ROLES, ROLE_SKILLS) == GOLD["skill_sdgs"][skill]


@pytest.mark.parametrize("name", list(GOLD["portfolios"]))
def test_allocation_matches_the_independent_numbers_and_order(name):
    case = GOLD["portfolios"][name]
    out = sdg.impact_allocation(case["weights"], ROLES, ROLE_SKILLS)
    assert [s for s, _ in case["allocation"]] == list(out)          # same SDGs, same order: share desc, then SDG number
    assert list(out.values()) == pytest.approx([v for _, v in case["allocation"]], rel=1e-12)
    assert sum(out.values()) == pytest.approx(1.0, rel=1e-12)
    assert all(isinstance(s, int) for s in out)


def test_weight_threshold_is_inclusive_and_origin_roles_count():
    roles = [{"role_id": "r", "sdgs": [9]}, {"role_id": "o", "sdgs": [10], "role_type": "origin"}]
    rows = lambda w: [{"role_id": "r", "skill_id": "s", "weight": w, "required_level": 1}]
    assert sdg.skill_sdgs("s", roles, rows(1)) == [4]
    assert sdg.skill_sdgs("s", roles, rows(2)) == [4, 9]
    assert sdg.skill_sdgs("s", roles, rows(3)) == [4, 9]
    assert sdg.skill_sdgs("s", roles, rows(2) + [{"role_id": "o", "skill_id": "s", "weight": 2, "required_level": 1}]) == [4, 9, 10]


def test_baseline_is_first_never_repeated_and_others_ascend():
    roles = [{"role_id": "a", "sdgs": [13, 4, 8]}, {"role_id": "b", "sdgs": [8, 2]}]
    rows = [{"role_id": r, "skill_id": "s", "weight": 3, "required_level": 1} for r in "ab"]
    assert sdg.skill_sdgs("s", roles, rows) == [4, 2, 8, 13]


def test_baseline_and_threshold_come_from_config(monkeypatch):
    roles = [{"role_id": "r", "sdgs": [9]}]
    rows = [{"role_id": "r", "skill_id": "s", "weight": 1, "required_level": 1}]
    monkeypatch.setattr(config, "ROLE_SDG_MIN_WEIGHT", 1)
    assert sdg.skill_sdgs("s", roles, rows) == [4, 9]
    monkeypatch.setattr(config, "BASELINE_SKILL_SDG", 17)
    assert sdg.skill_sdgs("s", roles, rows) == [17, 9]


def test_rows_for_unknown_roles_other_skills_and_roles_without_rows_are_ignored():
    assert sdg.skill_sdgs("s_ghost", ROLES, ROLE_SKILLS) == [4]
    assert sdg.skill_sdgs("nobody_has_this", ROLES, ROLE_SKILLS) == [4]
    assert sdg.skill_sdgs("s_mix", ROLES, []) == [4]
    assert sdg.skill_sdgs("s_mix", [], ROLE_SKILLS) == [4]


def test_a_weight_is_split_equally_across_the_skills_sdgs():
    roles = [{"role_id": "r", "sdgs": [7, 13]}]
    rows = [{"role_id": "r", "skill_id": "s", "weight": 3, "required_level": 1}]
    out = sdg.impact_allocation({"s": 0.6, "t": 0.4}, roles, rows)
    assert out == pytest.approx({4: 0.2 + 0.4, 7: 0.2, 13: 0.2})
    assert list(out) == [4, 7, 13]


def test_ties_are_ordered_by_sdg_number_and_row_order_cannot_change_the_numbers():
    roles = [{"role_id": "r", "sdgs": [9, 3]}]
    rows = [{"role_id": "r", "skill_id": s, "weight": 3, "required_level": 1} for s in ("a", "b", "c")]
    w = {"a": 0.1, "b": 0.2, "c": 0.7}
    forward = sdg.impact_allocation(w, roles, rows)
    backward = sdg.impact_allocation(dict(reversed(list(w.items()))), roles, list(reversed(rows)))
    assert list(forward) == [3, 4, 9] and forward == backward                    # exactly equal, not just approx


def test_allocation_rejects_bad_weights():
    for bad in ({}, {"s": 0.5}, {"s": 1.2}, {"a": 0.5, "b": 0.6}):
        with pytest.raises(ValueError):
            sdg.impact_allocation(bad, ROLES, ROLE_SKILLS)
    sdg.impact_allocation({"a": 0.5, "b": 0.5 + 1e-12}, ROLES, ROLE_SKILLS)     # rounding is fine
    with pytest.raises(ValueError):
        sdg.impact_allocation({"a": float("nan")}, ROLES, ROLE_SKILLS)
    with pytest.raises(ValueError):
        sdg.impact_allocation({"a": 1.5, "b": -0.5}, ROLES, ROLE_SKILLS)        # negative weights


def test_inputs_are_not_changed():
    before = copy.deepcopy((ROLES, ROLE_SKILLS))
    w = {"s_mix": 1.0}
    sdg.impact_allocation(w, ROLES, ROLE_SKILLS)
    sdg.skill_sdgs("s_mix", ROLES, ROLE_SKILLS)
    assert (ROLES, ROLE_SKILLS) == before and w == {"s_mix": 1.0}


def test_every_skill_in_the_real_catalogue_gets_at_least_one_sdg():
    from engine import data
    skills = data.load_skills()
    out = {s["skill_id"]: sdg.skill_sdgs(s["skill_id"], data.load_roles(), data.load_role_skills()) for s in skills}
    assert len(out) == len(skills) and all(v and v[0] == 4 for v in out.values())


def test_equal_shares_are_ordered_by_sdg_number_not_by_first_appearance():
    roles = [{"role_id": "x", "sdgs": [9]}, {"role_id": "y", "sdgs": [3]}]
    rows = [{"role_id": "x", "skill_id": "a", "weight": 3, "required_level": 1}, {"role_id": "y", "skill_id": "b", "weight": 3, "required_level": 1}]
    out = sdg.impact_allocation({"a": 0.5, "b": 0.5}, roles, rows)    # SDG 9 is met first, SDG 3 second; both get 0.25
    assert out == pytest.approx({4: 0.5, 3: 0.25, 9: 0.25}) and list(out) == [4, 3, 9]


def test_the_weights_sum_tolerance_is_tight_for_mistakes():
    with pytest.raises(ValueError):
        sdg.impact_allocation({"a": 0.5, "b": 0.4999}, ROLES, ROLE_SKILLS)
    with pytest.raises(ValueError):
        sdg.impact_allocation({"a": 0.5, "b": float("inf")}, ROLES, ROLE_SKILLS)


def test_row_order_cannot_change_the_shares_bit_for_bit():
    import itertools
    weights = [0.1, 0.2, 0.2, 0.25, 0.25]       # found by search: a plain running total of these differs by order
    results = set()
    for perm in itertools.permutations(range(5)):
        w = {f"s{i}": weights[i] for i in perm}
        results.add(tuple(sdg.impact_allocation(w, [], []).items()))
    assert len(results) == 1


def test_zero_weight_skills_add_no_slices_but_zero_is_a_valid_weight():
    out = sdg.impact_allocation({"s_green": 0.0, "s_alone": 1.0}, ROLES, ROLE_SKILLS)
    assert out == {4: 1.0}                                   # s_green would have added SDGs 7 and 13 with 0.0 each
    assert sdg.impact_allocation({"s_green": -0.0, "s_alone": 1.0}, ROLES, ROLE_SKILLS) == {4: 1.0}


def test_bool_weights_and_small_sum_errors_are_rejected():
    for bad in ({"s_alone": True}, {"s_alone": False, "s_mix": True}):
        with pytest.raises(ValueError):
            sdg.impact_allocation(bad, ROLES, ROLE_SKILLS)
    for off in (1e-8, 1e-7, 1e-6):                           # the sum must match to about 1e-9
        with pytest.raises(ValueError):
            sdg.impact_allocation({"a": 0.5, "b": 0.5 + off}, ROLES, ROLE_SKILLS)
