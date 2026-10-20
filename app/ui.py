"""Shared UI helpers for every page (lane C)."""

from __future__ import annotations

import streamlit as st

from engine import config
from engine.data import load_snapshot


def page_setup(title: str) -> dict:
    """Page config + sidebar (scenario toggle, snapshot badge). Returns the loaded snapshot."""
    st.set_page_config(page_title=f"SkillFolio · {title}", page_icon="📈", layout="centered")
    snapshot = load_snapshot("latest")
    with st.sidebar:
        st.radio(
            "AI disruption scenario",
            options=list(config.SCENARIOS),
            format_func=lambda key: config.SCENARIOS[key]["label"],
            key="scenario",
        )
        st.caption(f"Data snapshot: **{snapshot['snapshot_date']}**")
    if snapshot.get("is_example"):
        st.warning("EXAMPLE DATA — no real snapshot yet. Numbers are illustrative only.")
    return snapshot


def todo(owner: str, items: list[str]) -> None:
    """Placeholder listing what this page must show (from docs/SPEC.md section 6)."""
    st.info(f"**To build ({owner}):**\n\n" + "\n".join(f"- {item}" for item in items))
