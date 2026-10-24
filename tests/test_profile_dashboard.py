"""Profile dashboard (app/profile_dashboard.py): study-progress logic and the HTML builders. Styles: tests/test_design_audit.py."""

import re

import pytest

from app import profile_dashboard as pd_

HOSTILE = '<script>alert("x")</script> & $x$ "quoted"'
COURSES = {
    "py1": {"course_id": "py1", "title": "Python Essentials", "provider": "Cisco", "skill_id": "python", "level_out": 2, "hours": 30, "url": "https://x.test/py"},
    "sql1": {"course_id": "sql1", "title": "SQL Basics", "provider": "Kaggle", "skill_id": "sql", "level_out": 1, "hours": 10, "url": "https://x.test/sql"},
}
STEPS = [{"order": 1, "course_id": "py1", "skill_id": "python", "hours": 30, "url": "https://x.test/py"},
         {"order": 2, "course_id": "sql1", "skill_id": "sql", "hours": 10, "url": "https://x.test/sql"}]


def rows(progress=None):
    return pd_.study_rows(STEPS, COURSES, progress or {})


# --- study rows and progress -------------------------------------------------------------------------

def test_rows_follow_plan_order_and_default_to_zero_percent():
    got = rows()
    assert [r["course_id"] for r in got] == ["py1", "sql1"]
    assert [r["pct"] for r in got] == [0, 0]
    assert got[0]["level_word"] == "Intermediate" and got[1]["level_word"] == "Beginner"


def test_rows_use_saved_progress_and_ignore_values_that_are_not_a_step():
    got = rows({"py1": 50, "sql1": 37})
    assert [r["pct"] for r in got] == [50, 0]


def test_hours_left_counts_only_the_part_not_done():
    assert pd_.hours_left(rows({"py1": 50})) == pytest.approx(15 + 10)
    assert pd_.hours_left(rows({"py1": 100, "sql1": 100})) == 0


def test_plan_share_done_is_weighted_by_hours():
    assert pd_.plan_done_pct(rows({"py1": 100})) == 75
    assert pd_.plan_done_pct(rows()) == 0
    assert pd_.plan_done_pct([]) == 0


def test_only_finished_courses_raise_skill_levels():
    profile = {"skills": [{"skill_id": "python", "level": 1}], "hours_budget": 40}
    after = pd_.profile_with_completed(profile, rows({"py1": 100, "sql1": 75}), COURSES)
    levels = {s["skill_id"]: s["level"] for s in after["skills"]}
    assert levels == {"python": 2}                         # sql1 is only 75 percent, so it adds nothing
    assert profile["skills"] == [{"skill_id": "python", "level": 1}]      # the saved profile is not changed


def test_a_finished_course_never_lowers_a_level_and_can_add_a_skill():
    profile = {"skills": [{"skill_id": "python", "level": 3}], "hours_budget": 40}
    after = pd_.profile_with_completed(profile, rows({"py1": 100, "sql1": 100}), COURSES)
    levels = {s["skill_id"]: s["level"] for s in after["skills"]}
    assert levels == {"python": 3, "sql": 1}


# --- builders ----------------------------------------------------------------------------------------

def test_goal_block_shows_fit_and_a_bar_with_a_hatched_part_still_to_gain():
    html = pd_.goal_block(68, 88, 25, "Data Analyst")
    assert "68" in html and "25% of your plan done" in html and "Data Analyst" in html
    assert 'style="width:68%"' in html and "sf-hatch" in html and "88%" in html
    assert "\n" not in html


def test_goal_block_has_no_hatch_when_the_plan_adds_nothing():
    assert "sf-hatch" not in pd_.goal_block(70, 70, 0, "Data Analyst")


def test_stat_columns_one_line_and_escaped():
    html = pd_.stat_columns([("Skills you have", "6", "of 52 we track"), (HOSTILE, "1", HOSTILE)])
    assert "<script" not in html and "&lt;script&gt;" in html and "\n" not in html and html.count("sf-pstat ") + html.count('sf-pstat"') >= 2


def test_petals_show_six_skills_with_percentages_and_the_fit_in_the_middle():
    items = [(f"Skill {i}", i * 15) for i in range(1, 7)]
    html = pd_.petal_chart(items, 68)
    assert html.count("sf-petal ") + html.count('sf-petal"') == 6 and "68%" in html and "Skill 6" in html and "\n" not in html
    assert re.findall(r"\d+%", html).count("90%") == 1


def test_petals_cap_at_six_and_escape():
    html = pd_.petal_chart([(HOSTILE, 50)] * 9, 10)
    assert html.count("sf-petal ") + html.count('sf-petal"') == 6 and "<script" not in html


def test_coverage_is_how_much_of_each_required_level_you_hold():
    match = {"contributions": [{"skill_id": "a", "weight": 3, "user_level": 2, "required_level": 2, "credit": 1.0}],
             "gaps": [{"skill_id": "b", "weight": 5, "user_level": 1, "required_level": 2},
                      {"skill_id": "c", "weight": 1, "user_level": 0, "required_level": 3}]}
    got = pd_.coverage(match, lambda s: s.upper())
    assert got[0] == ("B", 50)                              # heaviest first
    assert dict(got) == {"A": 100, "B": 50, "C": 0}


def test_stat_columns_show_label_and_number_only():
    assert "sf-pstat-sub" not in pd_.stat_columns([("Skills you have", "6", "in your profile")])


def test_skill_names_have_no_ticker_in_brackets():
    from app.ui import skill_label
    assert "(" not in skill_label("python")
