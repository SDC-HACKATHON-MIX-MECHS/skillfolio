import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.dashboard import holdings, spark_values
from app.page_components import PLAIN, sdg_donut_fig, skill_list, skill_row
from app.ui import (
    LEVEL_LABELS, SDG_NAMES, fmt_pct, fmt_score, fmt_signed, page_header, page_setup, require_profile, risk_return_fig, run_engine,
    show, show_fig, show_warnings, skill_name, skill_ticker, source_caption, stat_row,
)

snapshot = page_setup("My Portfolio")
_who = (st.session_state.get("profile") or {}).get("display_name")
page_header("My portfolio",
            f"{_who}: how your skills look to employers today." if _who else "How your skills look to employers today.", narrow=True)
profile = require_profile()

result = run_engine(profile, snapshot)
if result is None:
    st.stop()
m = result["portfolio"]

# --- A strip of three numbers -----------------------------------------------------------------------
show(stat_row([
    ("Outlook score", f"{m['readiness'] * 100:.1f}", PLAIN["outlook"]),
    ("Hiring trend, 12 months", fmt_signed(m["growth"]), PLAIN["trend"]),
    ("AI impact (0 to 100)", fmt_score(m["ai_exposure"]).replace("/100", ""), PLAIN["ai"]),
]))
st.caption("Outlook score: " + PLAIN["outlook"] + " All three are estimates for your skills as a whole, not predictions.")
source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")

# --- The one primary action -------------------------------------------------------------------------
if st.button("See which roles fit me", type="primary", use_container_width=True, icon=":material/arrow_forward:"):
    st.switch_page("pages/4_Matches.py")

# --- Details, tucked away ---------------------------------------------------------------------------
held = holdings(result)
with st.expander(f"Your {len(held)} skills"):
    show(skill_list([
        skill_row(
            skill_name(h["skill_id"]), skill_ticker(h["skill_id"]), h["projected"], h["trajectory"], h["thin"],
            spark_values(h["index"]), h["exposure"],
            sub=f"Level {LEVEL_LABELS[h['level']]} · {h['weight'] * 100:.0f}% of your skills", with_ai=True,
        )
        for h in held
    ], with_ai=True))
    source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
    st.caption("Skill variety: " + fmt_score(m["diversification"]).replace("/100", "") + " out of 100. " + PLAIN["variety"])
    st.caption("How much hiring bounces around: " + fmt_pct(m["volatility"], 1) + " a year. " + PLAIN["bounce"])

with st.expander("Show how you compare with future roles"):
    st.write("Up is more hiring growth; left is less AI impact. Bigger bubbles are roles you already fit more closely.")
    if not result["matches"]:
        show_warnings(result)
    elif m["ai_exposure"] is None:
        st.info("None of your skills has AI-impact data yet, so we can't place you on this chart.")
    else:
        show_fig(risk_return_fig(result["matches"], m))
        source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")

if result["sdg_allocation"]:
    with st.expander("Where your skills point (UN Sustainable Development Goals)"):
        show_fig(sdg_donut_fig({a["sdg"]: a["share"] for a in result["sdg_allocation"]}, SDG_NAMES))
        st.caption("Source: roles.csv SDG links (see Matches for each reason) · every skill supports SDG 4.4")
