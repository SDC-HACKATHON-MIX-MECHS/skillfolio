"""Shared UI helpers for every page (lane C). Visual rules: docs/DESIGN.md."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from engine import config
from engine.data import load_courses, load_role_skills, load_roles, load_skills, load_snapshot

# Colours (DESIGN.md §1). No hex codes in page files.
ACCENT = "#4338CA"
UP = "#1A7F37"
DOWN = "#CF222E"
FLAT = "#6E7781"
GRID = "#E5E7EB"
TEXT = "#1F2328"
EXPOSURE_STEPS = ["#E0E7FF", "#C7D2FE", "#A5B4FC"]

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
TRAJECTORY = {"rising": "▲ rising", "stable": "■ stable", "declining": "▼ declining"}

# Tooltips (DESIGN.md §6)
HELP = {
    "momentum": "How fast job posts mentioning this skill grew over the last 12 months, adjusted for the AI scenario. Above zero means rising. An estimate.",
    "exposure": "How much AI is already used on tasks linked to this skill, 0–100. It is not a forecast of job loss.",
    "swing": "How much demand jumps around month to month. Lower means steadier.",
    "growth": "Your skills' average demand trend, weighted by your level in each. An estimate.",
    "spread": "How evenly your learning is spread across skills, 0–100. Higher means less riding on one skill.",
    "readiness": "Growth minus a penalty for demand swing, scaled by your risk tolerance. Higher is better.",
    "match": "How much of this role's skill list you already cover at the level it needs.",
}


# --- Page frame ---------------------------------------------------------------------------------

def page_setup(title: str) -> dict:
    """Page config + sidebar (scenario toggle, snapshot badge, current profile). Returns the loaded snapshot."""
    st.set_page_config(page_title=f"SkillFolio · {title}", page_icon="📈", layout="centered")
    snapshot = load_snapshot(st.session_state.get("snapshot_date", "latest"))
    # Widget state is dropped on page change, so the toggle is refilled from a plain session key.
    st.session_state["scenario"] = st.session_state.get("_scenario", config.DEFAULT_SCENARIO)
    with st.sidebar:
        st.radio(
            "AI disruption scenario",
            options=list(config.SCENARIOS),
            format_func=lambda key: config.SCENARIOS[key]["label"],
            key="scenario",
            on_change=lambda: st.session_state.update(_scenario=st.session_state["scenario"]),
        )
        st.caption(f"Data snapshot: **{snapshot['snapshot_date']}**")
        profile = st.session_state.get("profile")
        if profile:
            st.caption(f"Profile: **{profile['display_name']}** · {len(profile['skills'])} skills")
    if snapshot.get("is_example"):
        st.warning("EXAMPLE DATA — no real snapshot yet. Numbers are illustrative only.")
    return snapshot


def scenario() -> str:
    return st.session_state.get("scenario", config.DEFAULT_SCENARIO)


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


# --- Data lookups -------------------------------------------------------------------------------

@st.cache_data
def skill_catalog() -> dict[str, dict]:
    """skills.csv keyed by skill_id, in file order."""
    return {skill["skill_id"]: skill for skill in load_skills()}


@st.cache_data
def role_catalog() -> dict[str, dict]:
    return {role["role_id"]: role for role in load_roles()}


@st.cache_data
def role_skill_rows() -> list[dict]:
    return load_role_skills()


@st.cache_data
def course_catalog() -> dict[str, dict]:
    return {course["course_id"]: course for course in load_courses()}


def skill_name(skill_id: str) -> str:
    skill = skill_catalog().get(skill_id)
    return skill["name"] if skill else skill_id


def skill_ticker(skill_id: str) -> str:
    skill = skill_catalog().get(skill_id)
    return skill["ticker"] if skill else skill_id.upper()[:5]


def skill_label(skill_id: str) -> str:
    skill = skill_catalog().get(skill_id)
    return f"{skill['name']} ({skill['ticker']})" if skill else skill_id


def source(snapshot: dict, source_id: str) -> dict:
    return next((s for s in snapshot["sources"] if s["id"] == source_id), {"name": source_id, "retrieved_at": "????-??-??"})


def source_caption(snapshot: dict, *source_ids: str) -> None:
    """The caption under every chart and table (DESIGN.md §5)."""
    parts = [f"{source(snapshot, sid)['name']} · retrieved {source(snapshot, sid)['retrieved_at'][:10]}" for sid in source_ids]
    st.caption("Source: " + " · ".join(parts) + " · estimates, not predictions")


# --- Number formats (DESIGN.md §2) --------------------------------------------------------------

def arrow(x: float, threshold: float = 0.005) -> str:
    return "▲" if x > threshold else "▼" if x < -threshold else "■"


def fmt_change(x: float | None) -> str:
    """0.123 -> '▲ +12.3%'."""
    if x is None:
        return "—"
    return f"{arrow(x)} {x * 100:+.1f}%".replace("-", "−")


def fmt_pct(x: float | None, decimals: int = 0) -> str:
    return "—" if x is None else f"{x * 100:.{decimals}f}%"


def fmt_score(x: float | None) -> str:
    """0–1 -> '46/100'."""
    return "—" if x is None else f"{round(x * 100)}/100"


def fmt_rm(x: float | None) -> str:
    return "—" if x is None else f"RM {x:,.0f}"


# --- Engine bundle ------------------------------------------------------------------------------

def user_levels(skills: list[dict]) -> dict[str, int]:
    return {s["skill_id"]: s["level"] for s in skills}


def run_engine(profile: dict, snapshot: dict) -> dict | None:
    """Forecasts, portfolio metrics, ranked matches and SDG allocation for a profile.
    Shows a waiting note and returns None if a lane-A function isn't built yet."""
    from engine import matching, portfolio, sdg
    from engine.forecast import forecast_all

    forecasts = call_or_wait("A", "skill forecasts", forecast_all, snapshot, scenario())
    if forecasts is None:
        return None
    levels = user_levels(profile["skills"])
    weights = call_or_wait("A", "portfolio weights", portfolio.weights, profile["skills"])
    cov = call_or_wait("A", "the covariance matrix", portfolio.covariance, snapshot, list(levels))
    if weights is None or cov is None:
        return None
    metrics = call_or_wait("A", "portfolio metrics", portfolio.metrics, weights, forecasts, cov, profile["risk_tolerance"])
    matches = call_or_wait(
        "A", "role matching", matching.rank_roles, list(role_catalog().values()), role_skill_rows(),
        levels, forecasts, profile["sdg_interests"], snapshot["snapshot_date"],
    )
    allocation = call_or_wait("A", "the SDG lens", sdg.impact_allocation, weights, list(role_catalog().values()), role_skill_rows())
    return {"forecasts": forecasts, "weights": weights, "metrics": metrics, "matches": matches, "allocation": allocation}


