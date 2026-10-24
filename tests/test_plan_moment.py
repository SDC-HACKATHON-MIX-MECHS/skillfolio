"""The "Apply plan" moment on the Learning plan page: the Fit number counts from before to after, the Fit arc fills to the
new value and your dot on the plan chart slides, once per press, with every number straight from engine.pathway.plan.
Builders: app/page_components.py (plan_fit, plan_motion_script). Chart: app/ui.py risk_return_fig(start=...). Motion: app/theme.css."""

import json
import re
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from app import page_components as pc
from app import ui

ROOT = Path(__file__).resolve().parents[1]
HOSTILE = '<script>alert("x")</script> & $x$ "quoted"'


# --- the Fit card -----------------------------------------------------------------------------------------------

def test_plan_fit_static_shows_the_current_fit_as_an_arc_and_a_number():
    html = pc.plan_fit("Data Analyst", 68, 88, applied=False, caption="Press Apply plan to see the change.")
    assert "Fit with Data Analyst" in html and ">68%<" in html and 'aria-valuenow="68"' in html
    assert 'stroke-dasharray="68 100"' in html                       # the arc is the shared Home fit_arc
    assert "sf-planfit-anim" not in html and "--sf-from" not in html  # no motion unless the page asks for it
    assert "Press Apply plan" in html and "\n" not in html


def test_plan_fit_applied_shows_the_after_value_and_the_change():
    html = pc.plan_fit("Data Analyst", 68, 88, applied=True, delta_text="+20 points with this plan, an estimate", delta_dir="up")
    assert ">88%<" in html and 'aria-valuenow="88"' in html and "+20 points with this plan, an estimate" in html
    assert "sf-planfit-delta" in html and "sf-pill-up" in html


def test_plan_fit_animates_from_before_to_after_on_apply_and_back_on_undo():
    up = pc.plan_fit("Data Analyst", 68, 88, applied=True, animate=True, delta_text="+20 points", delta_dir="up")
    assert 'class="sf-planfit sf-planfit-anim sf-planfit-up"' in up
    assert "--sf-from:68;" in up and "--sf-to:88;" in up and "--sf-fit:88" in up   # the end value also stands without @property
    assert ">88%<" in up and 'aria-valuenow="88"' in up                          # screen readers and no-CSS get the real value
    assert 'class="sf-count"' in up and 'aria-hidden="true"' in up               # the counting copy is decoration only
    down = pc.plan_fit("Data Analyst", 68, 88, applied=False, animate=True)
    assert "--sf-from:88;" in down and "--sf-to:68;" in down and ">68%<" in down
    assert 'class="sf-planfit sf-planfit-anim sf-planfit-down"' in down
    # Apply and Undo always alternate, so the two directions use different animation names: Streamlit updates the
    # same element in place, and a browser only restarts a finished CSS animation when its name changes.


def test_count_up_and_count_down_are_separate_animations_so_every_press_replays():
    css = (Path(__file__).resolve().parents[1] / "app" / "theme.css").read_text(encoding="utf-8")
    assert "@keyframes sf-fit-count-down" in css and ".sf-planfit-down" in css
    assert re.search(r"\.sf-planfit-down\s*\{[^}]*animation-name:\s*sf-fit-count-down", css)
    assert re.search(r"\.sf-planfit-down \.sf-planfit-delta\s*\{[^}]*animation-name:\s*sf-rise-down", css)


def test_plan_fit_clamps_and_escapes():
    html = pc.plan_fit(HOSTILE, -5, 140, applied=True, animate=True, delta_text=HOSTILE, caption=HOSTILE)
    assert "<script>" not in html and "--sf-from:0;" in html and "--sf-to:100;" in html
    assert "--sf-to:0;" in pc.plan_fit("x", "bad", None, applied=True, animate=True)


def test_plan_fit_accepts_engine_fractions_via_fit_percent():
    assert pc.fit_pct(0.6849) == 68 and pc.fit_pct(0.885) == 88 and pc.fit_pct(None) == 0 and pc.fit_pct(1.7) == 100


# --- the dot: the chart opens on "Before" for the moment, then a tiny script presses "Both" --------------------------------

def _matches(n=5):
    return [{"title": f"Role {i}", "role_id": f"r{i}", "match_pct": 0.7 - 0.08 * i,
             "ai_exposure": 0.1 + 0.12 * i, "role_growth": 0.04 + 0.01 * i} for i in range(n)]


def test_risk_chart_can_open_on_before_so_the_dot_can_slide_to_now():
    before, after = {"ai_exposure": 0.3, "growth": 0.12}, {"ai_exposure": 0.2, "growth": 0.085}
    fig = ui.risk_return_fig(_matches(), after, before=before, start="Before")
    assert fig.layout.updatemenus[0].active == 0
    assert fig.data[-1].x[0] == 30 and fig.data[-1].y[0] == 12            # your dot starts where you were
    assert fig.data[1].text == ("",)                                       # no "Before" ring yet: it arrives with "Both"
    assert fig.layout.annotations[0].text == "<b>Growth 12.0%/yr</b>"
    assert [f.name for f in fig.frames] == ["Before", "Now", "Both"]
    usual = ui.risk_return_fig(_matches(), after, before=before)
    assert usual.layout.updatemenus[0].active == 2 and usual.data[-1].x[0] == 20      # the default is unchanged
    assert usual.layout.xaxis.range == fig.layout.xaxis.range                         # same axes: only the dot moves


