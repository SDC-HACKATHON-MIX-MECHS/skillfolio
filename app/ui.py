"""Shared UI helpers for every page.

The look is the v4 LIGHT system: warm off-white page, white cards with a 1px soft border and 10px radius, ink text, ONE
family (Inter), amber used for fills only (progress tracks, the chart line, the selected underline).

Page files never contain hex codes or raw HTML. They use:
  * tokens below (BG, CARD, MINT, UP, DOWN, FLAT, ...),
  * `page_setup(title)`, which injects the one shared stylesheet (`inject_css()`) and draws the sidebar,
  * the component builders in "HTML components" (each returns an HTML string; render it with `show(...)`),
  * `style_fig` / `show_fig` for Plotly.
"""

from __future__ import annotations

import html as _html
import re
import math
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from engine import config
from engine.data import load_courses, load_role_skills, load_roles, load_skills, load_snapshot

# --- Design tokens: the ONE token set for every page. No hex codes in page files. --------
# The look: a soft sage page, off-white cards with very large corners, ONE charcoal feature card, and mint green as the accent
# fill. Contrast is computed by tools/design_audit.py (and tests/test_design_audit.py): text >= 7:1 on every surface.
# MINT is about 1.3:1 on the light cards, so it is a FILL (bars, chips, the selected tab) and never text there; ink goes ON
# mint, and mint goes ON charcoal. There is no violet in this palette.
BG = "#D9E0D6"            # page (soft sage)
CARD = "#F2F4F0"          # cards, inputs (off-white)
SIDEBAR = "#E9EEE6"       # sidebar surface
RAISED = "#E2E8DE"        # hover rows, selected nav track, segmented-control track
BORDER = "#C9D2C5"        # 1px soft border
GRID = "#CAD3C6"          # chart gridlines
TEXT = "#171A18"          # ink: body text, primary button fill, links, outlines
MUTED = "#3D453F"         # secondary text (never lighter; never smaller than 14px)
ON_INK = "#F2F4F0"        # label on an ink fill (primary button)
CHARCOAL = "#1D1E1D"      # the one dark feature card
ON_CHARCOAL = "#F2F4F0"           # text on charcoal
ON_CHARCOAL_MUTED = "#BEC6BC"     # secondary text on charcoal
MINT = "#A8F5A2"          # THE ACCENT FILL: progress bars, chips, the selected tab, chart areas, the feature tile (ink text on it)
UP = "#1E8E5A"            # rising: arrows and chart marks (never text on its own)
UP_TEXT = "#0B4527"       # rising: text on a card or a green tint
DOWN = "#C8372D"          # falling: arrows and chart marks
DOWN_TEXT = "#7A1F19"     # falling: text on a card or a red tint
FLAT = MUTED
EXPOSURE_LOW = "#C2CBBE"  # AI impact: one neutral grey-green scale, never red/green/mint (AI impact is not "bad")
EXPOSURE_HIGH = "#4E5A52"
EXPOSURE_STEPS = ["#D3DAD0", "#A6B2A2", "#4E5A52"]
ROLE_DOT = "#7D8F80"       # role dots on the risk/return charts: a dark, greyed-out green, so the bright "You" dot leads
ROLE_DOT_EDGE = "#5F7062"  # their 1px outline
ROLE_DOT_DARK = "#3A3D3A"       # the same dots on the charcoal card: a step lighter than CHARCOAL, so they read as quiet discs
ROLE_DOT_DARK_EDGE = "#565A56"  # their 1px outline on charcoal
GRID_DARK = "rgba(242,244,240,0.10)"   # chart gridlines on the charcoal card (ON_CHARCOAL at 10%)
DIRECTION_COLOUR = {"up": UP, "down": DOWN, "flat": FLAT, "low": FLAT}
FONT_TEXT = "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"   # the only family
RADIUS = 32               # px: cards and expanders (very large corners, as in the reference)
RADIUS_TILE = 24          # px: tiles inside a card (the mint tile, a chart panel)
RADIUS_CONTROL = 16       # px: buttons, inputs, nav items (chips and tabs are fully round)
SHADOW = "0 10px 30px rgba(23,26,24,0.07)"   # the only shadow: very soft, on cards

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
# Tooltips
HELP = {
    "momentum": "How fast job posts mentioning this skill grew over the last 12 months, adjusted for the AI scenario. Above zero means rising. An estimate.",
    "exposure": "How much of this work already shows up in real AI use, 0–100. It means the work is changing fastest, not that the job disappears.",
    "swing": "How much demand jumps around month to month. Lower means steadier.",
    "growth": "Your skills' average demand trend, weighted by your level in each. An estimate.",
    "spread": "How evenly your learning is spread across skills, 0–100. Higher means less riding on one skill.",
    "readiness": "Growth minus a penalty for demand swing, scaled by your risk tolerance. Higher is better.",
    "match": "How much of this role's skill list you already cover at the level it needs.",
}


# --- Page frame ---------------------------------------------------------------------------------

def scenario_label(key: str) -> str:
    """'Steady AI change' -> 'Steady' (the short pill label, under the heading 'How fast will AI change jobs?')."""
    return config.SCENARIOS[key]["label"].replace(" AI change", "")


def _keep_scenario() -> None:
    """Remember the choice in a plain session key (widget state is dropped on page change). The control can be deselected
    by clicking the active pill; that is ignored and the previous scenario stays."""
    chosen = st.session_state.get("scenario")
    if chosen in config.SCENARIOS:
        st.session_state["_scenario"] = chosen
    else:
        st.session_state["scenario"] = st.session_state.get("_scenario", config.DEFAULT_SCENARIO)


