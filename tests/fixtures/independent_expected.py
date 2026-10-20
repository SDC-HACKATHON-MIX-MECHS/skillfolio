"""Independent recomputation of the forecast numbers in docs/SPEC.md section 5.1.

Deliberately does NOT import anything from engine/. Uses pandas + numpy (least squares with an
explicit covariance matrix for the standard error), so it can disagree with engine/forecast.py.
Written from the SPEC text, before the engine implemented it.

Run:  python tests/fixtures/independent_expected.py
      (rewrites golden_30m.json, golden_3m.json, golden_flat6.json, golden_example.json)

Rules implemented (from the SPEC):
  eps        = 0.5 / mean(total_posts)
  smoothed   = trailing 3-month mean, partial at the start
  trend      = OLS of ln(smoothed + eps) on 0..n-1 over the last min(12, M) months (needs n >= 3);
               g = 12 b (annual log growth), s = 12 SE_b with n-2 degrees of freedom
  thin       = history < 3 or mean monthly count (all months) < 3
  prior      = from reference skills (history >= 3 and not thin), k of them; none if k < 5:
               s* = max(s, 0.05); w = 1/s*^2; mu0 = sum(w g)/sum(w); Q = sum(w (g-mu0)^2);
               tau2_DL = max(0, (Q-(k-1)) / (sum(w) - sum(w^2)/sum(w))); tau2 = max(tau2_DL, 0.10^2);
               mu = sum(w' g)/sum(w') with w' = 1/(s*^2 + tau2)
  damping    = every skill with history >= 3: B = tau2/(tau2 + s^2) (own unfloored s);
               g' = mu + B (g - mu); s' = s sqrt(B).  No prior: g' = g, s' = s
  momentum   = exp(g') - 1; interval exp(g' -/+ 1.28 s') - 1; momentum_raw = exp(g) - 1
  scenarios  = lambda moderate 0.5, fast 1.5; delta = lambda (exposure - mean known exposure), 0 if
               exposure unknown or history < 3; projected = exp(g' - delta) - 1, interval exp(g' -/+ 1.28 s' - delta) - 1
  label      = stable if thin; rising if projected_low > 0.05; declining if projected_high < -0.05; else stable
  history < 3 -> g = s = g' = s' = 0 and every number above is 0 (projections too)
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

assert "engine" not in sys.modules, "this script must stay independent of the engine"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LAMBDA = {"moderate": 0.5, "fast": 1.5}
SE_FLOOR, TAU_FLOOR, MIN_REF_SKILLS, Z = 0.05, 0.10, 5, 1.28


def ols(y):
    n = len(y)
    X = np.column_stack([np.ones(n), np.arange(n)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    sigma2 = resid @ resid / (n - 2)
    cov = sigma2 * np.linalg.inv(X.T @ X)
    return beta[1], float(np.sqrt(cov[1, 1]))


def random_effects_prior(g, s):
    """DerSimonian-Laird between-skill variance and random-effects mean; None if too few skills."""
    k = len(g)
    if k < MIN_REF_SKILLS:
        return None
    g, s = np.array(g, float), np.maximum(np.array(s, float), SE_FLOOR)
    w = 1 / s**2
    mu0 = (w * g).sum() / w.sum()
    q = (w * (g - mu0) ** 2).sum()
    tau2_dl = max(0.0, (q - (k - 1)) / (w.sum() - (w**2).sum() / w.sum()))
    tau2 = max(tau2_dl, TAU_FLOOR**2)
    w2 = 1 / (s**2 + tau2)
    return {"k": k, "mu": float((w2 * g).sum() / w2.sum()), "tau2_dl": float(tau2_dl), "tau2": float(tau2)}


def expected(snapshot):
    totals = np.array([m["total_posts"] for m in snapshot["months"]], float)
    eps = 0.5 / totals.mean() if len(totals) and totals.mean() > 0 else 0.5
    known = [s["exposure"] for s in snapshot["skills"].values() if s["exposure"] is not None]
    ebar = float(np.mean(known))
    per = {}
    for sid, s in snapshot["skills"].items():
        shares = pd.Series(s["shares"], dtype=float)
        smoothed = shares.rolling(3, min_periods=1).mean().to_numpy()
        history = len(shares)
        enough = history >= 3
        if enough:
            b, se = ols(np.log(smoothed[-min(12, history):] + eps))
            g, sg = 12 * b, 12 * se
        else:
            g = sg = 0.0
        thin = (not enough) or float(np.mean(s["counts"])) < 3
        per[sid] = {"g": g, "s": sg, "thin": bool(thin), "enough": enough, "smoothed": smoothed, "exposure": s["exposure"]}
    ref = [v for v in per.values() if v["enough"] and not v["thin"]]
    prior = random_effects_prior([v["g"] for v in ref], [v["s"] for v in ref])
    out = {"epsilon": eps, "mean_exposure": ebar, "prior": prior, "skills": {}}
    for sid, v in per.items():
        g, sg = v["g"], v["s"]
        if prior and v["enough"]:
            b_ = prior["tau2"] / (prior["tau2"] + sg**2)
            g2, s2 = prior["mu"] + b_ * (g - prior["mu"]), sg * np.sqrt(b_)
        else:
            g2, s2 = g, sg
        smoothed = v["smoothed"]
        d = np.diff(np.log(smoothed[-24:] + eps))
        vol = float(d.std(ddof=1) * np.sqrt(12)) if len(d) >= 2 else 0.0
        base = next((x for x in smoothed if x > 0), None)
        index = [0.0] * len(smoothed) if base is None else [float(100 * x / base) for x in smoothed]
        scen = {}
        for name, lam in LAMBDA.items():
            delta = 0.0 if (v["exposure"] is None or not v["enough"]) else lam * (v["exposure"] - ebar)
            lo, hi = np.exp(g2 - Z * s2 - delta) - 1, np.exp(g2 + Z * s2 - delta) - 1
            label = "stable" if v["thin"] else ("rising" if lo > 0.05 else "declining" if hi < -0.05 else "stable")
            scen[name] = {"projected": float(np.exp(g2 - delta) - 1), "projected_low": float(lo), "projected_high": float(hi), "trajectory": label}
        out["skills"][sid] = {
            "g": g, "s": sg, "g_damped": float(g2), "s_damped": float(s2),
            "momentum_raw": float(np.exp(g) - 1), "momentum": float(np.exp(g2) - 1),
            "momentum_low": float(np.exp(g2 - Z * s2) - 1), "momentum_high": float(np.exp(g2 + Z * s2) - 1),
            "volatility": vol, "thin_data": v["thin"], "history_months": len(smoothed), "index": index, "scenarios": scen,
        }
    return out


SNAPSHOTS = {
    "30m": HERE / "snapshot_30m.json",
    "3m": HERE / "snapshot_3m.json",
    "flat6": HERE / "snapshot_flat6.json",
    "example": ROOT / "contracts" / "examples" / "snapshot.example.json",
}

if __name__ == "__main__":
    for name, path in SNAPSHOTS.items():
        result = expected(json.loads(path.read_text(encoding="utf-8")))
        (HERE / f"golden_{name}.json").write_bytes((json.dumps(result, indent=1) + "\n").encode("utf-8"))
        p = result["prior"]
        print(f"== {name}: eps={result['epsilon']:.6f} mean exposure={result['mean_exposure']:.4f} prior="
              + (f"k={p['k']} mu={p['mu']:+.4f} tau2_DL={p['tau2_dl']:.4f} tau2={p['tau2']:.4f}" if p else "none (fewer than 5 reference skills)"))
        for sid, v in result["skills"].items():
            f, m = v["scenarios"]["fast"], v["scenarios"]["moderate"]
            print(f"  {sid:<14} raw={v['momentum_raw']:+9.4f} damped={v['momentum']:+9.4f} [{v['momentum_low']:+8.4f},{v['momentum_high']:+8.4f}] "
                  f"thin={v['thin_data']!s:<5} mod={m['trajectory']:<9} fast={f['trajectory']:<9} proj mod/fast {m['projected']:+.4f}/{f['projected']:+.4f}")
