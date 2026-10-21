import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from app.ui import page_setup, todo
from engine import config

snapshot = page_setup("Methodology")
st.title("Methodology & sources")
st.write("Every number in SkillFolio comes from a public, dated source and a formula you can check. Forecasts are estimates, not predictions — you make the decision.")

st.subheader("Sources")
st.dataframe(
    pd.DataFrame([{
        "Source": s["name"], "Licence": s["licence"], "Retrieved": s["retrieved_at"][:10], "Link": s["url"],
    } for s in snapshot["sources"]]),
    hide_index=True, use_container_width=True,
    column_config={"Link": st.column_config.LinkColumn(display_text="Open")},
)
st.caption(f"Snapshot {snapshot['snapshot_date']} covers {snapshot['months'][0]['month']} to {snapshot['months'][-1]['month']} "
           f"({len(snapshot['months'])} monthly Hacker News hiring threads).")

st.subheader("How the numbers are made")
todo("lanes A + D", ["Formulas in plain English (docs/SPEC.md section 5)"])

st.subheader("Assumptions")
st.write("These are our starting choices, shown openly so you can judge them.")
scenario_rows = [{"Setting": f"{v['label']}: AI penalty λ", "Value": v["lambda"]} for v in config.SCENARIOS.values()]
st.dataframe(pd.DataFrame(scenario_rows + [
    {"Setting": "Months averaged to smooth noise", "Value": config.SMOOTHING_MONTHS},
    {"Setting": "Months used for momentum", "Value": config.MOMENTUM_WINDOW_MONTHS},
    {"Setting": "Months used for demand swing", "Value": config.VOLATILITY_WINDOW_MONTHS},
    {"Setting": "Rising / declining threshold (per year)", "Value": f"±{config.TREND_THRESHOLD:.0%}"},
    {"Setting": "Range shown around momentum", "Value": "80%"},
    {"Setting": "Thin data below (posts a month)", "Value": config.THIN_DATA_MIN_MEAN_COUNT},
    {"Setting": "Risk penalty γ (low / medium / high)", "Value": " / ".join(f"{v:g}" for v in config.RISK_AVERSION.values())},
    {"Setting": "SDG tilt α", "Value": config.SDG_TILT_ALPHA},
]).astype({"Value": str}), hide_index=True, use_container_width=True)

st.subheader("Limits")
st.markdown(
    "- Hacker News hiring posts are global and tech-heavy, so SkillFolio suits graduates moving into tech and data roles.\n"
    "- AI exposure measures how much AI is already used on a job's tasks. It is **not** a forecast of job loss.\n"
    "- Malaysian occupation data is a Phase 2 upgrade; the labour-force card on Home is context only.\n"
    "- We never ask your age, gender or other personal traits, and none are used in scoring."
)

st.subheader("AI disclosure")
st.markdown(
    "- **In the product:** no language model is used. CV text is matched against our own skill list with fixed rules.\n"
    "- **While building:** AI coding assistants (Claude Code, Replit Agent) helped write code. The team reviews all logic."
)
