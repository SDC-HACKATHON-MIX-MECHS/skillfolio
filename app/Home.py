"""Home: the roles-first screen. Which roles fit me, and why? Answered in five seconds.

With a profile and ranked roles: a hero, the top 3 roles as cards (title, status chip, Fit % with a progress track, one
sentence on why, hiring-trend pill, and an inline 'Missing: X' strip with one button), one primary button to the learning
plan, and at wide widths a panel on the right on how the user's skills are doing, with everything else behind a single
"Show details" expander. Without a profile: the hero, one button and a demo link. All wording is plain English
(docs/DESIGN.md); every figure is engine output, never invented. Look: the shared app/theme.css (docs/DESIGN.md).
"""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.dashboard import DEFAULT_RANGE, RANGES, basket_index, holdings, pct_change
from app.home_components import (
    NO_FIT_MESSAGE, NO_ROLES_MESSAGE, TOP_N, demand_chart, detail_numbers, first_name, greeting, how_it_works,
    kpi_items, kpi_strip, levels_after_plan, missing_strip, note, petal_chart, petal_values, plan_course_row, plan_progress,
    plan_summary, role_card, role_row, section_title, skill_rows, skills_table, top_roles, welcome,
)
from app.ui import (
    card_container, course_catalog, direction_of, fmt_signed, page_setup, pill, range_tabs, role_catalog, role_skill_rows, row_container,
    run_engine, scenario, show, show_fig, side_panel, skill_name, source, source_caption, strip_container, user_levels,
)
from engine import config
from engine.data import list_profiles, load_profile
from engine.pathway import plan

DEMO_PROFILE = "aina"          # the sample profile the "Try a demo profile" link loads
PLAN_PAGE = "pages/5_Rebalance_Plan.py"
RANGE_TABS = ("1Y", "6M", "All")   # the order of the tabs above the chart


def go_plan(role_id: str) -> None:
    """Button callback: remember which role's plan to open (the plan page reads plan_target, as the Matches page sets it)."""
    st.session_state["plan_target"] = role_id


def plan_link(role_id: str, key: str) -> None:
    """A quiet 'See your plan' link for one role: sets the target role, then opens the plan page."""
    kwargs = {"key": key, "on_click": go_plan, "args": (role_id,)}
    try:
        clicked = st.button("See your plan", type="tertiary", icon=":material/arrow_forward:", **kwargs)
    except Exception:                                        # older Streamlit has no tertiary buttons
        clicked = st.button("See your plan", **kwargs)
    if clicked:
        st.switch_page(PLAN_PAGE)


def lead_plan(profile: dict, result: dict, role_id: str) -> dict | None:
    """The course plan for the lead role, exactly as the Learning plan page builds it. None if the planner can't make one."""
    try:
        return plan(user_levels(profile["skills"]), role_catalog()[role_id], role_skill_rows(), list(course_catalog().values()),
                    result["forecasts"], snapshot, profile.get("risk_tolerance", "medium"), profile.get("hours_budget") or 0,
                    budget_rm=profile.get("budget_rm"))
    except (KeyError, ValueError, TypeError):
        return None


def load_demo_profile() -> None:
    """Button callback: put the sample profile in session state (made-up person, see data/profiles)."""
    ids = list_profiles()
    if not ids:
        return
    pid = DEMO_PROFILE if DEMO_PROFILE in ids else ids[0]
    st.session_state["profile"] = copy.deepcopy(load_profile(pid))


snapshot = page_setup("Home")
profile = st.session_state.get("profile")


# --- No profile: hero, one primary action, one small link, the four steps ---------------------------------
if not profile or not profile.get("skills"):
    show(welcome("Roles that fit you, and why.",
                 lead="Add your skills and see which roles fit you best, and what to learn next."))
    if st.button("Set up my portfolio", type="primary", key="sf_cta_welcome"):
        st.switch_page("pages/1_Profile.py")
    try:
        st.button("Try a demo profile", type="tertiary", key="home_demo", on_click=load_demo_profile)
    except Exception:                                        # older Streamlit has no tertiary buttons
        st.button("Try a demo profile", key="home_demo", on_click=load_demo_profile)
    show(how_it_works())
    st.stop()


# --- Profile loaded: roles first --------------------------------------------------------------------------
result = run_engine(profile, snapshot)
if result is None:
    st.stop()

name = first_name(profile)
roles = top_roles(result["matches"], TOP_N)
lead_result = lead_plan(profile, result, roles[0]["role_id"]) if roles else None
goal = plan_summary(lead_result)

if roles:
    show(greeting(
        name, "these roles fit you best",
        lead="Fit is how much of a role's skill list you already cover. Hiring trends are estimates for the next 12 months.",
    ))
    if st.button("See my learning plan", type="primary", key="sf_cta", on_click=go_plan, args=(roles[0]["role_id"],)):
        st.switch_page(PLAN_PAGE)
    show(kpi_strip(kpi_items(result)))
else:
    show(greeting(name, "here is where you stand"))

roles_col, panel_col = st.columns([13, 8], gap="large")