def _scenario_control() -> None:
    """Sidebar control: a segmented control 'Moderate AI' | 'Fast AI' (a styled radio on a Streamlit without it).
    Same session key ('scenario') and same scenario() contract as before."""
    options = list(config.SCENARIOS)
    if hasattr(st, "segmented_control"):
        st.segmented_control(
            "AI scenario", options=options, format_func=scenario_label, key="scenario", on_change=_keep_scenario,
            selection_mode="single", label_visibility="collapsed",
            help="A what-if, not a prediction. Fast gives AI impact more weight, so the skills AI affects most lose more of their "
                 "expected growth. Steady gives it less weight.",
        )
    else:
        st.radio("AI scenario", options=options, format_func=scenario_label, key="scenario", horizontal=True,
                 on_change=_keep_scenario, label_visibility="collapsed")


def range_tabs(key: str, options: tuple[str, ...] = ("1Y", "6M", "All"), default: str = "1Y", label: str = "Range") -> str:
    """A one-choice segmented control (a horizontal radio on a Streamlit without it): the range tabs above a chart, the sort control
    on Skill Market. Returns the chosen option; clicking the active tab (which would clear it) keeps the default instead of leaving
    nothing selected. `label` is the accessible name (the control shows no visible label)."""
    def _keep() -> None:
        if st.session_state.get(key) not in options:
            st.session_state[key] = default

    if hasattr(st, "segmented_control"):
        choice = st.segmented_control(label, options=list(options), default=default, key=key, selection_mode="single",
                                      label_visibility="collapsed", on_change=_keep)
    else:
        choice = st.radio(label, options=list(options), index=list(options).index(default), key=key, horizontal=True,
                          label_visibility="collapsed")
    return choice if choice in options else default


def profile_block(profile: dict | None) -> str:
    """The profile name at the bottom of the sidebar: the name, then how many skills. No profile -> a quiet 'No profile yet'."""
    if not profile:
        return '<div class="sf-profile"><div class="sf-profile-name">No profile yet</div></div>'
    count = len(profile.get("skills") or [])
    return (f'<div class="sf-profile"><div class="sf-profile-label">Your profile</div>'
            f'<div class="sf-profile-name">{esc(profile.get("display_name") or "You")}</div>'
            f'<div class="sf-profile-sub">{count} skill{"" if count == 1 else "s"}</div></div>')


def page_setup(title: str) -> dict:
    """Page config, the one shared stylesheet, and the sidebar: navigation on top; at the bottom the AI scenario
    control, the data date and the profile name. Returns the loaded snapshot."""
    st.set_page_config(page_title=f"SkillFolio · {title}", page_icon=":material/show_chart:", layout="wide")
    st.session_state["_sf_card_n"] = 0
    inject_css()
    snapshot = load_snapshot(st.session_state.get("snapshot_date", "latest"))
    # Widget state is dropped on page change, so the control is refilled from a plain session key.
    st.session_state["scenario"] = st.session_state.get("_scenario", config.DEFAULT_SCENARIO)
    with st.sidebar:
        show('<div class="sf-side-label">How fast will AI change jobs?</div>')
        _scenario_control()
        st.caption(f"Data snapshot: **{snapshot['snapshot_date']}**")
        show(profile_block(st.session_state.get("profile")))
    if snapshot.get("is_example"):
        st.warning("EXAMPLE DATA — no real snapshot yet. Numbers are illustrative only.")
    return snapshot


def scenario() -> str:
    chosen = st.session_state.get("scenario")
    return chosen if chosen in config.SCENARIOS else config.DEFAULT_SCENARIO


def require_profile() -> dict:
    """Return the saved profile, or point the user to the Profile page and stop."""
    profile = st.session_state.get("profile")
    if not profile or not profile.get("skills"):
        st.info("Set up your profile first. Pick your skills or load a sample.")
        st.page_link("pages/1_Profile.py", label="Go to 1 · Profile", icon=":material/person:")
        st.stop()
    return profile


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
    return skill["name"] if skill else skill_id


def source(snapshot: dict, source_id: str) -> dict:
    return next((s for s in snapshot["sources"] if s["id"] == source_id), {"name": source_id, "retrieved_at": "????-??-??"})


SOURCE_LABELS = {"hn_whoishiring": "Hacker News job posts", "aei_job_exposure": "Anthropic Economic Index (AI impact)"}


def source_html(items: list[str], note: str | None = "estimates, not predictions") -> str:
    """The quiet source line under a chart or table: a small icon, then 'Source:' and each source as a chunk whose DATE never splits
    across two lines (long names may wrap), then the estimate note. One line of HTML; every piece of text is escaped."""
    def protect(text: str) -> str:      # a date is one unit and never splits across two lines; names and words may wrap
        return re.sub(r"\d{4}-\d{2}-\d{2}", lambda m: f'<span class="sf-nowrap">{m.group(0)}</span>', esc(text))

    chunks = " · ".join(f'<span class="sf-src-i">{protect(item)}</span>' for item in items)
    tail = f" · {esc(note)}" if note else ""
    return f'<div class="sf-source">{icon("file-text", 16)}<span>Source: {chunks}{tail}</span></div>'


