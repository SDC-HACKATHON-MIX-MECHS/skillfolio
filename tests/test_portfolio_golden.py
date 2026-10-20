"""Pins every rule in docs/SPEC.md section 5.2 (portfolio) to numbers.

Golden values in tests/fixtures/golden_portfolio.json come from tests/fixtures/independent_portfolio.py,
which does not import the engine. Illustrative fixture data only (tests/fixtures/make_snapshots.py).
"""

import copy
import json
import math
from pathlib import Path

import numpy as np
import pytest

from engine import config, forecast, portfolio

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parents[1]
GOLD = json.loads((FIXTURES / "golden_portfolio.json").read_text(encoding="utf-8"))
SNAPSHOTS = {
    "30m": json.loads((FIXTURES / "snapshot_30m.json").read_text(encoding="utf-8")),
    "flat6": json.loads((FIXTURES / "snapshot_flat6.json").read_text(encoding="utf-8")),
    "example": json.loads((ROOT / "contracts" / "examples" / "snapshot.example.json").read_text(encoding="utf-8")),
}
CASES = list(GOLD["cases"].items())


def run(case, scenario, risk):
    snapshot = SNAPSHOTS[case["snapshot"]]
    ids = [s["skill_id"] for s in case["skills"]]
    w = portfolio.weights(case["skills"])
    cov = portfolio.covariance(snapshot, ids)
    return w, cov, portfolio.metrics(w, forecast.forecast_all(snapshot, scenario), cov, risk)


def test_config_matches_the_goldens():
    assert config.RISK_AVERSION == GOLD["gamma"]
    assert config.THIN_GROWTH_CAP == GOLD["thin_growth_cap"]
    assert config.COVARIANCE_SHRINKAGE == 0.5


@pytest.mark.parametrize("name,case", CASES)
def test_covariance_matches_independent_numbers(name, case):
    cov = portfolio.covariance(SNAPSHOTS[case["snapshot"]], [s["skill_id"] for s in case["skills"]])
    assert np.array(cov) == pytest.approx(np.array(case["cov"]), rel=1e-7, abs=1e-10), name


@pytest.mark.parametrize("name,case", CASES)
@pytest.mark.parametrize("scenario", ["moderate", "fast"])
@pytest.mark.parametrize("risk", ["low", "medium", "high"])
def test_metrics_match_independent_numbers(name, case, scenario, risk):
    expected = case["metrics"][scenario][risk]
    _, _, actual = run(case, scenario, risk)
    assert set(actual) == {"growth", "ai_exposure", "volatility", "diversification", "readiness"}
    for key, value in expected.items():
        if value is None:
            assert actual[key] is None, f"{name}.{key}"
        else:
            assert actual[key] == pytest.approx(value, rel=1e-7, abs=1e-9), f"{name}.{key}"


def test_one_skill_portfolio_volatility_is_that_skills_volatility():
    case = GOLD["cases"]["single_u_turn"]
    w, cov, m = run(case, "moderate", "medium")
    assert m["volatility"] == pytest.approx(forecast.forecast_all(SNAPSHOTS["30m"], "moderate")["u_turn"]["volatility"], rel=1e-9)
    assert m["diversification"] == 0.0


def test_covariance_diagonal_is_volatility_squared_and_matrix_is_symmetric():
    snap = SNAPSHOTS["30m"]
    ids = ["u_turn", "noisy_early", "late_riser", "sparse"]
    cov = np.array(portfolio.covariance(snap, ids))
    forecasts = forecast.forecast_all(snap, "moderate")
    assert np.diag(cov) == pytest.approx([forecasts[i]["volatility"] ** 2 for i in ids], rel=1e-9)
    assert cov == pytest.approx(cov.T, abs=1e-15)
    assert min(np.linalg.eigvalsh(cov)) >= -1e-12  # a covariance matrix is never negative-definite


def _plain_changes(snap, ids):
    totals = [m["total_posts"] for m in snap["months"]]
    eps = forecast.epsilon(totals)
    return np.array([np.diff(np.log(np.array(forecast.smooth(snap["skills"][i]["shares"])[-24:]) + eps)) for i in ids])


def test_shrinkage_pulls_only_the_off_diagonal(monkeypatch):
    snap = SNAPSHOTS["30m"]
    ids = ["u_turn", "noisy_early", "late_riser"]
    full = 12 * np.cov(_plain_changes(snap, ids))        # sample covariance, ddof = 1, annualised
    for lam in (0.0, 0.5, 1.0):
        monkeypatch.setattr(config, "COVARIANCE_SHRINKAGE", lam)
        expected = (1 - lam) * full + lam * np.diag(np.diag(full))
        assert np.array(portfolio.covariance(snap, ids)) == pytest.approx(expected, rel=1e-9, abs=1e-12), lam
    assert abs(full[0, 1]) > 1e-3, "fixture must have a visible off-diagonal for this test to mean anything"


