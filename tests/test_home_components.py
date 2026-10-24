"""Pure-logic tests for Home v2 (app/home_components.py): the one-sentence "why", the top-3 filter, trend words
and HTML escaping. Contrast and stylesheet rules: tests/test_design_audit.py."""

import re

import html as html_lib

import pytest

from app import home_components as hc

HOSTILE = '<script>alert("x")</script> & $x$ "quoted"'
NAMES = {"excel": "Excel", "sql": "SQL", "python": "Python", "erp": "ERP", "ml": "Machine learning", "aws": "AWS"}


def name_of(skill_id):
    return NAMES.get(skill_id, skill_id)


def contribution(skill_id, credit=1.0, weight=3):
    return {"skill_id": skill_id, "weight": weight, "user_level": 2, "required_level": 2, "credit": credit}


def gap(skill_id, user_level=0, required_level=2, weight=3):
    return {"skill_id": skill_id, "weight": weight, "user_level": user_level, "required_level": required_level}


def match(**kw):
    base = {"role_id": "analyst", "title": "Systems Analyst", "match_pct": 0.48, "role_growth": 0.07,
            "contributions": [], "gaps": []}
    base.update(kw)
    return base


# --- why_sentence ------------------------------------------------------------------------------------

def test_why_names_skills_you_have_and_the_biggest_missing_skill():
    m = match(contributions=[contribution("excel"), contribution("sql")], gaps=[gap("erp"), gap("aws")])
    text = hc.why_sentence(m, name_of)
    assert text == "You already use Excel and SQL, which this role needs, but ERP is the biggest skill you are missing."


def test_why_is_one_sentence():
    m = match(contributions=[contribution("excel")], gaps=[gap("erp")])
    assert hc.why_sentence(m, name_of).count(".") == 1


def test_why_caps_the_list_of_skills_you_have():
    m = match(contributions=[contribution(s) for s in ("excel", "sql", "python", "aws")], gaps=[gap("erp")])
    assert "Excel, SQL and 2 others" in hc.why_sentence(m, name_of)


def test_why_uses_a_step_up_when_you_have_every_skill_at_least_partly():
    m = match(contributions=[contribution("excel"), contribution("python", credit=0.5)], gaps=[gap("python", user_level=1)])
    text = hc.why_sentence(m, name_of)
    assert "biggest step up is reaching working level in Python" in text
    assert "missing" not in text


def test_why_prefers_a_skill_you_lack_over_a_step_up():
    m = match(contributions=[contribution("excel")], gaps=[gap("python", user_level=1), gap("erp", user_level=0)])
    assert "ERP is the biggest skill you are missing" in hc.why_sentence(m, name_of)


def test_why_with_no_gaps():
    m = match(contributions=[contribution("excel")], gaps=[])
    assert hc.why_sentence(m, name_of) == "You already cover the skills this role needs, including Excel."


def test_why_with_nothing_in_common():
    m = match(contributions=[], gaps=[gap("erp")])
    text = hc.why_sentence(m, name_of)
    assert "ERP is the biggest one to learn" in text
    assert "already use" not in text


def test_why_ignores_zero_credit_contributions():
    m = match(contributions=[contribution("excel", credit=0)], gaps=[gap("erp")])
    assert "already use" not in hc.why_sentence(m, name_of)


@pytest.mark.parametrize("bad", [None, {}, [], "x", 3, {"contributions": None, "gaps": None},
                                 {"contributions": [None, 5, {}], "gaps": ["a", None, {"skill_id": ""}]}])
def test_why_with_missing_or_malformed_data_is_a_calm_fallback(bad):
    assert hc.why_sentence(bad, name_of) == "We do not have a skill list for this role yet."


def test_why_without_a_name_lookup_uses_the_skill_id():
    assert "erp" in hc.why_sentence(match(gaps=[gap("erp")]))


def test_why_survives_a_failing_name_lookup():
    def boom(_):
        raise KeyError("nope")
    text = hc.why_sentence(match(contributions=[contribution("excel")], gaps=[gap("erp")]), boom)
    assert "excel" in text and "erp" in text


