"""Shared UI helpers for every page (lane C). Visual rules: docs/DESIGN.md and .claude/skills/skillfolio-design.

The look is the v4 LIGHT system: warm off-white page, white cards with a 1px soft border and 10px radius, ink text, ONE
family (Inter), amber used for fills only (progress tracks, the chart line, the selected underline).

Page files never contain hex codes or raw HTML. They use:
  * tokens below (BG, CARD, AMBER, UP, DOWN, FLAT, ...),
  * `page_setup(title)`, which injects the one shared stylesheet (`inject_css()`) and draws the sidebar,
  * the component builders in "HTML components" (each returns an HTML string; render it with `show(...)`),
  * `style_fig` / `show_fig` for Plotly.
"""

from __future__ import annotations

import html as _html
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from engine import config
from engine.data import load_courses, load_role_skills, load_roles, load_skills, load_snapshot

# --- Design tokens (docs/DESIGN.md section 1): the ONE token set for every page. No hex codes in page files. --------
# Contrast is computed by tools/design_audit.py (and tests/test_design_audit.py): text >= 7:1 for body and secondary
# text, >= 4.5:1 for everything else. AMBER fails as text (about 2:1 on white), so it is a FILL colour only.
BG = "#F7F5F0"            # page (warm off-white)
CARD = "#FFFFFF"          # cards, inputs
SIDEBAR = "#FBFAF7"       # sidebar surface
RAISED = "#F1EEE6"        # hover rows, selected nav item, segmented-control track
BORDER = "#E7E2D8"        # 1px soft border
GRID = "#ECE8DE"          # chart gridlines
TEXT = "#1B1A17"          # ink: body text, primary button fill, links
MUTED = "#534E49"         # secondary text (never lighter; never smaller than 14px)
ON_INK = "#FFFFFF"        # label on an ink fill (primary button)
AMBER = "#E8A33D"         # FILLS ONLY: progress track, chart line, selected-tab underline, nav marker
UP = "#1E8E5A"            # rising: arrows and chart marks (never text on its own)
UP_TEXT = "#115A38"       # rising: text on a white card or a green tint
DOWN = "#C8372D"          # falling: arrows and chart marks
DOWN_TEXT = "#93251E"     # falling: text on a white card or a red tint
FLAT = MUTED
EXPOSURE_LOW = "#CFC5B0"  # AI impact: one neutral grey-brown scale, never red/green (AI impact is not "bad")
EXPOSURE_HIGH = "#6B5D45"
EXPOSURE_STEPS = ["#E4DDCE", "#B8AA90", "#6B5D45"]
DIRECTION_COLOUR = {"up": UP, "down": DOWN, "flat": FLAT, "low": FLAT}
FONT_TEXT = "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"   # the only family
RADIUS = 10               # px: cards, inputs, expanders (buttons and inputs use 8, chips 6)
SHADOW = "0 1px 2px rgba(27,26,23,0.06)"   # the only shadow: very soft, on cards

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
TRAJECTORY = {"rising": "▲ rising", "stable": "● stable", "declining": "▼ declining"}
LOW_DATA = "● low data"

# Tooltips (DESIGN.md §6)
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
    """'Moderate AI disruption' -> 'Moderate AI' (the short pill label)."""
    return config.SCENARIOS[key]["label"].replace(" disruption", "")


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
            help="Moderate or fast: how strongly AI changes which skills employers ask for. It is a what-if, not a prediction.",
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
        show('<div class="sf-side-label">AI scenario</div>')
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
        st.info("Set up your profile first — pick your skills or load a sample.")
        st.page_link("pages/1_Profile.py", label="Go to 1 · Profile", icon=":material/person:")
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
    return "▲" if x > threshold else "▼" if x < -threshold else "●"


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
    """engine.api.analyse for this profile and the sidebar scenario, with every role ranked (pages slice the top N).
    Shows the problem and returns None if the profile can't be scored."""
    from engine import api

    try:
        result = call_or_wait("A", "the engine", api.analyse, profile, snapshot, scenario(), top_n=None)
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


# --- Charts (DESIGN.md section 5) ---------------------------------------------------------------------

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
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def demand_fig(months: list[str], values: list[float], direction: str = "flat", height: int = 300) -> go.Figure:
    """The line chart: ONE amber line, an ink dot on the last month, a dotted line at the start level (100).
    `direction` is kept for callers; the line is amber whatever it is (up or down is said in words next to the chart)."""
    fig = go.Figure(go.Scatter(
        x=months, y=values, mode="lines", line=dict(color=AMBER, width=3, shape="spline", smoothing=0.4),
        hovertemplate="%{x}<br>Demand index %{y:.1f}<extra></extra>", showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=months[-1:], y=values[-1:], mode="markers", marker=dict(size=9, color=TEXT, line=dict(color=CARD, width=2)),
        hoverinfo="skip", showlegend=False,
    ))
    fig.add_hline(y=100, line_dash="dot", line_color=BORDER, line_width=1)
    fig.update_yaxes(title=None)
    fig.update_xaxes(title=None, showgrid=False)
    return style_fig(fig, height=height)


