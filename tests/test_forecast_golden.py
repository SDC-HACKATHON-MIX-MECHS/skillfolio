"""Pins every rule in docs/SPEC.md section 5.1 to numbers.

The golden values in tests/fixtures/golden_*.json come from tests/fixtures/independent_expected.py,
which does not import the engine. Fixtures: tests/fixtures/make_snapshots.py. Illustrative data only.

Why each skill exists in snapshot_30m (the rule it makes visible):
  u_turn         falls 18 months then rises -> 12-month momentum differs from 24-month and whole-series trends
  noisy_early    loud early, calm late      -> volatility window (24 months) differs from 12 and from the full series
  late_riser     absent for 15 months       -> demand index rebases on the first non-zero month, zeros before it
  sparse         ~1.4 posts a month         -> epsilon matters; thin data
  sparse_clumpy  mean 2.0 but 12 in busy months -> thin cutoff uses the mean over ALL months, not busy ones
  just_under     mean 2.9, exposure 0.0     -> thin; a known exposure of exactly 0 still counts in the average
  exactly_3      mean 3.0 with empty months -> not thin (strictly below 3 is thin)
  all_zero       never mentioned, exposure 0.9 -> no trend, label stable even though the fast scenario shifts it by >5%
  unknown_exp    exposure null              -> no scenario shift; left out of the average exposure
  shift_up       flat, well observed, sheltered -> only the fast scenario lifts it past +5% (label depends on the shift)
  shift_down     flat, well observed, exposed   -> only the fast scenario pushes it past -5%
  faded          5 posts a month for 18 months, then silent -> mean 3.0 over ALL months is not thin
Thread sizes vary (137 to 335), so epsilon built from the mean, the minimum or the last month differ.

snapshot_3m: rising3 / falling3 (trend with exactly 3 months), exposed3 / sheltered3 (flat, so only the
scenario shift moves their numbers: it must apply from 3 months, the minimum history).
"""

import json
from pathlib import Path

import pytest

from engine import config, forecast

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


SNAP30, GOLD30 = load("snapshot_30m"), load("golden_30m")
SNAP3, GOLD3 = load("snapshot_3m"), load("golden_3m")
TOTALS30 = [m["total_posts"] for m in SNAP30["months"]]


def check(actual, expected, scenario, label):
    for key in ("momentum", "momentum_low", "momentum_high", "volatility"):
        assert actual[key] == pytest.approx(expected[key], rel=1e-7, abs=1e-9), f"{label}.{key}"
    for key in ("projected", "projected_low", "projected_high"):
        assert actual[key] == pytest.approx(expected["scenarios"][scenario][key], rel=1e-7, abs=1e-9), f"{label}.{key}"
    assert actual["trajectory"] == expected["scenarios"][scenario]["trajectory"], f"{label}.trajectory"
    assert actual["thin_data"] is expected["thin_data"], f"{label}.thin_data"
    assert actual["history_months"] == expected["history_months"], f"{label}.history_months"
    assert actual["index"] == pytest.approx(expected["index"], rel=1e-7, abs=1e-9), f"{label}.index"


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
@pytest.mark.parametrize("skill", list(GOLD30["skills"]))
def test_golden_30_months(skill, scenario):
    actual = forecast.forecast_all(SNAP30, scenario)[skill]
    check(actual, GOLD30["skills"][skill], scenario, f"{skill}/{scenario}")


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
@pytest.mark.parametrize("skill", list(GOLD3["skills"]))
def test_golden_exactly_three_months(skill, scenario):
    # three months is the minimum for a trend: it must be estimated, not treated as "too little history"
    actual = forecast.forecast_all(SNAP3, scenario)[skill]
    check(actual, GOLD3["skills"][skill], scenario, f"{skill}/{scenario}")
    assert actual["thin_data"] is False
    if skill in ("rising3", "falling3"):
        assert actual["momentum"] != 0


def test_epsilon_is_half_a_post_over_the_mean_thread_size():
    assert forecast.epsilon(TOTALS30) == pytest.approx(GOLD30["epsilon"], rel=1e-12)
    assert config.EPSILON_POSTS == 0.5
    # no usable thread sizes: fall back to a thread of one post so ln() is still defined
    assert forecast.epsilon([]) == config.EPSILON_POSTS
    assert forecast.epsilon([0, 0]) == config.EPSILON_POSTS


def test_late_appearing_skill_rebases_on_its_first_non_zero_month():
    index = forecast.forecast_all(SNAP30, "moderate")["late_riser"]["index"]
    assert index[:15] == [0.0] * 15
    assert index[15] == pytest.approx(100.0)
    assert index[16] > 100.0


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
@pytest.mark.parametrize("exposure", [0.0, 1.0])
def test_thin_skills_are_labelled_stable_whatever_the_scenario_says(scenario, exposure):
    snap = json.loads(json.dumps(SNAP30))
    thin = [s for s, g in GOLD30["skills"].items() if g["thin_data"]]
    assert {"sparse", "sparse_clumpy", "just_under", "all_zero"} <= set(thin)
    for skill in thin:
        snap["skills"][skill]["exposure"] = exposure
    forecasts = forecast.forecast_all(snap, scenario)
    for skill in thin:
        assert forecasts[skill]["thin_data"] is True
        assert forecasts[skill]["trajectory"] == "stable", skill


