import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.ui import (
    HELP, call_or_wait, course_catalog, fmt_change, fmt_pct, fmt_rm, fmt_score, gauge_fig, page_setup, require_profile,
    risk_return_fig, role_catalog, role_skill_rows, run_engine, sdg_donut, show_fig, skill_label, source_caption,
    show_warnings, user_levels,
)
from engine import portfolio, sdg
from engine.pathway import plan

snapshot = page_setup("Rebalance Plan")
st.title("5 · Rebalance plan")
profile = require_profile()

result = run_engine(profile, snapshot)
if result is None:
    st.stop()
if not result["matches"]:
    show_warnings(result)
    st.stop()

# --- Target role ----------------------------------------------------------------------------------
roles = role_catalog()
ranked = [m["role_id"] for m in result["matches"]]
target_id = st.selectbox(
    "Target role", ranked, format_func=lambda rid: roles[rid]["title"],
    help="Starts on your top match. Pick another to see its plan.",
)
st.write(f"Courses in order, within your **{profile['hours_budget']} hours**, that move you furthest toward this role per hour.")

result_plan = call_or_wait(
    "A", "the course planner", plan, user_levels(profile["skills"]), roles[target_id], role_skill_rows(),
    list(course_catalog().values()), result["forecasts"], snapshot, profile["risk_tolerance"], profile["hours_budget"],
)
if result_plan is None:
    st.stop()
steps = result_plan["steps"]
if not steps:
    st.info("No course fits your hours for this role's gaps. Add hours on your Profile or pick another role.")
    st.stop()

# --- Course list ----------------------------------------------------------------------------------
courses = course_catalog()
st.dataframe(
    pd.DataFrame([{
        "#": s["order"],
        "Course": courses.get(s["course_id"], {}).get("title", s["course_id"]),
        "Skill": skill_label(s["skill_id"]),
        "Hours": f"{s['hours']:g} h",
        "Cost": fmt_rm(s["cost_rm"]),
        "HRD Corp": s["hrdc_claimable"],
        "Total": f"{s['cumulative_hours']:g} h",
        "Link": s["url"],
    } for s in steps]),
    hide_index=True, use_container_width=True,
    column_config={
        "Link": st.column_config.LinkColumn(display_text="Open"),
        "HRD Corp": st.column_config.TextColumn(help="Whether HRD Corp funding can be claimed. 'unknown' until we find a source."),
    },
)
total_cost = sum(s["cost_rm"] for s in steps)
st.caption(
    f"{result_plan['hours_used']:g} of {profile['hours_budget']} hours · {fmt_rm(total_cost)} total"
    f" (your budget {fmt_rm(profile['budget_rm'])}) · Source: courses.csv, each URL checked on its verified_on date"
)

# --- Apply plan (the wow moment) ------------------------------------------------------------------
applied = st.session_state.get("plan_applied") == target_id
if st.button("Undo plan" if applied else "Apply plan", type="primary", use_container_width=True):
    st.session_state["plan_applied"] = None if applied else target_id
    st.rerun()

before, after = result_plan["before"], result_plan["after"]
now = after if applied else before
c1, c2, c3 = st.columns(3)
c1.metric("Match", fmt_pct(now["match_pct"]), delta=f"{(after['match_pct'] - before['match_pct']) * 100:+.0f} pts" if applied else None)
c2.metric("Expected growth", fmt_change(now["growth"]), help=HELP["growth"])
c3.metric("Readiness score", f"{now['readiness'] * 100:.1f}",
          delta=f"{(after['readiness'] - before['readiness']) * 100:+.1f}" if applied else None, help=HELP["readiness"])

show_fig(gauge_fig(now["ai_exposure"], before=before["ai_exposure"] if applied else None))
if now["ai_exposure"] is not None and before["ai_exposure"] is not None:
    show_fig(risk_return_fig(result["matches"], now, before=before if applied else None))
source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")

if applied:
    new_levels = user_levels(profile["skills"])
    for s in steps:
        level_out = courses.get(s["course_id"], {}).get("level_out")
        if level_out:  # only courses.csv rows can change a level
            new_levels[s["skill_id"]] = max(new_levels.get(s["skill_id"], 0), level_out)
    new_weights = call_or_wait("A", "portfolio weights", portfolio.weights, [{"skill_id": k, "level": v} for k, v in new_levels.items()])
    allocation = new_weights and call_or_wait(
        "A", "the SDG lens", sdg.impact_allocation, new_weights, list(roles.values()), role_skill_rows())
    st.subheader("Where your skills point after the plan")
else:
    allocation = {a["sdg"]: a["share"] for a in result["sdg_allocation"]}
    st.subheader("Where your skills point today")
if allocation:
    show_fig(sdg_donut(allocation))

with st.expander("Before and after, in full"):
    st.dataframe(pd.DataFrame({
        "": ["Match", "Expected growth", "AI exposure", "Demand swing", "Spread", "Readiness score"],
        "Before": [fmt_pct(before["match_pct"]), fmt_change(before["growth"]), fmt_score(before["ai_exposure"]),
                   fmt_pct(before["volatility"], 1), fmt_score(before["diversification"]), f"{before['readiness'] * 100:.1f}"],
        "After": [fmt_pct(after["match_pct"]), fmt_change(after["growth"]), fmt_score(after["ai_exposure"]),
                  fmt_pct(after["volatility"], 1), fmt_score(after["diversification"]), f"{after['readiness'] * 100:.1f}"],
    }), hide_index=True, use_container_width=True)
st.caption("These are estimates. You decide what to learn.")
