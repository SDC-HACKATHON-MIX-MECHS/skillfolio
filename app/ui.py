"""Shared UI helpers for every page (lane C)."""

from __future__ import annotations

import streamlit as st

from engine import config
from engine.data import load_skills, load_snapshot

# UN SDG short names (https://sdgs.un.org/goals)
SDG_NAMES = {
    1: "No poverty", 2: "Zero hunger", 3: "Good health and well-being", 4: "Quality education",
    5: "Gender equality", 6: "Clean water and sanitation", 7: "Affordable and clean energy",
    8: "Decent work and economic growth", 9: "Industry, innovation and infrastructure",
    10: "Reduced inequalities", 11: "Sustainable cities and communities",
    12: "Responsible consumption and production", 13: "Climate action", 14: "Life below water",
    15: "Life on land", 16: "Peace, justice and strong institutions", 17: "Partnerships for the goals",
}
LEVEL_LABELS = {1: "1 · basic", 2: "2 · working", 3: "3 · strong"}
RISK_LABELS = {"low": "Low — play it safe", "medium": "Medium", "high": "High — chase growth"}


def page_setup(title: str) -> dict:
    """Page config + sidebar (scenario toggle, snapshot badge, current profile). Returns the loaded snapshot."""
    st.set_page_config(page_title=f"SkillFolio · {title}", page_icon="📈", layout="centered")
    snapshot = load_snapshot(st.session_state.get("snapshot_date", "latest"))
    with st.sidebar:
        st.radio(
            "AI disruption scenario",
            options=list(config.SCENARIOS),
            format_func=lambda key: config.SCENARIOS[key]["label"],
            key="scenario",
        )
        st.caption(f"Data snapshot: **{snapshot['snapshot_date']}**")
        profile = st.session_state.get("profile")
        if profile:
            st.caption(f"Profile: **{profile['display_name']}** · {len(profile['skills'])} skills")
    if snapshot.get("is_example"):
        st.warning("EXAMPLE DATA — no real snapshot yet. Numbers are illustrative only.")
    return snapshot


@st.cache_data
def skill_catalog() -> dict[str, dict]:
    """skills.csv keyed by skill_id, in file order."""
    return {skill["skill_id"]: skill for skill in load_skills()}


def skill_label(skill_id: str) -> str:
    skill = skill_catalog().get(skill_id)
    return f"{skill['name']} ({skill['ticker']})" if skill else skill_id


def require_profile() -> dict:
    """Return the saved profile, or point the user to the Profile page and stop."""
    profile = st.session_state.get("profile")
    if not profile or not profile["skills"]:
        st.info("Set up your profile first — pick your skills or load a sample.")
        st.page_link("pages/1_Profile.py", label="Go to 1 · Profile", icon="👤")
        st.stop()
    return profile


def call_or_wait(lane: str, what: str, fn, *args, **kwargs):
    """Call another lane's function; if it isn't built yet, say so on the page and return None."""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        st.info(f"Waiting for lane {lane}: {what} isn't built yet.")
        return None


def todo(owner: str, items: list[str]) -> None:
    """Placeholder listing what this page must show (from docs/SPEC.md section 6)."""
    st.info(f"**To build ({owner}):**\n\n" + "\n".join(f"- {item}" for item in items))