def gauge_fig(exposure: float | None, before: float | None = None) -> go.Figure:
    """AI-exposure gauge, 0-100, one neutral grey-brown scale with an amber bar (never red/green). Empty with "n/a" when unknown."""
    if exposure is None:
        fig = go.Figure(go.Indicator(mode="gauge", value=0, gauge={"axis": {"range": [0, 100]}, "bar": {"color": GRID}},
                                     title={"text": "AI impact: n/a"}))
        return style_fig(fig, height=240)
    if before is not None and round(before * 100) == round(exposure * 100):
        before = None   # no change at this precision: Plotly would draw a bare "-" under the number
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta" if before is not None else "gauge+number",
        value=round(exposure * 100),
        number={"suffix": "/100"},
        delta={"reference": round(before * 100), "increasing": {"color": FLAT}, "decreasing": {"color": FLAT}} if before is not None else None,
        gauge={
            "axis": {"range": [0, 100], "tickcolor": MUTED},
            "bar": {"color": AMBER},
            "bgcolor": RAISED,
            "borderwidth": 0,
            "steps": [{"range": [0, 33], "color": EXPOSURE_STEPS[0]}, {"range": [33, 66], "color": EXPOSURE_STEPS[1]},
                      {"range": [66, 100], "color": EXPOSURE_STEPS[2]}],
        },
        title={"text": "AI impact"},
    ))
    fig = style_fig(fig, height=260)
    fig.update_layout(margin=dict(t=56))   # room for the title above the arc
    return fig


def _wrap_label(title: str, width: int = 18) -> str:
    """Break a long role title onto two lines (at ' / ' or the middle space) so it fits beside the chart's edge."""
    if len(title) <= width:
        return title
    if " / " in title:
        return title.replace(" / ", " /<br>", 1)
    words = title.split()
    cut = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(title) / 2))
    return " ".join(words[:cut]) + "<br>" + " ".join(words[cut:])


# Pixel estimates for the risk/return chart's plot area at laptop width (14px text). On a phone a label can still
# touch a neighbour; the hover text always has the full title.
_PLOT_W, _PLOT_H, _CHAR_W, _LINE_H, _GAP = 760.0, 290.0, 7.5, 17.0, 3.0


def _label_size(label: str) -> tuple[float, float]:
    lines = label.split("<br>")
    return max(map(len, lines)) * _CHAR_W, len(lines) * _LINE_H


def _fit_ranges(points: list[tuple[float, float]], sizes: list[float], labels: list[str],
                x_range: tuple[float, float], y_range: tuple[float, float]) -> tuple[tuple[float, float], tuple[float, float]]:
    """Widen the axis ranges until every label fits centred above its dot, so no label is ever pushed past an edge
    (or across your arrow) for lack of room."""
    (x0, x1), (y0, y1) = x_range, y_range
    for _ in range(3):   # each widening shrinks the scale a little, so repeat until it settles
        x_unit, y_unit = (x1 - x0) / _PLOT_W, (y1 - y0) / _PLOT_H
        for (x, y), size, label in zip(points, sizes, labels):
            w, h = _label_size(label)
            x0, x1 = min(x0, x - (w / 2 + _GAP) * x_unit), max(x1, x + (w / 2 + _GAP) * x_unit)
            y1 = max(y1, y + (size / 2 + _GAP + h) * y_unit)
    return (x0, x1), (y0, y1)


