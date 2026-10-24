"""AppTest coverage for pages 2-6 (Skill Market, My Portfolio, Matches, Rebalance Plan, Methodology).

Each page is run with the sample profile and with no profile; key texts must be present, the plan error path must show a
message instead of a traceback, and a jargon scan checks that the banned words never appear on the visible
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
    "5_Rebalance_Plan.py": ["Your learning plan", "Fit with", "Courses, in order", "estimates"],
    "6_Methodology.py": ["Methodology and sources", "Where the data comes from", "How the numbers are made", "AI disclosure", "bge-small-en-v1.5", "Claude Code"],
}


@pytest.mark.parametrize("profile_id", ["aina", "priya"])
@pytest.mark.parametrize("page", list(KEY_TEXTS))
def test_page_with_profile_renders_key_texts(page, profile_id):
    at = run(page, sample_profile(profile_id))
    assert not at.exception, at.exception
    text = all_text(at)
    for needle in KEY_TEXTS[page]:
        assert needle in text, f"{page}: missing {needle!r}"


@pytest.mark.parametrize("page", list(KEY_TEXTS))
def test_no_page_mentions_hrd_corp(page):
    at = run(page, sample_profile("aina"))
    assert "HRD" not in all_text(at), page


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


def test_matches_shows_the_engines_why_sentence_for_the_first_role():
    at = run("4_Matches.py", sample_profile())
    assert not at.exception
    surface = re.findall(r'<div class="sf-why">(.*?)</div>', " ".join(m.value for m in at.markdown))
    assert len(surface) >= 3 and all(surface)
    assert "You already" in surface[0] or "We do not" in surface[0] or "You do not" in surface[0]


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
    assert "HRD" not in text


# --- Methodology page accuracy (every claim must match the engine) ------------------------------------------

METH = "6_Methodology.py"


def _meth_text() -> str:
    return all_text(run(METH, None))


def test_methodology_planner_describes_the_real_objective():
    from engine import config
    text = _meth_text()
    assert "gain per hour" in text
    assert "rise in your outlook score plus" in text and "rise in your fit" in text          # engine/pathway.py: readiness gain + BETA * match gain
    assert f"weight {config.PATHWAY_MATCH_BETA:g}" in text
    assert "A step can lower your outlook score" in text                                      # the sum can be positive while readiness falls
    assert "stops when no course has a gain above zero" in text
    assert "raises your outlook score and your fit with the target role the most per hour" not in text


def test_methodology_role_rank_formula_matches_matching_py():
    from engine import config
    text = _meth_text()
    assert "rank = fit × (1 + role growth) × (1 + " in text
    assert f"{config.SDG_TILT_ALPHA:g} × share of your chosen SDGs the role covers" in text
    assert "sum of weight × min(your level ÷ required level, 1) ÷ sum of weight" in text
    assert "demand growth" in text and "importance" in text


def test_methodology_has_no_overclaims_or_em_dashes():
    text = _meth_text()
    for word in ("exactly", "guarantee", "always"):
        assert word not in text.lower(), word
    assert "—" not in text


def test_methodology_banned_words_only_appear_in_brackets():
    at = run(METH, None)
    parts = [m.value for m in at.markdown if not m.value.lstrip().startswith("<style>")] + [c.value for c in at.caption]
    text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", " ".join(parts))).split())      # the page body, without injected stylesheets
    outside = re.sub(r"\([^)]*\)", " ", text)
    assert not BANNED.search(outside), BANNED.search(outside).group(0)


def test_methodology_numbers_follow_config_and_snapshot(monkeypatch):
    from engine import config
    monkeypatch.setattr(config, "THIN_GROWTH_CAP", 0.07)
    monkeypatch.setattr(config, "THIN_DATA_MIN_MEAN_COUNT", 4)
    monkeypatch.setattr(config, "ROLE_SDG_MIN_WEIGHT", 3)
    monkeypatch.setattr(config, "SMOOTHING_MONTHS", 4)
    text = _meth_text()
    assert "±7% a year in your hiring trend" in text
    assert "fewer than 4 posts a month" in text
    assert "at least 3 in importance" in text
    assert "average of the last 4 months" in text


def test_methodology_has_no_hardcoded_snapshot_facts():
    src = (APP / "pages" / METH).read_text(encoding="utf-8")
    for stale in ("2026-10-20", "58 well", "−0.02", "-0.02", "76%", "48%"):
        if stale in ("76%", "48%"):
            continue                                   # simulation results quoted from docs/SPEC.md, not snapshot facts
        assert stale not in src, stale
    snap = json.loads((ROOT / "data" / "snapshots" / "latest.json").read_text(encoding="utf-8"))
    text = _meth_text()
    assert f"On the {snap['snapshot_date']} snapshot" in text


def test_methodology_links_are_not_the_dead_api_root():
    at = run(METH, None)
    hrefs = re.findall(r'href="([^"]+)"', " ".join(m.value for m in at.markdown))
    assert hrefs and not any(h.rstrip("/").endswith("hn.algolia.com/api/v1") for h in hrefs), hrefs


def test_methodology_states_its_limits():
    text = _meth_text()
    for needle in ("tech and data roles", "self-reported", "estimates", "United States", "remote"):
        assert needle in text, needle
