import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.page_components import PLAIN, compare_cards, course_list, course_row, sdg_donut_fig
from app.ui import (
    SDG_NAMES, call_or_wait, course_catalog, fmt_pct, fmt_rm, fmt_score, fmt_signed, gauge_fig, hero, require_profile,
    page_header, page_setup, risk_return_fig, role_catalog, role_skill_rows, run_engine, section_header, show, show_fig, show_warnings,
    skill_label, source_caption, user_levels,
)
from engine import portfolio, sdg
from engine.pathway import plan

snapshot = page_setup("Your learning plan")
page_header("Your learning plan",
            "The courses that move you toward a role fastest, in the order to take them.", narrow=True)
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
preferred = st.session_state.get("plan_target")      # set by "See your plan" on the Matches page
target_id = st.selectbox(
    "Role you are aiming for", ranked, index=ranked.index(preferred) if preferred in ranked else 0,
    format_func=lambda rid: roles[rid]["title"], key="plan_role_pick",
    help="Starts on your closest role. Pick another to see its plan.",
)

# TODO(PR 11): engine.pathway.plan takes budget_rm from PR 11 on. This passes the profile's RM budget as soon as the
# planner accepts it, and leaves it out (as on the older planner) until then.
plan_kwargs = {"budget_rm": profile.get("budget_rm")} if "budget_rm" in inspect.signature(plan).parameters else {}
try:
    result_plan = call_or_wait(
        "A", "the course planner", plan, user_levels(profile["skills"]), roles[target_id], role_skill_rows(),
        list(course_catalog().values()), result["forecasts"], snapshot, profile["risk_tolerance"], profile["hours_budget"],
        **plan_kwargs,
    )
except ValueError as exc:
    st.error(f"We couldn't build a plan: {exc}")
    st.stop()
if result_plan is None:
    st.stop()
steps = result_plan["steps"]
if not steps:
    st.info("No course fits your hours or budget for this role's gaps. Add hours on your Profile or pick another role.")
    st.stop()

before, after = result_plan["before"], result_plan["after"]
applied = st.session_state.get("plan_applied") == target_id
now = after if applied else before
pts = (after["match_pct"] - before["match_pct"]) * 100

# --- The one message: how much closer the plan gets you -----------------------------------------------
show(hero(
    f"Fit with {roles[target_id]['title']}", fmt_pct(now["match_pct"]),
    f"{pts:+.0f} points with this plan, an estimate".replace("-", "−") if applied else None,
    "up" if pts > 0.5 else "down" if pts < -0.5 else "flat",
    caption="Press Apply plan to see the change." if not applied else "Press Undo plan to go back.",
))

# --- Courses, in order ----------------------------------------------------------------------------
courses = course_catalog()
rows = [
    course_row(
        s["order"], courses.get(s["course_id"], {}).get("title", s["course_id"]), courses.get(s["course_id"], {}).get("provider"),
        skill_label(s["skill_id"]), s["hours"], fmt_rm(s["cost_rm"]), s["hrdc_claimable"], s["url"], lead=s["order"] == 1,
    )
    for s in steps
]
SHOWN = 3
show(section_header("Courses, in order", "Chosen to move you toward this role fastest for each hour.", icon_name="briefcase"))
show(course_list(rows[:SHOWN]))
if len(rows) > SHOWN:
    with st.expander(f"Show the other {len(rows) - SHOWN} courses"):
        show(course_list(rows[SHOWN:]))
total_cost = sum(s["cost_rm"] for s in steps)
st.caption(
    f"{result_plan['hours_used']:g} of {profile['hours_budget']:g} hours · {fmt_rm(total_cost)} in total"
    f" (your budget {fmt_rm(profile.get('budget_rm'))}). HRD Corp status is 'unknown' until we find a source."
)
st.caption("Source: courses.csv, each URL checked on its verified_on date · estimates, not predictions")

# --- The one primary action (the wow moment) ------------------------------------------------------
if st.button("Undo plan" if applied else "Apply plan", type="primary", use_container_width=True):
    st.session_state["plan_applied"] = None if applied else target_id
    st.rerun()
