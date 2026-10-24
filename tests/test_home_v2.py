"""AppTest for Home v2 (roles first): no profile, a profile with ranked roles, a profile with an empty role list,
a profile whose skills overlap no role, a hostile display name, and the jargon scan for the Home surface.

data/role_skills.csv is empty on some branches, so these tests patch engine.data.load_role_skills with a small fixture
instead of depending on the file."""

import copy
import html as html_lib
import json
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app import home_components as hc
from engine import api, data

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "app" / "Home.py"
TIMEOUT = 60
HOSTILE = '<script>alert("x")</script> & $x$ "quoted"'


def rs(role_id, skill_id, weight=3, level=2):
    return {"role_id": role_id, "skill_id": skill_id, "weight": weight, "required_level": level, "source": "team"}


# Aina holds excel, sql, python, powerbi, statistics, data_analysis.
ROLE_SKILLS = [
    rs("data_scientist", "python"), rs("data_scientist", "sql"), rs("data_scientist", "ml"), rs("data_scientist", "statistics"),
    rs("statistician", "excel"), rs("statistician", "statistics"), rs("statistician", "r_lang"),
    rs("software_developer", "python"), rs("software_developer", "docker"), rs("software_developer", "cicd"),
    rs("web_developer", "javascript"), rs("web_developer", "html_css"), rs("web_developer", "react"),
]
NO_OVERLAP = [rs("web_developer", "javascript"), rs("web_developer", "html_css"), rs("software_developer", "rust")]


def aina() -> dict:
    return json.loads((ROOT / "data" / "profiles" / "aina.json").read_text(encoding="utf-8"))


def run_home(monkeypatch, profile, role_skills):
    monkeypatch.setattr(data, "load_role_skills", lambda: copy.deepcopy(role_skills))
    at = AppTest.from_file(str(HOME), default_timeout=TIMEOUT)
    if profile is not None:
        at.session_state["profile"] = profile
    at.run()
    return at


# --- text helpers -------------------------------------------------------------------------------------

def markdown_html(at) -> str:
    return " ".join(m.value for m in at.markdown)


def plain(text: str) -> str:
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
    text = re.sub(r"</?(?:em|b|i|span)\b[^>]*>", "", text)          # inline tags do not break words
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", text))


def page_text(block, include_expanders: bool) -> str:
    """Visible text of the main area: markdown (tags and <style> removed), captions, buttons, links, notices."""
    out = []
    for child in block.children.values():
        if child.type == "expander":
            if include_expanders:
                out.append(page_text(child, True))
            continue
        for attr in ("value", "label"):
            val = getattr(child, attr, None)
            if isinstance(val, str):
                out.append(plain(val))
        if getattr(child, "children", None):
            out.append(page_text(child, include_expanders))
    return " ".join(out)


ROLE_CARD = re.compile(r'class="sf-role(?: sf-role-lead)?" role="group"')      # the full card (role 1)
ROLE_ROW = re.compile(r'class="sf-rrow" role="group"')                         # a compact row (roles 2 and 3)
BANNED = re.compile(r"\b(momentum|volatility|covariance|spread|readiness|rebalance|holdings?|watchlist|basket|thin data|"
                    r"ai exposure|demand index)\b", re.I)


def primary_buttons(at):
    return [b.label for b in at.button if b.proto.type == "primary"]


# --- no profile ---------------------------------------------------------------------------------------

def test_no_profile_shows_one_sentence_one_primary_button_and_a_demo_link(monkeypatch):
    at = run_home(monkeypatch, None, ROLE_SKILLS)
    assert not at.exception
    assert [b.label for b in at.button] == ["Set up my portfolio", "Try this example"]
    assert primary_buttons(at) == ["Set up my portfolio"]
    assert not at.expander
    text = page_text(at.main, True)
    assert hc.WELCOME_HEADLINE in text and "YOUR SKILLS" not in text
    for step in ("Resume", "Skills", "Goals", "Your roles"):
        assert step in text
    assert "[01]" not in text
    assert not BANNED.search(text)