def _place_labels(points: list[tuple[float, float]], sizes: list[float], labels: list[str], you: list[tuple[float, float]],
                  path: list[tuple[float, float]], before_side: str | None,
                  x_range: tuple[float, float], y_range: tuple[float, float]) -> list[str]:
    """A text position per role dot: above, right, left, below or a diagonal, whichever label box hits nothing and stays
    inside the chart. Covering your dots, their labels or your before-to-after path counts ten times worse than
    touching a role's dot or label. Each label is re-placed against the others until none can do better, so an early
    label does not take the only clear spot a later one needed."""
    def px(x: float, y: float) -> tuple[float, float]:
        return ((x - x_range[0]) / (x_range[1] - x_range[0]) * _PLOT_W, (y - y_range[0]) / (y_range[1] - y_range[0]) * _PLOT_H)

    def overlap(a, b) -> float:
        return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))

    taken = [(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2) for (cx, cy), s in zip((px(*p) for p in points), sizes)]
    yours = []
    for i, (ux, uy) in enumerate(px(*p) for p in you):
        yours.append((ux - 10, uy - 10, ux + 10, uy + 10))
        if i == 0:   # the "You" label below your dot
            yours.append((ux - 15, uy - 10 - _GAP - _LINE_H, ux + 15, uy - 10))
        elif before_side == "top center":
            yours.append((ux - 27, uy + 10, ux + 27, uy + 10 + _GAP + _LINE_H))
        elif before_side == "bottom center":
            yours.append((ux - 27, uy - 10 - _GAP - _LINE_H, ux + 27, uy - 10))
    yours += [(x - 3, y - 3, x + 3, y + 3) for x, y in (px(*q) for q in path)]   # the path, as 6px boxes along it

    def candidates(cx: float, cy: float, size: float, label: str) -> dict[str, tuple]:
        (w, h), r = _label_size(label), size / 2 + _GAP
        return {
            "top center": (cx - w / 2, cy + r, cx + w / 2, cy + r + h),
            "middle right": (cx + r, cy - h / 2, cx + r + w, cy + h / 2),
            "middle left": (cx - r - w, cy - h / 2, cx - r, cy + h / 2),
            "bottom center": (cx - w / 2, cy - r - h, cx + w / 2, cy - r),
            "top right": (cx + r, cy + r, cx + r + w, cy + r + h),
            "top left": (cx - r - w, cy + r, cx - r, cy + r + h),
            "bottom right": (cx + r, cy - r - h, cx + r + w, cy - r),
            "bottom left": (cx - r - w, cy - r - h, cx - r, cy - r),
        }

    options = [candidates(*px(*p), size, label) for p, size, label in zip(points, sizes, labels)]
    sides = ["top center"] * len(points)

    def cost(i: int, box: tuple) -> float:
        others = [options[j][sides[j]] for j in range(len(points)) if j != i]
        outside = (box[2] - box[0]) * (box[3] - box[1]) - overlap(box, (0, 0, _PLOT_W, _PLOT_H + _LINE_H))
        return (sum(overlap(box, t) for t in taken + others) + 10 * sum(overlap(box, t) for t in yours) + 2 * outside)

    for _ in range(4):
        changed = False
        for i, boxes in enumerate(options):
            best = min(boxes, key=lambda sd: (cost(i, boxes[sd]), list(boxes).index(sd)))   # ties keep the earlier side
            if cost(i, boxes[best]) < cost(i, boxes[sides[i]]):
                sides[i], changed = best, True
        if not changed:
            break
    return sides


def _plan_path(start: tuple[float, float], end: tuple[float, float], x_range: tuple[float, float],
               y_range: tuple[float, float], gap_start: float = 14.0, gap_end: float = 15.0) -> list[tuple[float, float]]:
    """Points along a gentle curve from your before dot to your dot, stopping short of both (in pixels) so the line
    never cuts into a dot. Empty when the dots are too close for a line to show."""
    def px(x, y):
        return (x - x_range[0]) / (x_range[1] - x_range[0]) * _PLOT_W, (y - y_range[0]) / (y_range[1] - y_range[0]) * _PLOT_H

    def data(x, y):
        return x_range[0] + x / _PLOT_W * (x_range[1] - x_range[0]), y_range[0] + y / _PLOT_H * (y_range[1] - y_range[0])

    (ax, ay), (bx, by) = px(*start), px(*end)
    length = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
    if length < gap_start + gap_end + 12:
        return []
    bend = 0.18 * length   # how far the curve bows out from the straight line, sideways
    cx, cy = (ax + bx) / 2 - (by - ay) / length * bend, (ay + by) / 2 + (bx - ax) / length * bend
    curve = [((1 - t) ** 2 * ax + 2 * (1 - t) * t * cx + t ** 2 * bx, (1 - t) ** 2 * ay + 2 * (1 - t) * t * cy + t ** 2 * by)
             for t in (i / 80 for i in range(81))]
    kept = [(x, y) for x, y in curve
            if ((x - ax) ** 2 + (y - ay) ** 2) ** 0.5 >= gap_start and ((x - bx) ** 2 + (y - by) ** 2) ** 0.5 >= gap_end]
    return [data(x, y) for x, y in kept] if len(kept) >= 2 else []


