"""Design audit for the SkillFolio v4 (light) theme: contrast ratios of the token pairs, a type-size check and an 8px-grid check.

Run:  python tools/design_audit.py        (prints a table, exit code 1 on any failure)
tests/test_design_audit.py runs the same checks, so a token or stylesheet change that breaks them fails the suite.

Rules (docs/DESIGN.md section 8): body text >= 7:1 on the surfaces it sits on; UI and button text >= 4.5:1; nothing below 14px
(0.875rem) in the stylesheet; padding, margin and gap values on a 4px step (8px for everything that is not a hairline gap).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import ui  # noqa: E402  (needs the repo root on sys.path)

THEME_CSS = ROOT / "app" / "theme.css"


def _rgb(hex_colour: str) -> tuple[float, float, float]:
    h = hex_colour.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def luminance(hex_colour: str) -> float:
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (v / 255 for v in _rgb(hex_colour))]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def blend(fg: str, alpha: float, bg: str) -> str:
    """`fg` at `alpha` opacity over opaque `bg`, as a hex colour (how a translucent tint really looks)."""
    f, b = _rgb(fg), _rgb(bg)
    return "#" + "".join(f"{round(x * alpha + y * (1 - alpha)):02X}" for x, y in zip(f, b))


def token_pairs() -> list[tuple[str, str, str, float]]:
    """(label, foreground, background, minimum ratio). Tints are blended over the surface they sit on.
    AMBER is a FILL colour only (it is about 2:1 on white and is never text), so it is not in this list: every amber fill
    (progress track, chart line, selected underline, nav marker) always has its value written out as text next to it."""
    pill_up = blend(ui.UP, 0.12, ui.CARD)
    pill_down = blend(ui.DOWN, 0.10, ui.CARD)
    strong_chip = blend(ui.AMBER, 0.28, ui.CARD)       # 'Strong fit' chip tint
    pairs = []
    for surface_name, surface in (("page", ui.BG), ("card", ui.CARD), ("raised", ui.RAISED), ("sidebar", ui.SIDEBAR)):
        pairs += [
            (f"body text on {surface_name}", ui.TEXT, surface, 7.0),
            (f"secondary text on {surface_name}", ui.MUTED, surface, 7.0),
        ]
    for surface_name, surface in (("page", ui.BG), ("card", ui.CARD)):
        pairs += [
            (f"rising text on {surface_name}", ui.UP_TEXT, surface, 7.0),
            (f"falling text on {surface_name}", ui.DOWN_TEXT, surface, 7.0),
        ]
    pairs += [
        ("primary button label (white on ink)", ui.ON_INK, ui.TEXT, 7.0),
        ("primary button label on hover (white on secondary ink)", ui.ON_INK, ui.MUTED, 4.5),
        ("rising chip text on its tint", ui.UP_TEXT, pill_up, 7.0),
        ("falling chip text on its tint", ui.DOWN_TEXT, pill_down, 7.0),
        ("flat chip text on its fill", ui.TEXT, ui.RAISED, 7.0),
        ("'Strong fit' chip text on its amber tint", ui.TEXT, strong_chip, 7.0),
        ("active nav item text on its fill", ui.TEXT, ui.RAISED, 7.0),
        ("disabled button label on its fill", ui.MUTED, ui.RAISED, 4.5),
        ("rising arrow or chart mark against a card (non-text)", ui.UP, ui.CARD, 3.0),
        ("falling arrow or chart mark against a card (non-text)", ui.DOWN, ui.CARD, 3.0),
    ]
    return pairs


def contrast_report() -> list[tuple[str, float, float, bool]]:
    return [(label, contrast(fg, bg), need, contrast(fg, bg) >= need) for label, fg, bg, need in token_pairs()]


def _font_sizes(css: str) -> list[tuple[str, float]]:
    out = []
    for m in re.finditer(r"font-size:\s*([\d.]+)(rem|px)", css):
        value = float(m.group(1)) * (16 if m.group(2) == "rem" else 1)
        out.append((m.group(0), value))
    return out


def small_text(css: str | None = None, minimum_px: float = 14.0) -> list[str]:
    """font-size declarations below 14px, ignoring the 'font-size: 0' used to swap the Rebalance Plan nav label."""
    css = css if css is not None else THEME_CSS.read_text(encoding="utf-8")
    return [decl for decl, px in _font_sizes(css) if 0 < px < minimum_px]


def off_grid_spacing(css: str | None = None) -> list[str]:
    """padding / margin / gap values in px that are not on a 4px step (and not 0, 1, 2 hairlines)."""
    css = css if css is not None else THEME_CSS.read_text(encoding="utf-8")
    bad = []
    for m in re.finditer(r"(?:padding|margin|gap)(?:-[a-z]+)?:\s*([^;}]+)", css):
        for px in re.findall(r"(-?\d+(?:\.\d+)?)px", m.group(1)):
            value = abs(float(px))
            if value > 2 and value % 4:
                bad.append(m.group(0).strip())
    return bad


def main() -> int:
    failures = 0
    print(f"{'pair':58} {'ratio':>7} {'need':>6}")
    for label, ratio, need, ok in contrast_report():
        failures += not ok
        print(f"{label:58} {ratio:7.2f} {need:6.1f}  {'ok' if ok else 'FAIL'}")
    small = small_text()
    print(f"\nfont sizes below 14px in theme.css: {len(small)}" + ("" if not small else "  " + ", ".join(small)))
    off = off_grid_spacing()
    print(f"padding/margin/gap values off the 4px step: {len(off)}" + ("" if not off else "  " + "; ".join(off)))
    failures += len(small) + len(off)
    print("\nAUDIT " + ("PASSED" if not failures else f"FAILED ({failures})"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