def test_why_with_hostile_and_non_ascii_names_is_text_not_markup_once_rendered():
    names = {"excel": HOSTILE, "erp": "Gestão de Projetos ção 日本語"}
    m = match(contributions=[contribution("excel")], gaps=[gap("erp")])
    text = hc.why_sentence(m, lambda s: names[s])
    assert HOSTILE in text and "日本語" in text           # the logic does not alter the name
    html = hc.role_card({**m, "title": HOSTILE}, lambda s: names[s])
    assert "<script>" not in html and "&lt;script&gt;" in html        # rendering escapes it
    assert "&#36;x&#36;" in html


def test_why_collapses_whitespace_and_newlines_in_names():
    text = hc.why_sentence(match(contributions=[contribution("excel")]), lambda s: "Ex\ncel\t  Pro")
    assert "Ex cel Pro" in text


# --- top_roles / fit ---------------------------------------------------------------------------------

def test_top_roles_takes_three_in_engine_order():
    ms = [match(role_id=f"r{i}", match_pct=0.9 - i * 0.1) for i in range(5)]
    assert [m["role_id"] for m in hc.top_roles(ms)] == ["r0", "r1", "r2"]


def test_top_roles_skips_zero_and_junk_and_handles_none():
    ms = [match(role_id="a", match_pct=0), match(role_id="b", match_pct=None), None, "x", match(role_id="c", match_pct=0.2)]
    assert [m["role_id"] for m in hc.top_roles(ms)] == ["c"]
    assert hc.top_roles(None) == [] and hc.top_roles([]) == []


@pytest.mark.parametrize("value,expected", [(0.4821, 48), (1, 100), (1.4, 100), (0.004, 0), (-1, 0), (None, 0)])
def test_fit_percent(value, expected):
    assert hc.fit_percent({"match_pct": value}) == expected


# --- trend words -------------------------------------------------------------------------------------

@pytest.mark.parametrize("change,trajectory,word", [
    (0.1, "rising", "rising"), (0.0, "stable", "steady"), (-0.1, "declining", "falling"),
    (0.2, None, "rising"), (-0.2, None, "falling"), (0.04, None, "steady"), (None, None, "steady"),
    (0.2, "weird", "rising"), (-0.155, "stable", "unclear"), (0.03, "stable", "steady"), (-0.155, "declining", "falling"),
])
def test_trend_word(change, trajectory, word):
    assert hc.trend_word(change, trajectory) == word


def test_hiring_text_has_word_and_sign():
    assert hc.hiring_text(0.0714) == "Hiring rising +7.1%"
    assert hc.hiring_text(-0.05) == "Hiring falling −5.0%"
    assert hc.hiring_text(None) == "Hiring trend not available"


def test_skill_trend_text_says_not_enough_data_never_thin():
    assert hc.skill_trend_text(0.1, "rising", thin=True) == "Not enough data"
    assert hc.skill_trend_text(0.159, "rising") == "Rising +15.9%"
    assert hc.skill_trend_text(0.03, "stable") == "Steady +3.0%"
    assert hc.skill_trend_text(-0.155, "stable") == "Leaning down · uncertain"  # range spans zero: a direction, no number that overclaims
    assert hc.skill_trend_text(0.107, "stable") == "Leaning up · uncertain"
    assert "thin" not in hc.skill_trend_text(None, thin=True).lower()


def test_pills_use_direction_classes_and_an_arrow():
    up, down, flat = hc.hiring_pill(0.1), hc.hiring_pill(-0.1), hc.hiring_pill(0.0)
    assert "sf-pill-up" in up and "sf-pill-down" in down and "sf-pill-flat" in flat
    assert all("<svg" in p for p in (up, down, flat))                  # arrow icon
    assert "sf-pill-low" in hc.skill_pill(0.1, "rising", thin=True)


def test_an_uncertain_trend_says_which_way_it_leans_in_a_neutral_pill_with_help():
    up, down = hc.skill_pill(0.107, "stable"), hc.skill_pill(-0.151, "stable")
    assert "Leaning up · uncertain" in up and "Leaning down · uncertain" in down
    assert "sf-pill-lean-up" in up and "sf-pill-lean-down" in down               # neutral colour, never green or red
    assert "sf-pill-up" not in up and "sf-pill-down" not in down
    assert all("<svg" in p and f'title="{html_lib.escape(hc.LEAN_HELP)}"' in p for p in (up, down))
    assert hc.skill_word(0.107, "stable") == "Leaning up · uncertain"
    assert hc.hiring_text(0.107, "stable") == "Hiring leaning up · uncertain"
    assert "sf-pill-lean-up" in hc.hiring_pill(0.107, "stable")