def test_covariance_uses_the_last_24_smoothed_months_only():
    snap = SNAPSHOTS["30m"]
    ids = ["u_turn", "noisy_early"]
    # smoothed month 6 is the mean of shares 4..6, so shares 0..3 only affect smoothed months 0..5 (outside the window)
    changed = copy.deepcopy(snap)
    for sid in ids:
        changed["skills"][sid]["shares"][:4] = [0.9, 0.0, 0.9, 0.0]
    assert np.array(portfolio.covariance(changed, ids)) == pytest.approx(np.array(portfolio.covariance(snap, ids)), rel=1e-12, abs=1e-15)
    # but a change inside the window does matter
    changed["skills"]["u_turn"]["shares"][10] += 0.1
    assert np.array(portfolio.covariance(changed, ids)) != pytest.approx(np.array(portfolio.covariance(snap, ids)), rel=1e-6)
    assert _plain_changes(snap, ids).shape[1] == 23   # 24 months -> 23 changes, sample variance divides by 22


def test_covariance_with_fewer_than_two_changes_is_zero():
    snap = {"months": [{"month": "a", "total_posts": 100}, {"month": "b", "total_posts": 100}],
            "skills": {"x": {"counts": [5, 9], "shares": [0.05, 0.09], "exposure": 0.2},
                       "y": {"counts": [9, 5], "shares": [0.09, 0.05], "exposure": 0.2}}}
    assert portfolio.covariance(snap, ["x", "y"]) == [[0.0, 0.0], [0.0, 0.0]]


def test_covariance_of_two_changes_is_defined_and_one_change_is_not():
    def snap(n):
        shares = [0.05, 0.09, 0.04, 0.08][:n]
        return {"months": [{"month": str(i), "total_posts": 100} for i in range(n)],
                "skills": {"x": {"counts": [round(v * 100) for v in shares], "shares": shares, "exposure": 0.2},
                           "y": {"counts": [9, 5, 8, 4][:n], "shares": [0.09, 0.05, 0.08, 0.04][:n], "exposure": 0.2}}}
    assert portfolio.covariance(snap(2), ["x", "y"]) == [[0.0, 0.0], [0.0, 0.0]]    # one change: no sample variance
    three = np.array(portfolio.covariance(snap(3), ["x", "y"]))                      # two changes: sample variance exists
    assert three[0, 0] > 0 and three[1, 1] > 0
    assert three[0, 0] == pytest.approx(forecast.volatility(forecast.smooth(snap(3)["skills"]["x"]["shares"]), forecast.epsilon([100] * 3)) ** 2)


def test_covariance_rejects_unknown_duplicate_and_ragged_series():
    snap = SNAPSHOTS["30m"]
    with pytest.raises(KeyError):
        portfolio.covariance(snap, ["u_turn", "no_such_skill"])
    with pytest.raises(ValueError):
        portfolio.covariance(snap, ["u_turn", "u_turn"])
    ragged = copy.deepcopy(snap)
    ragged["skills"]["u_turn"]["shares"] = ragged["skills"]["u_turn"]["shares"][:10]
    with pytest.raises(ValueError):
        portfolio.covariance(ragged, ["u_turn", "noisy_early"])
    assert portfolio.covariance(snap, []) == []


def test_weights_follow_levels_and_keep_order():
    w = portfolio.weights([{"skill_id": "b", "level": 1}, {"skill_id": "a", "level": 3}, {"skill_id": "c", "level": 2}])
    assert list(w) == ["b", "a", "c"]
    assert w == pytest.approx({"b": 1 / 6, "a": 3 / 6, "c": 2 / 6})
    assert sum(w.values()) == pytest.approx(1.0)


@pytest.mark.parametrize("bad", [
    [],
    [{"skill_id": "a", "level": 0}],
    [{"skill_id": "a", "level": 4}],
    [{"skill_id": "a", "level": 1.5}],
    [{"skill_id": "a", "level": True}],
    [{"skill_id": "a", "level": 1}, {"skill_id": "a", "level": 2}],
])
def test_weights_reject_bad_profiles(bad):
    with pytest.raises(ValueError):
        portfolio.weights(bad)


def _forecasts(**skills):
    return {k: {"projected": v[0], "exposure": v[1], "thin_data": v[2]} for k, v in skills.items()}


