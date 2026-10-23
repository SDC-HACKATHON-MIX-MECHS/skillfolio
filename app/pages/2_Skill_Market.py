import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.dashboard import spark_values
from app.page_components import PLAIN, ai_word, card_list, choice_control, skill_card, skill_list, skill_row
from app.home_components import skill_pill
from app.ui import (
    call_or_wait, demand_fig, fmt_pct, fmt_signed, page_header, page_setup, scenario, section_header, show, show_fig, side_panel,
    skill_catalog, skill_label, skill_name, skill_ticker, source_caption, stat_row,
)
from engine import config
from engine.data import list_snapshots
from engine.forecast import forecast_all
from pipeline.build_snapshot import build

snapshot = page_setup("Skill Market")
page_header("Skill Market")

forecasts = call_or_wait("A", "skill forecasts", forecast_all, snapshot, scenario())
series = snapshot["skills"]
catalog = skill_catalog()
SORTS = ["Hiring trend", "AI impact", "A to Z"]


def entry(sid: str) -> dict:
    """Everything one card needs, from the forecast (when it exists) and the snapshot series."""
    f = (forecasts or {}).get(sid)
    s = series[sid]
    return {
        "id": sid, "f": f, "thin": bool(f["thin_data"]) if f else False,
        "trend": spark_values(f["index"]) if f else [round(x * 100, 2) for x in s["shares"]],
        "exposure": s.get("exposure"), "change": f["projected"] if f else None, "trajectory": f["trajectory"] if f else None,
        "name": skill_name(sid), "ticker": skill_ticker(sid), "category": catalog.get(sid, {}).get("category"),
    }


entries = [entry(sid) for sid in series]
solid = sorted((e for e in entries if e["f"] and not e["thin"]), key=lambda e: (-e["change"], e["id"]))
rising = [e for e in solid if e["trajectory"] == "rising"]
falling = [e for e in solid if e["trajectory"] == "declining"]
not_enough = [e for e in entries if e["thin"]]

# --- A strip of three numbers -----------------------------------------------------------------------
if forecasts:
    show(stat_row([
        ("Rising", f"{len(rising)}", "Skills whose whole estimated range is above +5% a year. An estimate."),
        ("Falling", f"{len(falling)}", "Skills whose whole estimated range is below −5% a year. An estimate."),
        ("Not enough data", f"{len(not_enough)}", "Skills mentioned in fewer than 3 posts a month on average. We do not call a trend for them."),
    ]))
    st.caption(f"Out of {len(entries)} skills we track.")

list_col, detail_col = st.columns([11, 9], gap="large")

# --- Left: the list ---------------------------------------------------------------------------------
with list_col:
    if forecasts:
        show(section_header("Rising fastest", icon_name="line-chart", tight=True))
        show(card_list(
            [skill_card(e["name"], e["ticker"], e["category"], e["change"], e["trajectory"], False, e["exposure"], lead=i == 0)
             for i, e in enumerate(solid[:3])],
            empty_text="No skill has enough data to call a trend yet.",
        ))
        source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")

    with st.expander("Show all skills"):
        sort_by = choice_control("Sort by", SORTS, SORTS[0], key="market_sort")
        query = st.text_input("Find a skill", placeholder="Search by name or ticker", key="market_query").strip().lower()

        def sort_key(e: dict):
            if sort_by == "AI impact":
                value = -(e["exposure"] if e["exposure"] is not None else -1)
            elif sort_by == "A to Z":
                value = e["name"].lower()
            else:
                value = -(e["change"] if e["change"] is not None else -9)
            return (e["thin"], value, e["id"])      # skills without enough data always sit at the bottom

        ordered = sorted(entries, key=sort_key)
        matched = [e for e in ordered if not query or query in e["name"].lower() or query in e["ticker"].lower()]
        show(skill_list(
            [skill_row(e["name"], e["ticker"], e["change"], e["trajectory"], e["thin"], e["trend"], e["exposure"],
                       sub=e["category"], with_ai=True) for e in matched],
            with_ai=True, empty_text="No skill matches that search.",
        ))
        source_caption(snapshot, "hn_whoishiring", "aei_job_exposure")
        st.caption("Grey rows: fewer than 3 posts a month on average, so we do not call a trend. AI impact: " + PLAIN["ai"])

# --- Right: the detail panel ------------------------------------------------------------------------
with detail_col:
    show(section_header("One skill, closer", icon_name="eye", tight=True))
    with side_panel():
        by_id = {e["id"]: e for e in entries}
        ordered_ids = [e["id"] for e in sorted(entries, key=lambda e: (e["thin"], -(e["change"] if e["change"] is not None else -9), e["id"]))]
        pick = st.selectbox("Skill", options=ordered_ids, format_func=skill_label, key="market_pick")
        e = by_id[pick]
        f = e["f"]
        show(skill_pill(e["change"], e["trajectory"], e["thin"]))
        ai_text = f"AI impact: {ai_word(e['exposure'])}" + (f" ({round(e['exposure'] * 100)} out of 100)" if e["exposure"] is not None else "")
        st.write(ai_text)
        if f and e["thin"]:
            st.caption("Not enough data: fewer than 3 posts a month on average, so this is not a trend call.")
        elif f:
            st.caption(
                f"Approximate range for the hiring trend: {fmt_signed(f['projected_low'])} to {fmt_signed(f['projected_high'])} a year · estimate. "
                "How reliable the range is: see Methodology."
            )
        months = [m["month"] for m in snapshot["months"]]
        y = e["trend"]
        direction = {"rising": "up", "declining": "down"}.get(e["trajectory"], "flat") if f and not e["thin"] else "flat"
        show_fig(demand_fig(months[-len(y):], y, direction, height=260))
        source_caption(snapshot, "hn_whoishiring")
        st.caption("Job-post demand: 100 is the first month with job posts for this skill. Technical name: demand index." if f
                   else "Share of job posts mentioning the skill, by month (percent).")
        with st.expander("More numbers for this skill"):
            st.write(f"How much hiring bounces around: {fmt_pct(f['volatility']) if f else '—'}. {PLAIN['bounce']}")
            st.write(f"Hiring trend: {PLAIN['trend']}")

# --- Refresh (the one primary action) + snapshot fallback ----------------------------------------------
show(section_header("Fresh data", f"Snapshot {snapshot['snapshot_date']}, retrieved {snapshot['retrieved_at'][:16].replace('T', ' ')} UTC.", icon_name="info"))
if st.button("Refresh data", type="primary", use_container_width=True, icon=":material/refresh:"):
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
    with st.expander("View a saved snapshot"):
        current = st.session_state.get("snapshot_date", "latest")
        options = ["latest"] + dates
        choice = st.selectbox(
            "Snapshot", options, index=options.index(current) if current in options else 0,
            format_func=lambda d: "Latest" if d == "latest" else d,
        )
        if choice != current:
            st.session_state["snapshot_date"] = choice
            st.rerun()