def test_a_small_stable_change_is_still_steady_and_certain_trends_are_unchanged():
    assert hc.skill_trend_text(0.03, "stable") == "Steady +3.0%"
    assert hc.skill_trend_text(0.159, "rising") == "Rising +15.9%" and "sf-pill-up" in hc.skill_pill(0.159, "rising")
    assert "title=" not in hc.skill_pill(0.159, "rising")


def test_skill_rows_words_only_use_the_lean_pill():
    held = [{"skill_id": "sql", "projected": 0.107, "trajectory": "stable", "thin": False}]
    html = hc.skill_rows(held, name_of, numbers=False)
    assert "sf-pill-lean-up" in html and "Leaning up · uncertain" in html and "%" not in html


# --- names and greeting ------------------------------------------------------------------------------

@pytest.mark.parametrize("profile,expected", [
    ({"display_name": "Aina (synthetic)"}, "Aina"), ({"display_name": "  Mei  Ling "}, "Mei"),
    ({"display_name": ""}, ""), ({"display_name": None}, ""), ({}, ""), (None, ""), ({"display_name": 7}, ""),
    ({"display_name": "(synthetic)"}, ""), ({"display_name": "Zoë"}, "Zoë"),
    ({"display_name": "You"}, ""), ({"display_name": "you (demo)"}, ""), ({"display_name": "Youssef"}, "Youssef"),   # the default name is not greeted
])
def test_first_name(profile, expected):
    assert hc.first_name(profile) == expected


def test_greeting_with_and_without_a_name():
    assert "Aina, these roles fit you best" in hc.greeting("Aina", "these roles fit you best")
    assert ">These roles fit you best<" in hc.greeting("", "these roles fit you best")


def test_greeting_is_a_title_and_one_line_with_no_eyebrow_or_emphasis_word():
    html = hc.greeting("Aina", "these roles fit you best", lead="Short grey line.")
    assert "<h1" in html and "Aina, these roles fit you best" in html and "Short grey line." in html
    assert "<em>" not in html and "YOUR SKILLS" not in html            # v4: no serif emphasis word, no mono eyebrow
    assert "<em>" not in hc.welcome("Plain headline")


def test_greeting_without_a_name_starts_with_a_capital():
    assert "These roles fit you best" in hc.greeting("", "these roles fit you best")


def test_greeting_escapes_a_hostile_name():
    html = hc.greeting(HOSTILE, "these roles fit you best")
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_how_it_works_strip():
    html = hc.how_it_works()
    for needle in ("Resume", "Skills", "Goals", "Your roles"):
        assert needle in html
    assert "[01]" not in html                                          # v4: plain words, no numbered mono steps


# --- status chip, track, missing strip ---------------------------------------------------------------

@pytest.mark.parametrize("pct,label", [(100, "Strong fit"), (70, "Strong fit"), (69, "Good fit"), (40, "Good fit"), (39, "Stretch"), (0, "Stretch")])
def test_fit_label_uses_words(pct, label):
    assert hc.fit_label(pct) == label and label in hc.fit_chip(pct)


def test_fit_track_is_an_accessible_progress_bar():
    html = hc.fit_track(48)
    assert 'role="progressbar"' in html and 'aria-valuenow="48"' in html and "width:48%" in html


def test_role_card_shows_title_chip_fit_track_why_and_hiring_pill():
    html = hc.role_card(match(contributions=[contribution("excel")], gaps=[gap("erp")], match_pct=0.48, role_growth=0.07), name_of)
    for needle in ("Systems Analyst", "Good fit", "48%", 'role="progressbar"', "Hiring rising +7.0%", "sf-pill-up"):
        assert needle in html, needle
    assert "\n" not in html and "biggest skill you are missing" not in html and "sf-why" not in html     # no explaining sentence


@pytest.mark.parametrize("gaps,expected", [
    ([gap("erp")], ("missing", "erp")),
    ([gap("python", user_level=1), gap("erp")], ("missing", "erp")),
    ([gap("python", user_level=1)], ("level", "python")),
    ([], (None, None)),
])
def test_missing_skill(gaps, expected):
    assert hc.missing_skill(match(gaps=gaps)) == expected