with roles_col:
    if roles:
        lead_match, others = roles[0], roles[1:]
        with card_container():                                   # role 1: the full card
            show(role_card(lead_match, skill_name, rank=1, lead=True, goal=goal))
            with strip_container("home-0"):
                show(missing_strip(lead_match, skill_name))
                plan_link_btn = st.button("See your plan", key="sf_plan_0", on_click=go_plan, args=(lead_match["role_id"],))
                if plan_link_btn:
                    st.switch_page(PLAN_PAGE)
        if others:                                               # roles 2 and 3: compact rows on ONE shared surface
            with card_container():
                for i, match in enumerate(others, start=2):
                    with row_container(f"home-{i}", separated=i > 2):
                        show(role_row(match, skill_name, rank=i))
                        plan_link(match["role_id"], f"sf_plan_{i - 1}")
    elif result["matches"]:
        show(note(NO_FIT_MESSAGE))
        st.page_link("pages/1_Profile.py", label="Update my skills", icon=":material/person:")
    else:
        show(note(NO_ROLES_MESSAGE))
        st.page_link("pages/6_Methodology.py", label="How roles are matched", icon=":material/menu_book:")

# --- Right-hand panel at wide widths: a small demand chart with range tabs, three skill rows, then the details ----------
with panel_col:
    with side_panel():
        held = holdings(result)
        weights = {s["skill_id"]: s["weight"] for s in result["skills"]}
        indices = {sid: (result["forecasts"].get(sid) or {}).get("index", []) for sid in weights}
        thin_ids = {s["skill_id"] for s in result["skills"] if s["thin_data"]}
        all_months = [mo["month"] for mo in snapshot["months"]]

        show(section_title("Demand for your skills", "How often job posts ask for them. Set to 100 at the start of the range.", tight=True))
        chosen = range_tabs("home_range", RANGE_TABS, DEFAULT_RANGE)
        basket, left_out = basket_index(weights, indices, skip=thin_ids, months=RANGES[chosen])
        if not basket:
            st.info("Not enough job-post history for your skills to draw this chart yet.")
        else:
            change = pct_change(basket)
            if change is not None:
                show(pill(f"{fmt_signed(change)} in the last {len(basket) - 1} months", direction_of(change)))
            show_fig(demand_chart(all_months[-len(basket):], basket, direction_of(change), height=200))
            st.caption(f"Source: Hacker News job posts, retrieved {source(snapshot, 'hn_whoishiring')['retrieved_at'][:10]}. An estimate.")

        show(section_title("How your skills are doing", "The hiring trend for the skills you use most, as an estimate."))
        show(skill_rows(held, skill_name, numbers=False))

        with st.expander("Show details"):
            if left_out:
                st.caption("Left out of the chart (not enough data in this range): " + ", ".join(skill_name(s) for s in left_out) + ".")
            st.caption("The chart shows the market, not your own score: the share of Hacker News job posts that mention each skill (3-month average).")
            show('<div class="sf-detail-title">Your skills</div>')
            query = st.text_input("Find a skill", key="home_find", placeholder="Find a skill", label_visibility="collapsed")
            show(skills_table(held, skill_name, query))
            show('<div class="sf-detail-title">The numbers behind this</div>')
            show(detail_numbers(result["portfolio"]))
            source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
            st.caption(f"Scenario: {config.SCENARIOS[scenario()]['label']}. Data as of {snapshot['snapshot_date']}.")
            st.page_link("pages/6_Methodology.py", label="How these are worked out", icon=":material/menu_book:")

# --- Below: the lead role's learning plan with progress ticks, and its Fit skill by skill (petals) ----------------------------
if roles and goal:
    lead_match = roles[0]
    courses = course_catalog()
    steps = lead_result["steps"]
    plan_col, petal_col = st.columns([13, 8], gap="large")

    with plan_col:
        show(section_title("Your learning plan", f"For {lead_match['title']}, in the order to take them. Tick a course when you finish it."))
        with card_container():
            done = {s["course_id"]: bool(st.session_state.get(f"home_done_{s['course_id']}")) for s in steps}
            show(plan_progress(sum(s["hours"] for s in steps if done[s["course_id"]]), goal["hours"], sum(done.values()), len(steps)))
            for i, step in enumerate(steps, start=1):
                course = courses.get(step["course_id"], {})
                show(plan_course_row(i, course.get("title", step["course_id"]), course.get("provider"), skill_name(step["skill_id"]),
                                     course.get("level_out"), step["hours"], done[step["course_id"]]))
                st.checkbox("Done", key=f"home_done_{step['course_id']}")
            st.caption("Your ticks are kept for this visit only.")

    with petal_col:
        with card_container():
            show(section_title("Your fit, skill by skill", "Each petal is one skill this role needs. The pale part is what your plan adds.", tight=True))
            levels = user_levels(profile["skills"])
            role_rows = [r for r in role_skill_rows() if r["role_id"] == lead_match["role_id"]]
            values = petal_values(role_rows, levels, levels_after_plan(levels, steps, courses))
            show_fig(petal_chart(values, skill_name))
            st.caption("Source: the role's skill list (O*NET 31.0 and our team) and our free course catalogue · estimates, not predictions.")
