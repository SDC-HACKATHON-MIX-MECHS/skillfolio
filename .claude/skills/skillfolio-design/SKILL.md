---
name: skillfolio-design
description: Design guardrails for every SkillFolio screen (Streamlit app). Use whenever building, restyling or reviewing any page, component, copy or chart in app/. Holds the audience, message, layout rules, anti-slop rules and the reference library to translate from. Not for engine, data or pipeline work.
---

# SkillFolio design guardrails

Internal instructions for whoever (human or Claude) designs a SkillFolio screen. Read this, then the matching files in `references/`, before touching `app/`.

## Audience, message, goal
- Audience: Malaysian fresh graduates and early-career switchers moving into tech and data roles, on a phone or laptop, who have never used a trading app.
- Primary message: "Here are the roles that fit you, why, and what to learn next."
- Goal of the first session: a new user reaches their ranked roles in under 3 minutes without help.

## Non-negotiables (from the user, binding)
- Clear, clean, easy to read. Factual numbers only, each with its source and date. Forecasts say "estimate".
- Not cluttered. Per screen: at most one hero, three cards or rows, one chart, four numbers above the fold. Everything else behind "Show details".
- Body text 16px or more, secondary 14px or more, body contrast 7:1 where possible, 4.5:1 minimum.
- Plain English. Banned on the visible surface: momentum, volatility, covariance, spread, readiness, rebalance, holdings, watchlist, basket. The precise term may appear after the plain one inside "Show details" or on the Methodology page.
- Dark theme. No real money, no advice, no "buy". No real CVs: demo with made-up data.

## Anti-slop rules (the tells of AI-generated UI; do not ship these)
- No row of three or more identical cards. Make one element clearly dominant and the others secondary, or use an asymmetric split or a list.
- No decorative gradient or glow except, at most, one soft glow behind a page hero. No glowing chips, no neon borders, no glass-on-everything.
- No generic copy ("unlock", "supercharge", "seamless", "powerful", "all-in-one"). Write like a person explaining to a friend. Use real role and skill names from the data.
- No emoji, no icon-in-a-circle feature tiles, no stock illustrations, no fake logos, testimonials or statistics.
- No uniform rounded-everything. Use radius, weight and size contrast deliberately: few levels, used consistently.
- One accent colour, used only for the primary action and the user's own item. Green and red only for up and down, always with an arrow and a word.
- One italic serif emphasis word per hero headline at most. Mono type only for numbers and tiny labels.
- Spacing on an 8px grid. Alignment beats decoration.

## How to use references (translate, do not copy)
Look at the files in `references/` first. For each, note the composition and the restraint that make it readable, then rebuild it with SkillFolio tokens and content. Never copy another brand's colours, logo, copy or exact layout. When a new pattern is needed, add a reference and a rule here: guardrails drift unless they are kept up.

## Build process
Section by section, one section per pass: hero, role list, detail panel, plan, onboarding step. After each, run the `skillfolio-design-qa` skill, fix what it finds, then move on. Do not rebuild whole pages in one go.

## Tokens
Defined once in `app/ui.py` (`page_setup()` injects them). Page files contain no hex codes and no raw HTML.
