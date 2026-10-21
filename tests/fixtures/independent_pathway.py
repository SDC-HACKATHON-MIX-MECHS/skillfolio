"""Independent recomputation of the reskilling plan in docs/SPEC.md section 5.4.

Deliberately does NOT import anything from engine/. Reuses the engine-free generators (independent_expected: forecasts,
independent_portfolio: covariance and metrics, independent_matching: role scoring and fixture roles). Written from the
SPEC text, before engine/pathway.py implemented it.

Run:  python tests/fixtures/independent_pathway.py      (rewrites golden_pathway.json)

Rules implemented (SPEC 5.4, plus the decisions recorded here):
  gap skills   = skills of the target role where the user's level < the required level
  candidates   = courses that (1) teach a gap skill, (2) raise it: level_out > the user's current level of that skill,
                 (3) have a skill the snapshot has a series for (otherwise they cannot be scored), (4) fit the remaining hours
                 (hours <= remaining), (5) fit the remaining RM budget when one is given, (6) have their prerequisite met by the
                 CURRENT levels (prereq_skill_id at prereq_level or more), levels that earlier steps raised count
  score        = (dU + BETA * dM) / hours, dU = readiness after taking the course minus now (portfolio of all the user's skills,
                 a newly learned skill joins it with weight level/sum), dM = the target role's match % after minus now
  pick         = the highest score; exact ties go to the lower cost, then the smaller course_id
  stop         = when no candidate is left, or the best score is <= 0 (a step that does not help is not recommended)
  apply        = the skill's level becomes level_out; repeat
  output       = steps (with cumulative hours and RM), before and after = portfolio metrics + match_pct, hours_used, cost_used
"""

import json
import sys
from pathlib import Path

assert "engine" not in sys.modules, "this script must stay independent of the engine"

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import independent_expected as ie  # noqa: E402
import independent_matching as im  # noqa: E402
import independent_portfolio as ip  # noqa: E402

BETA = 1.0


def course(cid, skill, level_out, hours, cost=0, prereq=None, prereq_level=None, hrdc="unknown"):
    return {"course_id": cid, "title": f"Course {cid}", "provider": f"Provider of {cid}", "url": f"https://example.org/{cid}", "skill_id": skill,
            "level_out": level_out, "hours": hours, "cost_rm": cost, "hrdc_claimable": hrdc,
            "prereq_skill_id": prereq or "", "prereq_level": prereq_level}


COURSES = [
    course("c_up2", "shift_up", 2, 10, hrdc="yes"),
    course("c_up3", "shift_up", 3, 20, prereq="shift_up", prereq_level=2),
    course("c_down1", "shift_down", 1, 6),
    course("c_a_down1", "shift_down", 1, 6),                      # identical to c_down1: the smaller id wins the tie
    course("c_down2", "shift_down", 2, 14, prereq="shift_down", prereq_level=1),
    course("c_unk1", "unknown_exp", 1, 4, cost=50),
    course("c_other", "u_turn", 3, 8),                            # not a gap skill of the target role
    course("c_ghost", "ghost", 3, 3),                             # the snapshot has no series for it
    course("c_low", "shift_up", 1, 2),                            # does not raise shift_up above the user's level 1
    course("c_noisy", "noisy_early", 2, 3),                       # noisy_early is not a gap skill of r_ops
    course("c_downgrade", "shift_up", 1, 3),                      # LOWERS shift_up from the user's level 2: never a step
    course("c_uturn3", "u_turn", 3, 5),                           # u_turn is already at the required level for r_data
    course("c_dear_up2", "shift_up", 2, 10, cost=40),
    course("c_cross_prereq", "unknown_exp", 1, 5, prereq="u_turn", prereq_level=3),   # prerequisite is another skill: u_turn >= 3
]

