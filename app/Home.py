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
    NO_FIT_MESSAGE, NO_ROLES_MESSAGE, TOP_N, detail_numbers, first_name, greeting, how_it_works,
    kpi_items, missing_strip, note, role_card, role_row, section_title, skill_rows, skills_table, tile, top_roles, trend_bars,
    trend_head, welcome,
)
from app.ui import (
    card_container, dark_container, direction_of, fmt_signed, page_setup, pill, range_tabs, row_container, run_engine, scenario, show,
    skill_name, source_caption, strip_container,
)
from engine import config
from engine.data import list_profiles, load_profile

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

if roles:
    show(greeting(name, "these roles fit you best"))
    if st.button("See my learning plan", type="primary", key="sf_cta", on_click=go_plan, args=(roles[0]["role_id"],)):
        st.switch_page(PLAN_PAGE)
else:
    show(greeting(name, "here is where you stand"))

# the data both columns use
held = holdings(result)
weights = {s["skill_id"]: s["weight"] for s in result["skills"]}
indices = {sid: (result["forecasts"].get(sid) or {}).get("index", []) for sid in weights}
thin_ids = {s["skill_id"] for s in result["skills"] if s["thin_data"]}
all_months = [mo["month"] for mo in snapshot["months"]]
items = kpi_items(result)
left_out: list[str] = []

# --- the bento: two columns of big rounded cards (one charcoal card, a mint Fit panel, two tiles) ---------------------------
left_col, right_col = st.columns(2, gap="large")

with left_col:
    if roles:
        with dark_container():                                   # the ONE charcoal card: the hiring-trend number and its bars
            show(trend_head(items[0]))
            chosen = range_tabs("home_range", RANGE_TABS, DEFAULT_RANGE)
            basket, left_out = basket_index(weights, indices, skip=thin_ids, months=RANGES[chosen])
            if not basket:
                st.info("Not enough job-post history for your skills to draw this chart yet.")
            else:
                change = pct_change(basket)
                if change is not None:
                    show(pill(f"{fmt_signed(change)} in the last {len(basket) - 1} months", direction_of(change)))
                show(trend_bars(all_months[-len(basket):], basket, result["portfolio"].get("growth")))
                source_caption(snapshot, "hn_whoishiring")
        lead_match, others = roles[0], roles[1:]
        with card_container():                                   # role 1: the full card, Fit as an arc on a mint panel
            show(role_card(lead_match, skill_name, rank=1, lead=True))
            with strip_container("home-0"):
                show(missing_strip(lead_match, skill_name))
                plan_link_btn = st.button("See your plan", key="sf_plan_0", on_click=go_plan, args=(lead_match["role_id"],))
                if plan_link_btn:
                    st.switch_page(PLAN_PAGE)
    elif result["matches"]:
        show(note(NO_FIT_MESSAGE))
        st.page_link("pages/1_Profile.py", label="Update my skills", icon=":material/person:")
    else:
        show(note(NO_ROLES_MESSAGE))
        st.page_link("pages/6_Methodology.py", label="How roles are matched", icon=":material/menu_book:")

with right_col:
    with card_container():                                       # your skills, as words, and everything else behind one expander
        show(section_title("How your skills are doing", tight=True))
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
    if roles:
        with card_container():                                   # the next roles as a timeline, then the two tiles
            if len(roles) > 1:
                show(section_title("Your next roles", tight=True))
                for i, match in enumerate(roles[1:], start=2):
                    with row_container(f"home-{i}", separated=i > 2):
                        show(role_row(match, skill_name, rank=i))
                        plan_link(match["role_id"], f"sf_plan_{i - 1}")
            show(f'<div class="sf-tiles">'
                 f'{tile(items[1]["label"], items[1]["value"], "", "mint", items[1].get("fraction"))}'
                 f'{tile(items[2]["label"], items[2]["value"], items[2]["pill"][1], "charcoal")}</div>')