def test_no_profile_shows_a_live_example_built_from_the_engine_and_labelled_made_up(monkeypatch):
    at = run_home(monkeypatch, None, ROLE_SKILLS)
    assert not at.exception
    snap = json.loads((ROOT / "data" / "snapshots" / "latest.json").read_text(encoding="utf-8"))
    expected = api.analyse(aina(), snap, "moderate", role_skills=copy.deepcopy(ROLE_SKILLS), top_n=None)
    top = hc.top_roles(expected["matches"], 1)[0]
    body = markdown_html(at)
    text = plain(body)
    assert "a made-up graduate" in text
    assert hc.fmt_signed(expected["portfolio"]["growth"]) in text                 # the big number is the engine's growth
    assert html_lib.escape(top["title"]) in body and f'{hc.fit_percent(top)}%' in text
    assert 'class="sf-bars"' in body and "sf-bar-est" in body                   # measured bars plus the hatched estimate bar
    assert "profile" not in at.session_state                                    # the example is not saved as the user's profile
    assert "Hacker News job posts, retrieved" in text


def test_no_profile_without_the_demo_profile_shows_the_hero_alone_and_no_numbers(monkeypatch):
    monkeypatch.setattr(data, "list_profiles", lambda: [])
    at = run_home(monkeypatch, None, ROLE_SKILLS)
    assert not at.exception
    text = page_text(at.main, True)
    assert hc.WELCOME_HEADLINE in text and "made-up" not in text and "%" not in text
    assert 'class="sf-bars"' not in markdown_html(at)


def test_demo_profile_button_loads_the_sample_and_shows_roles(monkeypatch):
    at = run_home(monkeypatch, None, ROLE_SKILLS)
    at.button[1].click().run()
    assert not at.exception
    assert at.session_state["profile"]["display_name"].startswith("Aina")
    assert "these roles fit you best" in plain(markdown_html(at))


# --- profile with ranked roles ------------------------------------------------------------------------

@pytest.fixture
def ranked(monkeypatch):
    return run_home(monkeypatch, aina(), ROLE_SKILLS)


def test_ranked_home_has_greeting_three_role_cards_and_one_primary_button(ranked):
    assert not ranked.exception
    html = markdown_html(ranked)
    assert "Aina, these roles fit you best" in plain(html) and "<em>" not in html and "YOUR SKILLS" not in html
    assert len(ROLE_CARD.findall(html)) == 1 and html.count('class="sf-role sf-role-lead"') == 1      # one dominant card ...
    assert len(ROLE_ROW.findall(html)) == 2                                                          # ... and two quieter rows
    assert primary_buttons(ranked) == ["See my learning plan"]
    assert "Set up my portfolio" not in [b.label for b in ranked.button]


def test_role_cards_show_the_engines_fit_and_titles_without_a_why_sentence(ranked, monkeypatch):
    monkeypatch.setattr(data, "load_role_skills", lambda: copy.deepcopy(ROLE_SKILLS))
    from app.ui import skill_name
    result = api.analyse(aina(), data.load_snapshot("latest"), "moderate", top_n=None)
    html = markdown_html(ranked)
    for i, match in enumerate(hc.top_roles(result["matches"])[:3]):
        assert f'{round(match["match_pct"] * 100)}%' in html
        assert html_lib.escape(match["title"], quote=True) in html
        assert html_lib.escape(hc.why_sentence(match, skill_name), quote=True) not in html     # no explaining sentence under a role
        if i == 0:                                                      # only the lead card carries the hiring chip; rows stay quiet
            assert hc.hiring_text(match["role_growth"]) in plain(html)


