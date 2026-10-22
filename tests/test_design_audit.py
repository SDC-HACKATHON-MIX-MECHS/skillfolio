"""The v4 (light) design audit as tests: contrast of every token pair, nothing below 14px, spacing on the grid, one token set.

The numbers are printed by `python tools/design_audit.py`; this file makes a regression fail the suite.
"""

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("design_audit", ROOT / "tools" / "design_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

from app import ui  # noqa: E402


@pytest.mark.parametrize("label,ratio,need,ok", audit.contrast_report(), ids=lambda v: v if isinstance(v, str) else None)
def test_contrast_pair(label, ratio, need, ok):
    assert ok, f"{label}: {ratio:.2f}:1, needs {need}:1"


def test_body_and_secondary_text_are_at_least_7_to_1_on_every_surface():
    for surface in (ui.BG, ui.CARD, ui.RAISED, ui.SIDEBAR):
        for fg in (ui.TEXT, ui.MUTED):
            assert audit.contrast(fg, surface) >= 7, (fg, surface)


def test_no_text_below_14px_in_the_stylesheet():
    assert audit.small_text() == []


def test_spacing_is_on_the_4px_step():
    assert audit.off_grid_spacing() == []


def test_stylesheet_has_no_hex_codes_glow_blur_serif_or_mono_and_the_only_gradient_is_the_hatch():
    css = audit.THEME_CSS.read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    assert not re.findall(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b(?![\w-])", code)
    assert "blur(" not in code and "backdrop" not in code and "glow" not in code.lower()
    assert all(g.startswith("repeating-linear-gradient(") for g in re.findall(r"[\w-]*gradient\(", code))   # the hatch that marks an estimate; no other gradient
    assert "serif" not in code and "mono" not in code.lower() and "Fira" not in code      # one family (Inter)
    assert "3B82F6" not in css.upper()                                                    # no leftover v1 blue


def test_mint_is_never_used_as_a_text_colour():
    code = re.sub(r"/\*.*?\*/", "", audit.THEME_CSS.read_text(encoding="utf-8"), flags=re.S)
    for line in code.splitlines():
        for decl in re.findall(r"(?<![-\w])color:\s*([^;}]+)", line):
            assert "--sf-mint" not in decl, line.strip()          # mint on a light surface is about 1.3:1; mint is a fill (or text on charcoal via --sf-on-charcoal)


def test_there_is_one_stylesheet_and_no_parallel_ones():
    from app import home_components, page_components

    assert not hasattr(home_components, "inject_home_css") and not hasattr(home_components, "home_css")
    assert not hasattr(page_components, "page_start") and not hasattr(page_components, "_PAGE_CSS")
    for page in (ROOT / "app" / "pages").glob("*.py"):
        assert "<style" not in page.read_text(encoding="utf-8"), page.name


# --- the black-and-green palette (reference: charcoal feature card, mint fills, sage page) ----------------------------------

def _hsv(hex_colour: str) -> tuple[float, float, float]:
    import colorsys
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, sat, val = colorsys.rgb_to_hsv(r, g, b)
    return h * 360, sat, val


def test_palette_is_charcoal_and_mint_and_has_no_violet_or_amber():
    assert ui.MINT.upper() == "#A8F5A2" and ui.CHARCOAL.upper() in ("#1D1E1D", "#1C1D1C", "#1E1F1E")
    assert not hasattr(ui, "AMBER")                                   # the old accent is gone, not just unused
    for name, value in vars(ui).items():
        if name.isupper() and isinstance(value, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            hue, sat, _ = _hsv(value)
            assert not (sat > 0.10 and 240 <= hue <= 335), f"{name} {value} is violet/lavender"     # the user's decision: no violet
            assert not (sat > 0.45 and 25 <= hue <= 50), f"{name} {value} is amber/orange"


def test_surfaces_are_sage_page_with_off_white_cards():
    assert 80 <= _hsv(ui.BG)[0] <= 160 and _hsv(ui.BG)[1] < 0.15       # a soft green-grey page
    assert audit.contrast(ui.CARD, ui.BG) < 1.3 and ui.CARD != ui.BG   # off-white cards sit gently on it
    assert audit.contrast(ui.TEXT, ui.CHARCOAL) < 3                    # a dark card needs its own light text token ...
    assert audit.contrast(ui.ON_CHARCOAL, ui.CHARCOAL) >= 7 and audit.contrast(ui.ON_CHARCOAL_MUTED, ui.CHARCOAL) >= 7
    assert audit.contrast(ui.TEXT, ui.MINT) >= 7 and audit.contrast(ui.MINT, ui.CHARCOAL) >= 7     # ink on mint, mint on charcoal


def test_text_stays_readable_on_every_new_surface():
    for surface in (ui.BG, ui.CARD, ui.RAISED, ui.SIDEBAR):
        for fg in (ui.TEXT, ui.MUTED):
            assert audit.contrast(fg, surface) >= 7, (fg, surface)
    assert audit.contrast(ui.ON_INK, ui.TEXT) >= 7


def test_radius_scale_is_large_and_emitted_as_css_variables():
    assert ui.RADIUS >= 28 and ui.RADIUS_TILE >= 20 and ui.RADIUS_CONTROL >= 12
    assert ui.RADIUS > ui.RADIUS_TILE > ui.RADIUS_CONTROL              # cards > tiles inside them > controls
    css = ui.css_text()
    for var, value in (("--sf-radius", ui.RADIUS), ("--sf-radius-tile", ui.RADIUS_TILE), ("--sf-radius-control", ui.RADIUS_CONTROL)):
        assert f"{var}:{value}px" in css, var
    assert "--sf-mint:" in css and "--sf-charcoal:" in css and "--sf-on-charcoal:" in css and "--sf-amber" not in css


def test_stylesheet_uses_the_radius_variables_not_old_fixed_corners():
    code = re.sub(r"/\*.*?\*/", "", audit.THEME_CSS.read_text(encoding="utf-8"), flags=re.S)
    small = [m for m in re.findall(r"border-radius:\s*(\d+)px", code) if int(m) < 12]
    assert small == [], small                                          # no 6px/8px/10px corners left from the old look


def test_hatch_pattern_exists_for_estimates():
    css = audit.THEME_CSS.read_text(encoding="utf-8")
    assert ".sf-hatch" in css and "repeating-linear-gradient" in css


# --- defects found by looking at the first screenshots -------------------------------------------------------------

def test_every_track_is_thick_enough_to_show_its_outline_and_fill():
    code = re.sub(r"/\*.*?\*/", "", audit.THEME_CSS.read_text(encoding="utf-8"), flags=re.S)
    for rule in re.findall(r"[^{}]*\.sf-[\w-]*track[\w-]*[^{}]*\{[^{}]*height:\s*(\d+)px", code):
        assert int(rule) >= 10, rule                                   # a 4px track with a 2px outline is just a black line


def test_demand_chart_area_fills_to_the_axis_not_to_zero():
    fig = ui.demand_fig([f"m{i}" for i in range(13)], [100 + i for i in range(13)])
    low, high = fig.layout.yaxis.range
    assert low > 50 and high > 112, (low, high)                        # the line uses the plot; the mint area sits under it
    assert fig.data[0].fill in ("tozeroy", "tonexty") and fig.data[0].line.color == ui.TEXT


def test_every_class_the_bento_builders_emit_has_a_style():
    css = audit.THEME_CSS.read_text(encoding="utf-8")
    for cls in ("sf-trend-head", "sf-trend-label", "sf-trend-num", "sf-trend-sub", "sf-bars", "sf-bar-col", "sf-bar-plot", "sf-bar",
                "sf-bar-m", "sf-bar-now", "sf-bar-est", "sf-bar-label", "sf-arc", "sf-arc-fit", "sf-arc-rest", "sf-arc-line", "sf-arcwrap",
                "sf-arcnum", "sf-fitpanel", "sf-tiles", "sf-tile", "sf-tile-mint", "sf-tile-charcoal", "sf-tile-label", "sf-tile-value",
                "sf-tile-sub", "st-key-sf-dark"):
        assert re.search(rf"[.]{re.escape(cls)}(?![\w-])", css), cls


def test_the_dark_card_restyles_its_own_widgets_and_text():
    css = re.sub(r"/\*.*?\*/", "", audit.THEME_CSS.read_text(encoding="utf-8"), flags=re.S)
    dark = " ".join(rule for rule in re.findall(r"[^{}]*st-key-sf-dark[^{}]*\{[^{}]*\}", css))
    assert "var(--sf-charcoal)" in dark and "var(--sf-on-charcoal)" in dark and "stButtonGroup" in dark and "var(--sf-mint)" in dark


def test_every_class_the_profile_dashboard_emits_has_a_style():
    css = ui.css_text()
    for cls in ("sf-study-meta", "sf-study-main", "sf-goal", "sf-goal-big", "sf-goal-cap", "sf-goal-main", "sf-goal-line", "sf-goal-bar", "sf-goal-fill", "sf-goal-gain", "sf-goal-mark",
                "sf-pstats", "sf-pstat", "sf-pstat-label", "sf-pstat-value", "sf-pstat-sub", "sf-ptitle", "sf-study", "sf-study-title", "sf-study-sub",
                "sf-study-level", "sf-study-left", "sf-study-pct", "sf-ring", "sf-ring-bg", "sf-ring-fg", "sf-petals", "sf-petal", "sf-petal-hi",
                "sf-petal-mid", "sf-petal-lo", "sf-petal-core", "sf-avatar", "sf-whoami", "sf-profilehead"):
        assert f".{cls}" in css, cls