def test_never_mentioned_skill_has_no_trend_but_still_gets_the_scenario_shift_in_its_number():
    f = forecast.forecast_all(SNAP30, "fast")["all_zero"]
    assert f["momentum"] == pytest.approx(0, abs=1e-12) and f["volatility"] == pytest.approx(0, abs=1e-12)
    assert f["index"] == [0.0] * 30
    assert f["projected"] == pytest.approx(-config.SCENARIOS["fast"]["lambda"] * (0.90 - GOLD30["mean_exposure"]))
    assert f["trajectory"] == "stable"  # a number we cannot trust must not become a headline


def test_unknown_exposure_gets_no_shift_and_is_left_out_of_the_average():
    for scenario in ("moderate", "fast"):
        forecasts = forecast.forecast_all(SNAP30, scenario)
        f = forecasts["unknown_exp"]
        assert f["exposure"] is None
        assert f["projected"] == pytest.approx(f["momentum"], abs=1e-12)
        assert f["projected_low"] == pytest.approx(f["momentum_low"], abs=1e-12)
        assert f["projected_high"] == pytest.approx(f["momentum_high"], abs=1e-12)
    known = [s["exposure"] for s in SNAP30["skills"].values() if s["exposure"] is not None]
    assert 0.0 in known  # a known exposure of exactly 0 counts toward the average
    assert len(known) == len(SNAP30["skills"]) - 1
    assert GOLD30["mean_exposure"] == pytest.approx(sum(known) / len(known))


def test_volatility_needs_epsilon_when_a_share_is_zero():
    with pytest.raises(ValueError):
        forecast.volatility([0.0, 0.1, 0.2], 0.0)
    assert forecast.volatility([0.0, 0.1, 0.2], 0.01) > 0


# --- the scenario may move a label, but only for skills with enough data -------------------------

def test_scenario_shift_can_move_a_label_when_data_is_not_thin():
    moderate = forecast.forecast_all(SNAP30, "moderate")
    fast = forecast.forecast_all(SNAP30, "fast")
    for skill, label in (("shift_up", "rising"), ("shift_down", "declining")):
        f = fast[skill]
        assert f["thin_data"] is False
        # without the shift the interval sits inside +/-5%, so the label really is the scenario's doing
        assert forecast.trajectory(f["momentum_low"], f["momentum_high"]) == "stable"
        assert moderate[skill]["trajectory"] == "stable"
        assert f["trajectory"] == label


def test_shift_applies_from_the_minimum_history_of_three_months():
    lam = config.SCENARIOS["fast"]["lambda"]
    ebar = GOLD3["mean_exposure"]
    fast = forecast.forecast_all(SNAP3, "fast")
    moderate = forecast.forecast_all(SNAP3, "moderate")
    assert fast["exposed3"]["projected"] == pytest.approx(-lam * (0.90 - ebar), abs=1e-12)
    assert fast["sheltered3"]["projected"] == pytest.approx(-lam * (0.10 - ebar), abs=1e-12)
    assert (fast["exposed3"]["trajectory"], fast["sheltered3"]["trajectory"]) == ("declining", "rising")
    assert (moderate["exposed3"]["trajectory"], moderate["sheltered3"]["trajectory"]) == ("stable", "stable")


def test_thin_mean_covers_all_months_so_a_faded_skill_is_not_thin():
    f = forecast.forecast_all(SNAP30, "moderate")["faded"]
    counts = SNAP30["skills"]["faded"]["counts"]
    assert sum(counts[-12:]) == 0 and sum(counts) / len(counts) == 3.0
    assert f["thin_data"] is False and f["trajectory"] == "declining"


# --- exact thin cutoff: strictly fewer than 3 posts a month on average -------------------------

def _flat_snapshot(counts):
    n = len(counts)
    return {
        "months": [{"month": f"m{i}", "total_posts": 100} for i in range(n)],
        "skills": {"s": {"counts": counts, "shares": [c / 100 for c in counts], "exposure": 0.4}},
    }


@pytest.mark.parametrize("total,thin", [(250, True), (290, True), (299, True), (300, False), (301, False), (310, False)])
def test_thin_cutoff_is_exactly_three_posts_a_month(total, thin):
    k = total - 200  # 100 months of 2 or 3 posts; k of them have 3
    counts = [3 if i < k else 2 for i in range(100)] if k <= 100 else [3] * 100
    if total > 300:
        counts[0] += total - 300
    assert sum(counts) == total and len(counts) == 100
    assert forecast.forecast_all(_flat_snapshot(counts), "moderate")["s"]["thin_data"] is thin


# --- epsilon, config-driven numbers, defaults, signatures, metadata ------------------------------

def test_epsilon_averages_every_month_including_empty_ones():
    assert forecast.epsilon([100, 0, 100]) == pytest.approx(0.5 / (200 / 3))