@pytest.mark.parametrize("bad", [None, {}, "x", {"gaps": None}, {"gaps": [None, {}]}])
def test_missing_skill_with_bad_data(bad):
    assert hc.missing_skill(bad) == (None, None)


def test_missing_strip_text():
    strip = hc.missing_strip(match(gaps=[gap("erp")]), name_of)
    assert "Missing:" in strip and "<b>ERP</b>" in strip
    assert "Level up:" in hc.missing_strip(match(gaps=[gap("python", user_level=1)]), name_of)
    assert "Nothing missing" in hc.missing_strip(match(gaps=[]), name_of)


def test_missing_strip_escapes_the_skill_name():
    html = hc.missing_strip(match(gaps=[gap("x")]), lambda _: HOSTILE)
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_every_builder_escapes_hostile_text():
    m = match(title=HOSTILE)
    for html in (hc.role_card(m), hc.welcome(HOSTILE), hc.note(HOSTILE), hc.section_title(HOSTILE, HOSTILE),
                 hc.skill_rows([{"skill_id": "x", "projected": 0.1, "trajectory": "rising", "thin": False}], lambda _: HOSTILE)):
        assert "<script>" not in html and "\n" not in html


def test_skill_rows_cap_and_empty():
    held = [{"skill_id": f"s{i}", "projected": 0.1, "trajectory": "rising", "thin": False} for i in range(6)]
    assert hc.skill_rows(held, name_of).count('role="listitem"') == 3
    assert "No skills" in hc.skill_rows([], name_of)


def test_skill_rows_put_skills_with_enough_data_first():
    held = [{"skill_id": "thin1", "projected": 0.1, "trajectory": "stable", "thin": True},
            {"skill_id": "a", "projected": 0.2, "trajectory": "rising", "thin": False},
            {"skill_id": "b", "projected": 0.2, "trajectory": "rising", "thin": False},
            {"skill_id": "c", "projected": 0.2, "trajectory": "rising", "thin": False}]
    html = hc.skill_rows(held, name_of)
    assert "thin1" not in html and html.index(">a<") < html.index(">b<") < html.index(">c<")
    assert "Not enough data" in hc.skill_rows(held[:2], name_of)


def test_detail_numbers_use_plain_labels_and_survive_missing_values():
    html = hc.detail_numbers({"readiness": 0.0753, "ai_exposure": 0.186, "diversification": 0.819})
    for label in ("Outlook score", "AI impact (0-100)", "Skill variety (0-100)", "7.5", "19/100", "82/100"):
        assert label in html
    assert "—" in hc.detail_numbers({})


def _analyse_result(fits, growth=0.097, rising=1):
    """A minimal analyse() output: matches with the given fit fractions, two skills of which `rising` are rising."""
    skills = [{"skill_id": "a"}, {"skill_id": "b"}]
    return {"portfolio": {"growth": growth}, "matches": [{"match_pct": f} for f in fits], "skills": skills,
            "forecasts": {"a": {"trajectory": "rising" if rising >= 1 else "stable"}, "b": {"trajectory": "rising" if rising >= 2 else "stable"}}}


def test_kpi_items_are_three_real_numbers():
    items = hc.kpi_items(_analyse_result([0.68, 0.40, 0.39, 0.0], rising=1))
    assert [i["label"] for i in items] == ["Hiring trend for your skills", "Roles that are a good fit", "Skills you have"]
    assert items[0]["value"] == "+9.7%" and items[0]["pill"] == ("up", "Rising")
    assert items[1]["value"] == "2" and "of 4 roles" in items[1]["sub"] and items[1]["pill"][0] is None   # 68% and 40% reach "Good fit"
    assert items[2]["value"] == "2" and items[2]["pill"] == ("up", "1 rising")


def test_kpi_items_with_nothing_rising_or_no_data_never_invent_a_number():
    items = hc.kpi_items(_analyse_result([], growth=None, rising=0))
    assert items[0]["value"] == "—" and items[0]["pill"][1] == "Not available"
    assert items[1]["value"] == "0" and items[2]["pill"] == ("flat", "None rising yet")
    assert [i["value"] for i in hc.kpi_items(None)][:2] == ["—", "0"]


