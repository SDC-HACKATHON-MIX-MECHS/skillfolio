import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.dashboard import holdings, spark_values
from app.home_components import kpi_items, section_title, tile, trend_head
from app.page_components import PLAIN, sdg_bars, skill_list, skill_mix, skill_row, tiles
from app.ui import (
    SDG_NAMES, card_container, dark_container, fmt_pct, fmt_score, page_header, page_setup, require_profile, risk_return_fig,
    run_engine, show, show_fig, show_warnings, skill_name, skill_ticker, source_caption, source_note,
)

snapshot = page_setup("My Portfolio")
_who = (st.session_state.get("profile") or {}).get("display_name")
page_header("My portfolio")
profile = require_profile()

result = run_engine(profile, snapshot)
if result is None:
    st.stop()
m = result["portfolio"]

held = holdings(result)
items = kpi_items(result)

# --- The portfolio picture: your hiring-trend number, then your skills as one mix (share by level + each one's trend word) ----
mix_col, side_col = st.columns([7, 5], gap="large")
with mix_col:
    with dark_container():
        show(trend_head(items[0]))
        show(section_title("Your skill mix", "Each skill's share of your skills, by your level, and where its hiring is heading.",
                           tight=True))
        show(skill_mix(held, skill_name))
        source_caption(snapshot, "hn_whoishiring")

with side_col:
    with card_container():
        show(tiles([
            tile("Outlook score", f"{m['readiness'] * 100:.1f}", "An estimate. Higher is better.", "mint"),
            tile("AI impact (0 to 100)", fmt_score(m["ai_exposure"]).replace("/100", ""), "How much AI already does this work.",
                 "charcoal"),
        ], stacked=True))
        source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
    # --- The one primary action -------------------------------------------------------------------------
    if st.button("See which roles fit me", type="primary", use_container_width=True, icon=":material/arrow_forward:"):
        st.switch_page("pages/4_Matches.py")

# --- Details, tucked away ---------------------------------------------------------------------------
with st.expander(f"Your {len(held)} skills"):
    show(skill_list([
        skill_row(
            skill_name(h["skill_id"]), skill_ticker(h["skill_id"]), h["projected"], h["trajectory"], h["thin"],
            spark_values(h["index"]), h["exposure"], with_ai=True,
        )
        for h in held
    ], with_ai=True))
    source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
    st.caption("Skill variety: " + fmt_score(m["diversification"]).replace("/100", "") + " out of 100. " + PLAIN["variety"])
    st.caption("How much hiring bounces around: " + fmt_pct(m["volatility"], 1) + " a year. " + PLAIN["bounce"])

with st.expander("Show how you compare with future roles"):
    st.write("Up is more hiring growth, left is less AI impact. Each grey dot is a role; bigger means you already fit it more closely. The orange dot is you.")
    if not result["matches"]:
        show_warnings(result)
    elif m["ai_exposure"] is None:
        st.info("None of your skills has AI-impact data yet, so we can't place you on this chart.")
    else:
        show_fig(risk_return_fig(result["matches"], m))
        source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")

if result["sdg_allocation"]:
    with st.expander("Where your skills point (UN Sustainable Development Goals)"):
        show(sdg_bars({a["sdg"]: a["share"] for a in result["sdg_allocation"]}, SDG_NAMES))
        source_note("our role-to-goal links, with the reason for each on the Matches page", "every skill supports SDG 4.4")
