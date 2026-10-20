"""Independent recomputation of the SDG-lens numbers in docs/SPEC.md section 5.5.

Deliberately does NOT import anything from engine/. Written from the SPEC text, before engine/sdg.py implemented it.

Run:  python tests/fixtures/independent_sdg.py      (rewrites golden_sdg.json)

Rules implemented:
  skill SDGs   = {4} (the baseline: SDG 4, target 4.4) plus the SDGs of every role that weights the skill >= 2
                 (origin roles count too; rows naming a role that is not in the roles list are ignored);
                 listed as 4 first, then the others ascending, no repeats
  allocation   = each skill's portfolio weight is split EQUALLY across that skill's SDGs; an SDG's share is the sum of
                 the pieces it receives. The shares sum to 1. Listed by share (high to low), then SDG number.
"""

import json
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE, MIN_WEIGHT = 4, 2

ROLES = [
    {"role_id": "R1", "sdgs": [7, 13]},
    {"role_id": "R2", "sdgs": [4, 8]},
    {"role_id": "R3", "sdgs": [16, 16]},
    {"role_id": "R4_origin", "sdgs": [8, 10]},
    {"role_id": "R5_no_skills", "sdgs": [17]},
]


def row(role, skill, weight):
    return {"role_id": role, "skill_id": skill, "weight": weight, "required_level": 1}


ROLE_SKILLS = [
    row("R1", "s_green", 3), row("R1", "s_mix", 2),
    row("R2", "s_mix", 3), row("R2", "s_light", 1),
    row("R3", "s_light", 1), row("R3", "s_mix", 2),
    row("R4_origin", "s_origin", 2), row("R4_origin", "s_mix", 1),
    row("not_a_role", "s_ghost", 3),
]
SKILLS = ["s_green", "s_mix", "s_light", "s_origin", "s_ghost", "s_alone"]

PORTFOLIOS = {
    "three_skills": {"s_green": 0.5, "s_mix": 0.3, "s_alone": 0.2},
    "single_mixed_skill": {"s_mix": 1.0},
    "only_baseline_skills": {"s_alone": 0.6, "s_ghost": 0.4},
    "equal_weights": {"s_green": 0.25, "s_mix": 0.25, "s_light": 0.25, "s_origin": 0.25},
}


def skill_sdgs(skill):
    roles = {r["role_id"]: r["sdgs"] for r in ROLES}
    found = {s for rw in ROLE_SKILLS if rw["skill_id"] == skill and rw["weight"] >= MIN_WEIGHT and rw["role_id"] in roles for s in roles[rw["role_id"]]}
    return [BASELINE] + sorted(found - {BASELINE})


def allocation(weights):
    shares = {}
    for skill, w in weights.items():
        sdgs = skill_sdgs(skill)
        for s in sdgs:
            shares[s] = shares.get(s, Fraction(0)) + Fraction(w).limit_denominator(1000) / len(sdgs)
    ordered = sorted(shares.items(), key=lambda kv: (-kv[1], kv[0]))
    return [[s, float(v)] for s, v in ordered]


if __name__ == "__main__":
    out = {"baseline": BASELINE, "min_weight": MIN_WEIGHT, "roles": ROLES, "role_skills": ROLE_SKILLS,
           "skill_sdgs": {s: skill_sdgs(s) for s in SKILLS},
           "portfolios": {n: {"weights": w, "allocation": allocation(w)} for n, w in PORTFOLIOS.items()}}
    (HERE / "golden_sdg.json").write_bytes((json.dumps(out, indent=1) + "\n").encode("utf-8"))
    for s in SKILLS:
        print(f"{s:10} {out['skill_sdgs'][s]}")
    for n, p in out["portfolios"].items():
        print(f"{n:22} {p['allocation']}")
