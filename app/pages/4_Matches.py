import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.home_components import GOOD_FIT, NO_FIT_MESSAGE, STRONG_FIT, fit_label, fit_percent, hiring_pill, missing_strip, role_card, top_roles
from app.page_components import link_button, role_extras, sdg_chips
from app.ui import (
    HELP, LEVEL_LABELS, SDG_NAMES, card_container, page_header, page_setup, require_profile, role_catalog, run_engine, show,
    show_warnings, skill_label, skill_name, source_caption, strip_container,
)
from engine import config

snapshot = page_setup("Matches")
page_header("Which roles fit me?",
            "Your three closest roles, and why. Fit is how much of each role's skill list you already cover.", narrow=True)
profile = require_profile()

result = run_engine(profile, snapshot)
if result is None:
    st.stop()
if not result["matches"]:
    show_warnings(result)
    st.stop()
matches = top_roles(result["matches"], config.TOP_N_ROLES)
if not matches:
    st.info(NO_FIT_MESSAGE)
    st.stop()

roles = role_catalog()
SHOWN = 3


def card(rank: int, match: dict, nested: bool = False) -> None:
    """One role: the card (status chip, fit track, one sentence, what is missing, one button), then the details."""
    role = roles.get(match["role_id"], {})
    with card_container():
        show(role_card(match, skill_name, rank, lead=rank == 1))
        with strip_container(f"{match['role_id']}-{'x' if nested else 's'}"):
            show(missing_strip(match, skill_name))
            if st.button("See your plan", key=f"plan_{match['role_id']}_{'x' if nested else 's'}"):
                st.session_state["plan_target"] = match["role_id"]
                st.switch_page("pages/5_Rebalance_Plan.py")
        with (st.container() if nested else st.expander("Why this score")):
            if role.get("description"):
                st.write(role["description"])
            show(role_extras(hiring_pill(match["role_growth"]), match["ai_exposure"],
                             sdg_chips(match["sdgs"], SDG_NAMES, role.get("sdg_source_url"))))
            st.markdown(
                f"**Rank score {match['rank_score']:.2f}** = fit {match['match_pct']:.2f} "
                f"× (1 + demand growth {match['role_growth']:+.2f}) × (1 + {config.SDG_TILT_ALPHA} × shared SDGs {match['sdg_overlap']:.2f})"
            )
            st.caption(f"Fit label: Strong fit is {STRONG_FIT}% or more, Good fit is {GOOD_FIT} to {STRONG_FIT - 1}%, Stretch is below {GOOD_FIT}% (this role: {fit_label(fit_percent(match))}).")
            if match["contributions"]:
                st.markdown("**What counts**")
                st.dataframe(
                    pd.DataFrame([{
                        "Skill": skill_label(c["skill_id"]),
                        "You": LEVEL_LABELS.get(c["user_level"], "—"),
                        "Needed": LEVEL_LABELS[c["required_level"]],
                        "Importance": c["weight"],
                        "Credit": c["credit"],
                    } for c in match["contributions"]]),
                    hide_index=True, use_container_width=True,
                    column_config={"Credit": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")},
                )
            if match["gaps"]:
                st.markdown("**What's missing** (most important first)")
                for g in match["gaps"]:
                    have_level = LEVEL_LABELS.get(g["user_level"], "none")
                    st.write(f"- {skill_label(g['skill_id'])}: you have {have_level}, needs {LEVEL_LABELS[g['required_level']]}")
            st.markdown("**SDG link**")
            st.write(
                ", ".join(f"SDG {g} · {SDG_NAMES.get(g, '')}" for g in match["sdgs"])
                + (f" — {role['sdg_rationale']}" if role.get("sdg_rationale") else "")
            )
            show(link_button("SDG source", role.get("sdg_source_url")))
            st.caption(
                "AI impact (technical name: AI exposure): " + HELP["exposure"] + " · Citations: "
                + ", ".join(f"{c['source_id']} ({c['snapshot_date']})" for c in match["citations"])
            )


for rank, match in enumerate(matches[:SHOWN], start=1):
    card(rank, match)

if len(matches) > SHOWN:
    with st.expander(f"Show {len(matches) - SHOWN} more roles"):
        for rank, match in enumerate(matches[SHOWN:], start=SHOWN + 1):
            card(rank, match, nested=True)

source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