CASES = {
    "ops_plenty_of_hours": dict(target="r_ops", levels={"shift_up": 1, "u_turn": 2}, risk="low", hours=100, rm=None, scenario="moderate"),
    "ops_tight_hours": dict(target="r_ops", levels={"shift_up": 1, "u_turn": 2}, risk="low", hours=15, rm=None, scenario="moderate"),
    "ops_fast_medium": dict(target="r_ops", levels={"shift_up": 1, "u_turn": 2}, risk="medium", hours=40, rm=None, scenario="fast"),
    "ops_rm_budget": dict(target="r_ops", levels={"shift_up": 1, "u_turn": 2}, risk="low", hours=100, rm=30, scenario="moderate"),
    "ops_zero_hours": dict(target="r_ops", levels={"shift_up": 1, "u_turn": 2}, risk="low", hours=0, rm=None, scenario="moderate"),
    "ops_prereq_from_other_skill": dict(target="r_ops", levels={"shift_up": 3, "shift_down": 2, "u_turn": 3}, risk="high", hours=50, rm=None, scenario="moderate"),
    "data_gap_and_thin_skill": dict(target="r_data", levels={"noisy_early": 1, "exactly_3": 2}, risk="medium", hours=30, rm=None, scenario="moderate"),
    "tie_break_only_two": dict(target="r_ops", levels={"shift_up": 3}, risk="medium", hours=100, rm=None, scenario="moderate", only=["c_down1", "c_a_down1"]),
    "exact_hours_fit": dict(target="r_ops", levels={"shift_up": 3}, risk="medium", hours=6, rm=None, scenario="moderate", only=["c_down1"]),
    "one_hour_short": dict(target="r_ops", levels={"shift_up": 3}, risk="medium", hours=5.99, rm=None, scenario="moderate", only=["c_down1"]),
    "prereq_on_other_skill_unmet": dict(target="r_ops", levels={"shift_up": 3, "u_turn": 2}, risk="medium", hours=100, rm=None, scenario="moderate", only=["c_cross_prereq"]),
    "prereq_on_other_skill_met": dict(target="r_ops", levels={"shift_up": 3, "u_turn": 3}, risk="medium", hours=100, rm=None, scenario="moderate", only=["c_cross_prereq"]),
    "exact_rm_fit": dict(target="r_ops", levels={"shift_up": 3}, risk="medium", hours=100, rm=50, scenario="moderate", only=["c_unk1"]),
    "rm_one_short": dict(target="r_ops", levels={"shift_up": 3}, risk="medium", hours=100, rm=49.99, scenario="moderate", only=["c_unk1"]),
    "downgrade_course_never_a_step": dict(target="r_ops", levels={"shift_up": 2, "u_turn": 2}, risk="medium", hours=50, rm=None, scenario="moderate", only=["c_downgrade"]),
    "met_skill_is_not_trained_again": dict(target="r_data", levels={"u_turn": 2, "exactly_3": 2}, risk="medium", hours=50, rm=None, scenario="moderate", only=["c_uturn3"]),
    "course_for_a_skill_without_a_series": dict(target="r_ghost", levels={"u_turn": 2}, risk="medium", hours=50, rm=None, scenario="moderate", only=["c_ghost"]),
    "rm_budget_is_cumulative": dict(target="r_ops", levels={"shift_up": 1}, risk="medium", hours=100, rm=60, scenario="moderate", only=["c_unk1", "c_dear_up2"]),
    "rm_budget_roomy": dict(target="r_ops", levels={"shift_up": 1}, risk="medium", hours=100, rm=100, scenario="moderate", only=["c_unk1", "c_dear_up2"]),
    "nothing_to_learn": dict(target="r_ops", levels={"shift_up": 3, "shift_down": 2, "unknown_exp": 1}, risk="low", hours=50, rm=None, scenario="moderate"),
}


def portfolio_numbers(levels, risk, scenario, snapshot, numbers, cov_cache):
    ids = list(levels)
    key = tuple(ids)
    if key not in cov_cache:
        cov_cache[key] = ip.covariance(snapshot, ids)
    return ip.metrics([(i, levels[i]) for i in ids], numbers, scenario, cov_cache[key], risk)


def evaluate(levels, role, rows, risk, scenario, snapshot, numbers, expected_skills, cov_cache):
    m = portfolio_numbers(levels, risk, scenario, snapshot, numbers, cov_cache)
    match = im.score(role, rows, levels, [], expected_skills, scenario)["match_pct"]
    return m, match