def test_motion_script_presses_both_once_and_respects_reduced_motion():
    js = pc.plan_motion_script("abc123")
    assert js.startswith("<script>") and js.endswith("</script>") and "\n" not in js
    assert "prefers-reduced-motion" in js and "st-key-sf-plan-chart" in js and "updatemenu-button" in js
    assert '"abc123"' in js and "sfPlayed" in js and "IntersectionObserver" in js
    assert "duration" in js                                                 # reduced motion: the slide is set to 0 ms
    body = js[len("<script>"):-len("</script>")]
    assert "<" not in body       # st.html sanitises with DOMPurify, which drops a whole script whose text has a "<" in it
    assert "abc" in pc.plan_motion_script('abc"</script><script>x')[:400] and "</script><script>x" not in pc.plan_motion_script('abc"</script><script>x')


# --- the stylesheet -----------------------------------------------------------------------------------------------

def test_css_counts_with_a_registered_property_and_keeps_motion_inside_reduced_motion():
    css = ui.css_text()
    assert "@property --sf-fit" in css and 'syntax: "<integer>"' in css
    assert "@keyframes sf-fit-count" in css and "counter(sf-fit)" in css
    anim = re.search(r"\.sf-planfit-anim\s*\{[^}]*animation:[^;]*?(\d+)ms", css)
    assert anim and 400 <= int(anim.group(1)) <= 900
    reduce = css[css.index("@media (prefers-reduced-motion: reduce)"):]
    assert "animation-delay: 0ms !important" in reduce                    # the moment never waits or plays under reduced motion
    rise = re.search(r"@keyframes sf-rise\s*\{(.*?)\}\s*\}", css, re.S)
    assert rise and "transform" in rise.group(1) and "opacity" in rise.group(1) and "height" not in rise.group(1)


# --- the page ----------------------------------------------------------------------------------------------------

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


@pytest.fixture(autouse=True)
def role_data(monkeypatch):
    import engine.data

    monkeypatch.setattr(engine.data, "load_role_skills", lambda: [dict(r) for r in ROLE_SKILLS])
    monkeypatch.setattr(ui, "load_role_skills", lambda: [dict(r) for r in ROLE_SKILLS])
    st.cache_data.clear()
    yield
    st.cache_data.clear()


def _plan_page() -> AppTest:
    at = AppTest.from_file(str(ROOT / "app" / "Home.py"), default_timeout=60)
    at.session_state["profile"] = json.loads((ROOT / "data" / "profiles" / "aina.json").read_text(encoding="utf-8"))
    at.run()
    at.switch_page("pages/5_Rebalance_Plan.py").run()
    return at


def _fit_html(at: AppTest) -> str:
    cards = [m.value for m in at.markdown if 'class="sf-planfit' in m.value]
    assert len(cards) == 1
    return cards[0]


def _scripts(at: AppTest) -> list[str]:
    return [h.proto.body for h in at.get("html") if "sfPlayed" in h.proto.body]


def test_apply_counts_up_once_with_the_engines_numbers_and_undo_counts_back():
    at = _plan_page()
    assert not at.exception, at.exception
    first = _fit_html(at)
    assert "sf-planfit-anim" not in first and not _scripts(at)
    before = int(re.search(r">(\d+)%<", first).group(1))

    at.button[0].click().run()                                           # Apply
    assert not at.exception, at.exception
    applied = _fit_html(at)
    after = int(re.search(r">(\d+)%<", applied).group(1))
    assert "sf-planfit-anim" in applied and f"--sf-from:{before};" in applied and f"--sf-to:{after};" in applied
    assert after > before and len(_scripts(at)) == 1                     # the dot slides on this run only

    at.run()                                                             # any later rerun: no replay
    assert "sf-planfit-anim" not in _fit_html(at) and not _scripts(at) and f">{after}%<" in _fit_html(at)

    at.button[0].click().run()                                           # Undo: counts back down, the dot has nowhere to slide
    undone = _fit_html(at)
    assert f"--sf-from:{after};" in undone and f"--sf-to:{before};" in undone and f">{before}%<" in undone
    assert not _scripts(at) and [b.label for b in at.button] == ["Apply plan"]


def test_plan_page_numbers_match_the_engine(monkeypatch):
    import engine.pathway

    seen = {}
    real = engine.pathway.plan

    def spy(*args, **kwargs):
        out = real(*args, **kwargs)
        seen.update(before=out["before"]["match_pct"], after=out["after"]["match_pct"])
        return out

    monkeypatch.setattr(engine.pathway, "plan", spy)
    at = _plan_page()
    at.button[0].click().run()
    html = _fit_html(at)
    assert f"--sf-from:{pc.fit_pct(seen['before'])};" in html and f"--sf-to:{pc.fit_pct(seen['after'])};" in html
