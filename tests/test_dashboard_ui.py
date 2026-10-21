"""Pure-helper tests for the broker-style UI: basket maths (app/dashboard.py) and HTML components (app/ui.py)."""

import tomllib
from pathlib import Path

import pytest

from app import dashboard as d
from app import ui

ROOT = Path(__file__).resolve().parents[1]
HOSTILE = '<script>alert("x")</script> & $x$ "quoted"'


# --- basket maths ------------------------------------------------------------------------------------

def test_basket_is_the_weighted_average_and_starts_at_100():
    series, left_out = d.basket_index({"a": 0.5, "b": 0.5}, {"a": [100, 110, 120], "b": [100, 90, 80]})
    assert series == pytest.approx([100, 100, 100])
    series, _ = d.basket_index({"a": 0.75, "b": 0.25}, {"a": [100, 120], "b": [100, 80]})
    assert series == pytest.approx([100, 0.75 * 120 + 0.25 * 80])
    assert left_out == []


def test_basket_renormalises_when_a_skill_is_skipped_or_unusable():
    idx = {"a": [100, 110, 120], "b": [100, 90, 80], "late": [0, 100, 150], "short": [100]}
    series, left_out = d.basket_index({"a": 0.3, "b": 0.3, "late": 0.2, "short": 0.2}, idx, skip={"b"})
    assert series == pytest.approx([100, 110, 120])            # only "a" is left, weight renormalised to 1
    assert set(left_out) == {"b", "late", "short"}


def test_basket_window_rebases_each_skill_so_late_starters_can_join():
    idx = {"a": [100, 150, 200], "late": [0, 100, 150]}
    # whole history: "late" has no demand in month 1, so it is left out
    assert d.basket_index({"a": 0.5, "late": 0.5}, idx) == (pytest.approx([100, 150, 200]), ["late"])
    # last 1 month (2 points): both start the window above zero and are rebased to 100
    series, left_out = d.basket_index({"a": 0.5, "late": 0.5}, idx, months=1)
    assert left_out == []
    assert series == pytest.approx([100, 0.5 * (200 / 150 * 100) + 0.5 * 150])


def test_basket_is_empty_when_nothing_is_usable():
    assert d.basket_index({"a": 1.0}, {"a": [100, 100]}, skip={"a"}) == ([], ["a"])
    assert d.basket_index({}, {}) == ([], [])
    assert d.basket_index({"a": 1.0}, {}) == ([], ["a"])


def test_slice_rebase_and_change():
    s = [100.0, 110.0, 121.0, 133.1, 146.41]
    assert d.slice_range(s, 2) == [121.0, 133.1, 146.41]
    assert d.slice_range(s, None) == s
    assert d.slice_range(s, 12) == s                            # asking for more than exists returns everything
    r = d.rebase(d.slice_range(s, 2))
    assert r[0] == pytest.approx(100) and r[-1] == pytest.approx(146.41 / 121 * 100)
    assert d.pct_change(r) == pytest.approx(146.41 / 121 - 1)
    assert d.pct_change([100.0]) is None and d.pct_change([0.0, 5.0]) is None
    assert d.rebase([0.0, 5.0]) == [0.0, 5.0]


def test_spark_values_are_capped():
    assert d.spark_values([100, 900, 50]) == [100.0, d.SPARK_CAP, 50.0]
    assert d.spark_values(None) == []


def _forecast(projected, thin=False, trajectory="stable"):
    return {"projected": projected, "thin_data": thin, "exposure": 0.2, "index": [100, 101], "trajectory": trajectory}


def test_watchlist_skips_owned_sorts_by_momentum_and_puts_thin_last():
    f = {"own": _forecast(0.9), "x": _forecast(0.1), "y": _forecast(0.3), "z": _forecast(0.2),
         "thin_hi": _forecast(0.8, thin=True), "thin_lo": _forecast(0.0, thin=True)}
    rows = d.watchlist(f, {"own"}, n=2, thin_n=1)
    assert [r["skill_id"] for r in rows] == ["y", "z", "thin_hi"]
    assert rows[-1]["thin"] is True
    assert "own" not in {r["skill_id"] for r in d.watchlist(f, {"own"})}


def test_holdings_sorted_by_weight_with_forecast_fields():
    result = {
        "skills": [
            {"skill_id": "b", "level": 1, "weight": 0.2, "projected": 0.05, "thin_data": False, "exposure": None},
            {"skill_id": "a", "level": 3, "weight": 0.8, "projected": 0.2, "thin_data": True, "exposure": 0.4},
        ],
        "forecasts": {"a": _forecast(0.2, True, "stable"), "b": _forecast(0.05, False, "rising")},
    }
    rows = d.holdings(result)
    assert [r["skill_id"] for r in rows] == ["a", "b"]
    assert rows[0]["thin"] is True and rows[1]["trajectory"] == "rising" and rows[1]["exposure"] is None


# --- HTML components: escaping ----------------------------------------------------------------------