def test_epsilon_follows_the_config(monkeypatch):
    monkeypatch.setattr(config, "EPSILON_POSTS", 2.0)
    assert forecast.epsilon(TOTALS30) == pytest.approx(2.0 / (sum(TOTALS30) / len(TOTALS30)))
    assert forecast.epsilon([]) == 2.0


def test_zero_total_month_does_not_crash():
    snap = {"months": [{"month": f"m{i}", "total_posts": t} for i, t in enumerate([200, 0, 200, 200, 200])],
            "skills": {"s": {"counts": [20, 0, 20, 20, 20], "shares": [0.1, 0.0, 0.1, 0.1, 0.1], "exposure": 0.4}}}
    f = forecast.forecast_all(snap, "moderate")["s"]
    assert f["history_months"] == 5 and f["thin_data"] is False


def test_trend_threshold_comes_from_the_config(monkeypatch):
    monkeypatch.setattr(config, "TREND_THRESHOLD", 100.0)
    assert {f["trajectory"] for f in forecast.forecast_all(SNAP30, "fast").values()} == {"stable"}
    assert forecast.trajectory(0.5, 0.9) == "stable"


def test_interval_width_comes_from_the_config(monkeypatch):
    monkeypatch.setattr(config, "INTERVAL_Z", 0.0)
    for skill, f in forecast.forecast_all(SNAP30, "moderate").items():
        assert f["momentum_low"] == pytest.approx(f["momentum"], abs=1e-12), skill
        assert f["momentum_high"] == pytest.approx(f["momentum"], abs=1e-12), skill


def test_thin_cutoff_and_minimum_history_come_from_the_config(monkeypatch):
    monkeypatch.setattr(config, "THIN_DATA_MIN_MEAN_COUNT", 1000)
    assert all(f["thin_data"] and f["trajectory"] == "stable" for f in forecast.forecast_all(SNAP30, "fast").values())
    monkeypatch.setattr(config, "THIN_DATA_MIN_MEAN_COUNT", 3)
    monkeypatch.setattr(config, "MIN_HISTORY_MONTHS", 31)  # more than the 30 months we have
    for f in forecast.forecast_all(SNAP30, "fast").values():
        assert f["thin_data"] is True and f["momentum"] == 0.0 and f["projected"] == 0.0 and f["trajectory"] == "stable"


def test_default_scenario_is_moderate():
    assert config.DEFAULT_SCENARIO == "moderate"
    default = forecast.forecast_all(SNAP30)
    assert default == forecast.forecast_all(SNAP30, "moderate") != forecast.forecast_all(SNAP30, "fast")
    assert {f["scenario"] for f in default.values()} == {"moderate"}


def test_bad_scenario_is_rejected_even_with_nothing_to_forecast():
    with pytest.raises(KeyError):
        forecast.forecast_all({"months": [], "skills": {}}, "slow")


def test_volatility_requires_epsilon_as_an_argument():
    with pytest.raises(TypeError):
        forecast.volatility([0.1, 0.2, 0.3])


def contract_keys():
    readme = (Path(__file__).resolve().parents[1] / "contracts" / "README.md").read_text(encoding="utf-8")
    block = readme.split("### SkillForecast", 1)[1].split("```json", 1)[1].split("```", 1)[0]
    return list(json.loads(block))


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
@pytest.mark.parametrize("snap", [SNAP30, SNAP3], ids=["30m", "3m"])
def test_each_forecast_echoes_its_ids_and_matches_the_contract_key_order(snap, scenario):
    keys = contract_keys()
    assert keys[:2] == ["skill_id", "scenario"] and "history_months" in keys
    for skill, f in forecast.forecast_all(snap, scenario).items():
        assert f["skill_id"] == skill and f["scenario"] == scenario
        assert list(f) == keys
        json.dumps(f, allow_nan=False)


def test_momentum_window_comes_from_the_config(monkeypatch):
    baseline = forecast.forecast_all(SNAP30, "moderate")["u_turn"]["momentum"]
    monkeypatch.setattr(config, "MOMENTUM_WINDOW_MONTHS", 6)
    assert forecast.forecast_all(SNAP30, "moderate")["u_turn"]["momentum"] != pytest.approx(baseline, rel=1e-3)


def test_volatility_window_comes_from_the_config(monkeypatch):
    baseline = forecast.forecast_all(SNAP30, "moderate")["noisy_early"]["volatility"]
    monkeypatch.setattr(config, "VOLATILITY_WINDOW_MONTHS", 12)
    assert forecast.forecast_all(SNAP30, "moderate")["noisy_early"]["volatility"] != pytest.approx(baseline, rel=1e-3)


def test_scenario_lambda_comes_from_the_config(monkeypatch):
    monkeypatch.setitem(config.SCENARIOS["fast"], "lambda", 0.0)
    for skill, f in forecast.forecast_all(SNAP30, "fast").items():
        assert f["projected"] == pytest.approx(f["momentum"], abs=1e-12), skill
