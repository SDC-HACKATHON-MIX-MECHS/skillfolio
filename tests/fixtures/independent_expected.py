"""Independent recomputation of the forecast numbers in docs/SPEC.md section 5.1.

Deliberately does NOT import anything from engine/. Uses pandas + numpy (least squares with an
explicit covariance matrix for the standard error), so it can disagree with engine/forecast.py.

Run:  python tests/fixtures/independent_expected.py   (rewrites golden_30m.json and golden_3m.json)

Rules implemented (from the SPEC, not from the engine code):
  eps       = 0.5 / mean(total_posts)
  smoothed  = trailing 3-month mean, partial at the start
  momentum  = OLS of ln(smoothed + eps) on 0..n-1 over the last min(12, M) months (needs n >= 3),
              r = exp(12 b) - 1, interval b -/+ 1.28 SE
  volatility= sample std of diffs of ln(smoothed + eps) over the last 24 smoothed values, x sqrt(12)
  scenarios = lambda moderate 0.10, fast 0.30; shift = lambda * (exposure - mean known exposure)
  label     = stable if thin; rising if projected_low > 0.05; declining if projected_high < -0.05
  thin      = history < 3 or mean monthly count < 3
  history < 3 -> momentum, interval and projections are all 0
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

assert "engine" not in sys.modules, "this script must stay independent of the engine"

HERE = Path(__file__).resolve().parent
LAMBDA = {"moderate": 0.10, "fast": 0.30}


def ols(y):
    n = len(y)
    X = np.column_stack([np.ones(n), np.arange(n)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    sigma2 = resid @ resid / (n - 2)
    cov = sigma2 * np.linalg.inv(X.T @ X)
    return beta[1], float(np.sqrt(cov[1, 1]))


def expected(snapshot):
    totals = np.array([m["total_posts"] for m in snapshot["months"]], float)
    eps = 0.5 / totals.mean() if len(totals) and totals.mean() > 0 else 0.5
    known = [s["exposure"] for s in snapshot["skills"].values() if s["exposure"] is not None]
    ebar = float(np.mean(known))
    out = {"epsilon": eps, "mean_exposure": ebar, "skills": {}}
    for sid, s in snapshot["skills"].items():
        shares = pd.Series(s["shares"], dtype=float)
        smoothed = shares.rolling(3, min_periods=1).mean().to_numpy()
        history = len(shares)
        enough = history >= 3
        if enough:
            n = min(12, history)
            b, se = ols(np.log(smoothed[-n:] + eps))
            ann = lambda x: float(np.exp(12 * x) - 1)
            r, lo, hi = ann(b), ann(b - 1.28 * se), ann(b + 1.28 * se)
        else:
            r = lo = hi = 0.0
        d = np.diff(np.log(smoothed[-24:] + eps))
        vol = float(d.std(ddof=1) * np.sqrt(12)) if len(d) >= 2 else 0.0
        base = next((v for v in smoothed if v > 0), None)
        index = [0.0] * history if base is None else [float(100 * v / base) for v in smoothed]
        thin = (not enough) or float(np.mean(s["counts"])) < 3
        per_scenario = {}
        for name, lam in LAMBDA.items():
            shift = 0.0 if (s["exposure"] is None or not enough) else lam * (s["exposure"] - ebar)
            plo, phi = lo - shift, hi - shift
            label = "stable" if thin else ("rising" if plo > 0.05 else "declining" if phi < -0.05 else "stable")
            per_scenario[name] = {"projected": r - shift, "projected_low": plo, "projected_high": phi, "trajectory": label}
        out["skills"][sid] = {"momentum": r, "momentum_low": lo, "momentum_high": hi, "volatility": vol,
                              "thin_data": bool(thin), "history_months": history, "index": index, "scenarios": per_scenario}
    return out


if __name__ == "__main__":
    for name in ("30m", "3m"):
        snap = json.loads((HERE / f"snapshot_{name}.json").read_text(encoding="utf-8"))
        result = expected(snap)
        (HERE / f"golden_{name}.json").write_bytes((json.dumps(result, indent=1) + "\n").encode("utf-8"))
        print(f"== {name}: eps={result['epsilon']:.6f} mean exposure={result['mean_exposure']:.4f}")
        for sid, v in result["skills"].items():
            f, m = v["scenarios"]["fast"], v["scenarios"]["moderate"]
            print(f"  {sid:<14} r={v['momentum']:+9.4f} [{v['momentum_low']:+9.4f},{v['momentum_high']:+9.4f}] vol={v['volatility']:.4f} "
                  f"thin={v['thin_data']!s:<5} mod={m['trajectory']:<9} fast={f['trajectory']}")