def test_kpi_strip_is_one_surface_of_at_most_three_cells_and_escapes_text():
    html = hc.kpi_strip(hc.kpi_items(_analyse_result([0.5])) + [{"label": HOSTILE, "value": "1", "pill": (None, ""), "sub": HOSTILE}])
    assert html.count('class="sf-stat"') == 3 and html.count('class="sf-stats"') == 1 and "<script>" not in html and "\n" not in html


def test_skill_rows_can_show_words_only():
    held = [{"skill_id": "a", "projected": 0.337, "trajectory": "rising", "thin": False},
            {"skill_id": "b", "projected": 0.1, "trajectory": "stable", "thin": False},
            {"skill_id": "c", "projected": None, "trajectory": None, "thin": True}]
    html = hc.skill_rows(held, name_of, numbers=False)
    assert "Rising" in html and "Leaning up · uncertain" in html and "Not enough data" in html and "%" not in html
    assert "+33.7%" in hc.skill_rows(held, name_of)                                   # the default still shows the figure


HELD = [{"skill_id": "excel", "level": 3, "projected": 0.337, "trajectory": "rising", "thin": False, "exposure": 0.0818},
        {"skill_id": "sql", "level": 2, "projected": 0.02, "trajectory": "stable", "thin": False, "exposure": None},
        {"skill_id": "powerbi", "level": 1, "projected": None, "trajectory": None, "thin": True, "exposure": 0.25}]


def test_skills_table_is_a_real_table_with_trend_level_and_ai_impact():
    html = hc.skills_table(HELD, name_of)
    assert html.count("<tr>") == 4 and "<th scope=\"col\">Skill</th>" in html and "\n" not in html      # header row + 3 skills
    assert "Rising +33.7%" in html and "Your level: strong" in html and "AI impact 8/100" in html
    assert "AI impact —" in html and "Not enough data" in html                                          # a missing figure is a dash, never made up


def test_skills_table_filters_by_name_and_says_so_when_nothing_matches():
    only = hc.skills_table(HELD, name_of, "  SQ ")
    assert only.count("<tr>") == 2 and "sql" in only.lower() and "excel" not in only.lower()
    assert "No skill matches that search." in hc.skills_table(HELD, name_of, "zzz")
    assert "No skills to show yet." in hc.skills_table([], name_of)


def test_skills_table_escapes_text():
    html = hc.skills_table(HELD, lambda _: HOSTILE)
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_role_row_is_a_compact_row_not_a_card():
    html = hc.role_row(match(contributions=[contribution("excel")], gaps=[gap("erp")], match_pct=0.62), name_of, rank=2)
    assert 'class="sf-rrow"' in html and "sf-role-lead" not in html and "Role 2:" in html and "62%" in html
    assert "biggest skill you are missing" not in html and "sf-rrow-sub" not in html and "\n" not in html and "<script>" not in hc.role_row(match(title=HOSTILE))


def test_the_lead_role_card_is_marked_and_the_others_are_not():
    lead = hc.role_card(match(), name_of, rank=1, lead=True)
    other = hc.role_card(match(), name_of, rank=2)
    assert "sf-role sf-role-lead" in lead and "Role 1:" in lead
    assert "sf-role-lead" not in other and "Role 2:" in other


# --- the bento pieces (reference: charcoal card with thick bars, arc gauge, mint and charcoal tiles) ------------------------

MONTHS = [f"2026-{m:02d}" for m in range(1, 11)]


def test_trend_bars_show_measured_months_solid_and_the_forecast_hatched():
    html = hc.trend_bars(MONTHS, [100, 104, 99, 108, 112, 109, 115, 118, 121, 119], 0.097, n=6)
    assert html.count('class="sf-bar sf-bar-m') == 6 and html.count("sf-bar-est") == 1       # six measured months + one estimate
    assert html.count("sf-bar-now") == 1 and html.index("sf-bar-now") < html.index("sf-bar-est")  # the latest month is marked; the estimate comes last
    assert "sf-hatch" in html.split("sf-bar-est")[1][:120]                                         # the estimate is hatched, never solid
    assert "Estimate" in html and 'role="img"' in html and "\n" not in html
    assert hc.trend_bars(MONTHS, [], 0.1) == ""


