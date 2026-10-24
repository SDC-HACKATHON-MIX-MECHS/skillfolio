import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.page_components import PLAIN, compare_cards, course_list, course_row, fit_pct, plan_fit, plan_motion_script, sdg_bars
from app.ui import (
    SDG_NAMES, card_container, course_catalog, dark_container, fmt_pct, fmt_rm, fmt_score, fmt_signed, gauge_fig, require_profile,
    page_header, page_setup, risk_return_fig, role_catalog, role_skill_rows, run_engine, section_header, show, show_fig, show_warnings,
    skill_label, source_caption, source_note, user_levels,
)
from engine import portfolio, sdg
from engine.pathway import plan

snapshot = page_setup("Your learning plan")
page_header("Your learning plan")
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

try:
    result_plan = plan(
        user_levels(profile["skills"]), roles[target_id], role_skill_rows(), list(course_catalog().values()), result["forecasts"],
        snapshot, profile["risk_tolerance"], profile["hours_budget"], budget_rm=profile.get("budget_rm"),
    )
except ValueError as exc:
    st.error(f"We couldn't build a plan: {exc}")
    st.stop()
steps = result_plan["steps"]
if not steps:
    st.info("No course fits your hours or budget for this role's gaps. Add hours on your Profile or pick another role.")
    st.stop()

before, after = result_plan["before"], result_plan["after"]
applied = st.session_state.get("plan_applied") == target_id
now = after if applied else before
pts = (after["match_pct"] - before["match_pct"]) * 100
# The Apply / Undo moment plays on the ONE run right after the press (the press stores a fresh token; this run takes it).
motion = st.session_state.pop("plan_motion", None)
animate = bool(motion) and motion.get("role") == target_id


def press() -> None:
    """Apply or Undo: flip the plan, and ask the next run to play the moment once."""
    st.session_state["plan_applied"] = None if applied else target_id
    st.session_state["plan_motion"] = {"role": target_id, "token": uuid.uuid4().hex[:12]}


# --- The one message: how much closer the plan gets you, with the one primary action beside it ----------------------------
courses = course_catalog()
fit_col, course_col = st.columns(2, gap="large")
with fit_col:
    with card_container():
        show(plan_fit(
            roles[target_id]["title"], fit_pct(before["match_pct"]), fit_pct(after["match_pct"]), applied, animate=animate,
            delta_text=f"{pts:+.0f} points with this plan, an estimate".replace("-", "−") if applied else None,
            delta_dir="up" if pts > 0.5 else "down" if pts < -0.5 else "flat",
            caption="Press Undo plan to go back." if applied else "Press Apply plan to see the change.",
        ))
        st.button("Undo plan" if applied else "Apply plan", type="primary", use_container_width=True, on_click=press)
        st.caption("These are estimates. You decide what to learn.")

# --- Courses, in order ----------------------------------------------------------------------------
with course_col:
    rows = [
        course_row(
            s["order"], courses.get(s["course_id"], {}).get("title", s["course_id"]), courses.get(s["course_id"], {}).get("provider"),
            skill_label(s["skill_id"]), s["hours"], fmt_rm(s["cost_rm"]), s["url"], lead=s["order"] == 1,
        )
        for s in steps
    ]
    SHOWN = 3
    show(section_header("Courses, in order", icon_name="briefcase", tight=True))
    show(course_list(rows[:SHOWN]))
    if len(rows) > SHOWN:
        with st.expander(f"Show the other {len(rows) - SHOWN} courses"):
            show(course_list(rows[SHOWN:]))
    total_cost = sum(s["cost_rm"] for s in steps)
    st.caption(
        f"{result_plan['hours_used']:g} of {profile['hours_budget']:g} hours · {fmt_rm(total_cost)} in total"
        f" (your budget {fmt_rm(profile.get('budget_rm'))})."
    )
    source_note("our course list, each link checked on the date shown in its row", "estimates, not predictions")

# --- Where you stand among the roles: after Apply your dot slides from where you were to where the plan takes you ----------
if now["ai_exposure"] is not None and before["ai_exposure"] is not None:
    with dark_container():   # this page's one charcoal card
        show(section_header("Where you stand among the roles", "Up is more hiring growth, left is less AI impact. Bigger dots fit you more.",
                            tight=True))
        with st.container(key="sf-plan-chart"):   # theme.css styles its Before / Now / Both buttons and your dot's pulse
            show_fig(risk_return_fig(result["matches"], now, before=before if applied else None,
                                     start="Before" if animate and applied else "Both", dark=True))
        source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
    if animate and applied:
        with st.container(key="sf-plan-motion"):   # hidden by theme.css: only runs the one script that presses "Both"
            st.html(plan_motion_script(motion["token"]), unsafe_allow_javascript=True)


def delta(change: float, text: str):
    return (text, "up" if change > 0.0005 else "down" if change < -0.0005 else "flat") if applied else (None, "flat")


# --- Details --------------------------------------------------------------------------------------
with st.expander("Show details", expanded=applied):
    ready_delta = delta(after["readiness"] - before["readiness"], f"{(after['readiness'] - before['readiness']) * 100:+.1f}".replace("-", "−"))
    # AI impact is not good or bad, so its change is never green or red.
    if applied and before["ai_exposure"] is not None and after["ai_exposure"] is not None:
        # worked out from the two numbers the card shows (rounded), so "+1 points" never sits next to "Before 19 · after plan 19"
        ai_change = round(after["ai_exposure"] * 100) - round(before["ai_exposure"] * 100)
        ai_delta = ("no change" if ai_change == 0 else f"{ai_change:+d} points".replace("-", "−"), "flat")
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
    source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")

    st.markdown("**Where your skills point " + ("after the plan" if applied else "today") + "**")
    if applied:
        new_levels = user_levels(profile["skills"])
        for s in steps:
            level_out = courses.get(s["course_id"], {}).get("level_out")
            if level_out:  # only courses.csv rows can change a level
                new_levels[s["skill_id"]] = max(new_levels.get(s["skill_id"], 0), level_out)
        new_weights = portfolio.weights([{"skill_id": k, "level": v} for k, v in new_levels.items()])
        allocation = new_weights and sdg.impact_allocation(new_weights, list(roles.values()), role_skill_rows())
    else:
        allocation = {a["sdg"]: a["share"] for a in result["sdg_allocation"]}
    if allocation:
        show(sdg_bars(allocation, SDG_NAMES))
        source_note("our role-to-goal links, with the reason for each on the Matches page", "every skill supports SDG 4.4")

    st.markdown("**Before and after, in full**")
    st.dataframe(pd.DataFrame({
        "": ["Fit", "Hiring trend, next 12 months", "AI impact (0 to 100)", "How much hiring bounces around", "Skill variety (0 to 100)", "Outlook score"],
        "Before": [fmt_pct(before["match_pct"]), fmt_signed(before["growth"]), fmt_score(before["ai_exposure"]),
                   fmt_pct(before["volatility"], 1), fmt_score(before["diversification"]), f"{before['readiness'] * 100:.1f}"],
        "After": [fmt_pct(after["match_pct"]), fmt_signed(after["growth"]), fmt_score(after["ai_exposure"]),
                  fmt_pct(after["volatility"], 1), fmt_score(after["diversification"]), f"{after['readiness'] * 100:.1f}"],
    }), hide_index=True, use_container_width=True)
    source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