# --- Charts (DESIGN.md §5) ----------------------------------------------------------------------

def style_fig(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        font=dict(family="sans-serif", size=13, color=TEXT),
        height=height,
        margin=dict(l=8, r=8, t=32, b=8),
        legend=dict(orientation="h", y=-0.2),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def show_fig(fig: go.Figure) -> None:
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def gauge_fig(exposure: float, before: float | None = None) -> go.Figure:
    """AI-exposure gauge, 0–100, one hue (never red/green)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta" if before is not None else "gauge+number",
        value=round(exposure * 100),
        number={"suffix": "/100"},
        delta={"reference": round(before * 100), "increasing": {"color": FLAT}, "decreasing": {"color": FLAT}} if before is not None else None,
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": ACCENT},
            "steps": [{"range": [0, 33], "color": EXPOSURE_STEPS[0]}, {"range": [33, 66], "color": EXPOSURE_STEPS[1]},
                      {"range": [66, 100], "color": EXPOSURE_STEPS[2]}],
        },
        title={"text": "AI exposure"},
    ))
    return style_fig(fig, height=240)


def risk_return_fig(matches: list[dict], user: dict, before: dict | None = None) -> go.Figure:
    """x = AI exposure, y = growth. Roles as grey bubbles sized by match %, the user as the accent dot."""
    top = matches[: config.TOP_N_ROLES]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[m["ai_exposure"] * 100 for m in top],
        y=[m["role_growth"] * 100 for m in top],
        mode="markers+text",
        text=[m["title"] for m in top],
        textposition="top center",
        marker=dict(size=[12 + 40 * m["match_pct"] for m in top], color=FLAT, opacity=0.6),
        customdata=[[round(m["match_pct"] * 100)] for m in top],
        hovertemplate="%{text}<br>AI exposure %{x:.0f}/100<br>Growth %{y:+.1f}%<br>Match %{customdata[0]}%<extra></extra>",
        name="Future roles",
    ))
    if before is not None:
        fig.add_trace(go.Scatter(
            x=[before["ai_exposure"] * 100], y=[before["growth"] * 100], mode="markers",
            marker=dict(size=18, color="rgba(0,0,0,0)", line=dict(color=ACCENT, width=2)),
            hovertemplate="You, before the plan<extra></extra>", name="Before",
        ))
        fig.add_annotation(
            x=user["ai_exposure"] * 100, y=user["growth"] * 100, ax=before["ai_exposure"] * 100, ay=before["growth"] * 100,
            xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowcolor=ACCENT, arrowwidth=2,
        )
    fig.add_trace(go.Scatter(
        x=[user["ai_exposure"] * 100], y=[user["growth"] * 100], mode="markers+text", text=["You"], textposition="bottom center",
        marker=dict(size=18, color=ACCENT, line=dict(color="white", width=2)),
        hovertemplate="You<br>AI exposure %{x:.0f}/100<br>Growth %{y:+.1f}%<extra></extra>", name="You",
    ))
    fig.update_xaxes(title="AI exposure (0–100) — lower is harder to automate")
    fig.update_yaxes(title="Expected demand growth (%/yr)")
    return style_fig(fig, height=380)


def sdg_donut(allocation: dict[int, float]) -> go.Figure:
    goals = sorted(allocation, key=allocation.get, reverse=True)
    fig = go.Figure(go.Pie(
        labels=[f"SDG {g} · {SDG_NAMES.get(g, '')}" for g in goals],
        values=[allocation[g] for g in goals],
        hole=0.55, sort=False,
        marker=dict(colors=[ACCENT, "#6366F1", "#818CF8", "#A5B4FC", "#C7D2FE", "#E0E7FF"][: len(goals)] + [GRID] * max(0, len(goals) - 6)),
        hovertemplate="%{label}<br>%{percent} of your skills<extra></extra>",
        textinfo="percent",
    ))
    return style_fig(fig, height=320)