def plan(case, snapshot, expected):
    role = next(r for r in im.ROLES if r["role_id"] == case["target"])
    rows = [r for r in im.ROLE_SKILLS if r["role_id"] == role["role_id"]]
    required = {r["skill_id"]: r["required_level"] for r in rows}
    scenario, risk = case["scenario"], case["risk"]
    numbers = {i: dict(expected["skills"][i], exposure=snapshot["skills"][i]["exposure"]) for i in snapshot["skills"]}
    cov_cache = {}
    levels = dict(case["levels"])
    before_m, before_match = evaluate(levels, role, rows, risk, scenario, snapshot, numbers, expected["skills"], cov_cache)
    steps, hours_used, cost_used = [], 0.0, 0.0
    taken = set()
    while True:
        best = None
        for c in COURSES:
            if case.get("only") and c["course_id"] not in case["only"]:
                continue
            skill = c["skill_id"]
            if c["course_id"] in taken or skill not in snapshot["skills"] or skill not in required:
                continue
            current = levels.get(skill, 0)
            if current >= required[skill] or c["level_out"] <= current:
                continue
            if c["hours"] > case["hours"] - hours_used:
                continue
            if case["rm"] is not None and c["cost_rm"] > case["rm"] - cost_used:
                continue
            if c["prereq_skill_id"] and levels.get(c["prereq_skill_id"], 0) < c["prereq_level"]:
                continue
            trial = dict(levels, **{skill: c["level_out"]})
            now_m, now_match = evaluate(levels, role, rows, risk, scenario, snapshot, numbers, expected["skills"], cov_cache)
            new_m, new_match = evaluate(trial, role, rows, risk, scenario, snapshot, numbers, expected["skills"], cov_cache)
            gain = ((new_m["readiness"] - now_m["readiness"]) + BETA * (new_match - now_match)) / c["hours"]
            key = (-gain, c["cost_rm"], c["course_id"])
            if best is None or key < best[0]:
                best = (key, c, gain, current)
        if best is None or best[2] <= 0:
            break
        _, c, gain, current = best
        taken.add(c["course_id"])
        levels[c["skill_id"]] = c["level_out"]
        hours_used += c["hours"]
        cost_used += c["cost_rm"]
        steps.append({"order": len(steps) + 1, "course_id": c["course_id"], "skill_id": c["skill_id"], "level_before": current, "level_out": c["level_out"],
                      "title": c["title"], "provider": c["provider"], "url": c["url"], "hrdc_claimable": c["hrdc_claimable"],
                      "hours": c["hours"], "cost_rm": c["cost_rm"], "gain_per_hour": gain, "cumulative_hours": hours_used, "cumulative_cost_rm": cost_used})
    after_m, after_match = evaluate(levels, role, rows, risk, scenario, snapshot, numbers, expected["skills"], cov_cache)
    return {"steps": steps, "before": dict(before_m, match_pct=before_match), "after": dict(after_m, match_pct=after_match),
            "hours_used": hours_used, "cost_used": cost_used}


def build():
    snapshot = json.loads(ie.SNAPSHOTS["30m"].read_text(encoding="utf-8"))
    expected = ie.expected(snapshot)
    out = {"beta": BETA, "courses": COURSES, "cases": {}}
    for name, case in CASES.items():
        out["cases"][name] = {"input": case, "plan": plan(case, snapshot, expected)}
    return out


if __name__ == "__main__":
    result = build()
    (HERE / "golden_pathway.json").write_bytes((json.dumps(result, indent=1) + "\n").encode("utf-8"))
    for name, c in result["cases"].items():
        p = c["plan"]
        print(f"{name:<30} steps={[s['course_id'] for s in p['steps']]} hours={p['hours_used']} rm={p['cost_used']} "
              f"match {p['before']['match_pct']:.3f}->{p['after']['match_pct']:.3f} U {p['before']['readiness']:+.3f}->{p['after']['readiness']:+.3f}")
