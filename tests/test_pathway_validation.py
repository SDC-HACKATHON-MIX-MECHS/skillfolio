"""Input validation and numeric robustness of engine.pathway.plan (verifier findings BUG1-BUG5, 4a, missing keys)."""

import itertools
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
BY_ID = {c["course_id"]: c for c in COURSES}
FC = forecast.forecast_all(SNAP, "moderate")
NAN, INF = float("nan"), float("inf")


def _plan(levels=None, hours=50, courses=None, forecasts=None, **kw):
    return pathway.plan({"shift_up": 1} if levels is None else levels, ROLES["r_ops"], ROLE_SKILLS,
                        COURSES if courses is None else courses, FC if forecasts is None else forecasts, SNAP, "low", hours, **kw)


def _with(target, **change):
    """The catalogue with one course changed (a key set to the sentinel DROP is removed)."""
    out = []
    for c in COURSES:
        if c["course_id"] == target:
            c = {k: v for k, v in dict(c, **change).items() if v is not DROP}
        out.append(c)
    return out


DROP = object()


@pytest.mark.parametrize("cost", [NAN, INF, -INF, -5000, -0.01, True, False, None, "10", [1]])
def test_bad_cost_rm_is_a_value_error(cost):
    with pytest.raises(ValueError):
        _plan(courses=_with("c_other", cost_rm=cost))           # c_other is never a candidate: only validation can catch it


def test_a_missing_cost_rm_is_a_value_error():
    with pytest.raises(ValueError):
        _plan(courses=_with("c_other", cost_rm=DROP))


@pytest.mark.parametrize("key", ["course_id", "skill_id", "hours", "level_out", "title", "provider", "url", "hrdc_claimable"])
def test_missing_course_keys_are_value_errors(key):
    with pytest.raises(ValueError):
        _plan(courses=_with("c_other", **{key: DROP}))


def test_zero_and_float_cost_are_fine():
    assert _plan(courses=_with("c_other", cost_rm=0)) == _plan()
    assert _plan(courses=_with("c_other", cost_rm=12.5)) == _plan()


def test_a_nan_cost_can_no_longer_defeat_the_rm_budget():
    with pytest.raises(ValueError):
        _plan(budget_rm=0, courses=_with("c_down1", cost_rm=NAN))


# --- 4a: an exact fit with decimal hours is allowed ---------------------------------------------------------------

def _decimal_pool(h1, h2):
    return [dict(BY_ID["c_down1"], hours=h1), dict(BY_ID["c_unk1"], hours=h2)]


def test_an_exact_fit_with_decimal_hours_is_allowed():
    pool = _decimal_pool(0.8, 0.9)
    wide = pathway.plan({"shift_up": 3}, ROLES["r_ops"], ROLE_SKILLS, pool, FC, SNAP, "medium", 10)
    assert len(wide["steps"]) == 2
    exact = pathway.plan({"shift_up": 3}, ROLES["r_ops"], ROLE_SKILLS, pool, FC, SNAP, "medium", 1.7)
    assert [s["course_id"] for s in exact["steps"]] == [s["course_id"] for s in wide["steps"]]


@pytest.mark.parametrize("pair", [(0.9, 0.8, 1.7), (1.1, 0.9, 2.0), (0.9, 5.7, 6.6), (0.8, 1.1, 1.9), (80.93, 5.64, 86.57), (5.64, 80.93, 86.57)])
def test_exact_decimal_fits_from_the_real_catalogue_hours(pair):
    h1, h2, total = pair
    out = pathway.plan({"shift_up": 3}, ROLES["r_ops"], ROLE_SKILLS, _decimal_pool(h1, h2), FC, SNAP, "medium", total)
    assert len(out["steps"]) == 2


def test_a_budget_clearly_short_still_refuses():
    out = pathway.plan({"shift_up": 3}, ROLES["r_ops"], ROLE_SKILLS, _decimal_pool(0.8, 0.9), FC, SNAP, "medium", 1.69)
    assert len(out["steps"]) == 1


def test_the_tolerance_is_a_tiny_configured_number():
    assert 0 < config.BUDGET_TOLERANCE <= 1e-6


def test_decimal_rm_fits_exactly_too():
    pool = [dict(BY_ID["c_down1"], cost_rm=0.1), dict(BY_ID["c_unk1"], cost_rm=0.2)]
    out = pathway.plan({"shift_up": 3}, ROLES["r_ops"], ROLE_SKILLS, pool, FC, SNAP, "medium", 100, budget_rm=0.3)
    assert len(out["steps"]) == 2


# --- BUG2: prerequisite level --------------------------------------------------------------------------------------

@pytest.mark.parametrize("level", [NAN, INF, None, True, "2", [2]])
def test_bad_prereq_level_is_a_value_error(level):
    with pytest.raises(ValueError):
        _plan(courses=_with("c_other", prereq_skill_id="shift_up", prereq_level=level))


@pytest.mark.parametrize("level", [0, -5, 3.5, 4, 100])
def test_out_of_range_prereq_level_is_a_value_error(level):
    with pytest.raises(ValueError):
        _plan(courses=_with("c_other", prereq_skill_id="shift_up", prereq_level=level))


@pytest.mark.parametrize("level", [1, 2, 3, 1.5])
def test_in_range_prereq_level_is_accepted(level):
    _plan(courses=_with("c_other", prereq_skill_id="shift_up", prereq_level=level))


def test_a_missing_prereq_level_with_a_prereq_skill_is_a_value_error():
    with pytest.raises(ValueError):
        _plan(courses=_with("c_other", prereq_skill_id="shift_up", prereq_level=DROP))


