import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.ui import page_setup, todo

page_setup("Profile")
st.title("1 · Your profile")

todo("lane C", [
    "Skill picker from data/skills.csv with level 1–3 per skill",
    "Paste CV text → detected skills (pipeline.extract_skills.skills_in_text) → user confirms",
    "Hour budget, risk tolerance (low / medium / high), SDG picker",
    "Buttons: Load sample Aina / Ravi (data/profiles)",
    "Save to st.session_state['profile'] in the Profile shape (contracts/README.md)",
])
