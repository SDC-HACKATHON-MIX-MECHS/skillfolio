import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.ui import page_setup, todo

page_setup("Matches")
st.title("4 · Future roles for you")

todo("lane C", [
    "Top 5 roles from engine.matching.rank_roles",
    "Per role: match %, rank-score breakdown, contributing skills, gaps, AI exposure with plain-English tooltip",
    "SDG badges with the reason and source link (roles.csv)",
    "Citations: source IDs + snapshot date",
])
