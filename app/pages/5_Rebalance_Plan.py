import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.ui import page_setup, todo

page_setup("Rebalance Plan")
st.title("5 · Rebalance plan")

todo("lane C", [
    "Target-role picker (default: top match)",
    "Ordered courses from engine.pathway.plan: hours, cost RM, link, HRD Corp flag, cumulative hours",
    "Before / after metrics",
    "Apply plan toggle → dot moves on the risk/return chart, AI-exposure gauge drops, SDG donut updates (the wow moment)",
])
