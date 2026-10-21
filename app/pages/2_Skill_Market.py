import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.ui import (
    DOWN, FLAT, HELP, LOW_DATA, TRAJECTORY, UP, call_or_wait, fmt_change, fmt_pct, fmt_score, page_setup, scenario,
    show_fig, skill_label, skill_name, skill_ticker, source_caption, style_fig,
)
from engine import config
from engine.data import list_snapshots
from engine.forecast import forecast_all
from pipeline.build_snapshot import build

snapshot = page_setup("Skill Market")
st.title("2 · Skill Market")
st.write(f"Every skill as a stock: how often job posts ask for it, and where it's heading under **{config.SCENARIOS[scenario()]['label'].lower()}**.")

forecasts = call_or_wait("A", "skill forecasts", forecast_all, snapshot, scenario())
series = snapshot["skills"]
INDEX_CAP = 400  # a skill that appears late can have a huge index; cap it so the sparkline stays readable


def trend(f: dict | None, s: dict) -> list[float]:
    return [min(v, INDEX_CAP) for v in f["index"]] if f else [round(x * 100, 2) for x in s["shares"]]


def momentum_text(f: dict | None) -> str:
    if not f or f.get("history_months", 3) < 3:
        return "—"
    return fmt_change(f["projected"]) + (" (low data)" if f["thin_data"] else "")


# --- Ticker table ---------------------------------------------------------------------------------
rows = []
for sid, s in series.items():
    f = (forecasts or {}).get(sid)
    thin = f["thin_data"] if f else False
    rows.append({
        "_id": sid,
        "_thin": thin,
        "Ticker": skill_ticker(sid),
        "Skill": skill_name(sid),
        "Trend": trend(f, s),
        "Momentum": momentum_text(f),
        "AI exposure": round(s["exposure"] * 100) if s.get("exposure") is not None else None,
        "Trajectory": (LOW_DATA if thin else TRAJECTORY[f["trajectory"]]) if f else "—",
        "_sort": f["projected"] if f else 0,
    })
# Low-data skills go to the bottom, greyed, and are never highlighted.
df = pd.DataFrame(rows).sort_values(["_thin", "_sort"], ascending=[True, False])
grey = df["_thin"].tolist()
table = df.drop(columns=["_id", "_thin", "_sort"]).reset_index(drop=True)

st.dataframe(
    table.style.apply(lambda row: [f"color: {FLAT}" if grey[row.name] else "" for _ in row], axis=1),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Ticker": st.column_config.TextColumn(width="small"),
        "Trend": st.column_config.LineChartColumn(
            "Demand" if forecasts else "% of posts",
            help="Demand index: 100 = the first month." if forecasts else "Share of job posts mentioning the skill, by month.",
        ),
        "Momentum": st.column_config.TextColumn(help=HELP["momentum"]),
        "AI exposure": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d", help=HELP["exposure"]),
        "Trajectory": st.column_config.TextColumn(help="Rising or declining only when the whole 80% range clears ±5% a year. An estimate."),
    },
)
source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
if any(grey):
    st.caption("● low data (grey rows): fewer than 3 posts a month on average, so we don't call a trend.")

# --- Skill detail ---------------------------------------------------------------------------------
st.subheader("Look closer at one skill")
pick = st.selectbox("Skill", options=list(df["_id"]), format_func=skill_label)
f = (forecasts or {}).get(pick)
s = series[pick]
months = [m["month"] for m in snapshot["months"]]
c1, c2, c3 = st.columns(3)
c1.metric("Momentum", momentum_text(f), help=HELP["momentum"])
c2.metric("AI exposure", fmt_score(s.get("exposure")), help=HELP["exposure"] if s.get("exposure") is not None else "No AI-exposure data for this skill yet.")
c3.metric("Demand swing", fmt_pct(f["volatility"]) if f else "—", help=HELP["swing"])
if f and f["thin_data"]:
    st.caption("Low data: fewer than 3 posts a month on average, so this is not a trend call.")
elif f:
    st.caption(f"80% range for momentum: {fmt_change(f['projected_low'])} to {fmt_change(f['projected_high'])} a year · estimate")

colour = {"rising": UP, "declining": DOWN}.get(f["trajectory"], FLAT) if f and not f["thin_data"] else FLAT
y = trend(f, s)
fig = go.Figure(go.Scatter(
    x=months[-len(y):], y=y, mode="lines", line=dict(color=colour, width=2.5),
    hovertemplate="%{x}<br>%{y:.1f}<extra></extra>",
))
fig.update_yaxes(title="Demand index (first month = 100)" if f else "% of job posts")
show_fig(style_fig(fig, height=280))
source_caption(snapshot, "hn_whoishiring")

# --- Refresh + snapshot fallback ------------------------------------------------------------------
st.subheader("Data")
st.caption(f"Snapshot {snapshot['snapshot_date']} · retrieved {snapshot['retrieved_at'][:16].replace('T', ' ')} UTC")
if st.button("Refresh data", type="primary", use_container_width=True):
    with st.spinner("Fetching this month's job posts…"):
        try:
            build(refresh_current_only=True)
        except NotImplementedError:
            st.info("Waiting for lane B: live refresh isn't built yet.")
        except Exception as exc:  # network down, API change… keep the old data on screen
            st.error(f"Couldn't reach Hacker News. Still showing the snapshot from {snapshot['snapshot_date']}.")
            with st.expander("Details"):
                st.write(str(exc))
        else:
            st.session_state["snapshot_date"] = "latest"
            st.rerun()

dates = list_snapshots()
if dates:
    current = st.session_state.get("snapshot_date", "latest")
    options = ["latest"] + dates
    choice = st.selectbox(
        "Or view a saved snapshot", options, index=options.index(current) if current in options else 0,
        format_func=lambda d: "Latest" if d == "latest" else d,
    )
    if choice != current:
        st.session_state["snapshot_date"] = choice
        st.rerun()
