"""Extra building blocks for pages 2-6 (Skill Market, My Portfolio, Matches, Rebalance Plan, Methodology).

Design rules: one message per screen, at most one hero + three cards or rows + one chart, big type, plain words, detail
behind expanders. Same technical rules as app/ui.py: every builder returns ONE LINE of HTML, every piece of data text
goes through `esc()`, render with `show(...)`; page files never contain raw HTML or hex codes. There is no stylesheet
here: every class used below is styled by the shared app/theme.css (injected once per page by `ui.page_setup`).
"""

from __future__ import annotations

from app.home_components import skill_pill
from app.ui import esc, exposure_bar, icon, pill, range_tabs, small_label, sparkline, status_chip

# --- Plain-English words. Precise terms live only in expanders and on Methodology. ----------

PLAIN = {
    "trend": "How much more or less often job posts ask for this skill over a year. An estimate, not a prediction.",
    "ai": "How much of this work AI already does, 0 to 100. It means the work is changing fastest, not that the job disappears.",
    "bounce": "How much hiring for this skill goes up and down from month to month. Lower means steadier.",
    "outlook": "Your skills' hiring trend minus a penalty for ups and downs, adjusted for the risk you accept. Higher is better. An estimate.",
    "variety": "How evenly your skills are shared out, 0 to 100. Higher means less rests on one skill.",
    "fit": "How much of this role's skill list you already cover at the level it needs.",
}


def choice_control(label: str, options: list[str], default: str, key: str) -> str:
    """A single-choice control (segmented where Streamlit has it, otherwise horizontal radio). Never returns None.
    One implementation with the chart range tabs: deselecting the active choice keeps the default."""
    return range_tabs(key, tuple(options), default, label=label)


# --- Small pieces -------------------------------------------------------------------------------------

def _safe_url(url) -> str | None:
    url = str(url or "").strip()
    return url if url.lower().startswith(("https://", "http://")) else None


def link_button(label: str, url, new_tab_note: str = "opens in a new tab") -> str:
    """An outbound link styled as a 44px button. Not http(s) -> empty string (never a javascript: link)."""
    safe = _safe_url(url)
    if not safe:
        return ""
    return (f'<a class="sf-linkbtn" href="{esc(safe)}" target="_blank" rel="noopener noreferrer">{esc(label)}'
            f'<span class="sf-vh"> ({esc(new_tab_note)})</span>{icon("arrow-right", 14)}</a>')


# --- Skill rows ---------------------------------------------------------------------------------------

def _trend_pill(change: float | None, trajectory: str | None, thin: bool) -> str:
    return skill_pill(change, trajectory, thin)


def skill_row(name: str, ticker: str, change: float | None, trajectory: str | None, thin: bool, trend: list[float] | None,
              exposure: float | None = None, sub: str | None = None, with_ai: bool = False) -> str:
    """One skill: Name (TICKER) + a sub line, a little demand line, the hiring-trend pill, and (long list only) AI impact."""
    direction = "flat" if thin else {"rising": "up", "declining": "down"}.get(trajectory or "", "flat")
    sub_html = f'<div class="sf-sub">{esc(sub)}</div>' if sub else ""
    ai = f'<div class="sf-c-exp">{exposure_bar(exposure)}</div>' if with_ai else ""
    return (f'<div class="sf-row{" sf-row-thin" if thin else ""}{"" if with_ai else " sf-row-3"}" role="listitem" aria-label="{esc(name)}">'
            f'<div class="sf-c-name"><div class="sf-name">{esc(name)}</div>{sub_html}</div>'
            f'<div class="sf-c-spark">{sparkline(trend, direction)}</div><div class="sf-c-pill">{_trend_pill(change, trajectory, thin)}</div>{ai}</div>')


def skill_list(rows: list[str], with_ai: bool = False, empty_text: str = "Nothing to show yet.") -> str:
    """Wrap skill_row() strings in the list card. Empty -> a plain message."""
    if not rows:
        return f'<div class="sf-list"><div class="sf-empty">{esc(empty_text)}</div></div>'
    ai_head = '<div class="sf-c-exp">AI impact</div>' if with_ai else ""
    head = (f'<div class="sf-list-head" aria-hidden="true"><div class="sf-c-name">Skill</div><div class="sf-c-spark">Job-post demand</div>'
            f'<div class="sf-c-pill">Hiring trend (estimate)</div>{ai_head}</div>') if with_ai else ""
    return f'<div class="sf-list" role="list">{head}{"".join(rows)}</div>'