def _all_components_with(text):
    return [
        ui.esc(text),
        ui.pill(text, "up"),
        ui.hero(text, text, text, "up", caption=text),
        ui.section_header(text, text, "briefcase", right_html=ui.pill(text)),
        ui.stat_row([(text, text, text)]),
        ui.holding_row(text, text, 0.1, "rising", False, [1, 2, 3], 0.5, sub=text),
        ui.holdings_list([], empty_text=text),
    ]


def test_hostile_text_is_escaped_everywhere():
    for out in _all_components_with(HOSTILE):
        assert "<script" not in out
        assert "alert(" not in out or "&lt;script&gt;" in out
        assert "$" not in out                                    # kept out of Streamlit's maths parser


def test_esc_escapes_quotes_and_collapses_whitespace():
    assert ui.esc('a "b" <i>\n\n  c') == "a &quot;b&quot; &lt;i&gt; c"
    assert ui.esc(None) == "None"


def test_components_are_single_line_html():
    sample = ui.holdings_list([ui.holding_row("Python", "PY", 0.1, "rising", False, [1, 2, 3], 0.2)])
    for out in [sample, ui.hero("Readiness score", "7.5", "+9.7%", "up"), ui.section_header("T", "S", "eye"),
                ui.stat_row([("A", "1")]), *_all_components_with("x\n\ny")]:
        assert "\n" not in out and "  " not in out


# --- HTML components: meaning never by colour alone ---------------------------------------------------

def test_change_pill_has_arrow_sign_and_word():
    up = ui.change_pill(0.123, "rising")
    assert "<svg" in up and "+12.3%" in up and "rising" in up and "sf-pill-up" in up
    down = ui.change_pill(-0.04, "declining")
    assert "−4.0%" in down and "declining" in down and "sf-pill-down" in down
    flat = ui.change_pill(0.008, "stable")
    assert "+0.8%" in flat and "stable" in flat and "sf-pill-flat" in flat
    assert "sf-pill-up" in ui.change_pill(0.2) and "rising" in ui.change_pill(0.2)    # word from the sign when no trajectory
    assert "n/a" in ui.change_pill(None)


def test_thin_data_says_low_data_and_greys_the_row():
    row = ui.holding_row("Rust", "RS", 0.9, "stable", True, [1, 2], 0.3)
    assert "low data" in row and "sf-row-thin" in row and "+90.0%" not in row
    assert "Rust" in row and "(RS)" in row                       # Name (TICKER)


def test_exposure_bar_is_amber_never_red_or_green():
    for value in (0.0, 0.5, 1.0):
        out = ui.exposure_bar(value)
        assert ui.UP not in out and ui.DOWN not in out
    assert "—" in ui.exposure_bar(None)
    assert ui._lerp_hex(ui.EXPOSURE_LOW, ui.EXPOSURE_HIGH, 0) == ui.EXPOSURE_LOW
    assert ui._lerp_hex(ui.EXPOSURE_LOW, ui.EXPOSURE_HIGH, 1) == ui.EXPOSURE_HIGH


def test_sparkline_and_icon_edge_cases():
    assert "polyline" in ui.sparkline([1, 3, 2])
    assert "polyline" not in ui.sparkline([1])
    assert ui.sparkline([5, 5, 5]).count("polyline") == 1         # flat series does not divide by zero
    assert ui.icon("nope") == ""
    assert "aria-hidden" in ui.icon("eye")


# --- tokens and CSS -----------------------------------------------------------------------------------

def _luminance(hex_colour: str) -> float:
    rgb = [int(hex_colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("fg", ["TEXT", "MUTED", "UP_TEXT", "DOWN_TEXT", "FLAT"])
@pytest.mark.parametrize("bg", ["BG", "CARD", "RAISED", "SIDEBAR"])
def test_text_tokens_meet_7_to_1_on_surfaces(fg, bg):
    assert contrast(getattr(ui, fg), getattr(ui, bg)) >= 7


def test_primary_button_text_is_white_on_ink():
    assert contrast(ui.ON_INK, ui.TEXT) >= 7        # the primary button is the ink fill; amber is a fill only and never carries text


def test_streamlit_theme_matches_the_tokens():
    theme = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))["theme"]
    assert theme["base"] == "light"
    assert theme["primaryColor"].upper() == ui.TEXT          # ink, so Streamlit's own widgets are dark, never blue
    assert theme["backgroundColor"].upper() == ui.BG
    assert theme["secondaryBackgroundColor"].upper() == ui.RAISED
    assert theme["textColor"].upper() == ui.TEXT


def test_css_has_the_non_negotiables():
    css = ui.css_text()
    for needle in ("Inter", "tabular-nums", "cursor: pointer", ":focus-visible", "prefers-reduced-motion", "max-width: 640px",
                   "min-height: 48px", "200ms"):
        assert needle in css, needle
    assert "system-ui" in css                                      # graceful fallback when Inter does not load
    assert "Instrument" not in css and "JetBrains" not in css and "monospace" not in css     # Inter only: no serif, no mono