def source_caption(snapshot: dict, *source_ids: str) -> None:
    """The source line under every chart and table, with the plain name of each source and the date it was retrieved."""
    items = []
    for sid in source_ids:
        src = source(snapshot, sid)
        name = SOURCE_LABELS.get(sid) or str(src["name"]).split(" — ")[0]
        items.append(f"{name}, retrieved {src['retrieved_at'][:10]}")
    show(source_html(items))


def source_note(text: str, note: str | None = None) -> None:
    """The same source line for a source that is not in the snapshot (our own files), e.g. the SDG links or the course list."""
    show(source_html([text], note))


# --- Number formats --------------------------------------------------------------

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
    """engine.api.analyse for this profile and the sidebar scenario, with every role ranked (pages slice the top N).
    Shows the problem and returns None if the profile can't be scored."""
    from engine import api

    try:
        result = api.analyse(profile, snapshot, scenario(), top_n=None)
    except ValueError as exc:
        st.error(f"We couldn't score this profile: {exc}")
        st.page_link("pages/1_Profile.py", label="Fix it on 1 · Profile", icon=":material/person:")
        return None
    if result and result["dropped_skills"]:
        st.caption("No job-post data yet for: " + ", ".join(skill_name(s) for s in result["dropped_skills"]) + " — left out of the numbers.")
    return result


def show_warnings(result: dict) -> None:
    """The engine says why something is empty (e.g. no role skills yet); show that instead of an empty chart."""
    for warning in result["warnings"]:
        st.info(f"Nothing to show yet: {warning}.")


# --- Charts ---------------------------------------------------------------------