def risk_return_fig(matches: list[dict], user: dict, before: dict | None = None) -> go.Figure:
    """x = AI exposure, y = growth. Roles as grey bubbles sized by match %, the user as the amber dot with an ink ring;
    with `before`, a faded dot where you were and a dotted curve to where the plan takes you."""
    top = matches[: config.TOP_N_ROLES]
    you = [(user["ai_exposure"] * 100, user["growth"] * 100)] + ([(before["ai_exposure"] * 100, before["growth"] * 100)] if before else [])
    roles = [(m["ai_exposure"] * 100, m["role_growth"] * 100) for m in top]
    # Fixed ranges padded past the outermost dots, then widened so every role label fits (see _fit_ranges).
    xs, ys = [x for x, _ in roles + you], [y for _, y in roles + you]
    x_pad, y_span = max(8.0, 0.12 * (max(xs) - min(xs))), max(4.0, max(ys) - min(ys))
    x_range, y_range = (min(xs) - x_pad, max(xs) + x_pad), (min(ys) - 0.12 * y_span, max(ys) + 0.3 * y_span)
    labels = [_wrap_label(m["title"]) for m in top]
    sizes = [12 + 40 * m["match_pct"] for m in top]
    x_range, y_range = _fit_ranges(roles, sizes, labels, x_range, y_range)
    path = _plan_path(you[1], you[0], x_range, y_range) if before is not None else []
    before_side = None if before is None else "top center" if you[1][1] >= you[0][1] else "bottom center"
    sides = _place_labels(roles, sizes, labels, you, path, before_side, x_range, y_range)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[x for x, _ in roles],
        y=[y for _, y in roles],
        mode="markers+text",
        text=labels,
        textposition=sides,
        cliponaxis=False,
        marker=dict(size=sizes, color=EXPOSURE_STEPS[1], opacity=0.7),
        customdata=[[round(m["match_pct"] * 100), m["title"]] for m in top],
        hovertemplate="%{customdata[1]}<br>AI exposure %{x:.0f}/100<br>Growth %{y:+.1f}%<br>Match %{customdata[0]}%<extra></extra>",
        name="Future roles",
    ))
    if before is not None:
        # You before the plan: a faded copy of your dot, joined to it by a dotted amber curve that ends in an arrowhead.
        fig.add_trace(go.Scatter(
            x=[you[1][0]], y=[you[1][1]], mode="markers+text", text=["Before"], textposition=before_side,
            textfont=dict(color=MUTED), cliponaxis=False,
            marker=dict(size=16, color="rgba(232,163,61,0.28)", line=dict(color=AMBER, width=2)),   # AMBER at 28%, full ring
            hovertemplate="You, before the plan<br>AI exposure %{x:.0f}/100<br>Growth %{y:+.1f}%<extra></extra>", name="Before",
        ))
        if path:
            fig.add_trace(go.Scatter(
                x=[x for x, _ in path], y=[y for _, y in path], mode="lines+markers",
                line=dict(color=AMBER, width=3, dash="dot", shape="spline"),
                marker=dict(symbol="arrow-wide", angleref="previous", size=[0] * (len(path) - 1) + [13], color=AMBER, line=dict(width=0)),
                hoverinfo="skip", showlegend=False, cliponaxis=False,
            ))
    fig.add_trace(go.Scatter(
        x=[user["ai_exposure"] * 100], y=[user["growth"] * 100], mode="markers+text", text=["You"], textposition="bottom center",
        marker=dict(size=18, color=AMBER, line=dict(color=TEXT, width=2)),
        hovertemplate="You<br>AI exposure %{x:.0f}/100<br>Growth %{y:+.1f}%<extra></extra>", name="You",
    ))
    fig.update_xaxes(title="AI exposure (0–100) — lower is harder to automate", range=list(x_range))
    fig.update_yaxes(title="Expected demand growth (%/yr)", range=list(y_range))
    return style_fig(fig, height=400)


SDG_COLOURS = [AMBER, "#F2CB8A", "#D9C7A3", "#B8AA90", "#F7E3BD", "#CFC8BA", "#E3B46B", "#EFE6D2"]   # warm neutrals + amber; ink text stays >= 7:1 on all


