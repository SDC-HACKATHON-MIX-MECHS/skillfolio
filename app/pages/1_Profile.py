"""Profile page = the first-run onboarding wizard (resume, skills, goals) or, for a returning user, their saved profile.

The wizard lives in app/onboarding.py. The finished profile is saved in st.session_state["profile"], the one key every
other page reads; its shape is documented there and has not changed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app import onboarding
from app.ui import page_setup

page_setup("Profile")
onboarding.render()
