"""Independent recomputation of everything engine/api.analyse returns, from the SPEC rules only.

Deliberately does NOT import anything from engine/. It reuses the other engine-free generators
(independent_expected: forecasts; independent_portfolio: covariance and metrics; independent_matching:
role scoring and its fixture roles) and adds its own SDG allocation. Written before engine/api.py.

Run:  python tests/fixtures/independent_api.py      (rewrites golden_api.json)

What analyse() must return for a profile on snapshot_30m with the fixture roles of independent_matching:
  skills        one row per kept profile skill, in profile order: level, weight = level / sum(levels of the kept skills),
                projected growth for the scenario, thin flag, exposure, SDG list (baseline 4 first, then ascending)
  dropped       profile skills that the snapshot has no series for (listed, not scored)
  portfolio     independent_portfolio.metrics for the kept skills
  matches       independent_matching ranking, first TOP_N = 5
  sdg           each kept skill's weight split equally over its SDGs; shares sum to 1; ordered by share desc, SDG asc
"""

import json
import sys
from fractions import Fraction
from pathlib import Path

assert "engine" not in sys.modules, "this script must stay independent of the engine"

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import independent_expected as ie  # noqa: E402
import independent_matching as im  # noqa: E402
import independent_portfolio as ip  # noqa: E402

TOP_N = 5
BASELINE, MIN_WEIGHT = 4, 2

PROFILES = {
    "full_profile": {"profile_id": "p_full", "risk_tolerance": "medium", "sdg_interests": [9, 13],
                     "skills": [{"skill_id": s, "level": lv} for s, lv in [("u_turn", 3), ("noisy_early", 1), ("shift_up", 2), ("shift_down", 3), ("exactly_3", 3), ("faded", 1)]]},
    "unknown_skill_dropped": {"profile_id": "p_drop", "risk_tolerance": "low", "sdg_interests": [8],
                              "skills": [{"skill_id": "ghost_skill", "level": 3}, {"skill_id": "u_turn", "level": 2}, {"skill_id": "sparse", "level": 1}]},
    "no_sdg_interests_high_risk": {"profile_id": "p_nosdg", "risk_tolerance": "high",
                                   "skills": [{"skill_id": "shift_up", "level": 1}, {"skill_id": "unknown_exp", "level": 1}]},
}


def sdgs_of(skill):
    by_role = {r["role_id"]: r["sdgs"] for r in im.ROLES}
    found = {s for rw in im.ROLE_SKILLS if rw["skill_id"] == skill and rw["weight"] >= MIN_WEIGHT and rw["role_id"] in by_role for s in by_role[rw["role_id"]]}
    return [BASELINE] + sorted(found - {BASELINE})


def allocation(weights):
    shares = {}
    for skill, w in weights.items():
        sdgs = sdgs_of(skill)
        for s in sdgs:
            shares[s] = shares.get(s, Fraction(0)) + Fraction(w).limit_denominator(10**6) / len(sdgs)
    return [[s, float(v)] for s, v in sorted(shares.items(), key=lambda kv: (-kv[1], kv[0]))]


def build():
    snapshot = json.loads(ie.SNAPSHOTS["30m"].read_text(encoding="utf-8"))
    expected = ie.expected(snapshot)
    out = {"top_n": TOP_N, "profiles": PROFILES, "cases": {}}
    for name, profile in PROFILES.items():
        kept = [s for s in profile["skills"] if s["skill_id"] in snapshot["skills"]]
        dropped = [s["skill_id"] for s in profile["skills"] if s["skill_id"] not in snapshot["skills"]]
        ids = [s["skill_id"] for s in kept]
        total = sum(s["level"] for s in kept)
        weights = {s["skill_id"]: s["level"] / total for s in kept}
        levels = {s["skill_id"]: s["level"] for s in kept}
        numbers = {i: dict(expected["skills"][i], exposure=snapshot["skills"][i]["exposure"]) for i in ids}
        cov = ip.covariance(snapshot, ids)
        user_sdgs = profile.get("sdg_interests", [])
        for scenario in ("moderate", "fast"):
            matches = {}
            for role in im.ROLES:
                rows = [r for r in im.ROLE_SKILLS if r["role_id"] == role["role_id"]]
                if rows and role["role_type"] == "future":
                    matches[role["role_id"]] = im.score(role, rows, levels, user_sdgs, expected["skills"], scenario)
            ranked = sorted(matches.values(), key=lambda m: (-m["rank_score"], -m["match_pct"], m["role_id"]))[:TOP_N]
            out["cases"][f"{name}/{scenario}"] = {
                "profile": name, "scenario": scenario, "dropped": dropped,
                "skills": [{"skill_id": i, "level": levels[i], "weight": weights[i], "projected": numbers[i]["scenarios"][scenario]["projected"],
                            "thin_data": numbers[i]["thin_data"], "exposure": numbers[i]["exposure"], "sdgs": sdgs_of(i)} for i in ids],
                "portfolio": ip.metrics([(i, levels[i]) for i in ids], numbers, scenario, cov, profile["risk_tolerance"]),
                "sdg": allocation(weights),
                "match_ids": [m["role_id"] for m in ranked],
                "matches": {m["role_id"]: m for m in ranked},
            }
    return out


if __name__ == "__main__":
    result = build()
    (HERE / "golden_api.json").write_bytes((json.dumps(result, indent=1) + "\n").encode("utf-8"))
    for name, c in result["cases"].items():
        p = c["portfolio"]
        e = "None" if p["ai_exposure"] is None else f"{p['ai_exposure']:.3f}"
        print(f"{name:<36} dropped={c['dropped']} R={p['growth']:+.3f} E={e} U={p['readiness']:+.3f} top={c['match_ids'][:3]} sdg={c['sdg'][:3]}")
