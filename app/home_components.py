"""Home (roles first): the pieces of the Home screen. Visual rules: docs/DESIGN.md. The stylesheet is the shared app/theme.css (nothing page-specific lives here).

Two halves:
  * PURE LOGIC (no Streamlit calls, unit-tested in tests/test_home_components.py): the one-sentence "why" for a role,
    the top-3 filter, trend words, the profile's first name.
  * HTML BUILDERS + one stylesheet. Every builder returns ONE LINE of HTML and escapes all data text with `esc()`
    (skill names, role titles and profile names are user or file input). Render with `app.ui.show(...)`.

Everything shown comes from the engine's `analyse` output. Nothing here invents a number, a role or a skill.
Plain labels only (no "momentum", "readiness", "spread", ...): the precise terms live on the Methodology page.
"""

from __future__ import annotations

import re
from typing import Callable

from engine import config
from app.ui import TEXT, MUTED, esc, fmt_signed, note, page_head, pill, section_header, status_chip, steps_html

STEPS = ("Resume", "Skills", "Goals", "Your roles")
STRONG_FIT, GOOD_FIT = 70, 40      # display cut-offs (percent) for the "Strong fit" / "Good fit" / "Stretch" chip

TOP_N = 3                # role cards on the first screen
SKILL_ROWS = 3           # rows in "How your skills are doing"
LEVEL_WORDS = {1: "basic", 2: "working", 3: "strong"}

NO_ROLES_MESSAGE = "We can't rank roles yet: the role list is still being finished."
NO_FIT_MESSAGE = "None of the roles we track use your skills yet. Update your skills to see roles that fit."


# =============================== Pure logic ================================================================

def first_name(profile: dict | None) -> str:
    """'Aina (synthetic)' -> 'Aina'. Missing, blank or non-text names -> ''. Only the first word is used."""
    raw = (profile or {}).get("display_name")
    if not isinstance(raw, str):
        return ""
    cleaned = re.sub(r"\s*\(.*?\)\s*", " ", raw).strip()
    return cleaned.split()[0] if cleaned else ""


def list_phrase(names: list[str], limit: int = 2) -> str:
    """['Excel'] -> 'Excel'; two -> 'Excel and SQL'; more -> 'Excel, SQL and 3 others'. Empty -> ''."""
    names = [n for n in names if n]
    if not names:
        return ""
    head = names[:limit]
    extra = len(names) - len(head)
    if extra > 0:
        return f"{', '.join(head)} and {extra} other{'s' if extra != 1 else ''}"
    return " and ".join(head)


def _skill_text(skill_id, name_of: Callable[[str], str]) -> str:
    try:
        text = name_of(skill_id)
    except Exception:           # a failing lookup must never break the screen; fall back to the id
        text = skill_id
    return " ".join(str(text if text is not None else skill_id).split())


def why_sentence(match: dict | None, name_of: Callable[[str], str] | None = None) -> str:
    """ONE plain-English sentence on why a role fits, built only from the engine's Match object:
    the skills the user already has that the role uses (`contributions`, credit > 0) and the biggest gap (`gaps`).
    A gap the user has none of is "missing"; if every gap is a skill they partly have, it is a "step up".
    Missing or malformed data gives a calm fallback, never an invented claim. Returns plain text (escape on render)."""
    name_of = name_of or (lambda skill_id: str(skill_id))
    match = match if isinstance(match, dict) else {}
    contributions = [c for c in (match.get("contributions") or [])
                     if isinstance(c, dict) and c.get("skill_id") and _positive(c.get("credit"))]
    gaps = [g for g in (match.get("gaps") or []) if isinstance(g, dict) and g.get("skill_id")]
    have = list_phrase([_skill_text(c["skill_id"], name_of) for c in contributions])

    missing = next((g for g in gaps if not _positive(g.get("user_level"))), None)
    step_up = None if missing else (gaps[0] if gaps else None)

    if have and missing:
        return f"You already use {have}, which this role needs, but {_skill_text(missing['skill_id'], name_of)} is the biggest skill you are missing."
    if have and step_up:
        skill = _skill_text(step_up["skill_id"], name_of)
        level = LEVEL_WORDS.get(step_up.get("required_level"))
        goal = f"reaching {level} level in {skill}" if level else f"building up {skill}"
        return f"You already use {have}, which this role needs, and your biggest step up is {goal}."
    if have:
        return f"You already cover the skills this role needs, including {have}."
    if missing or step_up:
        gap = missing or step_up
        return f"You do not have this role's key skills yet, and {_skill_text(gap['skill_id'], name_of)} is the biggest one to learn."
    return "We do not have a skill list for this role yet."


