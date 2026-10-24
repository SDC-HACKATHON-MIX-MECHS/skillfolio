"""Profile page = the first-run onboarding wizard (resume, skills, goals) or, for a returning user, a dashboard: fit to your goal,
the courses you are studying with your progress, and how much of the role's skill list you cover.

The wizard lives in app/onboarding.py, the dashboard in app/profile_dashboard.py. The finished profile is saved in
st.session_state["profile"], the one key every other page reads; its shape is documented there and has not changed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app import onboarding, profile_dashboard
from app.ui import page_setup

snapshot = page_setup("Profile")
profile = st.session_state.get("profile")
if profile and profile.get("skills") and st.session_state.get("ob_step") in (None, 5) and profile_dashboard.render(profile, snapshot):
    onboarding._actions()
else:
    onboarding.render()