def test_each_card_has_a_chip_a_fit_track_and_a_missing_strip_with_one_button(ranked):
    html = markdown_html(ranked)
    assert html.count('class="sf-status sf-status-') == 3
    assert html.count('role="progressbar"') == 4          # the lead role's Fit arc, the two rows' Fit bars, and the good-fit tile's bar
    assert html.count('class="sf-missing"') == 1                         # the lead card has the strip; rows say it in their sentence
    text = plain(html)
    assert text.count("Missing:") + text.count("Level up:") + text.count("Nothing missing") == 1
    assert [b.label for b in ranked.button if b.proto.type != "primary"] == ["See your plan"] * 3
    assert len(ranked.button) == 4                                      # one primary + one "See your plan" per role, nothing else


def _ranked_role_ids(at) -> list[str]:
    from app.home_components import top_roles
    from app.ui import scenario  # noqa: F401  (the page uses the default scenario in a fresh session)
    result = api.analyse(aina(), data.load_snapshot("latest"), "moderate", top_n=None)
    return [m["role_id"] for m in top_roles(result["matches"])]


@pytest.mark.parametrize("key,index", [("sf_cta", 0), ("sf_plan_0", 0), ("sf_plan_1", 1), ("sf_plan_2", 2)])
def test_every_see_your_plan_opens_the_plan_for_its_own_role(ranked, key, index):
    """The plan page preselects the role from session_state['plan_target'] (the Matches page sets it the same way). Home used to
    leave it unset, so 'See your plan' under role 3 opened the plan for role 1."""
    expected = _ranked_role_ids(ranked)[index]
    ranked.button(key=key).click().run()
    assert ranked.session_state["plan_target"] == expected


def test_role_cards_come_in_the_engines_order(ranked):
    fits = [int(m) for m in re.findall(r'class="sf-(?:fit|rrow)-num">(\d+)%', markdown_html(ranked))]
    assert fits == sorted(fits, reverse=True) and len(fits) == 3


def test_skills_section_has_at_most_three_rows_and_one_details_expander(ranked):
    html = markdown_html(ranked)
    assert "How your skills are doing" in html
    assert html.count('role="listitem"') <= 3
    assert [e.label for e in ranked.expander] == ["Show details"]


def test_details_expander_holds_the_numbers_help_and_source(ranked):
    expander = ranked.expander[0]
    text = page_text(expander, True)
    for needle in ("Outlook score", "AI impact (0-100)", "Skill variety (0-100)",
                   "How much of this work AI already does", "Source:", "estimates, not predictions"):
        assert needle in text, needle
    assert not any(el.type == "plotly_chart" for el in expander.children.values())    # the chart is on the surface (right panel)
    outside = page_text(ranked.main, False)
    assert "Outlook score" not in outside and "Skill variety" not in outside          # the score numbers are NOT above the fold
    assert "Source: Hacker News job posts" in outside                                  # but the chart keeps a short source line


def test_dark_card_has_the_bars_and_the_1y_6m_all_tabs(ranked):
    assert len(ranked.get("plotly_chart")) == 0                                         # Home draws its demand chart as thick bars in the charcoal card
    assert markdown_html(ranked).count('class="sf-bars"') == 1
    tabs = [b for b in ranked.get("button_group") if list(b.options) == ["1Y", "6M", "All"]]
    assert len(tabs) == 1 and tabs[0].value == "1Y"                                    # the range tabs, in this order, 1Y first
    assert "in the last 12 months" in plain(markdown_html(ranked))


def test_panel_skill_rows_show_words_not_numbers(ranked):
    html = markdown_html(ranked)
    rows = re.findall(r'<div class="sf-skill".*?</div>', html)
    assert 1 <= len(rows) <= 3 and not any(re.search(r"\d%", plain(r)) for r in rows)


def test_surface_numbers_stay_few(ranked):
    """Above the fold: per role card one Fit and one hiring figure, plus at most 3 skill rows (no grids of metrics)."""
    outside = page_text(ranked.main, False)
    assert len(re.findall(r"\d+(?:\.\d+)?%", outside)) <= 3 * 2 + 3
    assert "/100" not in outside