def _positive(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x > 0


def missing_skill(match: dict | None) -> tuple[str | None, str | None]:
    """The biggest gap for a role from the engine's `gaps` (already sorted biggest first): ('missing', skill_id) for the
    first skill the user has none of, else ('level', skill_id) for the first partly-met skill, else (None, None)."""
    match = match if isinstance(match, dict) else {}
    gaps = [g for g in (match.get("gaps") or []) if isinstance(g, dict) and g.get("skill_id")]
    first_missing = next((g for g in gaps if not _positive(g.get("user_level"))), None)
    if first_missing:
        return "missing", first_missing["skill_id"]
    if gaps:
        return "level", gaps[0]["skill_id"]
    return None, None


def top_roles(matches: list[dict] | None, n: int = TOP_N) -> list[dict]:
    """The first `n` matches that really overlap with the user's skills (fit above 0), in the engine's order.
    A role with a 0% fit is never shown as something that "fits you"."""
    good = [m for m in (matches or []) if isinstance(m, dict) and _positive(m.get("match_pct"))]
    return good[:n]


def fit_percent(match: dict) -> int:
    """0.4821 -> 48. Clamped to 0..100."""
    return max(0, min(100, round(float(match.get("match_pct") or 0) * 100)))


def trend_word(change: float | None, trajectory: str | None = None) -> str:
    """'rising' | 'steady' | 'falling' | 'unclear'. The engine's trajectory wins; otherwise the sign decides, with the
    engine's own +/-5% band for "steady". The engine calls a skill "stable" when its range of estimates spans zero, so a
    stable skill with a big estimate (outside the band) is 'unclear': a steady-looking word next to a big number would
    contradict itself. None -> 'steady'."""
    if trajectory == "rising":
        return "rising"
    if trajectory == "declining":
        return "falling"
    if trajectory == "stable":
        return "unclear" if change is not None and abs(change) >= config.TREND_THRESHOLD else "steady"
    if change is None or abs(change) < config.TREND_THRESHOLD:
        return "steady"
    return "rising" if change > 0 else "falling"


def _trend_direction(word: str) -> str:
    return {"rising": "up", "falling": "down"}.get(word, "flat")


def hiring_text(change: float | None, trajectory: str | None = None) -> str:
    """Word + sign for a role: 'Hiring rising +7.1%'. No number -> 'Hiring trend not available'."""
    if change is None:
        return "Hiring trend not available"
    word = trend_word(change, trajectory)
    return "Hiring trend unclear" if word == "unclear" else f"Hiring {word} {fmt_signed(change)}"


def skill_trend_text(change: float | None, trajectory: str | None = None, thin: bool = False) -> str:
    """Word + sign for a skill: 'Rising +15.9%'. Thin data -> 'Not enough data'; an unclear trend has no number."""
    if thin:
        return "Not enough data"
    if change is None:
        return "Not available"
    word = trend_word(change, trajectory)
    return "No clear trend" if word == "unclear" else f"{word.capitalize()} {fmt_signed(change)}"


# =============================== HTML builders ==============================================================

def hiring_pill(change: float | None, trajectory: str | None = None) -> str:
    """The small hiring-trend pill on a role card: arrow + word + sign."""
    if change is None:
        return pill(hiring_text(None), "flat")
    return pill(hiring_text(change, trajectory), _trend_direction(trend_word(change, trajectory)))


def skill_pill(change: float | None, trajectory: str | None = None, thin: bool = False) -> str:
    if thin:
        return pill(skill_trend_text(None, thin=True), "low")
    if change is None:
        return pill(skill_trend_text(None), "flat")
    return pill(skill_trend_text(change, trajectory), _trend_direction(trend_word(change, trajectory)))


def skill_word(change: float | None, trajectory: str | None = None, thin: bool = False) -> str:
    """The trend as a word only, no number: Rising, Steady, Falling, No clear trend or Not enough data."""
    if thin:
        return "Not enough data"
    if change is None:
        return "Not available"
    word = trend_word(change, trajectory)
    return "No clear trend" if word == "unclear" else word.capitalize()


def greeting(name: str, line: str, lead: str | None = None) -> str:
    """The page header for a known profile: title + one line. `name` may be empty. `line` is the rest of the title ('these roles fit you best')."""
    text = f"{name}, {line}" if name else line[:1].upper() + line[1:]
    return page_head(text, lead)


def welcome(headline: str, lead: str | None = None) -> str:
    """No profile yet: the same header, with the welcome copy."""
    return page_head(headline, lead)


def how_it_works(steps: tuple[str, ...] = STEPS) -> str:
    """'Resume, Skills, Goals, Your roles' as one plain line of words (no numbering)."""
    return steps_html(steps, None, "How it works", extra_class="sf-home-steps")


def fit_label(pct: int) -> str:
    """The status chip words for a Fit percentage. These cut-offs are display labels only (they are not engine output)."""
    return "Strong fit" if pct >= STRONG_FIT else "Good fit" if pct >= GOOD_FIT else "Stretch"


def fit_chip(pct: int) -> str:
    level = {"Strong fit": "strong", "Good fit": "plain"}.get(fit_label(pct), "stretch")
    return status_chip(fit_label(pct), level)


def fit_track(pct: int) -> str:
    return (f'<div class="sf-track" role="progressbar" aria-label="Fit" aria-valuemin="0" aria-valuemax="100" '
            f'aria-valuenow="{pct}"><i style="width:{pct}%"></i></div>')


FIT_HELP = "How much of this role's skill list you already cover at the level it needs."


def role_card(match: dict, name_of: Callable[[str], str] | None = None, rank: int | None = None, lead: bool = False) -> str:
    """The top of a role card (Home and Matches): title and status chip, Fit % with its progress track, one
    sentence on why, hiring pill. `lead=True` is the dominant first card (bigger Fit number and title); the others are quieter,
    so three cards never read as three identical tiles. The 'Missing: X' strip and its button come after it (see `missing_strip`, rendered by the page)."""
    title = match.get("title") or match.get("role_id") or "Role"
    pct = fit_percent(match)
    rank_text = f"Role {int(rank)}: " if rank else ""
    return (f'<div class="sf-role{" sf-role-lead" if lead else ""}" role="group" aria-label="{rank_text}{esc(title)}, {pct} percent fit">'
            f'<div class="sf-role-head"><div class="sf-role-title">{esc(title)}</div>{fit_chip(pct)}</div>'
            f'<div class="sf-fitrow" title="{esc(FIT_HELP)}"><span class="sf-fit-num">{pct}%</span><span class="sf-fit-label">Fit</span></div>'
            f'{fit_track(pct)}'
            f'<div class="sf-why">{esc(why_sentence(match, name_of))}</div>'
            f'<div>{hiring_pill(match.get("role_growth"))}</div></div>')


def role_row(match: dict, name_of: Callable[[str], str] | None = None, rank: int | None = None) -> str:
    """A compact role row (roles 2 and 3 on Home): title and status chip, a small Fit % with a thin track, one sentence on why.
    The page puts a 'See your plan' link beside it. Quieter than the lead card on purpose: three equal cards read as a template."""
    title = match.get("title") or match.get("role_id") or "Role"
    pct = fit_percent(match)
    rank_text = f"Role {int(rank)}: " if rank else ""
    return (f'<div class="sf-rrow" role="group" aria-label="{rank_text}{esc(title)}, {pct} percent fit">'
            f'<div class="sf-rrow-head"><div class="sf-rrow-title">{esc(title)}</div>{fit_chip(pct)}</div>'
            f'<div class="sf-rrow-fit" title="{esc(FIT_HELP)}"><span class="sf-rrow-num">{pct}%</span><span class="sf-fit-label">Fit</span>{fit_track(pct)}</div>'
            f'<div class="sf-rrow-sub">{esc(why_sentence(match, name_of))}</div></div>')


def missing_strip(match: dict, name_of: Callable[[str], str] | None = None) -> str:
    """The text half of the inline alert strip: 'Missing: X' (a skill the user has none of), 'Level up: X' (a skill they
    partly have) or 'Nothing missing'. Built from the engine's `gaps`. The button next to it is added by the page."""
    name_of = name_of or (lambda skill_id: str(skill_id))
    kind, skill = missing_skill(match)
    if kind is None:
        return '<div class="sf-missing">Nothing missing</div>'
    label = "Missing" if kind == "missing" else "Level up"
    return f'<div class="sf-missing"><span class="sf-missing-label">{label}:</span> <b>{esc(_skill_text(skill, name_of))}</b></div>'


def kpi_items(result: dict | None) -> list[dict]:
    """The three numbers of the KPI strip, all counted or read straight from the engine's `analyse` output (nothing invented):
    the hiring trend for the user's skills (with a rising / steady / falling word), how many tracked roles are a good fit (the same
    cut-off as the card chip), and how many skills they have (with how many of those are rising). A change pill needs a real change, so
    the other cell has none. Score-style numbers (outlook, AI impact) stay behind 'Show details'. Missing data shows a dash."""
    result = result if isinstance(result, dict) else {}
    growth = (result.get("portfolio") or {}).get("growth")
    matches = [m for m in (result.get("matches") or []) if isinstance(m, dict)]
    skills = [s for s in (result.get("skills") or []) if isinstance(s, dict)]
    forecasts = result.get("forecasts") or {}
    fitting = sum(1 for m in matches if _positive(m.get("match_pct")) and fit_percent(m) >= GOOD_FIT)
    rising = sum(1 for s in skills if (forecasts.get(s.get("skill_id")) or {}).get("trajectory") == "rising")
    word = trend_word(growth) if growth is not None else None
    return [
        {"label": "Hiring trend for your skills", "value": fmt_signed(growth) if growth is not None else "—",
         "pill": ("up" if word == "rising" else "down" if word == "falling" else "flat", word.capitalize() if word else "Not available"),
         "sub": "Estimate for the next 12 months"},
        {"label": "Roles that are a good fit", "value": str(fitting), "pill": (None, ""),
         "sub": f"A fit of {GOOD_FIT}% or more, of {len(matches)} roles" if matches else "We have no role list yet"},
        {"label": "Skills you have", "value": str(len(skills)),
         "pill": ("up", f"{rising} rising") if rising else ("flat", "None rising yet"), "sub": "Counted from your profile"},
    ]


def kpi_strip(items: list[dict]) -> str:
    """Up to three big numbers on ONE surface with dividers (not three identical cards): label, number, a small pill, one line of help."""
    cells = []
    for it in items[:3]:
        direction, text = it["pill"]
        chip = f'<div class="sf-stat-pill">{pill(text, direction)}</div>' if direction else ""
        cells.append(f'<div class="sf-stat"><div class="sf-stat-label">{esc(it["label"])}</div><div class="sf-stat-value">{esc(it["value"])}</div>'
                     f'{chip}<div class="sf-stat-sub">{esc(it["sub"])}</div></div>')
    return f'<div class="sf-stats" role="group" aria-label="Your numbers">{"".join(cells)}</div>'


def section_title(title: str, sub: str | None = None, tight: bool = False) -> str:
    return section_header(title, sub, tight=tight)


def skill_rows(held: list[dict], name_of: Callable[[str], str], n: int = SKILL_ROWS, numbers: bool = True) -> str:
    """At most `n` rows: skill name + hiring-trend pill. `held` is app.dashboard.holdings() (biggest weight first);
    skills with enough data come first (the sort is stable), so the rows say something whenever they can.
    `numbers=False` shows the trend as a word only (the figures live in the details)."""
    rows = []
    for h in sorted(held, key=lambda h: bool(h.get("thin")))[:n]:
        change, trajectory, thin = h.get("projected"), h.get("trajectory"), bool(h.get("thin"))
        if numbers:
            chip = skill_pill(change, trajectory, thin)
        else:
            direction = "low" if thin else "flat" if change is None else _trend_direction(trend_word(change, trajectory))
            chip = pill(skill_word(change, trajectory, thin), direction)
        rows.append(f'<div class="sf-skill" role="listitem"><span class="sf-skill-name">{esc(_skill_text(h["skill_id"], name_of))}</span>{chip}</div>')
    if not rows:
        return note("No skills to show yet.")
    return f'<div class="sf-skills" role="list">{"".join(rows)}</div>'


def skills_table(held: list[dict], name_of: Callable[[str], str], query: str = "") -> str:
    """The quiet table in 'Show details': every skill the user has, biggest first, with the hiring trend as a word and a figure,
    their level, and the AI impact (0-100). `query` filters by skill name (case-insensitive). Built as a real table (screen readers get
    the column names) and laid out stacked, because the panel is narrow. Nothing here is invented: a missing figure is a dash."""
    needle = " ".join(str(query or "").split()).lower()
    rows = []
    for h in held:
        name = _skill_text(h["skill_id"], name_of)
        if needle and needle not in name.lower():
            continue
        thin = bool(h.get("thin"))
        trend = skill_trend_text(None, thin=True) if thin else skill_trend_text(h.get("projected"), h.get("trajectory"))
        exposure = h.get("exposure")
        ai = "—" if exposure is None else f"{max(0, min(100, round(exposure * 100)))}/100"
        level = LEVEL_WORDS.get(h.get("level"), "—")
        rows.append(f'<tr><td class="sf-t-name">{esc(name)}</td><td class="sf-t-trend">{esc(trend)}</td>'
                    f'<td class="sf-t-meta">Your level: {esc(level)} · AI impact {esc(ai)}</td></tr>')
    if not rows:
        return note("No skill matches that search." if needle else "No skills to show yet.")
    head = ('<thead class="sf-vh"><tr><th scope="col">Skill</th><th scope="col">Hiring trend (estimate)</th>'
            '<th scope="col">Your level and AI impact (0-100)</th></tr></thead>')
    return f'<table class="sf-table">{head}<tbody>{"".join(rows)}</tbody></table>'


def detail_numbers(metrics: dict) -> str:
    """The three numbers behind 'Show details', each with its plain-English help. Missing values show a dash."""
    def score(x):
        return "—" if x is None else f"{round(x * 100)}/100"
    outlook = metrics.get("readiness")
    items = [
        ("Outlook score", "—" if outlook is None else f"{outlook * 100:.1f}",
         "Your skills' expected hiring growth, reduced for how much hiring bounces around and for your comfort with risk. Higher is better. An estimate."),
        ("AI impact (0-100)", score(metrics.get("ai_exposure")),
         "How much of this work AI already does. Higher means the work is changing fastest, not that the job disappears."),
        ("Skill variety (0-100)", score(metrics.get("diversification")),
         "How evenly your learning is divided across skills. Higher means less depends on any one skill."),
    ]
    cells = "".join(f'<div class="sf-num-item"><div class="sf-num-label">{esc(label)}</div><div class="sf-num-value">{esc(value)}</div>'
                    f'<div class="sf-num-help">{esc(help_text)}</div></div>' for label, value, help_text in items)
    return f'<div class="sf-nums">{cells}</div>'


def demand_chart(months: list[str], values: list[float], direction: str = "flat", height: int = 320):
    """The market-demand line chart (the basket chart), with larger labels and plain wording."""
    from app.ui import demand_fig

    fig = demand_fig(months, values, direction, height=height)
    fig.data[0].hovertemplate = "%{x}<br>Job-post demand %{y:.1f}<extra></extra>"
    fig.update_layout(font=dict(size=15, color=TEXT))
    fig.update_xaxes(tickfont=dict(size=14, color=MUTED), tickangle=0, nticks=4, tickformat="%b %y")
    fig.update_yaxes(tickfont=dict(size=14, color=MUTED))
    return fig