st.caption("These are estimates. You decide what to learn.")


def delta(change: float, text: str):
    return (text, "up" if change > 0.0005 else "down" if change < -0.0005 else "flat") if applied else (None, "flat")


# --- Details --------------------------------------------------------------------------------------
with st.expander("Show details", expanded=applied):
    ready_delta = delta(after["readiness"] - before["readiness"], f"{(after['readiness'] - before['readiness']) * 100:+.1f}".replace("-", "−"))
    # AI impact is not good or bad, so its change is never green or red.
    if applied and before["ai_exposure"] is not None and after["ai_exposure"] is not None:
        # From the rounded scores, so "21 -> 22" reads "+1 points", matching the gauge (not "+0" from 21.1 -> 21.6).
        ai_change = round(after["ai_exposure"] * 100) - round(before["ai_exposure"] * 100)
        ai_delta = (f"{ai_change:+d} points".replace("-", "−"), "flat")
    else:
        ai_delta = (None, "flat")
    show(compare_cards([
        ("Outlook score", f"{now['readiness'] * 100:.1f}", f"{before['readiness'] * 100:.1f}", f"{after['readiness'] * 100:.1f}", *ready_delta, PLAIN["outlook"]),
        ("AI impact (0 to 100)", fmt_score(now["ai_exposure"]).replace("/100", ""), fmt_score(before["ai_exposure"]).replace("/100", ""),
         fmt_score(after["ai_exposure"]).replace("/100", ""), *ai_delta, PLAIN["ai"]),
        ("Hiring trend, next 12 months", fmt_signed(now["growth"]), fmt_signed(before["growth"]), fmt_signed(after["growth"]),
         *delta(after["growth"] - before["growth"], f"{(after['growth'] - before['growth']) * 100:+.1f} pts".replace("-", "−")), PLAIN["trend"]),
    ]))
    show_fig(gauge_fig(now["ai_exposure"], before=before["ai_exposure"] if applied else None))
    if now["ai_exposure"] is not None and before["ai_exposure"] is not None:
        with st.container(key="sf-plan-chart"):   # theme.css styles its Before / Now / Both buttons and your dot's pulse
            show_fig(risk_return_fig(result["matches"], now, before=before if applied else None))
    source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")

    st.markdown("**Where your skills point " + ("after the plan" if applied else "today") + "**")
    if applied:
        new_levels = user_levels(profile["skills"])
        for s in steps:
            level_out = courses.get(s["course_id"], {}).get("level_out")
            if level_out:  # only courses.csv rows can change a level
                new_levels[s["skill_id"]] = max(new_levels.get(s["skill_id"], 0), level_out)
        new_weights = call_or_wait("A", "portfolio weights", portfolio.weights, [{"skill_id": k, "level": v} for k, v in new_levels.items()])
        allocation = new_weights and call_or_wait(
            "A", "the SDG lens", sdg.impact_allocation, new_weights, list(roles.values()), role_skill_rows())
    else:
        allocation = {a["sdg"]: a["share"] for a in result["sdg_allocation"]}
    if allocation:
        show_fig(sdg_donut_fig(allocation, SDG_NAMES))
        st.caption("Source: roles.csv SDG links · every skill supports SDG 4.4")

    st.markdown("**Before and after, in full**")
    st.dataframe(pd.DataFrame({
        "": ["Fit", "Hiring trend, next 12 months", "AI impact (0 to 100)", "How much hiring bounces around", "Skill variety (0 to 100)", "Outlook score"],
        "Before": [fmt_pct(before["match_pct"]), fmt_signed(before["growth"]), fmt_score(before["ai_exposure"]),
                   fmt_pct(before["volatility"], 1), fmt_score(before["diversification"]), f"{before['readiness'] * 100:.1f}"],
        "After": [fmt_pct(after["match_pct"]), fmt_signed(after["growth"]), fmt_score(after["ai_exposure"]),
                  fmt_pct(after["volatility"], 1), fmt_score(after["diversification"]), f"{after['readiness'] * 100:.1f}"],
    }), hide_index=True, use_container_width=True)
    source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
