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


def test_stylesheet_has_no_hex_codes_gradients_glow_serif_or_mono():
    css = audit.THEME_CSS.read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    assert not re.findall(r"#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3}(?![\w-])", code)
    assert "gradient(" not in code and "blur(" not in code and "backdrop" not in code     # flat surfaces: no gradient, glow or blur
    assert "serif" not in code and "mono" not in code.lower() and "Fira" not in code      # Inter only
    assert "3B82F6" not in css.upper()                                                    # no leftover v1 blue


def test_amber_is_never_used_as_a_text_colour():
    code = re.sub(r"/\*.*?\*/", "", audit.THEME_CSS.read_text(encoding="utf-8"), flags=re.S)
    for line in code.splitlines():
        for decl in re.findall(r"(?<![-\w])color:\s*([^;}]+)", line):
            assert "--sf-amber" not in decl, line.strip()


def test_there_is_one_stylesheet_and_no_parallel_ones():
    from app import home_components, page_components

    assert not hasattr(home_components, "inject_home_css") and not hasattr(home_components, "home_css")
    assert not hasattr(page_components, "page_start") and not hasattr(page_components, "_PAGE_CSS")
    for page in (ROOT / "app" / "pages").glob("*.py"):
        assert "<style" not in page.read_text(encoding="utf-8"), page.name
