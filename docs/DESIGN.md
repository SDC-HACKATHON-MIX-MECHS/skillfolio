# SkillFolio — UI design system ("check your skills like a broker app")

Follow these on every page in SPEC §6. If a rule doesn't cover a case, choose the plainer option.
Reference: the named style of Trading 212 / Moomoo (dark, calm, many numbers, one big hero number). No screenshots were supplied; if some arrive they override this file.

## 0. What we took from the reference, and where we depart on purpose
| Point | Decision |
|---|---|
| Surfaces | FOLLOW. Near-black blue page, slightly lighter cards, 1px borders, almost no shadow. |
| Accent | FOLLOW with one cool blue. Used for the primary action, the selected control and "you". Orange (Moomoo) is not used. |
| Green / red | FOLLOW, always with arrow + sign + word. **Departure:** AI exposure is never red/green; it has its own amber scale, because exposure is not "bad". |
| Type | FOLLOW: clean sans for labels, a mono face with tabular figures for every number. |
| Density | FOLLOW (about 56-60px rows, many numbers per screen), but body text stays >= 14px and tap targets >= 44px. |
| Signature | FOLLOW: a huge hero number with a delta pill, a time-range line chart, then Holdings and Watchlist lists. |
| Money language | **Departure.** There is no money, no orders and no advice. Words: Holdings, Watchlist, Rebalance plan. Never "buy", never "guaranteed". Forecasts say "estimate". |
| Light theme | **Departure** from the old rules. Dark only (Streamlit `base = "dark"`); contrast still >= 4.5:1. |
| Custom fonts / raw HTML | **Departure** from the old rules ("no custom fonts", "no raw HTML"). Reason: the broker look needs a mono numeric face and pill/row components Streamlit does not have. Controlled by rule 8 below. |

Rules that still apply unchanged: plain-English tooltips (<= 25 words), "estimate, not prediction" wording, a Source caption under every chart and table, the empty/waiting/error table (section 7), thin-data rows greyed with the words "low data", skills shown as `Name (TICKER)`, mobile check at 390px, dates `YYYY-MM-DD`, no age or gender anywhere.

## 1. Tokens — set once, in `.streamlit/config.toml` and `app/ui.py`
```toml
[theme]
base = "dark"
primaryColor = "#3B82F6"
backgroundColor = "#0B0F14"
secondaryBackgroundColor = "#121821"
textColor = "#E6EDF3"
font = "sans serif"
```
| Token (`app/ui.py`) | Hex | Use only for |
|---|---|---|
| `BG` | `#0B0F14` | page |
| `CARD` | `#121821` | cards, sidebar |
| `RAISED` | `#1A2230` | hover, bar tracks, tooltips |
| `BORDER` | `#243042` | 1px borders |
| `GRID` | `#1E2836` | chart gridlines |
| `TEXT` / `MUTED` | `#E6EDF3` / `#8B98A9` | primary / secondary text |
| `ACCENT` | `#3B82F6` | primary buttons, selected tab, "you". Nothing else is blue. |
| `ON_ACCENT` | `#0B0F14` | text on an accent fill (white on this blue is only 3.7:1; near-black is 5.2:1) |
| `UP` / `DOWN` / `FLAT` | `#2EBD85` / `#F6465D` / `#8B98A9` | rising / declining / stable and low-data |
| `EXPOSURE_LOW` -> `EXPOSURE_HIGH` | `#3B2A0A` -> `#F5A524` | AI exposure only. One amber scale. Never red/green. |

- Colour is never the only signal. Every up/down value shows an arrow **and** a sign **and** a word (`+9.7% rising`, `−3.0% declining`, `+0.8% stable`, `low data`). Use `change_pill()`.
- No hex codes and no emoji in page files (`tests/test_app_smoke.py` checks this). Tokens come from `app/ui.py`.
- Contrast of the text tokens on `BG` and `CARD` is tested (>= 4.5:1).

## 2. Type and numbers
- Text: Fira Sans. Numbers (hero, pills, stat cards, tables, hover): Fira Code with `font-variant-numeric: tabular-nums`. Both load from Google Fonts in `inject_css()`; offline they fall back to `system-ui` / `ui-monospace` and nothing breaks.
- One `st.title` per page. Sections: `section_header()` or `st.subheader`. Body: `st.write`. Sources, dates, notes: `st.caption`.
- Growth/momentum: signed percent, 1 decimal, true minus sign: `+12.3%`, `−4.0%`. Intervals: `+3% to +22%`.
- AI exposure and match: integer 0-100 (`AI exposure 46/100`, `Match 67%`). Money: `RM 0` / `RM 120`. Hours: `12 h`. Dates: `YYYY-MM-DD`.
- Skills are shown as `Name (TICKER)`; `holding_row` and `skill_label()` do this.

## 3. Components — the only way to put custom markup on a page
All builders live in `app/ui.py`, return one line of HTML, escape every piece of data text with `esc()` (skill names and resume text are user input), and are rendered with `show(...)`.

