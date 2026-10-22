"""AppTest coverage for pages 2-6 (Skill Market, My Portfolio, Matches, Rebalance Plan, Methodology).

Each page is run with the sample profile and with no profile; key texts must be present, the plan error path must show a
message instead of a traceback, and a jargon scan checks that the banned words (brief v2 rule 3) never appear on the visible
surface (outside expanders; the Methodology page is exempt, it explains the technical names).

role_skills.csv is empty on some branches, so these tests patch in a small role list instead of depending on the data file.
"""

import html
import json
import re
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
TIMEOUT = 60

ROLE_SKILLS = [
    {"role_id": rid, "skill_id": sid, "weight": w, "required_level": lv, "source": "onet_in_demand"}
    for rid, rows in {
        "data_scientist": [("python", 3, 2), ("sql", 3, 2), ("statistics", 3, 2), ("excel", 1, 2)],
        "statistician": [("statistics", 3, 3), ("excel", 2, 2), ("data_analysis", 3, 2), ("python", 2, 2)],
        "software_developer": [("python", 3, 3), ("javascript", 3, 2), ("sql", 2, 2)],
        "web_developer": [("javascript", 3, 3), ("html_css", 3, 2), ("sql", 1, 2)],
    }.items()
    for sid, w, lv in rows
]

BANNED = re.compile(r"\b(momentum|volatility|covariance|spread|readiness|rebalance|holdings?|watchlist|basket|thin[- ]data)\b", re.I)


def sample_profile(profile_id: str = "aina") -> dict:
    return json.loads((ROOT / "data" / "profiles" / f"{profile_id}.json").read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def role_data(monkeypatch):
    """A fixed role list (so the tests do not depend on data/role_skills.csv) and fresh caches."""
    import engine.data
    import app.ui

    monkeypatch.setattr(engine.data, "load_role_skills", lambda: [dict(r) for r in ROLE_SKILLS])
    monkeypatch.setattr(app.ui, "load_role_skills", lambda: [dict(r) for r in ROLE_SKILLS])
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def run(page: str, profile: dict | None) -> AppTest:
    at = AppTest.from_file(str(APP / "Home.py"), default_timeout=TIMEOUT)
    if profile is not None:
        at.session_state["profile"] = profile
    at.run()
    at.switch_page(f"pages/{page}").run()
    return at


def all_text(at: AppTest) -> str:
    """Every markdown, caption, info and title on the page, expanders included."""
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption] + [i.value for i in at.info] + [t.value for t in at.title]
    text = re.sub(r"</?(?:em|b|i|span)[^>]*>", "", " ".join(parts))       # inline tags do not break words
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text)).split())


def visible_text(at: AppTest) -> str:
    """Text outside expanders (the page surface), without the injected stylesheets."""
    out: list[str] = []

    def walk(block) -> None:
        for child in block.children.values():
            if getattr(child, "type", None) == "expander":
                continue
            if hasattr(child, "children"):
                walk(child)
                continue
            for attr in ("value", "label", "body"):
                val = getattr(child, attr, None)
                if isinstance(val, str) and not val.lstrip().startswith("<style>"):
                    out.append(val)

    walk(at.main)
    text = re.sub(r"</?(?:em|b|i|span)[^>]*>", "", " ".join(out))       # inline tags do not break words ("Source: <span>Hacker News")
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text)).split())


# page file -> texts that must be on it with a profile
KEY_TEXTS = {
    "2_Skill_Market.py": ["Skill Market", "Rising fastest", "Not enough data", "Source: Hacker News"],
    "3_My_Portfolio.py": ["My portfolio", "Outlook score", "Hiring trend", "AI impact", "Skill variety", "Source: Hacker News"],
    "4_Matches.py": ["Which roles fit me?", "fit", "Source: Hacker News"],
    "5_Rebalance_Plan.py": ["Your learning plan", "Fit with", "Courses, in order", "HRD Corp", "unknown", "estimates"],
    "6_Methodology.py": ["Methodology and sources", "Where the data comes from", "How the numbers are made", "AI disclosure", "no language model"],
}


