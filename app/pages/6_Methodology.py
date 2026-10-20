import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.ui import page_setup, todo

page_setup("Methodology")
st.title("Methodology & sources")

todo("lanes C + D", [
    "Every source with URL, licence and retrieval date (from the snapshot's `sources`)",
    "Formulas in plain English (docs/SPEC.md section 5)",
    "Assumption values from engine/config.py",
    "Limits: HN postings are global and tech-heavy; exposure ≠ job loss",
    "AI disclosure: which LLM (if any) and what it may / may not do",
    "Forecasts are estimates, not predictions; humans make the decision",
])