def style_fig(fig: go.Figure, height: int = 340) -> go.Figure:
    """Light Plotly styling for every figure: white-card template, transparent background (sits on the card), soft grid, Inter."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", size=14, color=TEXT),
        height=height,
        margin=dict(l=8, r=8, t=32, b=8),
        legend=dict(orientation="h", y=-0.2),
        hoverlabel=dict(bgcolor=CARD, bordercolor=BORDER, font=dict(family="Inter, system-ui, sans-serif", size=14, color=TEXT)),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=BORDER, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=BORDER, tickfont=dict(color=MUTED))
    return fig


def show_fig(fig: go.Figure) -> None:
    """Every chart is read-only: no drag-to-zoom, scroll-wheel zoom, pinch or double-click reset (hover still works)."""
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(dragmode=False)
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showAxisDragHandles": False})


def demand_fig(months: list[str], values: list[float], direction: str = "flat", height: int = 300) -> go.Figure:
    """The line chart: ONE amber line, an ink dot on the last month, a dotted line at the start level (100).
    `direction` is kept for callers; the line is amber whatever it is (up or down is said in words next to the chart)."""
    fig = go.Figure(go.Scatter(
        x=months, y=values, mode="lines", line=dict(color=TEXT, width=3, shape="spline", smoothing=0.4),
        fill="tozeroy", fillcolor="rgba(168,245,162,0.55)",
        hovertemplate="%{x}<br>Demand index %{y:.1f}<extra></extra>", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=months[-1:], y=values[-1:], mode="markers", marker=dict(size=9, color=TEXT, line=dict(color=CARD, width=2)),
        hoverinfo="skip", showlegend=False,
    ))
    fig.add_hline(y=100, line_dash="dot", line_color=BORDER, line_width=1)
    fig.update_yaxes(title=None)
    fig.update_xaxes(title=None, showgrid=False)
    lo, hi = min(values + [100.0]), max(values + [100.0])
    pad = max((hi - lo) * 0.15, 2.0)
    fig.update_yaxes(range=[lo - pad, hi + pad])      # the line uses the plot; the mint area fills down to the axis, not to zero
    return style_fig(fig, height=height)


def gauge_fig(exposure: float | None, before: float | None = None) -> go.Figure:
    """AI-exposure gauge, 0-100, one neutral grey-brown scale with an amber bar (never red/green). Empty with "n/a" when unknown.
    `before` is accepted for the callers but not drawn: the before and after numbers are written out in the cards next to the chart,
    and a delta glyph inside the gauge only added clutter."""
    if exposure is None:
        fig = go.Figure(go.Indicator(mode="gauge", value=0, gauge={"axis": {"range": [0, 100]}, "bar": {"color": GRID}},
                                     title={"text": "AI impact: n/a", "font": {"size": 16}}))
        return style_fig(fig, height=260).update_layout(margin=dict(l=40, r=40, t=64, b=8))
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(exposure * 100),
        number={"suffix": "/100", "font": {"size": 40}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": MUTED},
            "bar": {"color": MINT, "line": {"color": TEXT, "width": 2}},
            "bgcolor": RAISED,
            "borderwidth": 0,
            "steps": [{"range": [0, 33], "color": EXPOSURE_STEPS[0]}, {"range": [33, 66], "color": EXPOSURE_STEPS[1]},
                      {"range": [66, 100], "color": EXPOSURE_STEPS[2]}],
        },
        title={"text": "AI impact", "font": {"size": 16}},
    ))
    return style_fig(fig, height=260).update_layout(margin=dict(l=40, r=40, t=64, b=8))


# One- or two-word names for the risk/return chart, so no label wraps or crowds a dot (the hover keeps the full title).
SHORT_ROLE_TITLES = {
    "data_scientist": "Data scientist", "statistician": "Data analyst", "software_developer": "Software developer",
    "web_developer": "Web developer", "ux_designer": "UX designer", "security_analyst": "Cybersecurity",
    "cloud_admin": "Cloud admin", "systems_analyst": "Business analyst", "data_architect": "Data architect",
    "qa_engineer": "QA engineer", "ai_researcher": "AI researcher", "it_manager": "IT manager",
    "management_analyst": "Process consultant", "electrical_engineer": "Energy engineer",
    "environmental_specialist": "Sustainability", "marketing_analyst": "Digital marketing", "technical_writer": "Technical writer",
}


def short_role_title(role_id: str | None, title: str) -> str:
    """The chart name for a role: the curated one above, else the part after ' / ' cut to two words, in sentence case."""
    if role_id in SHORT_ROLE_TITLES:
        return SHORT_ROLE_TITLES[role_id]
    words = title.split(" / ")[-1].split()[:2]
    return " ".join([words[0]] + [w.lower() for w in words[1:]]) if words else title


# Pixel estimates for the risk/return chart's plot area at laptop width (14px text). On a phone a label can still
# touch a neighbour; the hover text always has the full title.
_PLOT_W, _PLOT_H, _CHAR_W, _LINE_H, _GAP = 760.0, 300.0, 7.5, 17.0, 4.0
_LABEL_SIDES = ("middle right", "middle left", "top center", "bottom center")


def _label_box(cx: float, cy: float, radius: float, text: str, side: str, bold: bool = False) -> tuple[float, float, float, float]:
    """The pixel box (x0, y0, x1, y1; y up) of a one-line label beside a dot of this radius."""
    w, h, r = len(text) * _CHAR_W * (1.1 if bold else 1.0), _LINE_H, radius + _GAP
    return {
        "middle right": (cx + r, cy - h / 2, cx + r + w, cy + h / 2),
        "middle left": (cx - r - w, cy - h / 2, cx - r, cy + h / 2),
        "top center": (cx - w / 2, cy + r, cx + w / 2, cy + r + h),
        "bottom center": (cx - w / 2, cy - r - h, cx + w / 2, cy - r),
    }[side]


def _fit_ranges(points: list[tuple[float, float]], sizes: list[float], labels: list[str],
                x_range: tuple[float, float], y_range: tuple[float, float]) -> tuple[tuple[float, float], tuple[float, float]]:
    """Widen the x range until every label fits beside its dot on at least one side, however close it is to an edge."""
    x0, x1 = x_range
    for _ in range(3):   # each widening shrinks the scale a little, so repeat until it settles
        x_unit = (x1 - x0) / _PLOT_W
        for (x, _), size, label in zip(points, sizes, labels):
            half = (size / 2 + _GAP + len(label) * _CHAR_W) / 2 * x_unit
            x0, x1 = min(x0, x - half), max(x1, x + half)
    return (x0, x1), y_range


def _place_labels(points: list[tuple[float, float]], sizes: list[float], labels: list[str],
                  fixed: list[tuple[float, float, float, str, str, bool]],
                  x_range: tuple[float, float], y_range: tuple[float, float]) -> list[str]:
    """A side per role label: right of the dot, else left, above or below, whichever hits nothing and stays inside the
    chart. `fixed` are your own dots and labels (x, y, radius, text, side, bold); covering one counts ten times worse.
    Labels are re-placed against each other until none can do better."""
    def px(x: float, y: float) -> tuple[float, float]:
        return ((x - x_range[0]) / (x_range[1] - x_range[0]) * _PLOT_W, (y - y_range[0]) / (y_range[1] - y_range[0]) * _PLOT_H)

    def overlap(a, b) -> float:
        return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))

    dots = [(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2) for (cx, cy), s in zip((px(*p) for p in points), sizes)]
    yours = []
    for x, y, radius, text, side, bold in fixed:
        cx, cy = px(x, y)
        yours += [(cx - radius, cy - radius, cx + radius, cy + radius), _label_box(cx, cy, radius, text, side, bold)]

    options = [{sd: _label_box(*px(*p), size / 2, label, sd) for sd in _LABEL_SIDES} for p, size, label in zip(points, sizes, labels)]
    sides = [_LABEL_SIDES[0]] * len(points)

    def cost(i: int, box: tuple) -> float:
        others = [options[j][sides[j]] for j in range(len(points)) if j != i]
        outside = (box[2] - box[0]) * (box[3] - box[1]) - overlap(box, (0, 0, _PLOT_W, _PLOT_H))
        return sum(overlap(box, t) for t in dots + others) + 10 * sum(overlap(box, t) for t in yours) + 2 * outside

    for _ in range(4):
        changed = False
        for i, boxes in enumerate(options):
            best = min(_LABEL_SIDES, key=lambda sd: (cost(i, boxes[sd]), _LABEL_SIDES.index(sd)))   # ties keep the earlier side
            if cost(i, boxes[best]) < cost(i, boxes[sides[i]]):
                sides[i], changed = best, True
        if not changed:
            break
    return sides


def _nice_step(lo: float, hi: float, most: int = 4) -> float:
    """The smallest of 1, 2, 5, 10, 20, 50, ... that puts at most `most` ticks (multiples of it) between lo and hi."""
    step, factors, i = 1.0, (2, 2.5, 2), 0
    while math.floor(hi / step) - math.ceil(lo / step) + 1 > most:
        step, i = step * factors[i % 3], i + 1
    return step


PLAN_VIEWS = ("Before", "Now", "Both")


def growth_readout(before: dict, after: dict, view: str) -> str:
    """The one line beside the Before / Now / Both control."""
    if view in ("Before", "Now"):
        growth = (before if view == "Before" else after)["growth"] * 100
        return f"Growth {growth:.1f}%/yr".replace("-", "−")
    change = (after["growth"] - before["growth"]) * 100
    if abs(change) < 0.05:
        return "Growth unchanged"
    return f"Growth {'up' if change > 0 else 'down'} {abs(change):.1f} points"


def risk_return_fig(matches: list[dict], user: dict, before: dict | None = None, start: str = "Both",
                    dark: bool = False) -> go.Figure:
    """x = AI exposure, y = growth. Roles as quiet grey-green dots with short names, you as the bright green dot labelled "You".
    With `before`, the chart carries its own Before / Now / Both buttons and a one-line readout. Each button plays a
    Plotly frame in the browser (no Streamlit rerun), so your dot slides between where you were and where the plan takes
    you, and "Both" adds a hollow "Before" ring. It opens on `start` ("Both" by default). The Learning plan opens it on "Before"
    once, right after Apply, and a tiny script presses "Both", so your dot slides from where you were to where the plan takes you.
    `dark` draws it for the charcoal card (dark_container): light text, darker role dots, a mint "You" dot without the ink ring."""
    start = start if before and start in PLAN_VIEWS else "Both"
    text, muted = (ON_CHARCOAL, ON_CHARCOAL_MUTED) if dark else (TEXT, MUTED)
    dot, dot_edge, grid = (ROLE_DOT_DARK, ROLE_DOT_DARK_EDGE, GRID_DARK) if dark else (ROLE_DOT, ROLE_DOT_EDGE, GRID)
    top = matches[: config.TOP_N_ROLES]
    now_xy = (user["ai_exposure"] * 100, user["growth"] * 100)
    before_xy = (before["ai_exposure"] * 100, before["growth"] * 100) if before else None
    roles = [(m["ai_exposure"] * 100, m["role_growth"] * 100) for m in top]
    labels = [short_role_title(m.get("role_id"), m["title"]) for m in top]
    sizes = [20 + 14 * m["match_pct"] for m in top]

    # Ranges from your dot in every view, then widened so each label fits: the chart never rescales between views.
    mine = [now_xy] + ([before_xy] if before_xy else [])
    xs, ys = [x for x, _ in roles + mine], [y for _, y in roles + mine]
    x_pad, y_span = max(6.0, 0.08 * (max(xs) - min(xs))), max(3.0, max(ys) - min(ys))
    x_range, y_range = _fit_ranges(roles, sizes, labels, (min(xs) - x_pad, max(xs) + x_pad),
                                   (min(ys) - 0.15 * y_span, max(ys) + 0.15 * y_span))

    def side_for(x: float, prefer: str) -> str:
        """"You" sits left of its dot and "Before" right of its ring, unless that side runs past the chart's edge."""
        from_left = (x - x_range[0]) / (x_range[1] - x_range[0]) * _PLOT_W
        if prefer == "middle left":
            return "middle left" if from_left > 60 else "middle right"
        return "middle right" if _PLOT_W - from_left > 80 else "middle left"

    before_side = side_for(before_xy[0], "middle right") if before_xy else "middle right"
    # Role labels keep clear of your dot and labels in every view, so they never move when you switch.
    fixed = [(*now_xy, 8, "You", side_for(now_xy[0], "middle left"), True)]
    if before_xy:
        fixed += [(*before_xy, 8, "You", side_for(before_xy[0], "middle left"), True),
                  (*before_xy, 8, "Before", before_side, False)]
    sides = _place_labels(roles, sizes, labels, fixed, x_range, y_range)

    def ring_trace(show: bool) -> go.Scatter:
        """The hollow "Before" ring: always drawn (see-through unless shown), so every view has the same traces."""
        xy = before_xy or now_xy
        return go.Scatter(
            x=[xy[0]], y=[xy[1]], mode="markers+text", text=["Before" if show else ""], textposition=before_side,
            textfont=dict(color=muted), cliponaxis=False, name="Before",
            marker=dict(size=16, color="rgba(0,0,0,0)", line=dict(color=muted if show else "rgba(0,0,0,0)", width=1.5)),
            hovertemplate="You, before the plan<br>AI exposure %{x:.0f}/100<br>Growth %{y:+.1f}%<extra></extra>",
        )

    def you_trace(xy: tuple[float, float]) -> go.Scatter:
        """Your dot: the last trace, so theme.css can give it the soft pulse (inside .st-key-sf-plan-chart)."""
        return go.Scatter(
            x=[xy[0]], y=[xy[1]], mode="markers+text", text=["<b>You</b>"], textposition=side_for(xy[0], "middle left"),
            textfont=dict(color=text, size=15), cliponaxis=False, name="You",
            marker=dict(size=16, color=MINT, line=dict(color=MINT, width=0) if dark else dict(color=TEXT, width=2)),
            hovertemplate="You<br>AI exposure %{x:.0f}/100<br>Growth %{y:+.1f}%<extra></extra>",
        )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[x for x, _ in roles], y=[y for _, y in roles], mode="markers+text", text=labels, textposition=sides,
        textfont=dict(color=text), cliponaxis=False,
        marker=dict(size=sizes, color=dot, opacity=1, line=dict(color=dot_edge, width=1)),   # Plotly fades these to 0.7 by default
        customdata=[[round(m["match_pct"] * 100), m["title"]] for m in top],
        hovertemplate="%{customdata[1]}<br>AI exposure %{x:.0f}/100<br>Growth %{y:+.1f}%<br>Match %{customdata[0]}%<extra></extra>",
        name="Future roles",
    ))
    you_at = {"Before": before_xy, "Now": now_xy, "Both": now_xy} if before_xy else {"Both": now_xy}
    fig.add_trace(ring_trace(before_xy is not None and start == "Both"))
    fig.add_trace(you_trace(you_at[start]))
    style_fig(fig, height=420 if before_xy else 400)
    axis = dict(showline=False, zeroline=False, ticks="", tickfont=dict(color=muted, size=14), title_font=dict(color=muted, size=14))
    fig.update_xaxes(**axis, title="AI exposure (lower is harder to automate)", range=list(x_range), showgrid=False,
                     tick0=0, dtick=20)
    fig.update_yaxes(**axis, title="Demand growth (%/yr)", range=list(y_range), showgrid=True, gridcolor=grid, gridwidth=1,
                     tick0=0, dtick=_nice_step(*y_range))
    fig.update_layout(showlegend=False, margin=dict(l=8, r=8, t=8, b=8))
    if dark:
        fig.update_layout(font=dict(color=text), hoverlabel=dict(bgcolor=CHARCOAL, bordercolor=ROLE_DOT_DARK_EDGE,
                                                                 font=dict(color=ON_CHARCOAL)))
    if before_xy is None:
        return fig

    def readout(view: str) -> dict:
        return dict(text=f"<b>{esc(growth_readout(before, user, view))}</b>", xref="paper", yref="paper", x=1, y=1.02,
                    xanchor="right", yanchor="bottom", showarrow=False, font=dict(color=text, size=15))

    fig.frames = [go.Frame(name=v, traces=[1, 2], data=[ring_trace(v == "Both"), you_trace(you_at[v])],
                           layout=dict(annotations=[readout(v)])) for v in PLAN_VIEWS]
    # redraw=True so the readout (a layout annotation) changes too; the dot still slides during the transition.
    slide = dict(frame=dict(duration=600, redraw=True), transition=dict(duration=600, easing="cubic-in-out"), mode="immediate")
    fig.update_layout(
        margin=dict(t=56),
        annotations=[readout(start)],
        updatemenus=[dict(
            type="buttons", direction="right", active=PLAN_VIEWS.index(start), showactive=True,
            x=0, y=1.02, xanchor="left", yanchor="bottom", pad=dict(t=0, r=0, b=0, l=0),
            bgcolor=CHARCOAL if dark else CARD, bordercolor=ROLE_DOT_DARK_EDGE if dark else BORDER, borderwidth=1,
            font=dict(color=text, size=15),
            buttons=[dict(label=v, method="animate", args=[[v], slide]) for v in PLAN_VIEWS],
        )],
    )
    return fig