def chip_row(texts: list[str]) -> str:
    return f'<div class="sf-chiprow">{"".join(status_chip(t) for t in texts)}</div>'


def track(fraction: float | None, label: str, neutral: bool = False) -> str:
    """A thin progress track (0..1) with an accessible label. None -> an empty track. `neutral=True` is the grey-brown fill for AI impact."""
    pct = 0 if fraction is None else max(0, min(100, round(fraction * 100)))
    return (f'<div class="sf-track{" sf-track-neutral" if neutral else ""}" role="img" aria-label="{esc(label)}">'
            f'<i style="width:{max(pct, 3) if fraction is not None else 0}%"></i></div>')


# --- Skill Market cards -------------------------------------------------------------------------------

def ai_word(exposure: float | None) -> str:
    """AI impact as a word, using the same thirds as the gauge: Low < 33, Medium < 66, High."""
    if exposure is None:
        return "No data"
    score = round(exposure * 100)
    return "Low" if score < 33 else "Medium" if score < 66 else "High"


def skill_card(name: str, ticker: str, category: str | None, change: float | None, trajectory: str | None, thin: bool,
               exposure: float | None, lead: bool = False) -> str:
    """One spacious skill card: category label, Name (TICKER), trend chip, AI-impact track with a word."""
    word = ai_word(exposure)
    tip = f"AI impact {round(exposure * 100)} out of 100" if exposure is not None else "No AI-impact data for this skill yet."
    eye = small_label(category) if category else ""
    return (f'<div class="sf-scard{" sf-scard-lead" if lead else ""}{" sf-row-thin" if thin else ""}" role="listitem"><div class="sf-scard-top"><div>{eye}'
            f'<div class="sf-name">{esc(name)}</div></div>{skill_pill(change, trajectory, thin)}</div>'
            f'<div class="sf-track-row" title="{esc(tip)}"><span class="sf-sub">AI impact: {esc(word)}</span>'
            f'{track(exposure, "AI impact " + word, neutral=True)}</div></div>')


def card_list(cards: list[str], empty_text: str = "Nothing to show yet.") -> str:
    if not cards:
        return f'<div class="sf-list"><div class="sf-empty">{esc(empty_text)}</div></div>'
    return f'<div class="sf-cards" role="list">{"".join(cards)}</div>'


# --- Matches ------------------------------------------------------------------------------------------

def sdg_chips(sdgs: list[int], names: dict[int, str], url=None) -> str:
    """SDG chips. With a valid URL each chip links to it (new tab); otherwise plain chips."""
    safe = _safe_url(url)
    chips = []
    for goal in sdgs:
        inner = f'<b>SDG {int(goal)}</b><span>{esc(names.get(goal, ""))}</span>'
        if safe:
            chips.append(f'<a class="sf-chip" href="{esc(safe)}" target="_blank" rel="noopener noreferrer">{inner}'
                         f'<span class="sf-vh"> (source, opens in a new tab)</span></a>')
        else:
            chips.append(f'<span class="sf-chip">{inner}</span>')
    return f'<div class="sf-chips">{"".join(chips)}</div>' if chips else ""


def role_extras(growth_pill_html: str, exposure: float | None, chips_html: str) -> str:
    """Role details for the expander: demand growth pill, AI impact bar, SDG chips."""
    return (f'<div class="sf-role"><div class="sf-role-meta"><div>{growth_pill_html}<span class="sf-sub"> demand growth, estimate</span></div>'
            f'<div class="sf-role-exp"><span class="sf-sub">AI impact</span>{exposure_bar(exposure)}</div></div>{chips_html}</div>')


# --- Learning plan ------------------------------------------------------------------------------------