# --- no ranked roles ----------------------------------------------------------------------------------

def test_profile_with_an_empty_role_list_says_so_honestly_and_fakes_nothing(monkeypatch):
    at = run_home(monkeypatch, aina(), [])
    assert not at.exception
    html = markdown_html(at)
    assert "We can't rank roles yet: the role list is still being finished." in plain(html)
    assert hc.NO_ROLES_MESSAGE in plain(html)
    assert not ROLE_CARD.search(html) and "Fit" not in page_text(at.main, False)
    assert primary_buttons(at) == []
    assert [p.label for p in at.get("page_link")][0] == "How roles are matched"
    assert "How your skills are doing" in html                                   # the rest of the page still works


def test_profile_whose_skills_overlap_no_role_is_told_so_instead_of_seeing_zero_percent_roles(monkeypatch):
    at = run_home(monkeypatch, aina(), NO_OVERLAP)
    assert not at.exception
    html = markdown_html(at)
    assert not ROLE_CARD.search(html)
    assert "None of the roles we track use your skills yet" in plain(html)
    assert primary_buttons(at) == []


# --- escaping and jargon ------------------------------------------------------------------------------

def test_hostile_display_name_is_escaped(monkeypatch):
    profile = aina()
    profile["display_name"] = HOSTILE
    at = run_home(monkeypatch, profile, ROLE_SKILLS)
    assert not at.exception
    body = re.sub(r"<style.*?</style>", "", markdown_html(at), flags=re.S)
    assert "<script>" not in body
    assert "&lt;script&gt;" in body                 # only the first word of the name is used in the greeting


@pytest.mark.parametrize("state", ["no_profile", "ranked", "empty_roles", "no_overlap"])
def test_jargon_scan_home_surface(monkeypatch, state):
    """No banned word on the visible Home surface, and none inside 'Show details' either (plain wording first)."""
    profile, rows = {"no_profile": (None, ROLE_SKILLS), "ranked": (aina(), ROLE_SKILLS),
                     "empty_roles": (aina(), []), "no_overlap": (aina(), NO_OVERLAP)}[state]
    at = run_home(monkeypatch, profile, rows)
    assert not at.exception
    for include_expanders in (False, True):
        text = page_text(at.main, include_expanders)
        assert text.strip()
        assert not BANNED.findall(text), BANNED.findall(text)
    emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
    assert not emoji.search(page_text(at.main, True))


# --- the bento (reference: one charcoal card, a mint arc panel, two tiles) ---------------------------------------------

def test_home_is_a_bento_of_cards_not_a_row_of_numbers(ranked):
    html = markdown_html(ranked)
    assert html.count('class="sf-trend-head"') == 1 and html.count('class="sf-bars"') == 1          # the one charcoal card: big number + bars
    assert html.count('class="sf-arc"') == 1 and html.count('class="sf-fitpanel"') == 1             # the lead role: Fit as an arc on a mint panel
    assert html.count('class="sf-tile sf-tile-mint"') == 1 and html.count('class="sf-tile sf-tile-charcoal"') == 1
    assert 'class="sf-stats"' not in html                                                            # the three-number strip is gone: its numbers moved into the cards


def test_the_estimate_bar_is_hatched_and_the_measured_bars_are_not(ranked):
    html = markdown_html(ranked)
    bars = re.findall(r'<div class="sf-bar sf-bar-(?:m|est)[^"]*"', html)
    assert len(bars) == 7 and sum("sf-hatch" in b for b in bars) == 1 and "sf-bar-est sf-hatch" in bars[-1]      # six measured months + one hatched estimate


def test_home_shows_the_next_two_roles_and_still_three_plan_buttons(ranked):
    assert ranked.markdown and len(re.findall(r'class="sf-rrow"', markdown_html(ranked))) == 2
    assert [b.label for b in ranked.button if b.proto.type != "primary"] == ["See your plan"] * 3