# --- CSS (the one injection point) --------------------------------------------------------------------

_CSS_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');"
_THEME_FILE = Path(__file__).with_name("theme.css")


def _lerp_hex(a: str, b: str, t: float) -> str:
    t = min(1.0, max(0.0, t))
    pa, pb = [int(a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)], [int(b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(pa, pb))


def _css_vars() -> str:
    """The tokens above as CSS variables (the stylesheet never repeats a hex code; tints are made with color-mix)."""
    return (
        ":root{"
        f"--sf-bg:{BG};--sf-card:{CARD};--sf-sidebar:{SIDEBAR};--sf-raised:{RAISED};--sf-border:{BORDER};"
        f"--sf-text:{TEXT};--sf-muted:{MUTED};--sf-on-ink:{ON_INK};--sf-mint:{MINT};"
        f"--sf-charcoal:{CHARCOAL};--sf-on-charcoal:{ON_CHARCOAL};--sf-on-charcoal-muted:{ON_CHARCOAL_MUTED};"
        f"--sf-up:{UP};--sf-up-text:{UP_TEXT};--sf-down:{DOWN};--sf-down-text:{DOWN_TEXT};"
        f"--sf-up-bg:color-mix(in srgb,{UP} 12%,{CARD});--sf-down-bg:color-mix(in srgb,{DOWN} 10%,{CARD});"
        f"--sf-flat-bg:{RAISED};--sf-exposure:{EXPOSURE_HIGH};--sf-exposure-soft:{EXPOSURE_STEPS[1]};"
        f"--sf-font:{FONT_TEXT};--sf-radius:{RADIUS}px;--sf-radius-tile:{RADIUS_TILE}px;--sf-radius-control:{RADIUS_CONTROL}px;--sf-shadow:{SHADOW};"
        "}"
    )


def css_text() -> str:
    """The whole stylesheet as one string: the font import, the token variables, then app/theme.css (separate from
    inject_css so it can be tested)."""
    return "\n".join([_CSS_IMPORT, _css_vars(), _THEME_FILE.read_text(encoding="utf-8")])


def inject_css() -> None:
    """Inject the SkillFolio stylesheet. Called once per page by `page_setup`, so pages never call it.

    Inter loads from Google Fonts; offline the system-ui fallback is used and nothing breaks.
    """
    st.markdown(f"<style>{css_text()}</style>", unsafe_allow_html=True)


# --- HTML components ----------------------------------------------------------------------------------
# Every builder returns ONE LINE of HTML (no blank lines or indentation, which Streamlit's markdown would
# mangle). Every piece of data text goes through esc(). Render with show(...). Pages never write raw HTML.

def esc(text) -> str:
    """HTML-escape data text (skill names, resume text, profile names). Collapses whitespace and neutralises
    `$` so Streamlit does not treat it as maths."""
    return _html.escape(" ".join(str(text).split()), quote=True).replace("$", "&#36;")


def show(*parts: str) -> None:
    """Render one or more HTML strings built by the helpers below."""
    st.markdown("".join(parts).replace("\n", " "), unsafe_allow_html=True)


def small_label(text: str) -> str:
    """A small plain label above a name inside a card (Inter, 14px, secondary colour). Not a page eyebrow: pages have none."""
    return f'<div class="sf-label">{esc(text)}</div>'


def lead(text: str) -> str:
    """One calm sentence under a page title."""
    return f'<p class="sf-lead">{esc(text)}</p>'


def page_head(title: str, lead_text: str | None = None, narrow: bool = False) -> str:
    """The opening of EVERY page: the title (32px semibold) and an optional one-line subtitle. No eyebrow, no numbering.
    `narrow=True` puts a marker the stylesheet uses to give text pages a narrower column."""
    cls = "sf-pagehead" + (" sf-narrow" if narrow else "")
    return f'<header class="{cls}"><h1 class="sf-title">{esc(title)}</h1>{lead(lead_text) if lead_text else ""}</header>'


def page_header(title: str, lead_text: str | None = None, narrow: bool = False) -> None:
    """Render `page_head(...)`. Every page calls this first (after page_setup)."""
    show(page_head(title, lead_text, narrow))


def steps_html(labels: tuple[str, ...] | list[str], current: int | None = None, aria_label: str = "How it works", extra_class: str = "") -> str:
    """The step indicator. With `current` (1-based): the text 'Step 2 of 4: Skills' and a thin amber progress bar, followed by the
    list of steps (visually hidden; each item says done / current / not started, and the current one has aria-current).
    Without `current`: the steps as one plain line of words."""
    total = len(labels)
    items = []
    for i, label in enumerate(labels, 1):
        state = "done" if current and i < current else "current" if i == current else "todo"
        aria = ' aria-current="step"' if state == "current" else ""
        word = {"done": "completed", "current": "current step", "todo": "not started"}[state]
        items.append(f'<li class="sf-step-{state}"{aria} aria-label="Step {i} of {total}: {esc(label)}, {word}">'
                     f'<span>{esc(label)}</span></li>')
    klass = f'sf-steps{" " + extra_class if extra_class else ""}'
    if not current:
        return f'<ol class="{klass}" aria-label="{esc(aria_label)}">{"".join(items)}</ol>'
    pct = max(0, min(100, round(100 * current / total)))
    label = labels[current - 1] if 1 <= current <= total else ""
    return (f'<div class="sf-stepper" aria-label="{esc(aria_label)}"><div class="sf-step-text">Step {int(current)} of {total}: {esc(label)}</div>'
            f'<div class="sf-track" role="progressbar" aria-label="Setup progress" aria-valuemin="0" aria-valuemax="100" '
            f'aria-valuenow="{pct}"><i style="width:{pct}%"></i></div><ol class="{klass} sf-vh" aria-label="{esc(aria_label)}">{"".join(items)}</ol></div>')


def status_chip(text: str, level: str = "plain") -> str:
    """A word-bearing status chip. level: 'strong' (accent tint) | 'plain' | 'stretch' (muted). Never colour alone."""
    return f'<span class="sf-status sf-status-{level if level in ("strong", "stretch") else "plain"}">{esc(text)}</span>'


def note(text: str) -> str:
    """A calm one-paragraph message card."""
    return f'<div class="sf-note">{esc(text)}</div>'


def strip_container(key: str):
    """The inline alert strip of a role card: a container with text on the left and ONE button on the right (flex row).
    Use as `with strip_container(f"{role_id}"): show(...); st.button(...)`."""
    try:
        return st.container(key=f"sf-strip-{key}")
    except TypeError:                       # older Streamlit without container keys: plain container
        return st.container()


def dark_container():
    """The ONE charcoal feature card on a page (Home: the hiring-trend number and its bars). Widgets inside it (the range tabs) are
    styled for a dark surface by app/theme.css."""
    try:
        return st.container(key="sf-dark")
    except TypeError:                       # older Streamlit without container keys: plain container
        return st.container()


def row_container(key: str, separated: bool = False):
    """One compact row in a list card (roles 2 and 3 on Home): a keyed container so the stylesheet can find it.
    `separated=True` (every row after the first) gets a hairline above it; the key prefix carries that, because Streamlit wraps each
    container in its own element, so a sibling selector cannot."""
    try:
        return st.container(key=f"sf-row-{'sep-' if separated else ''}{key}")
    except TypeError:                       # older Streamlit without container keys: plain container
        return st.container()


def side_panel():
    """The right-hand detail panel at wide widths (a card; sticky on desktop, stacks under the list on a phone)."""
    try:
        return st.container(key="sf-side")
    except TypeError:
        return st.container(border=True)


def card_container():
    """A bordered Streamlit container styled as a card (surface colour, 14px radius). Use as
    `with card_container(): ...` for widgets inside. Gets a per-run counter key so the CSS can find it; the counter
    is reset by page_setup, so keys are stable between reruns."""
    n = st.session_state.get("_sf_card_n", 0)
    st.session_state["_sf_card_n"] = n + 1
    try:
        return st.container(border=True, key=f"sf-card-{n}")
    except TypeError:                       # older Streamlit without container keys: plain bordered container
        return st.container(border=True)


_ICONS = {
    "trending-up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "trending-down": '<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/>',
    "minus": '<line x1="5" y1="12" x2="19" y2="12"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "briefcase": '<rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "eye": '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    "compass": '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>',
    "line-chart": '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "file-text": '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
}


def icon(name: str, size: int = 16) -> str:
    """Inline SVG icon (Lucide-style, stroke = currentColor, decorative). Unknown name -> empty string.
    Names: trending-up, trending-down, minus, arrow-right, briefcase, eye, compass, line-chart, info, user, file-text, check."""
    body = _ICONS.get(name)
    if not body:
        return ""
    return (f'<svg class="sf-icon" width="{int(size)}" height="{int(size)}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{body}</svg>')


_PILL_ICON = {"up": "trending-up", "down": "trending-down", "flat": "minus", "low": "minus",
              "lean-up": "trending-up", "lean-down": "trending-down"}       # lean: an uncertain direction, drawn in neutral colours


def pill(text: str, direction: str = "flat", help_text: str | None = None) -> str:
    """A rounded status pill: arrow icon + your text. direction: 'up' (green) | 'down' (red) | 'flat' | 'low' (grey) |
    'lean-up' / 'lean-down' (grey, with the arrow: a direction the estimate is not sure of). `help_text` becomes a hover tooltip.
    Put the sign AND a word in `text` (e.g. '+9.7% rising') so colour is never the only signal."""
    d = direction if direction in _PILL_ICON else "flat"
    title = f' title="{esc(help_text)}"' if help_text else ""
    return f'<span class="sf-pill sf-pill-{d}"{title}>{icon(_PILL_ICON[d], 14)}<span>{esc(text)}</span></span>'


def fmt_signed(x: float | None, decimals: int = 1) -> str:
    """0.123 -> '+12.3%', -0.04 -> '−4.0%' (true minus sign), None -> '—'."""
    return "—" if x is None else f"{x * 100:+.{decimals}f}%".replace("-", "−")


_TRAJECTORY_DIR = {"rising": "up", "declining": "down", "stable": "flat"}


def _direction(x: float | None, threshold: float = 0.005) -> str:
    return "flat" if x is None else "up" if x > threshold else "down" if x < -threshold else "flat"


def direction_of(x: float | None) -> str:
    """'up' | 'down' | 'flat' for a fractional change (use for hero / pill direction)."""
    return _direction(x)


def sparkline(values: list[float] | None, direction: str = "flat", width: int = 88, height: int = 28) -> str:
    """A tiny inline-SVG line. Fewer than 2 points -> a dash."""
    vals = [float(v) for v in (values or [])]
    if len(vals) < 2:
        return '<span class="sf-sub" aria-hidden="true">—</span>'
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    pad = 3
    pts = " ".join(
        f"{pad + (width - 2 * pad) * i / (len(vals) - 1):.1f},{height - pad - (height - 2 * pad) * (v - lo) / span:.1f}"
        for i, v in enumerate(vals)
    )
    colour = DIRECTION_COLOUR.get(direction, FLAT)
    return (f'<svg class="sf-spark" viewBox="0 0 {width} {height}" aria-hidden="true" focusable="false">'
            f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def exposure_bar(exposure: float | None) -> str:
    """AI exposure 0..1 as a thin amber bar plus the 0-100 number. None -> '—'. Never red/green."""
    if exposure is None:
        return '<div class="sf-exp" title="No AI-exposure data for this skill yet."><span class="sf-exp-num sf-sub">—</span></div>'
    score = max(0, min(100, round(exposure * 100)))
    fill = _lerp_hex(EXPOSURE_LOW, EXPOSURE_HIGH, score / 100)
    return (f'<div class="sf-exp" title="AI exposure {score} out of 100"><span class="sf-bar"><i style="width:{max(score, 4)}%;background:{fill}"></i></span>'
            f'<span class="sf-exp-num">{score}</span></div>')


def hero(label: str, value: str, delta_text: str | None = None, delta_dir: str = "flat", caption: str | None = None) -> str:
    """The big number: small label, huge mono value, optional delta pill (arrow + your text) and caption."""
    pill_html = f'<div>{pill(delta_text, delta_dir)}</div>' if delta_text else ""
    cap_html = f'<div class="sf-hero-cap">{esc(caption)}</div>' if caption else ""
    return (f'<div class="sf-hero"><div class="sf-hero-label">{esc(label)}</div><div class="sf-hero-value">{esc(value)}</div>'
            f'{pill_html}{cap_html}</div>')


def section_header(title: str, subtitle: str | None = None, icon_name: str | None = None, right_html: str | None = None,
                   tight: bool = False) -> str:
    """Section heading with optional icon, one-line subtitle and a right-aligned HTML snippet (e.g. a pill)."""
    sub = f'<div class="sf-sec-sub">{esc(subtitle)}</div>' if subtitle else ""
    right = f'<div>{right_html}</div>' if right_html else ""
    ic = icon(icon_name, 18) if icon_name else ""
    return (f'<div class="sf-sec{" sf-sec-tight" if tight else ""}"><div><div class="sf-sec-title" role="heading" aria-level="2">{ic}<span>{esc(title)}</span></div>'
            f'{sub}</div>{right}</div>')


def stat_row(items: list[tuple]) -> str:
    """A row of small stat cards. items = [(label, value), ...] or [(label, value, help_text), ...] (help = hover tooltip)."""
    cells = []
    for item in items:
        label, value, *rest = item
        tip = f' title="{esc(rest[0])}"' if rest and rest[0] else ""
        cells.append(f'<div class="sf-stat"{tip}><div class="sf-stat-label">{esc(label)}</div><div class="sf-stat-value">{esc(value)}</div></div>')
    return f'<div class="sf-stats">{"".join(cells)}</div>'