def course_row(order: int, title: str, provider: str | None, skill_label_text: str, hours: float, cost_text: str,
               url, lead: bool = False) -> str:
    """One course card in the ordered plan: step number, course, skill and provider, status chips (hours, cost), link."""
    chips = chip_row([f"{hours:g} h", cost_text])
    return (
        f'<div class="sf-order{" sf-order-lead" if lead else ""}" role="listitem"><div class="sf-ord-n">{int(order):02d}</div>'
        f'<div class="sf-ord-main"><div class="sf-name">{esc(title)}</div>{chips}</div>'
        f'<div class="sf-ord-link">{link_button("Open course", url)}</div></div>'
    )


def course_list(rows: list[str]) -> str:
    return f'<div class="sf-cards" role="list">{"".join(rows)}</div>'


def compare_cards(items: list[tuple]) -> str:
    """Before/after cards. items = [(label, now_text, before_text, after_text, delta_text_or_None, delta_dir, help), ...].
    The big number is `now_text`; when a delta is given it shows as a pill; the small line always shows before and after."""
    cells = []
    for label, now_text, before_text, after_text, delta_text, delta_dir, help_text in items:
        tip = f' title="{esc(help_text)}"' if help_text else ""
        delta = f'<div>{pill(delta_text, delta_dir)}</div>' if delta_text else ""
        cells.append(
            f'<div class="sf-stat"{tip}><div class="sf-stat-label">{esc(label)}</div><div class="sf-stat-big">{esc(now_text)}</div>{delta}'
            f'<div class="sf-stat-sub">Before {esc(before_text)} · after plan {esc(after_text)}</div></div>')
    return f'<div class="sf-stats">{"".join(cells)}</div>'


# --- Methodology --------------------------------------------------------------------------------------

def concept_card(title: str, paragraphs: list[str], formula: str | None = None) -> str:
    """A plain-English explanation card with an optional one-line formula (plain version first)."""
    body = "".join(f"<p>{esc(p)}</p>" for p in paragraphs)
    form = f'<div class="sf-formula">{esc(formula)}</div>' if formula else ""
    return f'<div class="sf-concept"><div class="sf-concept-title">{esc(title)}</div>{body}{form}</div>'


def source_list(rows: list[dict]) -> str:
    """Sources: name + what we use it for, licence and date, link. rows = [{name, use, licence, retrieved, url}, ...]."""
    items = []
    for r in rows:
        use = f'<div class="sf-sub">{esc(r["use"])}</div>' if r.get("use") else ""
        items.append(
            f'<div class="sf-src" role="listitem"><div><div class="sf-src-name">{esc(r["name"])}</div>{use}'
            f'<div class="sf-sub">Licence: {esc(r["licence"])} · retrieved {esc(r["retrieved"])}</div></div>'
            f'<div>{link_button("Open source", r.get("url"))}</div></div>')
    return f'<div class="sf-list" role="list">{"".join(items)}</div>'


# --- Charts -------------------------------------------------------------------------------------------

SDG_SHOWN = 5          # goals listed; the rest are summed into one line so the list stays readable


def sdg_bars(allocation: dict[int, float], names: dict[int, str], shown: int = SDG_SHOWN) -> str:
    """Where the user's skills point, as a ranked list: the biggest goals first, each with its name, its share and a thin bar
    (bars are drawn relative to the biggest share so differences are visible). The smaller goals are one line. SDG 4 is marked as the
    baseline every skill supports. One line of HTML; names are escaped."""
    goals = sorted((g for g, v in allocation.items() if v and v > 0), key=lambda g: (-allocation[g], g))
    if not goals:
        return ""
    biggest = allocation[goals[0]]
    rows = []
    for goal in goals[:shown]:
        share = allocation[goal]
        name = names.get(goal, "")
        base = '<span class="sf-sub"> · baseline</span>' if goal == 4 else ""
        width = max(4, round(100 * share / biggest)) if biggest else 0
        rows.append(f'<li class="sf-sdg-row"><span class="sf-keynum" aria-hidden="true">{int(goal)}</span>'
                    f'<div class="sf-sdg-main"><div class="sf-sdg-head"><span class="sf-keyname">SDG {int(goal)} · {esc(name)}{base}</span>'
                    f'<span class="sf-sdg-pct">{share * 100:.1f}%</span></div>'
                    f'<div class="sf-track sf-track-thin sf-track-neutral" role="img" aria-label="{share * 100:.1f} percent of your skills"><i style="width:{width}%"></i></div></div></li>')
    rest = goals[shown:]
    more = ""
    if rest:
        total = sum(allocation[g] for g in rest) * 100
        more = f'<div class="sf-sdg-more">{len(rest)} smaller goal{"s" if len(rest) != 1 else ""} make up {total:.1f}% together.</div>'
    return f'<ol class="sf-sdg" aria-label="Goals your skills point to, biggest first, as a share of your skills">{"".join(rows)}</ol>{more}'