@pytest.mark.parametrize("profile_id", ["aina", "priya"])
@pytest.mark.parametrize("page", list(KEY_TEXTS))
def test_page_with_profile_renders_key_texts(page, profile_id):
    at = run(page, sample_profile(profile_id))
    assert not at.exception, at.exception
    text = all_text(at)
    if page == "5_Rebalance_Plan.py" and "Waiting for lane A" in text:
        pytest.skip("this branch still has the stub planner")
    for needle in KEY_TEXTS[page]:
        assert needle in text, f"{page}: missing {needle!r}"


@pytest.mark.parametrize("page", list(KEY_TEXTS))
def test_page_without_profile_does_not_crash(page):
    at = run(page, None)
    assert not at.exception, at.exception
    if page in ("3_My_Portfolio.py", "4_Matches.py", "5_Rebalance_Plan.py"):
        assert any("Set up your profile first" in i.value for i in at.info)
    else:
        assert "Methodology" in all_text(at) or "Skill Market" in all_text(at)


@pytest.mark.parametrize("page", ["2_Skill_Market.py", "3_My_Portfolio.py", "4_Matches.py", "5_Rebalance_Plan.py"])
@pytest.mark.parametrize("profile_id", ["aina", "priya"])
def test_no_jargon_on_the_surface(page, profile_id):
    at = run(page, sample_profile(profile_id))
    assert not at.exception, at.exception
    hits = sorted({m.group(0).lower() for m in BANNED.finditer(visible_text(at))})
    assert not hits, f"{page}: banned words on the visible surface: {hits}"


def test_each_page_has_one_primary_button_at_most():
    for page in ("2_Skill_Market.py", "3_My_Portfolio.py", "4_Matches.py", "5_Rebalance_Plan.py"):
        at = run(page, sample_profile())
        primary = [b.label for b in at.button if b.proto.type == "primary"]
        assert len(primary) <= 1, (page, primary)


def test_plan_error_shows_a_message_not_a_traceback(monkeypatch):
    import engine.pathway

    def boom(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(engine.pathway, "plan", boom)
    at = run("5_Rebalance_Plan.py", sample_profile())
    assert not at.exception, at.exception
    assert any("We couldn't build a plan: boom" in e.value for e in at.error)


def test_apply_plan_changes_the_hero_and_can_be_undone():
    at = run("5_Rebalance_Plan.py", sample_profile())
    if any("Waiting for lane A" in i.value for i in at.info):
        pytest.skip("this branch still has the stub planner")
    assert [b.label for b in at.button] == ["Apply plan"]
    before = visible_text(at)
    at.button[0].click().run()
    assert not at.exception
    assert [b.label for b in at.button] == ["Undo plan"]
    assert "with this plan" in visible_text(at) and "with this plan" not in before
    at.button[0].click().run()
    assert [b.label for b in at.button] == ["Apply plan"]


def test_matches_shows_three_roles_and_the_learning_plan_button():
    at = run("4_Matches.py", sample_profile())
    text = all_text(at)
    assert text.count("sf-role-title") == 4 or text.count("sf-role-title") >= 3  # 3 on the surface (+ extras in the expander)
    assert "Why this score" in [e.label for e in at.expander]
    assert [b.label for b in at.button].count("See your plan") >= 3
    text = visible_text(at)
    assert "Strong fit" in text or "Good fit" in text or "Stretch" in text
    assert "Missing:" in text or "Level up:" in text


def test_skill_market_sort_and_search_keep_working():
    at = run("2_Skill_Market.py", sample_profile())
    assert not at.exception
    at.text_input(key="market_query").set_value("python").run()
    assert not at.exception
    assert "Python" in all_text(at)
    at.text_input(key="market_query").set_value("zzzz-no-such-skill").run()
    assert "No skill matches that search." in all_text(at)


def test_see_your_plan_opens_the_plan_for_that_role():
    at = run("4_Matches.py", sample_profile())
    first = at.button[0]
    role_id = first.key.split("_")[1:-1]
    first.click().run()
    assert not at.exception, at.exception
    assert at.session_state["plan_target"] == "_".join(role_id)


def test_methodology_states_the_band_coverage_honestly():
    text = all_text(run("6_Methodology.py", None))
    assert "about 76%" in text and "1.9" in text
    assert "95%" not in text
    assert "'unknown' until a source is found" in text
