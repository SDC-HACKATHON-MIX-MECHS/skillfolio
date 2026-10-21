"""Independent recomputation of the role-matching numbers in docs/SPEC.md section 5.3.

Deliberately does NOT import anything from engine/. Per-skill projected growth and thin flags come from
independent_expected.py (also engine-free). Written from the SPEC text, before engine/matching.py implemented it.

Run:  python tests/fixtures/independent_matching.py      (rewrites golden_matching.json)

Rules implemented (SPEC 5.3, plus the decisions recorded here):
  credit_j     = min(L_j / req_j, 1), L_j = 0 when the user lacks the skill
  match M      = sum_j w_j credit_j / sum_j w_j
  gaps         = role skills with L_j < req_j (including partly met ones), sorted by w desc, req desc, skill_id
  contributions= role skills with credit > 0, sorted by w desc, credit desc, skill_id
  role growth  = sum_j (w_j / sum w) r_j, r_j = the skill's `projected` growth for the scenario;
                 DECISION: a thin-data skill's r_j is clamped to +/-THIN_GROWTH_CAP (5%), as in portfolio growth, so one
                 thin skill cannot decide a ranking; DECISION: a role skill with no forecast counts as growth 0
  SDG overlap  = |role SDGs & user SDGs| / max(1, |user SDGs|)   (sets, so repeats do not count twice)
  rank score   = M (1 + R_role) (1 + alpha O),  alpha = 0.15
  ranking      = only role_type == 'future' roles that have at least one skill row, by rank score desc,
                 then match desc, then role_id asc
"""

import json
import sys
from pathlib import Path

assert "engine" not in sys.modules, "this script must stay independent of the engine"

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import independent_expected as ie  # noqa: E402  (engine-free)

ALPHA = 0.15
THIN_GROWTH_CAP = 0.05
SCENARIOS = ("moderate", "fast")

ROLES = [
    {"role_id": "r_tie_b", "title": "Tie B", "role_type": "future", "ai_exposure": 0.30, "sdgs": [8]},
    {"role_id": "r_data", "title": "Data role", "role_type": "future", "ai_exposure": 0.40, "sdgs": [9, 8]},
    {"role_id": "r_ops", "title": "Ops role", "role_type": "future", "ai_exposure": 0.20, "sdgs": [8, 10]},
    {"role_id": "r_green", "title": "Green role", "role_type": "future", "ai_exposure": None, "sdgs": [7, 13]},
    {"role_id": "r_ghost", "title": "Role with a skill missing from the snapshot", "role_type": "future", "ai_exposure": 0.10, "sdgs": [4]},
    {"role_id": "r_origin", "title": "Origin role (not ranked)", "role_type": "origin", "ai_exposure": 0.70, "sdgs": [8]},
    {"role_id": "r_empty", "title": "Role without skills", "role_type": "future", "ai_exposure": 0.10, "sdgs": [9]},
    {"role_id": "r_tie_a", "title": "Tie A", "role_type": "future", "ai_exposure": 0.30, "sdgs": [8]},
]


def rs(role, skill, weight, req, source="onet_in_demand"):
    return {"role_id": role, "skill_id": skill, "weight": weight, "required_level": req, "source": source}


ROLE_SKILLS = [
    rs("r_data", "u_turn", 3, 2), rs("r_data", "noisy_early", 2, 1, "onet_hot"), rs("r_data", "sparse", 1, 2),
    rs("r_ops", "shift_up", 3, 3), rs("r_ops", "shift_down", 2, 2), rs("r_ops", "unknown_exp", 1, 1),
    rs("r_green", "faded", 2, 2), rs("r_green", "exactly_3", 2, 1),
    rs("r_ghost", "ghost", 2, 1), rs("r_ghost", "u_turn", 2, 1),
    rs("r_origin", "shift_up", 3, 1),
    rs("r_tie_b", "shift_up", 1, 1), rs("r_tie_a", "shift_up", 1, 1),
]

USERS = {
    "full_profile": ({"u_turn": 3, "noisy_early": 1, "shift_up": 2, "shift_down": 3, "exactly_3": 3, "faded": 1}, [9, 13]),
    "empty_profile": ({}, []),
    "thin_and_repeated_sdgs": ({"sparse": 3, "u_turn": 1}, [8, 8, 9]),
}


def score(role, rows, levels, sdgs, numbers, scenario):
    total_w = sum(r["weight"] for r in rows)
    contributions, gaps, match, growth = [], [], 0.0, 0.0
    for r in rows:
        level = levels.get(r["skill_id"], 0)
        credit = min(level / r["required_level"], 1.0)
        match += r["weight"] * credit / total_w
        n = numbers.get(r["skill_id"])
        if n is not None:
            proj = n["scenarios"][scenario]["projected"]
            if n["thin_data"]:
                proj = max(-THIN_GROWTH_CAP, min(THIN_GROWTH_CAP, proj))
            growth += r["weight"] / total_w * proj
        if credit > 0:
            contributions.append({"skill_id": r["skill_id"], "weight": r["weight"], "user_level": level, "required_level": r["required_level"], "credit": credit})
        if level < r["required_level"]:
            gaps.append({"skill_id": r["skill_id"], "weight": r["weight"], "user_level": level, "required_level": r["required_level"]})
    contributions.sort(key=lambda c: (-c["weight"], -c["credit"], c["skill_id"]))
    gaps.sort(key=lambda g: (-g["weight"], -g["required_level"], g["skill_id"]))
    overlap = len(set(role["sdgs"]) & set(sdgs)) / max(1, len(set(sdgs)))
    return {
        "role_id": role["role_id"], "match_pct": match, "role_growth": growth, "sdg_overlap": overlap,
        "rank_score": match * (1 + growth) * (1 + ALPHA * overlap), "contributions": contributions, "gaps": gaps,
    }


def build():
    snapshot = json.loads(ie.SNAPSHOTS["30m"].read_text(encoding="utf-8"))
    numbers = ie.expected(snapshot)["skills"]
    out = {"alpha": ALPHA, "thin_growth_cap": THIN_GROWTH_CAP, "roles": ROLES, "role_skills": ROLE_SKILLS, "cases": {}}
    for uname, (levels, sdgs) in USERS.items():
        for scenario in SCENARIOS:
            matches = {}
            for role in ROLES:
                rows = [r for r in ROLE_SKILLS if r["role_id"] == role["role_id"]]
                if rows:
                    matches[role["role_id"]] = score(role, rows, levels, sdgs, numbers, scenario)
            ranked = [m for rid, m in matches.items() if next(r for r in ROLES if r["role_id"] == rid)["role_type"] == "future"]
            ranked.sort(key=lambda m: (-m["rank_score"], -m["match_pct"], m["role_id"]))
            out["cases"][f"{uname}/{scenario}"] = {
                "user_levels": levels, "user_sdgs": sdgs, "scenario": scenario,
                "ranking": [m["role_id"] for m in ranked], "matches": matches,
            }
    return out


if __name__ == "__main__":
    result = build()
    (HERE / "golden_matching.json").write_bytes((json.dumps(result, indent=1) + "\n").encode("utf-8"))
    for name, case in result["cases"].items():
        top = case["ranking"][0]
        m = case["matches"][top]
        print(f"{name:<34} ranking={case['ranking']}  top {top}: M={m['match_pct']:.4f} R={m['role_growth']:+.4f} O={m['sdg_overlap']:.2f} score={m['rank_score']:.4f}")