# --- My Portfolio: the skill mix ----------------------------------------------------------------------

import math  # noqa: E402  (kept with the section that uses it, so this section merges cleanly with other page work)

from app.home_components import skill_word, trend_word  # noqa: E402
from app.ui import note  # noqa: E402

MIX_TONES = 6          # segment shades in theme.css (sf-mix-s0 .. sf-mix-s5), reused in turn


def share_text(share: float) -> str:
    """A skill's share of the mix as a whole percent; a share above 0 that rounds to 0 says '<1%' (never a false 0%)."""
    pct = share * 100
    return "<1%" if 0 < pct < 0.5 else f"{round(pct)}%"


def tiles(cells: list[str], stacked: bool = False) -> str:
    """Tiles from home_components.tile side by side, as on Home (one column on a narrow phone). `stacked=True` puts them one above
    the other, for a narrow side column."""
    return f'<div class="sf-tiles{" sf-tiles-stack" if stacked else ""}">{"".join(cells)}</div>'


def _mix_direction(change, trajectory, thin: bool) -> str:
    if thin:
        return "low"
    if change is None:
        return "flat"
    word = trend_word(change, trajectory)
    if word == "unclear":
        return "lean-up" if change > 0 else "lean-down"
    return {"rising": "up", "falling": "down"}.get(word, "flat")


def skill_mix(held: list[dict], name_of) -> str:
    """The portfolio picture: ONE bar split by each skill's share of the user's skill mix (engine weights: level / sum of levels),
    then one row per skill, biggest first: a colour key, the name, the share and the hiring trend as a word (Rising, Steady, Falling,
    Leaning up/down, Not enough data). `held` is app.dashboard.holdings(). Unreadable shares are left out, never guessed.
    Colours come from app/theme.css classes (the bar sits on the charcoal card). One line of HTML; names are escaped."""
    rows = []
    for h in held or []:
        share = h.get("weight")
        if isinstance(share, (int, float)) and not isinstance(share, bool) and math.isfinite(share) and share > 0:
            rows.append((float(share), h))
    if not rows:
        return note("No skills to show yet.")
    rows.sort(key=lambda r: -r[0])
    segs, items, alt = [], [], []
    for i, (share, h) in enumerate(rows):
        tone = f"sf-mix-s{i % MIX_TONES}"
        name = " ".join(str(name_of(h["skill_id"])).split())
        text = share_text(share)
        alt.append(f"{name} {text}")
        segs.append(f'<i class="sf-mix-seg {tone}" style="width:{max(round(share * 100, 1), 1):g}%"></i>')
        change, trajectory, thin = h.get("projected"), h.get("trajectory"), bool(h.get("thin"))
        word = skill_word(change, trajectory, thin)
        items.append(f'<div class="sf-mix-row" role="listitem"><span class="sf-mix-key {tone}" aria-hidden="true"></span>'
                     f'<span class="sf-mix-name">{esc(name)}</span>'
                     f'<span class="sf-mix-word">{pill(word, _mix_direction(change, trajectory, thin))}</span>'
                     f'<span class="sf-mix-pct">{esc(text)}</span></div>')
    label = "Your skill mix: " + ", ".join(alt)
    return (f'<div class="sf-mix"><div class="sf-mix-bar" role="img" aria-label="{esc(label)}">{"".join(segs)}</div>'
            f'<div class="sf-mix-list" role="list">{"".join(items)}</div></div>')
