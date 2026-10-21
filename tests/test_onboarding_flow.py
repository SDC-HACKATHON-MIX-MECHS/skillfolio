"""AppTest flows for the onboarding wizard on pages/1_Profile.py (paste resume, demo profile, blank path, returning user).

The finished profile must be the exact shape pages 2-6 read, and engine.api.analyse must accept it.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app import onboarding as ob
from engine import api
from engine.data import load_snapshot

APP = Path(__file__).resolve().parents[1] / "app"
RESUME = "Data analyst. Dashboards in Power BI and Excel, SQL queries, Python scripts. Go to our careers page. <script>alert(1)</script>"
PROFILE_KEYS = {"profile_id", "display_name", "synthetic", "headline", "hours_budget", "budget_rm", "risk_tolerance",
                "sdg_interests", "skills"}


def open_profile_page(profile: dict | None = None) -> AppTest:
    at = AppTest.from_file(str(APP / "Home.py"), default_timeout=60)
    if profile is not None:
        at.session_state["profile"] = profile
    at.run()
    at.switch_page("pages/1_Profile.py").run()
    assert not at.exception
    return at


def visible_text(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [e.value for e in at.error] + [w.value for w in at.warning]
    parts += [i.value for i in at.info] + [s.value for s in at.success] + [c.value for c in at.caption] + [h.value for h in at.header]
    return " ".join(parts)


def primary_buttons(at: AppTest) -> list[str]:
    return [b.label for b in at.button if b.proto.type == "primary"]


def all_session_text(at: AppTest) -> str:
    return " ".join(repr(at.session_state[k]) for k in at.session_state.keys())


def assert_valid_profile(at: AppTest) -> dict:
    profile = at.session_state["profile"]
    assert set(profile) == PROFILE_KEYS
    assert profile["skills"] and all(set(s) == {"skill_id", "level"} and s["level"] in (1, 2, 3) for s in profile["skills"])
    result = api.analyse(profile, load_snapshot("latest"), top_n=None)
    assert result["portfolio"]["readiness"] is not None
    return profile


def test_first_visit_shows_welcome_with_one_primary_button_and_step_indicator():
    at = open_profile_page()
    assert primary_buttons(at) == ["Start with my resume"]
    html = visible_text(at)
    assert '<li class="sf-step-current"' not in html     # the welcome comes before "Step 1 of 4", so no step is current yet
    for step in ("Resume", "Skills", "Goals", "Your roles"):
        assert step in html
    assert "SkillFolio shows" not in html          # sanity: copy is the plain-English paragraph, not a leftover


def test_paste_resume_to_finished_profile():
    at = open_profile_page()
    at.button(key="ob_start").click().run()
    assert not at.exception
    assert primary_buttons(at) == ["Find my skills"]
    assert "Please do not use a real resume" in visible_text(at) and "discarded" in visible_text(at)

    at.text_area(key="ob_resume_text").set_value(RESUME)
    at.button(key="ob_find").click().run()
    assert not at.exception
    # Step 3: detected skills, resume text gone from state, Go (language) not counted
    ids = [e[0] for e in at.session_state["ob_skills"]]
    assert {"python", "sql", "excel", "powerbi"} <= set(ids) and "golang" not in ids
    assert "Power BI" in visible_text(at) or any("Power BI" in r.label for r in at.radio)
    assert "careers page" not in all_session_text(at) and "alert(1)" not in all_session_text(at)
    assert primary_buttons(at) == ["Continue"]

    at.radio(key="ob_lvl_python").set_value("strong").run()
    at.button(key="ob_rm_excel").click().run()
    assert "excel" not in [e[0] for e in at.session_state["ob_skills"]]
    at.selectbox(key="ob_add_pick").select("statistics").run()
    assert ["statistics", 1] in at.session_state["ob_skills"]
    at.button(key="ob_to_goals").click().run()

    # Step 4: goals
    assert not at.exception and primary_buttons(at) == ["See my profile"]
    assert at.number_input(key="ob_w_hours").value == 200 and at.number_input(key="ob_w_budget").value == 300
    at.number_input(key="ob_w_hours").set_value(120)
    at.number_input(key="ob_w_budget").set_value(0)
    at.radio(key="ob_w_risk").set_value("high")
    at.multiselect(key="ob_w_sdgs").set_value([4, 8]).run()
    at.button(key="ob_finish").click().run()

    # Step 5: done
    assert not at.exception and primary_buttons(at) == ["Open my portfolio"]
    profile = assert_valid_profile(at)
    levels = {s["skill_id"]: s["level"] for s in profile["skills"]}
    assert levels["python"] == 3 and levels["statistics"] == 1 and "excel" not in levels and "golang" not in levels
    assert (profile["hours_budget"], profile["budget_rm"], profile["risk_tolerance"], profile["sdg_interests"]) == (120, 0, "high", [4, 8])
    assert profile["display_name"] == "You" and profile["synthetic"] is False
    # privacy: no resume text survives anywhere in session state
    assert "careers page" not in all_session_text(at) and "alert(1)" not in all_session_text(at)
    assert "ob_resume_text" not in at.session_state.keys()

    # The saved profile drives the dashboard on Home.
    at.switch_page("Home.py").run()
    assert not at.exception and "How your skills are doing" in " ".join(m.value for m in at.markdown)


def test_resume_with_no_known_skills_is_handled_gracefully():
    at = open_profile_page()
    at.button(key="ob_start").click().run()
    at.text_area(key="ob_resume_text").set_value("Go to our careers page. Lorem ipsum dolor sit amet.")
    at.button(key="ob_find").click().run()
    assert not at.exception
    assert any("did not find any skills" in i.value for i in at.info)
    assert at.button(key="ob_to_goals").disabled
    at.selectbox(key="ob_add_pick").select("python").run()
    assert not at.button(key="ob_to_goals").disabled


def test_empty_resume_shows_a_clear_message_and_stays_on_the_step():
    at = open_profile_page()
    at.button(key="ob_start").click().run()
    at.button(key="ob_find").click().run()
    assert not at.exception
    assert any("Paste some text" in e.value for e in at.error)
    assert at.session_state["ob_step"] == 2


def test_skip_goes_straight_to_manual_skill_picking():
    at = open_profile_page()
    at.button(key="ob_start").click().run()
    at.button(key="ob_skip").click().run()
    assert not at.exception and at.session_state["ob_step"] == 3 and at.session_state["ob_skills"] == []
    assert any("No skills yet" in i.value for i in at.info)


@pytest.mark.parametrize("profile_id", ob.sample_ids())
def test_demo_profile_skips_straight_to_done(profile_id):
    at = open_profile_page()
    at.button(key=f"ob_demo_{profile_id}").click().run()
    assert not at.exception and at.session_state["ob_step"] == 5
    assert primary_buttons(at) == ["Open my portfolio"]
    profile = assert_valid_profile(at)
    assert profile["profile_id"] == profile_id and profile["synthetic"] is True


def test_blank_path_lands_on_skills_then_completes():
    at = open_profile_page()
    at.button(key="ob_demo_blank").click().run()
    assert not at.exception and at.session_state["ob_step"] == 3
    assert at.button(key="ob_to_goals").disabled
    at.selectbox(key="ob_add_pick").select("sql").run()
    at.radio(key="ob_lvl_sql").set_value("working").run()
    at.button(key="ob_to_goals").click().run()
    at.button(key="ob_finish").click().run()
    assert not at.exception and at.session_state["ob_step"] == 5
    profile = assert_valid_profile(at)
    assert profile["skills"] == [{"skill_id": "sql", "level": 2}]
    assert (profile["hours_budget"], profile["budget_rm"], profile["risk_tolerance"]) == (200, 300, "medium")


def test_returning_user_sees_summary_not_the_wizard_and_can_edit_or_start_over():
    from tests.test_app_smoke import sample_profile

    aina = sample_profile("aina")
    at = open_profile_page(aina)
    assert primary_buttons(at) == ["Open my portfolio"]
    assert [b.label for b in at.button] == ["Open my portfolio", "Edit", "Start over"]
    assert "Welcome" not in visible_text(at)

    at.button(key="ob_edit").click().run()
    assert not at.exception and at.session_state["ob_step"] == 3
    assert {e[0] for e in at.session_state["ob_skills"]} == {s["skill_id"] for s in aina["skills"]}
    at.radio(key="ob_lvl_python").set_value("strong").run()
    at.button(key="ob_to_goals").click().run()
    assert at.number_input(key="ob_w_hours").value == aina["hours_budget"]
    at.button(key="ob_finish").click().run()
    profile = assert_valid_profile(at)
    assert {s["skill_id"]: s["level"] for s in profile["skills"]}["python"] == 3
    assert profile["sdg_interests"] == sorted(aina["sdg_interests"])

    at.button(key="ob_reset").click().run()
    assert "profile" in at.session_state                      # asks first
    at.button(key="ob_reset_no").click().run()
    assert "profile" in at.session_state
    at.button(key="ob_reset").click().run()
    at.button(key="ob_reset_yes").click().run()
    assert not at.exception and "profile" not in at.session_state
    assert primary_buttons(at) == ["Start with my resume"]


def test_back_buttons_keep_the_user_entries():
    at = open_profile_page()
    at.button(key="ob_start").click().run()
    at.text_area(key="ob_resume_text").set_value("Python and SQL")
    at.button(key="ob_find").click().run()
    at.radio(key="ob_lvl_sql").set_value("strong").run()
    at.button(key="ob_to_goals").click().run()
    at.number_input(key="ob_w_hours").set_value(500).run()
    at.button(key="ob_back_3").click().run()
    assert at.session_state["ob_step"] == 3
    assert {e[0]: e[1] for e in at.session_state["ob_skills"]}["sql"] == 3
    at.button(key="ob_to_goals").click().run()
    assert at.number_input(key="ob_w_hours").value == 500


def test_page_shows_no_wizard_text_with_scripts_unescaped():
    at = open_profile_page()
    at.button(key="ob_start").click().run()
    at.text_area(key="ob_resume_text").set_value("<script>alert(1)</script> python")
    at.button(key="ob_find").click().run()
    assert "<script>" not in visible_text(at)