def test_prereq_level_is_ignored_without_a_prereq_skill():
    assert _plan(courses=_with("c_other", prereq_skill_id="", prereq_level=NAN)) == _plan()
    assert _plan(courses=_with("c_other", prereq_skill_id=None, prereq_level=None)) == _plan()


# --- BUG3: bool user levels ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("value", [False, True])
def test_bool_user_levels_are_errors_even_false(value):
    with pytest.raises(ValueError):
        _plan(levels={"shift_up": 1, "shift_down": value})


# --- BUG4: course hours / level_out types ---------------------------------------------------------------------------

@pytest.mark.parametrize("hours", [True, False, 1e-320, 1e-9, 0.0, -1])
def test_bad_course_hours_are_errors(hours):
    with pytest.raises(ValueError):
        _plan(courses=_with("c_other", hours=hours))


@pytest.mark.parametrize("level_out", [True, 2.0, 1.5, "2"])
def test_bool_float_or_text_level_out_is_an_error(level_out):
    with pytest.raises(ValueError):
        _plan(courses=_with("c_other", level_out=level_out))


def test_the_smallest_allowed_hours_gives_a_finite_gain():
    out = _plan(hours=100, courses=_with("c_down1", hours=config.MIN_COURSE_HOURS))
    assert all(s["gain_per_hour"] < float("inf") for s in out["steps"])


# --- BUG5: the order of user_levels does not change a single bit ---------------------------------------------------

def test_permuting_user_levels_gives_bit_identical_output():
    levels = {"shift_up": 1, "shift_down": 2, "u_turn": 2, "unknown_exp": 1}
    ref = json.dumps(_plan(levels=levels, hours=100), sort_keys=True)
    runs = 0
    for order in itertools.permutations(levels):
        assert json.dumps(_plan(levels={k: levels[k] for k in order}, hours=100), sort_keys=True) == ref
        runs += 1
    assert runs == 24
    assert json.loads(ref)["steps"]


def test_course_row_order_and_user_level_order_together_do_not_change_bits():
    levels = {"shift_up": 1, "shift_down": 2, "u_turn": 2}
    ref = json.dumps(_plan(levels=levels, hours=100), sort_keys=True)
    flipped = json.dumps(_plan(levels=dict(reversed(list(levels.items()))), hours=100, courses=list(reversed(COURSES))), sort_keys=True)
    assert flipped == ref


# --- missing forecasts, mixed id types ------------------------------------------------------------------------------

def test_a_user_skill_missing_from_forecasts_is_a_value_error():
    fc = {k: v for k, v in FC.items() if k != "shift_up"}
    with pytest.raises(ValueError):
        _plan(forecasts=fc)


def test_a_course_skill_missing_from_forecasts_is_a_value_error():
    fc = {k: v for k, v in FC.items() if k != "shift_down"}
    with pytest.raises(ValueError):
        _plan(forecasts=fc)


def test_mixed_int_and_str_course_ids_are_a_value_error():
    twin = dict(BY_ID["c_down1"], course_id=1)
    other = dict(BY_ID["c_down1"], course_id="1")
    with pytest.raises(ValueError):
        _plan(courses=COURSES + [twin, other])
    with pytest.raises(ValueError):
        _plan(courses=COURSES + [twin])                         # int ids next to the str ids already there


def test_all_int_course_ids_work():
    pool = [dict(c, course_id=i) for i, c in enumerate(COURSES)]
    assert _plan(courses=pool, hours=100)["steps"]


# --- snapshot membership (SPEC 5.4): a user skill with a forecast but no snapshot series --------------------------

def test_a_user_skill_without_a_snapshot_series_is_a_value_error_not_a_key_error():
    fc = {**FC, "ghost_skill": FC["shift_up"]}                  # a forecast exists, the snapshot has no series
    assert "ghost_skill" not in SNAP["skills"]
    with pytest.raises(ValueError, match="ghost_skill"):
        _plan(levels={"shift_up": 1, "ghost_skill": 2}, forecasts=fc)


# --- the tolerance edge: remaining + BUDGET_TOLERANCE is taken, remaining + 2 * BUDGET_TOLERANCE is refused ----------

TOL = config.BUDGET_TOLERANCE
EDGE_BASE = BY_ID["c_down1"]


def test_hours_exactly_remaining_plus_tolerance_is_taken():
    pool = [dict(EDGE_BASE, hours=5.0 + TOL)]
    assert len(pathway.plan({"shift_up": 3}, ROLES["r_ops"], ROLE_SKILLS, pool, FC, SNAP, "medium", 5.0)["steps"]) == 1


def test_hours_remaining_plus_twice_the_tolerance_is_refused():
    pool = [dict(EDGE_BASE, hours=5.0 + 2 * TOL)]
    assert pathway.plan({"shift_up": 3}, ROLES["r_ops"], ROLE_SKILLS, pool, FC, SNAP, "medium", 5.0)["steps"] == []


def test_rm_exactly_remaining_plus_tolerance_is_taken():
    pool = [dict(EDGE_BASE, hours=1.0, cost_rm=50.0 + TOL)]
    out = pathway.plan({"shift_up": 3}, ROLES["r_ops"], ROLE_SKILLS, pool, FC, SNAP, "medium", 100, budget_rm=50.0)
    assert len(out["steps"]) == 1


def test_rm_remaining_plus_twice_the_tolerance_is_refused():
    pool = [dict(EDGE_BASE, hours=1.0, cost_rm=50.0 + 2 * TOL)]
    out = pathway.plan({"shift_up": 3}, ROLES["r_ops"], ROLE_SKILLS, pool, FC, SNAP, "medium", 100, budget_rm=50.0)
    assert out["steps"] == []
