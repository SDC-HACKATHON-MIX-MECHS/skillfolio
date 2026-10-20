# SkillFolio — UI design rules (lane C)

Follow these exactly on every page in SPEC §6. If a rule doesn't cover a case, choose the plainer option.

## 1. Palette — set once in `.streamlit/config.toml`
```toml
[theme]
base = "light"
primaryColor = "#4338CA"          # ACCENT: buttons, links, the user's dot, active toggle
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F4F5F7"  # sidebar, cards
textColor = "#1F2328"
```
| Token | Hex | Use only for |
|---|---|---|
| `ACCENT` | `#4338CA` | the user (dot, "you" line), primary buttons. Nothing else is indigo. |
| `UP` | `#1A7F37` | rising momentum, positive deltas — always with `▲` |
| `DOWN` | `#CF222E` | declining momentum, negative deltas — always with `▼` |
| `FLAT` | `#6E7781` | stable, band fills (at 20% opacity), roles' bubbles, gridlines `#E5E7EB` |
| `EXPOSURE` | `#E0E7FF` → `#4338CA` | AI-exposure gauge and scale: one hue, light → dark. **Never red/green** — exposure is not "bad". |

- Colour is never the only signal: every up/down value shows an arrow **and** a sign **and**, in tables, the word (`▲ rising`, `■ stable`, `▼ declining`).
- Put these as constants in `app/ui.py` (`ACCENT`, `UP`, `DOWN`, `FLAT`); no hex codes in page files.

## 2. Type and numbers
- One `st.title` per page (`"2 · Skill Market"`). Sections: `st.subheader`. Body: `st.write`. Sources, dates, notes: `st.caption`. No custom fonts, no raw HTML headings.
- Growth/momentum: signed percent, 1 decimal — `▲ +12.3%`, `▼ −4.0%`, `■ +0.8%`. Intervals: `+3% to +22%`.
- AI exposure and match: integer 0–100 — `AI exposure 46/100`, `Match 67%`. Money: `RM 0` (free) / `RM 120`. Hours: `12 h`.
- Dates: `YYYY-MM-DD` everywhere. Skills shown as `Name (TICKER)` via `skill_label()`.

## 3. Cards
- A card = `st.container(border=True)`. Inside: bold title line, one number or chart, one caption. Max 3 cards per row.
- Metric cards use `st.metric(label, value, delta)` with `delta_color="normal"` for growth, `"inverse"` for exposure and volatility (lower is better). `help=` holds the tooltip (§6).
- Match cards (Matches page): title + match % on line 1, then `st.progress(match_pct)`, then an `st.expander("Why this score")` with the breakdown. Collapsed by default.

## 4. Tables
- Always `st.dataframe(df, hide_index=True, use_container_width=True, column_config=...)`. Never `st.table` or raw HTML.
- Ticker table columns, in order: Ticker · Skill · Trend (`LineChartColumn`, demand index) · Momentum · AI exposure (`ProgressColumn`, 0–100) · Trajectory. Demand swing (volatility) is not a column (phone width): show it in a `st.selectbox` skill detail below the table.
- Sort by momentum, high → low. Thin-data rows get `⚠` after the skill name.
- Every table is followed by a source caption (§5).

## 5. Plotly charts
Apply one helper `style_fig(fig)` in `app/ui.py` to every figure:
- `template="plotly_white"`, `font=dict(family="sans-serif", size=13, color="#1F2328")`, `height=340`, `margin=dict(l=8, r=8, t=32, b=8)`.
- Legend horizontal at bottom: `legend=dict(orientation="h", y=-0.2)`. Gridlines `#E5E7EB`, no zero-line emphasis.
- Show with `st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})`.
- Hover text uses the §2 number formats, via `hovertemplate`, ending in `<extra></extra>`.
- Risk/return chart: x = AI exposure (0–100), y = growth (%). Roles = `FLAT` bubbles at 60% opacity, sized by match %, labelled with the short title. User = one `ACCENT` dot, size 18, white outline, labelled `You`. After **Apply plan**: old position as a hollow `ACCENT` ring, arrow annotation old → new.
- Sparklines/bands: line `FLAT` (or `UP`/`DOWN` by trajectory), 80% band as fill at 20% opacity.
- Gauge (`go.Indicator`, mode `gauge+number`): range 0–100, bar `ACCENT`, steps in the `EXPOSURE` scale, no red zone. Show `delta` vs the "before" value after Apply plan.
- Caption under **every** chart and table: `Source: <source name> · retrieved YYYY-MM-DD · estimates, not predictions`.

## 6. Tooltip and label wording
- Plain English, ≤ 25 words, second person, no jargon (no "volatility", "covariance", "OLS" in the first sentence).
- Pattern: what it is → how to read it. Example — Momentum: "How fast job posts mentioning this skill grew over the last 12 months. Above zero means rising."
- AI exposure (use verbatim until lane D confirms the source's definition): "How much AI is already used on tasks linked to this skill, 0–100. It is not a forecast of job loss."
- Volatility → label it **"Demand swing"**; Diversification → **"Spread"**; Readiness → **"Readiness score"**.
- Forecasts always say "estimate". Never "will", "guaranteed" or "safe from AI".

## 7. Empty, waiting and error states
| Situation | Show |
|---|---|
| No profile yet | `require_profile()`: `st.info` + link to 1 · Profile. Nothing else on the page. |
| Another lane's function not built | `call_or_wait()` → `st.info("Waiting for lane X: …")`. Never a traceback. |
| Example fixture loaded | `st.warning` "EXAMPLE DATA" banner at top (already in `page_setup`). |
| Thin data / null exposure | `⚠ thin data` next to the value; exposure shows `—` with help "No AI-exposure data for this skill yet." |
| No matches / no courses fit the budget | `st.info` saying why + one suggested action ("Add hours on your Profile"). |
| Refresh fails | `st.error("Couldn't reach Hacker News. Still showing the snapshot from YYYY-MM-DD.")`; keep the old data on screen. |
| Unexpected exception | Catch at page level → `st.error("Something went wrong on this page.")` + `st.expander("Details")` with the message. |

## 8. Mobile (test at 390 px wide)
- `layout="centered"` only. Max 3 `st.columns`; anything wider becomes stacked cards.
- Tables ≤ 6 columns; no horizontal scroll on the main ticker table at 390 px.
- Charts use `use_container_width=True`; bubble labels only for the top 5 roles; tap targets are Streamlit buttons, never chart clicks.
- All controls on the page body except the global scenario toggle (sidebar). Key actions (**Apply plan**, **Refresh data**) are full-width buttons: `use_container_width=True`, `type="primary"`.