def test_growth_is_the_weighted_average_of_projected_growth():
    f = _forecasts(a=(0.20, 0.5, False), b=(-0.10, 0.1, False))
    m = portfolio.metrics({"a": 0.75, "b": 0.25}, f, [[0.0, 0.0], [0.0, 0.0]], "low")
    assert m["growth"] == pytest.approx(0.75 * 0.20 + 0.25 * -0.10)
    assert m["ai_exposure"] == pytest.approx(0.75 * 0.5 + 0.25 * 0.1)
    assert m["diversification"] == pytest.approx(1 - (0.75 ** 2 + 0.25 ** 2))
    assert m["volatility"] == 0.0 and m["readiness"] == pytest.approx(m["growth"])


def test_thin_skills_are_capped_in_growth_both_ways_and_boundary_is_inclusive():
    cap = config.THIN_GROWTH_CAP
    f = _forecasts(up=(2.0, 0.3, True), down=(-0.9, 0.3, True), inside=(cap / 2, 0.3, True), edge=(cap, 0.3, True),
                   big_solid=(2.0, 0.3, False))
    zero = lambda n: [[0.0] * n for _ in range(n)]
    one = lambda sid: portfolio.metrics({sid: 1.0}, f, zero(1), "low")["growth"]
    assert one("up") == pytest.approx(cap)
    assert one("down") == pytest.approx(-cap)
    assert one("inside") == pytest.approx(cap / 2)       # below the cap: untouched
    assert one("edge") == pytest.approx(cap)
    assert one("big_solid") == pytest.approx(2.0)        # solid skills are never capped


def test_unknown_exposure_is_left_out_and_weights_renormalised():
    f = _forecasts(a=(0.0, 0.8, False), b=(0.0, None, False), c=(0.0, 0.2, False))
    m = portfolio.metrics({"a": 0.5, "b": 0.3, "c": 0.2}, f, [[0.0] * 3 for _ in range(3)], "low")
    assert m["ai_exposure"] == pytest.approx((0.5 * 0.8 + 0.2 * 0.2) / 0.7)
    none_known = portfolio.metrics({"b": 1.0}, f, [[0.0]], "low")
    assert none_known["ai_exposure"] is None
    zero_known = portfolio.metrics({"x": 0.5, "y": 0.5}, _forecasts(x=(0.0, 0.0, False), y=(0.0, None, False)), [[0, 0], [0, 0]], "low")
    assert zero_known["ai_exposure"] == 0.0              # a known exposure of exactly 0 counts


def test_readiness_penalises_volatility_by_risk_tolerance():
    f = _forecasts(a=(0.10, 0.3, False))
    cov = [[0.04]]                                       # volatility 0.2
    out = {r: portfolio.metrics({"a": 1.0}, f, cov, r) for r in ("low", "medium", "high")}
    for risk, gamma in config.RISK_AVERSION.items():
        assert out[risk]["readiness"] == pytest.approx(0.10 - gamma / 2 * 0.04)
    assert out["low"]["readiness"] < out["medium"]["readiness"] < out["high"]["readiness"]
    assert out["low"]["volatility"] == pytest.approx(0.2)


def test_volatility_uses_the_whole_covariance_matrix():
    f = _forecasts(a=(0.0, 0.3, False), b=(0.0, 0.3, False))
    cov = [[0.04, 0.01], [0.01, 0.09]]
    m = portfolio.metrics({"a": 0.5, "b": 0.5}, f, cov, "low")
    assert m["volatility"] == pytest.approx(math.sqrt(0.25 * 0.04 + 0.25 * 0.09 + 2 * 0.25 * 0.01))


def test_metrics_reject_bad_inputs():
    f = _forecasts(a=(0.0, 0.3, False), b=(0.0, 0.3, False))
    ok_cov = [[0.0, 0.0], [0.0, 0.0]]
    with pytest.raises(KeyError):
        portfolio.metrics({"a": 0.5, "b": 0.5}, f, ok_cov, "reckless")
    with pytest.raises(KeyError):
        portfolio.metrics({"a": 0.5, "zzz": 0.5}, f, ok_cov, "low")
    with pytest.raises(ValueError):
        portfolio.metrics({"a": 0.5, "b": 0.5}, f, [[0.0]], "low")             # wrong size
    with pytest.raises(ValueError):
        portfolio.metrics({"a": 0.5, "b": 0.5}, f, [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], "low")   # right rows, wrong columns
    with pytest.raises(ValueError):
        portfolio.metrics({"a": 0.5, "b": 0.4}, f, ok_cov, "low")              # weights do not sum to 1
    with pytest.raises(ValueError):
        portfolio.metrics({}, f, [], "low")


