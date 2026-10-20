import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.ui import page_setup, todo

snapshot = page_setup("Home")

st.title("SkillFolio")
st.subheader("Your skills are a portfolio. AI is the market.")
st.write(
    "See which skills are rising or falling in real job postings, how exposed they are to AI, "
    "which future roles you can reach, and how to rebalance your learning hours. "
    "Every number shows its source and date. Forecasts are estimates — you make the decision."
)

todo("lane C", [
    "How it works in 3 steps (Profile → Market & Matches → Rebalance Plan)",
    "Data freshness badge with the snapshot date",
    "Malaysian labour-force context card from data.gov.my (lfs_qtr) with its date",
])