def sdg_donut(allocation: dict[int, float]) -> go.Figure:
    goals = sorted(allocation, key=allocation.get, reverse=True)
    fig = go.Figure(go.Pie(
        labels=[f"SDG {g} · {SDG_NAMES.get(g, '')}" for g in goals],
        values=[allocation[g] for g in goals],
        hole=0.55, sort=False,
        marker=dict(colors=[SDG_COLOURS[i % len(SDG_COLOURS)] for i in range(len(goals))], line=dict(color=CARD, width=2)),
        hovertemplate="%{label}<br>%{percent} of your skills<extra></extra>",
        textinfo="percent", textfont=dict(color=TEXT, size=14),
    ))
    return style_fig(fig, height=320)


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
        f"--sf-text:{TEXT};--sf-muted:{MUTED};--sf-on-ink:{ON_INK};--sf-amber:{AMBER};"
        f"--sf-up:{UP};--sf-up-text:{UP_TEXT};--sf-down:{DOWN};--sf-down-text:{DOWN_TEXT};"
        f"--sf-up-bg:color-mix(in srgb,{UP} 12%,{CARD});--sf-down-bg:color-mix(in srgb,{DOWN} 10%,{CARD});"
        f"--sf-flat-bg:{RAISED};--sf-exposure:{EXPOSURE_HIGH};"
        f"--sf-font:{FONT_TEXT};--sf-radius:{RADIUS}px;--sf-shadow:{SHADOW};"
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


_PILL_ICON = {"up": "trending-up", "down": "trending-down", "flat": "minus", "low": "minus"}


def pill(text: str, direction: str = "flat") -> str:
    """A rounded status pill: arrow icon + your text. direction: 'up' (green) | 'down' (red) | 'flat' | 'low' (grey).
    Put the sign AND a word in `text` (e.g. '+9.7% rising') so colour is never the only signal."""
    d = direction if direction in _PILL_ICON else "flat"
    return f'<span class="sf-pill sf-pill-{d}">{icon(_PILL_ICON[d], 14)}<span>{esc(text)}</span></span>'


def fmt_signed(x: float | None, decimals: int = 1) -> str:
    """0.123 -> '+12.3%', -0.04 -> '−4.0%' (true minus sign), None -> '—'."""
    return "—" if x is None else f"{x * 100:+.{decimals}f}%".replace("-", "−")


_TRAJECTORY_DIR = {"rising": "up", "declining": "down", "stable": "flat"}


def change_pill(change: float | None, trajectory: str | None = None, thin: bool = False) -> str:
    """Momentum pill: '+9.7% rising' / '−3.0% declining' / '+0.8% stable' / 'low data'.
    `trajectory` is the engine's word ('rising'|'stable'|'declining'); without it the word comes from the sign."""
    if thin:
        return pill("low data", "low")
    if change is None:
        return pill("n/a", "flat")
    if trajectory not in _TRAJECTORY_DIR:
        trajectory = {"up": "rising", "down": "declining", "flat": "stable"}[_direction(change)]
    return pill(f"{fmt_signed(change)} {trajectory}", _TRAJECTORY_DIR[trajectory])


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


def holding_row(name: str, ticker: str, change: float | None = None, trajectory: str | None = None, thin: bool = False,
                trend: list[float] | None = None, exposure: float | None = None, sub: str | None = None) -> str:
    """One row of the Holdings / Watchlist list: Name (TICKER) + sub line, sparkline, momentum pill, AI exposure bar.
    `change` = 12-month estimate as a fraction; `thin` greys the row and says 'low data'; `exposure` is 0..1."""
    if thin:
        direction = "low"
    elif trajectory in _TRAJECTORY_DIR:
        direction = _TRAJECTORY_DIR[trajectory]
    else:
        direction = _direction(change)
    sub_html = f'<div class="sf-sub">{esc(sub)}</div>' if sub else ""
    return (f'<div class="sf-row{" sf-row-thin" if thin else ""}" role="listitem" aria-label="{esc(name)} ({esc(ticker)})">'
            f'<div class="sf-c-name"><div class="sf-name">{esc(name)}<span class="sf-tick">({esc(ticker)})</span></div>{sub_html}</div>'
            f'<div class="sf-c-spark">{sparkline(trend, direction if not thin else "flat")}</div>'
            f'<div class="sf-c-pill">{change_pill(change, trajectory, thin)}</div>'
            f'<div class="sf-c-exp">{exposure_bar(exposure)}</div></div>')


def holdings_list(rows: list[str], empty_text: str = "Nothing to show yet.") -> str:
    """Wrap holding_row() strings in the list card with its column header. Empty -> a plain message."""
    if not rows:
        return f'<div class="sf-list"><div class="sf-empty">{esc(empty_text)}</div></div>'
    head = ('<div class="sf-list-head" aria-hidden="true"><div class="sf-c-name">Skill</div><div class="sf-c-spark">Demand</div>'
            '<div class="sf-c-pill">Hiring trend (estimate)</div><div class="sf-c-exp">AI impact</div></div>')
    return f'<div class="sf-list" role="list">{head}{"".join(rows)}</div>'
