import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.ui import (
    HELP, fmt_change, fmt_pct, fmt_score, gauge_fig, page_setup, require_profile, risk_return_fig, run_engine,
    sdg_donut, show_fig, source_caption,
)

snapshot = page_setup("My Portfolio")
st.title("3 · My portfolio")
profile = require_profile()
st.write(f"**{profile['display_name']}**'s skills, read like an investment portfolio.")

result = run_engine(profile, snapshot)
if result is None or result["metrics"] is None:
    st.stop()
m = result["metrics"]

# --- Metric cards ---------------------------------------------------------------------------------
c1, c2, c3 = st.columns(3)
c1.metric("Expected growth", fmt_change(m["growth"]), help=HELP["growth"])
c2.metric("Readiness score", f"{m['readiness'] * 100:.1f}", help=HELP["readiness"])
c3.metric("Spread", fmt_score(m["diversification"]), help=HELP["spread"])

left, right = st.columns([3, 2])
with left:
    show_fig(gauge_fig(m["ai_exposure"]))
with right:
    st.metric("Demand swing", fmt_pct(m["volatility"], 1), help=HELP["swing"], delta_color="inverse")
    st.caption(HELP["exposure"])
source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")

# --- Risk / return --------------------------------------------------------------------------------
st.subheader("You vs the future roles")
st.write("Up is more demand growth; left is less exposed to AI. Bigger bubbles are roles you already match more closely.")
if result["matches"]:
    show_fig(risk_return_fig(result["matches"], m))
    source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
elif result["matches"] is not None:
    st.info("No future roles to compare yet — add more skills on your Profile.")

# --- SDG impact -----------------------------------------------------------------------------------
st.subheader("Where your skills point")
if result["allocation"]:
    st.write("Share of your skills linked to each UN Sustainable Development Goal.")
    show_fig(sdg_donut(result["allocation"]))
    st.caption("Source: roles.csv SDG links (see Matches for each reason) · every skill supports SDG 4.4")

st.page_link("pages/4_Matches.py", label="Next: your matching roles", icon="🎯")
