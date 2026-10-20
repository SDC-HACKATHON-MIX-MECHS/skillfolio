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

retrieved = snapshot["retrieved_at"][:10]
st.metric("Job-posting data as of", snapshot["snapshot_date"], help=f"Retrieved {retrieved}")
st.caption(f"{len(snapshot['months'])} months of postings · {len(snapshot['skills'])} skills tracked")

st.subheader("How it works")
steps = [
    ("👤", "1 · Profile", "Pick your skills, hours and the SDGs you care about.", "pages/1_Profile.py"),
    ("📈", "2 · Market & matches", "See each skill's demand trend and AI exposure, and the future roles you can reach.", "pages/2_Skill_Market.py"),
    ("🧭", "3 · Rebalance plan", "Get courses, in order and within your hours, that move you toward growing, harder-to-automate skills.", "pages/5_Rebalance_Plan.py"),
]
for col, (icon, title, text, page) in zip(st.columns(3), steps):
    with col.container(border=True):
        st.markdown(f"**{icon} {title}**")
        st.write(text)
        st.page_link(page, label="Open")

todo("lane C + B", [
    "Malaysian labour-force context card from data.gov.my (lfs_qtr) with its date — needs the data shape from lane B",
])