| Helper | Use |
|---|---|
| `hero(label, value, delta_text, delta_dir, caption)` | the one big number with a delta pill |
| `pill(text, direction)` / `change_pill(change, trajectory, thin)` | arrow + sign + word status pill |
| `stat_row([(label, value, help), ...])` | row of small stat cards |
| `section_header(title, subtitle, icon_name, right_html)` | heading + one-line subtitle |
| `holding_row(...)` + `holdings_list(rows)` | Holdings / Watchlist list: Name (TICKER), sparkline, momentum pill, AI-exposure bar |
| `card_container()` | bordered container styled as a card, for widgets inside |
| `icon(name, size)`, `sparkline(values, direction)`, `exposure_bar(x)` | inline-SVG pieces |

- Icons: Streamlit Material icons (`:material/name:`) or `icon()` SVG. **No emoji as icons**, ever.
- Cards: a card is `card_container()` or a component above. Inside: a title, one number or chart, one caption. Max 3 columns per row.
- Metric cards may still use `st.metric(label, value, delta, help=...)`; they are styled as cards by the CSS.

## 4. Tables and lists
- Broker lists (Holdings, Watchlist) use `holdings_list`. Plain data tables use `st.dataframe(df, hide_index=True, use_container_width=True, column_config=...)`.
- Sort by momentum high to low. **Thin-data rows**: greyed, sorted to the bottom, pill says `low data`, never highlighted. Sparkline values are capped at 400.
- Every table or list is followed by a source caption (section 5).

## 5. Charts and the Source caption
- Every Plotly figure goes through `style_fig(fig)`: `plotly_dark`, transparent paper, muted gridlines, Fira fonts, mono hover, `height` 340 by default, legend horizontal at the bottom. Show with `show_fig(fig)` (no mode bar).
- Put a chart in `card_container()`. Caption under **every** chart and table: `Source: <source name> · retrieved YYYY-MM-DD · estimates, not predictions` (`source_caption()`).
- The Home line chart is "Market demand for your skills": the demand index of the user's skills, weighted by their levels, from the snapshot's monthly series. It is the **market**, not a history of the user's own score, and the page says so. Skills with thin data, or with no postings at the start of the chosen range, are left out and named in the caption. Maths: `app/dashboard.py::basket_index`.
- Risk/return chart: x = AI exposure, y = growth. Roles = `FLAT` bubbles sized by match %; the user = one `ACCENT` dot labelled `You`.
- Gauge: 0-100, bar `ACCENT`, steps in the amber `EXPOSURE_STEPS`, no red zone.

## 6. Tooltip and label wording
- Plain English, <= 25 words, second person, no jargon in the first sentence. Pattern: what it is, then how to read it.
- AI exposure (verbatim, matches replit.md): "How much of this work already shows up in real AI use, 0-100. It means the work is changing fastest, not that the job disappears."
- Volatility is **"Demand swing"**; Diversification is **"Spread"**; Readiness is **"Readiness score"**.
- Forecasts always say "estimate". Never "will", "guaranteed" or "safe from AI".

## 7. Empty, waiting and error states
| Situation | Show |
|---|---|
| No profile yet | Home: short welcome + one primary button "Set up my portfolio". Other pages: `require_profile()` (info + link to the Profile page). Nothing else on the page. |
| Another lane's function not built | `call_or_wait()` -> `st.info("Waiting for lane X: ...")`. Never a traceback. |
| Example fixture loaded | `st.warning` "EXAMPLE DATA" banner at top (already in `page_setup`). |
| Thin data / null exposure | Pill `low data`, row greyed. Exposure shows `—` with the tooltip "No AI-exposure data for this skill yet." |
| No matches / no courses fit the budget | `st.info` saying why + one suggested action. |
| Refresh fails | `st.error("Couldn't reach Hacker News. Still showing the snapshot from YYYY-MM-DD.")`; keep the old data on screen. |
| Unexpected exception | Catch at page level -> `st.error("Something went wrong on this page.")` + `st.expander("Details")`. |

## 8. The CSS rule (replaces "no raw HTML")
- ONE stylesheet, injected by `inject_css()`, which `page_setup()` calls. Pages never write `<style>` or raw HTML; they call helpers.
- It must contain: cursor `pointer` on clickable things, visible `:focus-visible` rings, 150-300ms transitions only (200ms used), a `prefers-reduced-motion` block, and the 390px (`max-width: 640px`) rules. `tests/test_dashboard_ui.py` checks these are present.
- Primary buttons use near-black text on the blue fill (contrast), and every button/link is at least 44px tall.

## 9. Mobile (test at 390 px wide)
- `layout="centered"` only. Max 3 `st.columns`; the holdings list re-flows to two lines per row; stat cards stay in one row of three.
- No horizontal scroll at 390px (checked on Home). Charts use `use_container_width=True`; bubble labels only for the top 5 roles.
- Key actions (Apply plan, Refresh data, Set up my portfolio) are full-width `type="primary"` buttons.
