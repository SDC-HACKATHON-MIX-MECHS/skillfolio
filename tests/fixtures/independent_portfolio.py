"""Independent recomputation of the portfolio numbers in docs/SPEC.md section 5.2.

Deliberately does NOT import anything from engine/. Per-skill forecast numbers (projected growth,
exposure, thin flag) come from independent_expected.py, which is also engine-free. Uses pandas + numpy.
Written from the SPEC text, before engine/portfolio.py implemented it.

Run:  python tests/fixtures/independent_portfolio.py      (rewrites golden_portfolio.json)

Rules implemented (from the SPEC, plus the two decisions recorded below):
  weights      w_i = L_i / sum(L)
  growth R     = sum w_i * r_i,  r_i = the skill's `projected` growth under the chosen scenario;
               DECISION: a thin-data skill's r_i is clamped to +/-THIN_GROWTH_CAP before it is averaged,
               so a skill we cannot trust never headlines the portfolio (SPEC 5.1 caveat)
  exposure E   = sum w_i e_i over skills with a KNOWN exposure, weights renormalised over those skills;
               DECISION: None when no skill has a known exposure
  covariance   = 12 * sample covariance (ddof = 1) of the monthly changes of ln(smoothed + eps) over the last
               24 smoothed months (same eps and window as the forecast volatility), then shrunk
               50% toward its diagonal: off-diagonals x 0.5, diagonal unchanged
  volatility   sigma_p = sqrt(w' Sigma w)  (a one-skill portfolio therefore has sigma_p = that skill's volatility)
  diversif. D  = 1 - sum w_i^2
  readiness U  = R - gamma/2 * sigma_p^2
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

assert "engine" not in sys.modules, "this script must stay independent of the engine"

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import independent_expected as ie  # noqa: E402  (engine-free)

ROOT = HERE.parents[1]
GAMMA = {"low": 1.5, "medium": 0.75, "high": 0.25}
THIN_GROWTH_CAP = 0.05
SHRINK = 0.5
WINDOW = 24
SCENARIOS = ("moderate", "fast")

# case name -> (snapshot key from independent_expected.SNAPSHOTS, [(skill_id, level), ...])
CASES = {
    "single_u_turn": ("30m", [("u_turn", 2)]),
    "mixed_with_thin_and_unknown": ("30m", [("u_turn", 3), ("noisy_early", 2), ("sparse", 1), ("unknown_exp", 2), ("shift_up", 1)]),
    "all_thin": ("30m", [("sparse", 2), ("sparse_clumpy", 1), ("all_zero", 2)]),
    "all_unknown_exposure": ("30m", [("unknown_exp", 2)]),
    "equal_pair": ("30m", [("shift_up", 2), ("shift_down", 2)]),
    "example_three": ("example", [("rising_skill", 3), ("flat_skill", 2), ("falling_skill", 1)]),
    "flat6_with_thin_riser": ("flat6", [("noisy1", 1), ("noisy2", 1), ("noisy3", 2), ("thin_riser", 3)]),
}


def covariance(snapshot, skill_ids):
    eps = ie.expected(snapshot)["epsilon"]
    changes = {}
    for sid in skill_ids:
        shares = pd.Series(snapshot["skills"][sid]["shares"], dtype=float)
        smoothed = shares.rolling(3, min_periods=1).mean().to_numpy()[-WINDOW:]
        changes[sid] = np.diff(np.log(smoothed + eps))
    frame = pd.DataFrame(changes)
    if len(frame) < 2:
        return np.zeros((len(skill_ids), len(skill_ids)))
    cov = 12 * frame.cov().to_numpy()
    return (1 - SHRINK) * cov + SHRINK * np.diag(np.diag(cov))


def metrics(levels, forecast_numbers, scenario, cov, risk):
    ids = [s for s, _ in levels]
    w = np.array([lv for _, lv in levels], float)
    w = w / w.sum()
    r = np.array([forecast_numbers[s]["scenarios"][scenario]["projected"] for s in ids])
    thin = np.array([forecast_numbers[s]["thin_data"] for s in ids])
    r = np.where(thin, np.clip(r, -THIN_GROWTH_CAP, THIN_GROWTH_CAP), r)
    growth = float(w @ r)
    exposure = [forecast_numbers[s]["exposure"] for s in ids]
    known = np.array([e is not None for e in exposure])
    e_value = None if not known.any() else float(sum(wi * e for wi, e in zip(w[known], np.array(exposure, dtype=object)[known])) / w[known].sum())
    vol = float(np.sqrt(w @ cov @ w))
    return {
        "growth": growth,
        "ai_exposure": e_value,
        "volatility": vol,
        "diversification": float(1 - (w ** 2).sum()),
        "readiness": growth - GAMMA[risk] / 2 * vol ** 2,
    }


def build():
    out = {"gamma": GAMMA, "thin_growth_cap": THIN_GROWTH_CAP, "cases": {}}
    cache = {}
    for name, (snap_key, levels) in CASES.items():
        if snap_key not in cache:
            snapshot = json.loads(ie.SNAPSHOTS[snap_key].read_text(encoding="utf-8"))
            cache[snap_key] = (snapshot, ie.expected(snapshot))
        snapshot, expected = cache[snap_key]
        ids = [s for s, _ in levels]
        numbers = {s: dict(expected["skills"][s], exposure=snapshot["skills"][s]["exposure"]) for s in ids}
        cov = covariance(snapshot, ids)
        out["cases"][name] = {
            "snapshot": snap_key,
            "skills": [{"skill_id": s, "level": lv} for s, lv in levels],
            "cov": cov.tolist(),
            "metrics": {sc: {risk: metrics(levels, numbers, sc, cov, risk) for risk in GAMMA} for sc in SCENARIOS},
        }
    return out


if __name__ == "__main__":
    result = build()
    (HERE / "golden_portfolio.json").write_bytes((json.dumps(result, indent=1) + "\n").encode("utf-8"))
    for name, case in result["cases"].items():
        m = case["metrics"]["moderate"]["medium"]
        e = "None" if m["ai_exposure"] is None else f"{m['ai_exposure']:.4f}"
        print(f"{name:<30} R={m['growth']:+.4f} E={e} vol={m['volatility']:.4f} D={m['diversification']:.4f} U={m['readiness']:+.4f}")
