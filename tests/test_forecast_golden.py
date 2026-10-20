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
  shift_up       flat, well observed, exposure a little under average -> only the fast scenario lifts it past +5%
  shift_down     flat, well observed, exposure a little over average  -> only the fast scenario pushes it past -5%
  noisy_up       well observed but very noisy -> point estimate above +5% while the 80% interval reaches below 0: stable, not rising
  noisy_down     the mirror image             -> point below -5% while the interval reaches above 0: stable, not declining
  faded          5 posts a month for 18 months, then silent -> mean 3.0 over ALL months is not thin
Thread sizes vary (137 to 335), so epsilon built from the mean, the minimum or the last month differ.

snapshot_flat6: five well-observed skills that differ only by noise (between-skill spread ~0, so the TAU floor binds) plus a
thin skill with a strong trend that must not influence the prior. snapshot.example (3 skills): below the 5-skill minimum, no damping.

snapshot_3m: rising3 / falling3 (trend with exactly 3 months), exposed3 / sheltered3 (flat, so only the
scenario shift moves their numbers: it must apply from 3 months, the minimum history).
"""

import json
import math
from pathlib import Path

import pytest

from engine import config, forecast

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


SNAP30, GOLD30 = load("snapshot_30m"), load("golden_30m")
SNAP3, GOLD3 = load("snapshot_3m"), load("golden_3m")
SNAP6, GOLD6 = load("snapshot_flat6"), load("golden_flat6")
SNAPEX, GOLDEX = json.loads((Path(__file__).resolve().parents[1] / "contracts" / "examples" / "snapshot.example.json").read_text(encoding="utf-8")), load("golden_example")
TOTALS30 = [m["total_posts"] for m in SNAP30["months"]]


def check(actual, expected, scenario, label):
    for key in ("momentum", "momentum_low", "momentum_high", "momentum_raw", "volatility"):
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
    assert f["projected"] == pytest.approx(math.exp(-config.SCENARIOS["fast"]["lambda"] * (0.90 - GOLD30["mean_exposure"])) - 1)
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
    assert fast["exposed3"]["projected"] == pytest.approx(math.exp(-lam * (0.46 - ebar)) - 1, abs=1e-12)
    assert fast["sheltered3"]["projected"] == pytest.approx(math.exp(-lam * (0.34 - ebar)) - 1, abs=1e-12)
    assert (fast["exposed3"]["trajectory"], fast["sheltered3"]["trajectory"]) == ("declining", "rising")
    assert (moderate["exposed3"]["trajectory"], moderate["sheltered3"]["trajectory"]) == ("stable", "stable")


def test_thin_mean_covers_all_months_so_a_faded_skill_is_not_thin():
    f = forecast.forecast_all(SNAP30, "moderate")["faded"]
    counts = SNAP30["skills"]["faded"]["counts"]
    assert sum(counts[-12:]) == 0 and sum(counts) / len(counts) == 3.0
    assert f["thin_data"] is False
    # damping softens its steep raw decline to a less extreme, less certain number: stable, as the golden says
    assert f["momentum"] > f["momentum_raw"] and f["trajectory"] == GOLD30["skills"]["faded"]["scenarios"]["moderate"]["trajectory"]


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


# --- damping noisy trends (shrinkage) and the log-space scenarios -------------------------------
# Goldens for these come from tests/fixtures/independent_expected.py, written from SPEC 5.1 before the code.

@pytest.mark.parametrize("scenario", ["moderate", "fast"])
@pytest.mark.parametrize("skill", list(GOLD6["skills"]))
def test_golden_flat6_where_the_spread_floor_binds(skill, scenario):
    check(forecast.forecast_all(SNAP6, scenario)[skill], GOLD6["skills"][skill], scenario, f"{skill}/{scenario}")


@pytest.mark.parametrize("scenario", ["moderate", "fast"])
@pytest.mark.parametrize("skill", list(GOLDEX["skills"]))
def test_golden_example_snapshot(skill, scenario):
    # only 3 skills: no prior, so nothing is damped and the numbers are the raw fit
    f = forecast.forecast_all(SNAPEX, scenario)[skill]
    check(f, GOLDEX["skills"][skill], scenario, f"{skill}/{scenario}")
    assert f["momentum"] == f["momentum_raw"]


def test_prior_estimated_from_non_thin_skills_matches_the_independent_numbers():
    for snap, gold in ((SNAP30, GOLD30), (SNAP6, GOLD6)):
        prior = forecast.prior_for_snapshot(snap)
        for key in ("k", "mu", "tau2_dl", "tau2"):
            assert prior[key] == pytest.approx(gold["prior"][key], rel=1e-9, abs=1e-12), key
    assert forecast.prior_for_snapshot(SNAP3) is None      # 4 reference skills: below the minimum of 5
    assert forecast.prior_for_snapshot(SNAPEX) is None     # 3 reference skills


def test_spread_floor_binds_only_when_skills_look_alike():
    assert GOLD6["prior"]["tau2_dl"] == 0.0
    assert forecast.prior_for_snapshot(SNAP6)["tau2"] == pytest.approx(config.TAU_FLOOR ** 2)
    assert GOLD30["prior"]["tau2_dl"] > config.TAU_FLOOR ** 2
    assert forecast.prior_for_snapshot(SNAP30)["tau2"] == pytest.approx(GOLD30["prior"]["tau2_dl"])


def test_shrinkage_prior_by_hand_two_cases():
    # five equally precise skills (s = 0.1), growth 0, .2, .4, .6, .8: w = 100, mu0 = .4, Q = 40,
    # tau2_DL = (40 - 4) / (500 - 5*100^2/500) = 36/400 = .09, equal weights -> mu = .4
    prior = forecast.shrinkage_prior([(g, 0.1) for g in (0.0, 0.2, 0.4, 0.6, 0.8)])
    assert prior == pytest.approx({"k": 5, "mu": 0.4, "tau2_dl": 0.09, "tau2": 0.09})
    # standard errors below the 0.05 floor are treated as 0.05: w = 400, Q = 160, tau2_DL = 156/1600 = .0975
    prior = forecast.shrinkage_prior([(g, 0.01) for g in (0.0, 0.2, 0.4, 0.6, 0.8)])
    assert prior == pytest.approx({"k": 5, "mu": 0.4, "tau2_dl": 0.0975, "tau2": 0.0975})
    assert forecast.shrinkage_prior([(g, 0.1) for g in (0.0, 0.2, 0.4, 0.6)]) is None  # fewer than 5 skills


def test_shrink_pulls_noisy_trends_further_than_solid_ones():
    prior = {"k": 9, "mu": 0.1, "tau2": 0.09, "tau2_dl": 0.09}
    g, s = forecast.shrink(1.0, 0.3, prior)               # B = .09 / (.09 + .09) = .5
    assert g == pytest.approx(0.1 + 0.5 * 0.9) and s == pytest.approx(0.3 * math.sqrt(0.5))
    g, s = forecast.shrink(1.0, 0.03, prior)              # a solid trend barely moves
    assert 0.99 < g < 1.0 and s == pytest.approx(0.03, rel=0.01)
    assert forecast.shrink(1.0, 0.0, prior) == (1.0, 0.0)  # no noise -> left exactly as it is
    assert forecast.shrink(1.0, 0.3, None) == (1.0, 0.3)   # no prior -> nothing damped


def test_never_mentioned_skill_is_not_pulled_toward_the_average():
    # the prior mean is far from 0, yet a skill with no posts and no noise stays at exactly 0
    f = forecast.forecast_all(SNAP30, "moderate")["all_zero"]
    assert GOLD30["prior"]["mu"] > 0.2
    assert f["momentum"] == 0.0 and f["momentum_raw"] == 0.0


def test_thin_skills_do_not_influence_the_prior():
    changed = json.loads(json.dumps(SNAP6))
    changed["skills"]["thin_riser"]["counts"] = [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    changed["skills"]["thin_riser"]["shares"] = [c / 200 for c in changed["skills"]["thin_riser"]["counts"]]
    assert forecast.prior_for_snapshot(changed) == pytest.approx(forecast.prior_for_snapshot(SNAP6))
    snap = json.loads(json.dumps(SNAP30))
    snap["skills"]["sparse"]["counts"] = [0] * 30
    snap["skills"]["sparse"]["shares"] = [0.0] * 30
    assert forecast.prior_for_snapshot(snap) == pytest.approx(forecast.prior_for_snapshot(SNAP30))


def test_prior_needs_five_non_thin_skills_not_five_skills():
    snap = json.loads(json.dumps(SNAP6))
    del snap["skills"]["noisy5"]                      # 4 non-thin + 1 thin skill left
    assert forecast.prior_for_snapshot(snap) is None
    for f in forecast.forecast_all(snap, "moderate").values():
        assert f["momentum"] == pytest.approx(f["momentum_raw"], abs=1e-12)  # nothing damped without a prior


def test_damping_pulls_toward_the_mean_by_less_than_the_whole_distance():
    forecasts = forecast.forecast_all(SNAP30, "moderate")
    prior_mu = GOLD30["prior"]["mu"]
    for skill in ("u_turn", "noisy_early", "late_riser", "sparse_clumpy", "faded"):
        raw_g, damped_g = math.log(1 + forecasts[skill]["momentum_raw"]), math.log(1 + forecasts[skill]["momentum"])
        assert min(raw_g, prior_mu) <= damped_g <= max(raw_g, prior_mu), skill
        assert abs(damped_g - prior_mu) < abs(raw_g - prior_mu), skill  # strictly closer: B < 1 for any noisy skill


def test_trend_threshold_is_pinned_from_both_sides():
    assert forecast.trajectory(0.0501, 0.2) == "rising" and forecast.trajectory(0.0499, 0.2) == "stable"
    assert forecast.trajectory(-0.2, -0.0501) == "declining" and forecast.trajectory(-0.2, -0.0499) == "stable"


def test_three_months_of_history_is_enough_to_join_the_prior():
    # six well-observed skills with exactly 3 months each: they are reference skills (history >= 3), so a prior exists
    series = [[10, 12, 16], [20, 16, 10], [30, 31, 30], [15, 14, 19], [25, 27, 22], [18, 18, 24]]
    snap = {"months": [{"month": f"m{i}", "total_posts": 200} for i in range(3)],
            "skills": {f"s{i}": {"counts": c, "shares": [x / 200 for x in c], "exposure": 0.3 + 0.05 * i} for i, c in enumerate(series)}}
    prior = forecast.prior_for_snapshot(snap)
    assert prior is not None and prior["k"] == 6
    forecasts = forecast.forecast_all(snap, "moderate")
    assert any(abs(f["momentum"] - f["momentum_raw"]) > 1e-6 for f in forecasts.values())  # damping is active
    assert all(f["history_months"] == 3 and f["thin_data"] is False for f in forecasts.values())


def test_damped_interval_is_narrower_than_the_raw_one_for_noisy_skills():
    f = forecast.forecast_all(SNAP30, "moderate")["sparse_clumpy"]
    damped_width = math.log(1 + f["momentum_high"]) - math.log(1 + f["momentum_low"])
    raw_s = GOLD30["skills"]["sparse_clumpy"]["s"]
    assert damped_width < 2 * config.INTERVAL_Z * raw_s


def test_raw_momentum_is_the_plain_fitted_trend():
    skill = "sparse_clumpy"
    smoothed = forecast.smooth(SNAP30["skills"][skill]["shares"])
    raw, _, _ = forecast.momentum(smoothed, TOTALS30)
    f = forecast.forecast_all(SNAP30, "moderate")[skill]
    assert f["momentum_raw"] == pytest.approx(raw, rel=1e-12)
    assert f["momentum"] != pytest.approx(raw, rel=1e-3)


def test_trend_is_annual_log_growth_and_its_standard_error():
    smoothed = forecast.smooth(SNAP30["skills"]["u_turn"]["shares"])
    g, s = forecast.trend(smoothed, TOTALS30)
    assert g == pytest.approx(GOLD30["skills"]["u_turn"]["g"], rel=1e-9)
    assert s == pytest.approx(GOLD30["skills"]["u_turn"]["s"], rel=1e-9)
    assert forecast.trend([0.1, 0.2], [100, 100]) == (0.0, 0.0)  # fewer than 3 months: no trend


def test_scenario_acts_in_log_space_so_it_scales_with_growth():
    lam = config.SCENARIOS["fast"]["lambda"]
    ebar = GOLD30["mean_exposure"]
    moderate, fast = forecast.forecast_all(SNAP30, "moderate"), forecast.forecast_all(SNAP30, "fast")
    for skill in ("u_turn", "noisy_early", "late_riser", "faded"):
        e = SNAP30["skills"][skill]["exposure"]
        factor = math.exp(-lam * (e - ebar))
        assert (1 + fast[skill]["momentum"]) * factor - 1 == pytest.approx(fast[skill]["projected"], rel=1e-9)
        assert (1 + fast[skill]["momentum_low"]) * factor - 1 == pytest.approx(fast[skill]["projected_low"], rel=1e-9)
        assert (1 + fast[skill]["momentum_high"]) * factor - 1 == pytest.approx(fast[skill]["projected_high"], rel=1e-9)
        assert moderate[skill]["momentum"] == fast[skill]["momentum"]  # the scenario never touches the damped trend


def test_the_scenario_visibly_changes_results_on_the_30_month_fixture():
    moderate, fast = forecast.forecast_all(SNAP30, "moderate"), forecast.forecast_all(SNAP30, "fast")
    differing = [s for s in moderate if moderate[s]["trajectory"] != fast[s]["trajectory"]]
    assert set(differing) == {"noisy_early", "shift_up", "shift_down"}
    order = lambda fc: [s for s, _ in sorted(((s, v["projected"]) for s, v in fc.items() if not v["thin_data"]), key=lambda x: -x[1])]
    assert order(moderate) != order(fast)


def test_scenario_weights_are_the_documented_ones():
    assert config.SCENARIOS["moderate"]["lambda"] == 0.5 and config.SCENARIOS["fast"]["lambda"] == 1.5
    assert (config.SE_FLOOR, config.TAU_FLOOR, config.SHRINK_MIN_SKILLS) == (0.05, 0.10, 5)


def test_shrinkage_settings_come_from_the_config(monkeypatch):
    monkeypatch.setattr(config, "TAU_FLOOR", 0.5)
    assert forecast.prior_for_snapshot(SNAP6)["tau2"] == pytest.approx(0.25)
    monkeypatch.setattr(config, "TAU_FLOOR", 0.10)
    monkeypatch.setattr(config, "SHRINK_MIN_SKILLS", 6)
    assert forecast.prior_for_snapshot(SNAP6) is None
    monkeypatch.setattr(config, "SHRINK_MIN_SKILLS", 5)
    monkeypatch.setattr(config, "SE_FLOOR", 50.0)  # every skill gets the same weight -> mu is the plain mean of g
    reference = [v["g"] for s, v in GOLD6["skills"].items() if not v["thin_data"]]
    assert forecast.prior_for_snapshot(SNAP6)["mu"] == pytest.approx(sum(reference) / len(reference), rel=1e-9)


def test_label_comes_from_the_interval_end_not_the_point_estimate():
    # noisy_up: point estimate well above +5%, but the 80% interval reaches below 0 -> stable, not rising
    # noisy_down: point estimate well below -5%, but the interval reaches above 0 -> stable, not declining
    for scenario in ("moderate", "fast"):
        forecasts = forecast.forecast_all(SNAP30, scenario)
        up, down = forecasts["noisy_up"], forecasts["noisy_down"]
        assert up["thin_data"] is False and down["thin_data"] is False
        assert up["projected"] > config.TREND_THRESHOLD > up["projected_low"] + 0.1
        assert down["projected"] < -config.TREND_THRESHOLD < down["projected_high"] - 0.1
        assert up["trajectory"] == "stable" and down["trajectory"] == "stable"


def test_is_estimate_is_the_literal_true_for_every_forecast():
    for snap in (SNAP30, SNAP3, SNAP6, SNAPEX):
        for f in forecast.forecast_all(snap, "fast").values():
            assert f["is_estimate"] is True


def test_trend_uncertainty_is_inflated_by_the_documented_factor_and_only_it(monkeypatch):
    """SPEC 5.1: s = 12 * SE_b * SE_INFLATION (1.9); the growth g itself is untouched."""
    totals = [m["total_posts"] for m in SNAP30["months"]]
    smoothed = forecast.smooth(SNAP30["skills"]["noisy_up"]["shares"])
    assert config.SE_INFLATION == 1.9
    g, s = forecast.trend(smoothed, totals)
    monkeypatch.setattr(config, "SE_INFLATION", 1.0)
    g_plain, s_plain = forecast.trend(smoothed, totals)
    assert g == pytest.approx(g_plain, rel=1e-12) and s == pytest.approx(1.9 * s_plain, rel=1e-12)
    monkeypatch.setattr(config, "SE_INFLATION", 2.5)
    assert forecast.trend(smoothed, totals)[1] == pytest.approx(2.5 * s_plain, rel=1e-12)


def test_plain_momentum_interval_uses_the_inflated_uncertainty():
    totals = [m["total_posts"] for m in SNAP30["months"]]
    smoothed = forecast.smooth(SNAP30["skills"]["noisy_up"]["shares"])
    g, s = forecast.trend(smoothed, totals)
    r, low, high = forecast.momentum(smoothed, totals)
    assert (r, low, high) == pytest.approx((math.exp(g) - 1, math.exp(g - 1.28 * s) - 1, math.exp(g + 1.28 * s) - 1), rel=1e-12)