def test_trend_bar_heights_come_from_the_numbers_and_stay_in_range():
    values = [100, 120, 80, 90, 110, 100]
    html = hc.trend_bars(MONTHS[:6], values, -0.2, n=6)
    heights = [int(h) for h in re.findall(r"height:(\d+)%", html)]
    assert len(heights) == 7 and max(heights) == 100 and min(heights) >= 12                   # the tallest fills the plot; none is a sliver
    assert heights.index(100) == 1 and heights[2] < heights[1]                                # 120 is tallest, 80 is shorter
    assert heights[-1] < heights[-2] or heights[-1] == 12                                    # a falling forecast is a shorter bar, not a taller one
    assert hc.trend_bars(MONTHS[:6], values, None).count("sf-bar-est") == 0                   # no forecast, no estimate bar


def test_trend_bars_escape_labels_and_survive_bad_numbers():
    html = hc.trend_bars([HOSTILE, "2026-02"], [100, float("nan")], 0.05, n=2)
    assert "<script>" not in html
    assert hc.trend_bars(["2026-01"], [0], 0.0, n=3) != ""                                    # all-zero data still draws something sensible
    labels = hc.trend_bars(["2026-10", "2026-11"], [100, 110], None, n=2)
    assert ">Oct<" in labels and ">Nov<" in labels and "Oct 26" not in labels                 # month names only: the bars are always the latest months, and long labels collide


def test_fit_arc_marks_the_share_you_cover_and_hatches_the_rest():
    html = hc.fit_arc(68)
    assert 'role="progressbar"' in html and 'aria-valuenow="68"' in html and "Fit" in html
    assert 'stroke-dasharray="68 100"' in html and 'pathLength="100"' in html and "<pattern" in html and "\n" not in html
    assert 'aria-valuenow="100"' in hc.fit_arc(150) and 'aria-valuenow="0"' in hc.fit_arc(-5) and 'aria-valuenow="0"' in hc.fit_arc("x")
    assert "#" not in re.sub(r'url\(#[\w-]+\)|id="#?[\w-]+"', "", html)                      # no hex colours: it reads the theme variables


def test_tile_is_mint_or_charcoal_and_escapes_text():
    mint = hc.tile("Roles that are a good fit", "6", "of 17 roles", tone="mint", fraction=6 / 17)
    dark = hc.tile("Skills you have", "6", "2 rising", tone="charcoal")
    assert "sf-tile-mint" in mint and "sf-tile-charcoal" in dark and 'role="progressbar"' in mint and "progressbar" not in dark
    assert "of 17 roles" in mint and "Roles that are a good fit" in mint
    assert "sf-tile-mint" in hc.tile("a", "b", "c", tone="violet")                              # unknown tone falls back to mint (there is no violet)
    assert "<script>" not in hc.tile(HOSTILE, HOSTILE, HOSTILE) and "\n" not in mint


def test_the_lead_card_shows_the_fit_as_an_arc_and_other_cards_keep_the_bar():
    lead = hc.role_card(match(), name_of, rank=1, lead=True)
    other = hc.role_card(match(), name_of, rank=2)
    assert "sf-arc" in lead and "sf-track" not in lead and lead.count('role="progressbar"') == 1
    assert "sf-arc" not in other and "sf-track" in other and other.count('role="progressbar"') == 1


def test_trend_head_is_a_label_a_big_number_and_a_word():
    item = hc.kpi_items({"portfolio": {"growth": 0.097}, "matches": [], "skills": [], "forecasts": {}})[0]
    html = hc.trend_head(item)
    assert html.count('class="sf-trend-head"') == 1 and "Hiring trend for your skills" in html and "+9.7%" in html
    assert "Rising" in html and "sf-trend-sub" not in html and "\n" not in html
    assert "<script>" not in hc.trend_head({"label": HOSTILE, "value": HOSTILE, "pill": ("up", HOSTILE), "sub": HOSTILE})


def test_kpi_items_carry_the_fraction_for_the_good_fit_tile():
    items = hc.kpi_items({"portfolio": {"growth": 0.1}, "matches": [{"match_pct": 0.7}, {"match_pct": 0.2}, {"match_pct": 0.45}, {"match_pct": 0.1}],
                          "skills": [], "forecasts": {}})
    assert items[1]["fraction"] == pytest.approx(2 / 4)                       # two of four roles reach the "good fit" line
    assert hc.kpi_items({"portfolio": {}, "matches": [], "skills": [], "forecasts": {}})[1]["fraction"] is None
