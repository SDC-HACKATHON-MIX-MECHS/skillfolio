import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.ui import page_setup, todo

page_setup("My Portfolio")
st.title("3 · My portfolio")

todo("lane C", [
    "Metric cards: growth, AI exposure (gauge 0–100), volatility, diversification, readiness",
    "Risk/return chart (Plotly): x = AI exposure, y = growth; roles as bubbles sized by match %; user as a highlighted dot",
    "SDG impact donut (engine.sdg.impact_allocation)",
])
