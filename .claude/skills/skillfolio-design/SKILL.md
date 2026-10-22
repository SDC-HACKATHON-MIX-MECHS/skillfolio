---
name: skillfolio-design
description: Design guardrails for every SkillFolio screen (Streamlit app). Use whenever building, restyling or reviewing any page, component, copy or chart in app/. Holds the audience, message, v4 light look, clarity rules, anti-slop rules and the reference library to translate from. Not for engine, data or pipeline work.
---

# SkillFolio design guardrails (v4, light)

Internal instructions for whoever (human or Claude) designs a SkillFolio screen. Binding source: `docs/design/UI_BRIEF.md` (sections "v4 IMPLEMENTATION NOTES" and "BRIEF v4 FINAL LOOK"). The older dark/violet v3 look is dropped; do not rebuild it. Read this, then `references/README.md`, before touching `app/`. Tokens live in `app/ui.py`, the stylesheet in `app/theme.css`.

## Audience, message, goal
- Audience: Malaysian fresh graduates and early-career switchers moving into tech and data roles, on a phone or laptop, who have never used a trading app.
- Primary message: "Here are the roles that fit you, why, and what to learn next."
- Goal of the first session: a new user reaches their ranked roles in under 3 minutes without help.

## The v4 look (binding)
- Surface: light warm off-white page, white cards with a 1px soft border and 10px radius (8px buttons and inputs). At most a very soft shadow. No gradient, no glow, no blur, no glass.
- Text: ink on the surface. Inter only, one family: no serif, no mono. Tabular numbers everywhere. Body 16px, secondary 14px (never smaller), KPI number 36px semibold, page title 32px semibold.
- Amber is for FILLS only: progress tracks, chart line, selected tab underline, nav marker. It fails as text, so never use it for text.
- Primary button: dark ink fill, white text, one per screen. Links are ink with an underline. Pill buttons and numbered `[01]` steps are gone.
- Up green and down red only for rising and falling, as a tinted chip with an arrow and a word (Rising, Falling, Not enough data). Status is never colour alone.
- AI impact uses the neutral grey-brown scale (`.sf-track-neutral`), never red, green or amber.
- Contrast: text at least 7:1 on its surface, enforced by `tools/design_audit.py` (it also checks the 14px minimum and the spacing grid). Use the tokens; page files contain no hex codes and no raw HTML.
- Spacing on an 8px grid (4px only for hairline gaps). Alignment beats decoration.

## Clarity rules (binding)
- Per screen: at most 1 hero, 3 cards or rows and 1 chart; at most 4 numbers above the fold. Everything else goes behind "Show details".
- Plain English. Banned on the visible surface: momentum, volatility, covariance, spread, readiness, rebalance, holdings, watchlist, basket, thin data (say "not enough data"). The precise term may appear after the plain one inside "Show details" or on the Methodology page.
- Numbers are factual and sourced; forecasts say "estimate". Every chart or table has one source line under it, via `source_caption` or `source_note` in `app/ui.py`.
- Charts: where labels would crowd, use numbered bubbles with a name key instead of labels on the chart.
- Layout: role 1 is a full card, roles 2-3 are compact rows on one shared surface; right panel at wide widths with the demand chart (1Y / 6M / All) and "Show details". No real money, no advice, no "buy". No real CVs: demo with made-up data.

## Anti-slop rules (do not ship the tells of AI-generated UI)
- No row of three or more identical cards. One element dominates, the others are secondary, or use a list.
- No decorative gradient, glow or glowing chip. No generic copy ("unlock", "supercharge", "seamless", "powerful", "all-in-one"). Use real role and skill names from the data.
- No emoji, no icon-in-a-circle tiles, no stock illustrations, no fake logos, testimonials or statistics.
- Few radius and weight levels, used consistently. Skill and role names are user data: escape them.

## How to use references (translate, do not copy)
Look at `references/` first. For each, note the composition and restraint that make it readable, then rebuild it with SkillFolio tokens and content. Never copy another brand's colours, logo, copy or exact layout. When a new pattern is needed, add a reference and a rule here: guardrails drift unless kept up.

## Build process
Section by section, never whole pages: shell (tokens, sidebar, page header), KPI strip, role list, right panel, Show details. After each, run `skillfolio-design-qa` and fix before moving on.
