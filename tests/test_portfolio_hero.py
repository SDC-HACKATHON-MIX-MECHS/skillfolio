"""My Portfolio's hero: the user's skills as one picture (each skill's share of the mix, by level, and its hiring-trend word), in the
charcoal card under the hiring-trend number. Builder: app/page_components.py skill_mix. Every share is engine.portfolio.weights output."""

import json
import re
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from app import page_components as pc

ROOT = Path(__file__).resolve().parents[1]
HOSTILE = '<script>alert("x")</script> & $x$ "quoted"'
NAMES = {"excel": "Excel", "sql": "SQL", "python": "Python", "erp": "SAP / ERP"}


def name_of(skill_id):
    return NAMES.get(skill_id, skill_id)


def row(skill_id, weight, projected=0.1, trajectory="rising", thin=False):
    return {"skill_id": skill_id, "weight": weight, "projected": projected, "trajectory": trajectory, "thin": thin, "level": 2}


HELD = [row("excel", 0.5), row("sql", 0.3, -0.12, "declining"), row("python", 0.2, 0.01, "stable", thin=True)]


def test_skill_mix_draws_one_bar_split_by_share_and_one_row_per_skill():
    html = pc.skill_mix(HELD, name_of)
    assert html.count('class="sf-mix-seg') == 3 and html.count('role="listitem"') == 3
    assert 'style="width:50%"' in html and 'style="width:30%"' in html and 'style="width:20%"' in html
    assert ">50%<" in html and ">30%<" in html and ">20%<" in html
    assert html.index("Excel") < html.index("SQL") < html.index("Python")       # biggest share first
    assert 'role="img"' in html and "Excel 50%" in html                            # the bar has a text alternative
    assert "\n" not in html and "#" not in html                                   # one line, no hex: colours come from theme.css


def test_skill_mix_says_the_trend_in_words_never_jargon():
    html = pc.skill_mix(HELD, name_of)
    assert "Rising" in html and "Falling" in html and "Not enough data" in html
    text = re.sub(r"<[^>]+>", " ", html)
    assert not re.search(r"\b(holdings?|basket|momentum|volatility|spread|thin data|weight)\b", text, re.I)


def test_skill_mix_orders_by_share_and_escapes_names():
    html = pc.skill_mix([row("a", 0.1), row("b", 0.9)], lambda s: HOSTILE if s == "b" else "A")
    assert "<script>" not in html and html.index("&lt;script&gt;") < html.index(">A<")


def test_skill_mix_handles_empty_and_bad_input():
    assert "No skills to show yet" in pc.skill_mix([], name_of)
    html = pc.skill_mix([row("excel", None), row("sql", float("nan")), row("python", 1.0)], name_of)
    assert html.count('class="sf-mix-seg') == 1 and ">100%<" in html


def test_skill_mix_tiny_shares_still_show_a_sliver_but_say_their_real_number():
    html = pc.skill_mix([row("excel", 0.996), row("sql", 0.004)], name_of)
    assert ">0%<" in html or ">0.4%<" in html or "&lt;1%" in html
    assert re.search(r'style="width:(\d+(?:\.\d+)?)%"', html)


def test_skill_mix_rows_put_the_share_last_so_the_numbers_line_up():
    html = pc.skill_mix(HELD, name_of)
    first = html[html.index('role="listitem"'):]
    assert first.index("sf-mix-name") < first.index("sf-mix-word") < first.index("sf-mix-pct")
    six = pc.skill_mix([row(f"s{i}", 0.1 * (7 - i)) for i in range(7)], name_of)
    assert "sf-mix-s5" in six and six.count("sf-mix-s0") == 4                      # six shades, then they repeat (key + segment each)


def test_tiles_sit_side_by_side_or_stacked():
    assert pc.tiles(["<i>a</i>", "<i>b</i>"]) == '<div class="sf-tiles"><i>a</i><i>b</i></div>'
    assert 'class="sf-tiles sf-tiles-stack"' in pc.tiles(["x"], stacked=True)


# --- the page ----------------------------------------------------------------------------------------------------

ROLE_SKILLS = [
    {"role_id": rid, "skill_id": sid, "weight": w, "required_level": lv, "source": "onet_in_demand"}
    for rid, rows in {
        "data_scientist": [("python", 3, 2), ("sql", 3, 2), ("statistics", 3, 2), ("excel", 1, 2)],
        "statistician": [("statistics", 3, 3), ("excel", 2, 2), ("data_analysis", 3, 2), ("python", 2, 2)],
    }.items()
    for sid, w, lv in rows
]


@pytest.fixture(autouse=True)
def role_data(monkeypatch):
    import engine.data
    import app.ui

    monkeypatch.setattr(engine.data, "load_role_skills", lambda: [dict(r) for r in ROLE_SKILLS])
    monkeypatch.setattr(app.ui, "load_role_skills", lambda: [dict(r) for r in ROLE_SKILLS])
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def _portfolio(profile_id="aina") -> AppTest:
    at = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=60)
    at.session_state["profile"] = json.loads((ROOT / "data" / "profiles" / f"{profile_id}.json").read_text(encoding="utf-8"))
    at.run()
    at.switch_page("pages/3_My_Portfolio.py").run()
    return at


@pytest.mark.parametrize("profile_id", ["aina", "priya"])
def test_portfolio_leads_with_the_skill_mix_from_the_engine(profile_id):
    from engine import portfolio

    at = _portfolio(profile_id)
    assert not at.exception, at.exception
    profile = at.session_state["profile"]
    shares = portfolio.weights([{"skill_id": s["skill_id"], "level": s["level"]} for s in profile["skills"]])
    mixes = [m.value for m in at.markdown if 'class="sf-mix"' in m.value]
    assert len(mixes) == 1
    for share in shares.values():
        assert f">{pc.share_text(share)}<" in mixes[0]
    in_expanders = [m.value for e in at.expander for m in e.markdown]
    assert not any('class="sf-mix"' in v for v in in_expanders)                 # on the surface, not tucked away
    heads = [m.value for m in at.markdown if 'class="sf-trend-head"' in m.value]
    assert len(heads) == 1 and "Hiring trend for your skills" in heads[0]


def test_portfolio_keeps_details_behind_expanders():
    at = _portfolio()
    labels = [e.label for e in at.expander]
    assert any("skills" in label for label in labels) and any("compare" in label for label in labels)
