import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.ui import (
    HELP, LEVEL_LABELS, SDG_NAMES, fmt_change, fmt_score, page_setup, require_profile, role_catalog, run_engine,
    skill_label, source_caption,
)
from engine import config

snapshot = page_setup("Matches")
st.title("4 · Future roles for you")
profile = require_profile()

result = run_engine(profile, snapshot)
if result is None or result["matches"] is None:
    st.stop()
matches = result["matches"][: config.TOP_N_ROLES]
if not matches:
    st.info("No roles matched yet. Add more skills on your Profile.")
    st.stop()

st.write(
    "Ranked by how much of each role you already cover, how fast its skills are growing, "
    "and whether it shares the SDGs you picked. Open **Why this score** to see every step."
)
roles = role_catalog()

for rank, match in enumerate(matches, start=1):
    role = roles.get(match["role_id"], {})
    with st.container(border=True):
        top, pct = st.columns([4, 1])
        top.markdown(f"**{rank}. {match['title']}**")
        pct.markdown(f"**{round(match['match_pct'] * 100)}%**", help=HELP["match"])
        st.progress(match["match_pct"])
        if role.get("description"):
            st.write(role["description"])
        st.caption(
            f"Demand growth {fmt_change(match['role_growth'])} · AI exposure {fmt_score(match['ai_exposure'])} · "
            + " ".join(f"SDG {g}" for g in match["sdgs"])
        )

        with st.expander("Why this score"):
            st.markdown(
                f"**Rank score {match['rank_score']:.2f}** = match {match['match_pct']:.2f} "
                f"× (1 + growth {match['role_growth']:+.2f}) × (1 + {config.SDG_TILT_ALPHA} × shared SDGs {match['sdg_overlap']:.2f})"
            )
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
                    have = LEVEL_LABELS.get(g["user_level"], "none")
                    st.write(f"- {skill_label(g['skill_id'])}: you have {have}, needs {LEVEL_LABELS[g['required_level']]}")
            st.markdown("**SDG link**")
            st.write(
                ", ".join(f"SDG {g} · {SDG_NAMES.get(g, '')}" for g in match["sdgs"])
                + (f" — {role['sdg_rationale']}" if role.get("sdg_rationale") else "")
            )
            if role.get("sdg_source_url"):
                st.markdown(f"[SDG source]({role['sdg_source_url']})")
            st.caption(
                "AI exposure: " + HELP["exposure"] + " · Citations: "
                + ", ".join(f"{c['source_id']} ({c['snapshot_date']})" for c in match["citations"])
            )

source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
st.page_link("pages/5_Rebalance_Plan.py", label="Next: build your rebalance plan", icon="🧭")
