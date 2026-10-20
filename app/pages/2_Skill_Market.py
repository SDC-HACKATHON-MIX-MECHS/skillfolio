import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.ui import page_setup, todo

page_setup("Skill Market")
st.title("2 · Skill Market")

todo("lane C", [
    "Ticker table: ticker, skill, sparkline (demand index + 80% band), momentum, volatility, AI exposure, trajectory",
    "Uses engine.forecast.forecast_all(snapshot, scenario) — recomputes when the sidebar scenario changes",
    "Refresh data button → pipeline.build_snapshot.build(refresh_current_only=True), then reload",
    "Snapshot dropdown (engine.data.list_snapshots) as the demo fallback",
    "Caption: Source: HN Who is hiring via Algolia API · retrieved <date>; 'estimates' label",
])
