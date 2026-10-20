import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.ui import LEVEL_LABELS, RISK_LABELS, SDG_NAMES, page_setup, skill_catalog, skill_label
from engine.data import list_profiles, load_profile, load_skills
from engine.guardrails import keep_known
from pipeline.extract_skills import compile_aliases, skills_in_text

page_setup("Profile")
st.title("1 · Your profile")
st.write("Tell us what you can do today. We never ask your age, gender or anything else about who you are.")

catalog = skill_catalog()
NEW_PROFILE = {
    "profile_id": "you", "display_name": "You", "synthetic": False, "headline": "",
    "hours_budget": 200, "budget_rm": 300, "risk_tolerance": "medium", "sdg_interests": [], "skills": [],
}


def fill_form(profile: dict) -> None:
    """Copy a Profile dict into the form's widget state."""
    skills = keep_known(profile["skills"], "skill_id", set(catalog))
    st.session_state["pf_meta"] = {k: profile[k] for k in ("profile_id", "display_name", "synthetic", "headline")}
    st.session_state["pf_skills"] = [s["skill_id"] for s in skills]
    for s in skills:
        st.session_state[f"pf_lvl_{s['skill_id']}"] = s["level"]
    st.session_state["pf_hours"] = int(profile["hours_budget"])
    st.session_state["pf_budget"] = int(profile["budget_rm"])
    st.session_state["pf_risk"] = profile["risk_tolerance"]
    st.session_state["pf_sdgs"] = [g for g in profile["sdg_interests"] if g in SDG_NAMES]
    st.session_state.pop("cv_detected", None)


@st.cache_resource
def alias_patterns():
    return compile_aliases(load_skills())


def detect_cv_skills() -> None:
    try:
        found = skills_in_text(st.session_state.get("pf_cv", ""), alias_patterns())
    except NotImplementedError:
        st.session_state["cv_detected"] = None
        return
    st.session_state["cv_detected"] = [sid for sid in catalog if sid in found]


def add_detected() -> None:
    chosen = st.session_state["pf_skills"]
    for sid in st.session_state.get("cv_detected") or []:
        if sid not in chosen:
            chosen.append(sid)
            st.session_state[f"pf_lvl_{sid}"] = 1
    st.session_state["pf_skills"] = chosen
    st.session_state.pop("cv_detected", None)


# Widget state is dropped when you visit another page, so refill it from the saved profile.
if "pf_skills" not in st.session_state:
    fill_form(st.session_state.get("profile") or NEW_PROFILE)

# --- Samples ---------------------------------------------------------------
st.subheader("Start from a sample")
samples = {pid: load_profile(pid) for pid in list_profiles()}
cols = st.columns(len(samples) + 1)
for col, (pid, sample) in zip(cols, samples.items()):
    col.button(f"Load {sample['display_name']}", on_click=fill_form, args=(sample,), use_container_width=True)
cols[-1].button("Start blank", on_click=fill_form, args=(NEW_PROFILE,), use_container_width=True)
meta = st.session_state["pf_meta"]
if meta["headline"]:
    st.caption(f"**{meta['display_name']}** — {meta['headline']}")

# --- Skills ----------------------------------------------------------------
st.subheader("Your skills")
with st.expander("Paste your CV or LinkedIn text to find skills"):
    st.text_area("CV text", key="pf_cv", height=150, placeholder="Paste text here — it stays in this browser session.")
    st.button("Find skills", on_click=detect_cv_skills)
    if "cv_detected" in st.session_state:
        detected = st.session_state["cv_detected"]
        if detected is None:
            st.info("Waiting for lane B: the skill matcher isn't built yet. Pick your skills below instead.")
        elif not detected:
            st.write("No skills from our list found. Pick them below instead.")
        else:
            new = [sid for sid in detected if sid not in st.session_state["pf_skills"]]
            st.write("Found: " + ", ".join(skill_label(sid) for sid in detected))
            if new:
                st.button(f"Add {len(new)} new skill(s) at level 1", on_click=add_detected, type="primary")
            else:
                st.caption("All of these are already in your list.")

st.multiselect("Skills you have", options=list(catalog), format_func=skill_label, key="pf_skills")
for sid in st.session_state["pf_skills"]:
    key = f"pf_lvl_{sid}"
    if key not in st.session_state:
        st.session_state[key] = 1
    st.select_slider(skill_label(sid), options=[1, 2, 3], format_func=LEVEL_LABELS.get, key=key)

# --- Goals -----------------------------------------------------------------
st.subheader("Your time, money and goals")
left, right = st.columns(2)
left.number_input("Learning hours available", min_value=10, max_value=2000, step=10, key="pf_hours")
right.number_input("Course budget (RM)", min_value=0, max_value=20000, step=50, key="pf_budget")
st.radio("Risk tolerance", options=list(RISK_LABELS), format_func=RISK_LABELS.get, horizontal=True, key="pf_risk")
st.multiselect(
    "UN Sustainable Development Goals you care about",
    options=list(SDG_NAMES),
    format_func=lambda g: f"SDG {g} · {SDG_NAMES[g]}",
    key="pf_sdgs",
)

# --- Save ------------------------------------------------------------------
profile = {
    **meta,
    "hours_budget": st.session_state["pf_hours"],
    "budget_rm": st.session_state["pf_budget"],
    "risk_tolerance": st.session_state["pf_risk"],
    "sdg_interests": st.session_state["pf_sdgs"],
    "skills": [{"skill_id": sid, "level": st.session_state[f"pf_lvl_{sid}"]} for sid in st.session_state["pf_skills"]],
}
st.session_state["profile"] = profile

st.divider()
if profile["skills"]:
    st.success(f"Profile saved: {len(profile['skills'])} skills · {profile['hours_budget']} hours · RM {profile['budget_rm']}.")
    st.page_link("pages/2_Skill_Market.py", label="Next: see the Skill Market", icon="📈")
else:
    st.info("Add at least one skill to continue.")