def test_scenario_changes_growth_but_not_volatility_or_diversification():
    case = GOLD["cases"]["mixed_with_thin_and_unknown"]
    _, _, moderate = run(case, "moderate", "medium")
    _, _, fast = run(case, "fast", "medium")
    assert moderate["growth"] != pytest.approx(fast["growth"])
    assert moderate["volatility"] == fast["volatility"] and moderate["diversification"] == fast["diversification"]


def test_tunables_are_read_from_config(monkeypatch):
    snap = SNAPSHOTS["30m"]
    ids = ["u_turn", "noisy_early"]
    before = np.array(portfolio.covariance(snap, ids))
    monkeypatch.setattr(config, "VOLATILITY_WINDOW_MONTHS", 12)
    after = np.array(portfolio.covariance(snap, ids))
    assert after != pytest.approx(before, rel=1e-3)
    changes = _plain_changes(snap, ids)[:, -11:]            # 12 months -> 11 changes
    expected = 12 * np.cov(changes)
    expected = 0.5 * expected + 0.5 * np.diag(np.diag(expected))
    assert after == pytest.approx(expected, rel=1e-9)
    monkeypatch.undo()

    f = _forecasts(a=(0.40, 0.3, True))
    monkeypatch.setattr(config, "THIN_GROWTH_CAP", 0.2)
    assert portfolio.metrics({"a": 1.0}, f, [[0.0]], "low")["growth"] == pytest.approx(0.2)
    monkeypatch.setattr(config, "RISK_AVERSION", {"low": 10.0, "medium": 20.0, "high": 30.0})
    ready = {r: portfolio.metrics({"a": 1.0}, _forecasts(a=(0.0, 0.3, False)), [[0.04]], r)["readiness"] for r in ("low", "medium", "high")}
    assert ready == pytest.approx({"low": -5 * 0.04, "medium": -10 * 0.04, "high": -15 * 0.04})


REAL = json.loads((FIXTURES / "real_snapshot_2026-10-20.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("profile", ["aina", "ravi"])
@pytest.mark.parametrize("scenario", ["moderate", "fast"])
def test_gamma_keeps_both_terms_in_play_on_the_sample_profiles(profile, scenario):
    """Calibration (SPEC 5.2): on the real 2026-10-20 snapshot the volatility penalty is a visible but never
    dominant share of growth, for every risk tolerance, and Readiness stays positive for both sample profiles."""
    skills = json.loads((ROOT / "data" / "profiles" / f"{profile}.json").read_text(encoding="utf-8"))["skills"]
    w = portfolio.weights(skills)
    cov = portfolio.covariance(REAL, list(w))
    forecasts = forecast.forecast_all(REAL, scenario)
    shares = {}
    for risk in ("low", "medium", "high"):
        m = portfolio.metrics(w, forecasts, cov, risk)
        penalty = m["growth"] - m["readiness"]
        assert m["growth"] > 0 and m["readiness"] > 0, (risk, m)
        shares[risk] = penalty / m["growth"]
        assert 0.03 <= shares[risk] <= 0.9, (risk, shares[risk])
    assert shares["low"] > shares["medium"] > shares["high"]


def test_non_finite_numbers_are_rejected_not_silently_zero_risk():
    nan, inf = float("nan"), float("inf")
    snap = copy.deepcopy(SNAPSHOTS["30m"])
    snap["skills"]["u_turn"]["shares"][12] = nan
    with pytest.raises(ValueError):
        portfolio.covariance(snap, ["u_turn", "noisy_early"])
    f = _forecasts(a=(0.1, 0.3, False))
    assert portfolio.metrics({"a": 1.0}, f, [[0.04]], "low")["volatility"] == pytest.approx(0.2)
    for bad_cov in ([[nan]], [[inf]]):
        with pytest.raises(ValueError):
            portfolio.metrics({"a": 1.0}, f, bad_cov, "low")
    for bad in (_forecasts(a=(nan, 0.3, True)), _forecasts(a=(inf, 0.3, False)), _forecasts(a=(0.1, nan, False))):
        with pytest.raises(ValueError):
            portfolio.metrics({"a": 1.0}, bad, [[0.04]], "low")


def test_weights_sum_tolerance_is_loose_for_rounding_and_tight_for_mistakes():
    f = _forecasts(a=(0.0, 0.3, False), b=(0.0, 0.3, False))
    zero = [[0.0, 0.0], [0.0, 0.0]]
    portfolio.metrics({"a": 0.5, "b": 0.5 + 1e-12}, f, zero, "low")          # float rounding is fine
    with pytest.raises(ValueError):
        portfolio.metrics({"a": 0.5, "b": 0.49}, f, zero, "low")             # a real mistake is not
