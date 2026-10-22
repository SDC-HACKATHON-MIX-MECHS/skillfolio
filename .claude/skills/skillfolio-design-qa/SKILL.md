---
name: skillfolio-design-qa
description: Design-drift check for a finished SkillFolio screen or section. Use after building or changing any page in app/ and before saying it is done. Runs tools/design_audit.py, screenshots the page, compares it with the v4 skillfolio-design guardrails and references, and returns a verdict table. Reports and offers fixes; never edits on its own.
---

# SkillFolio design-drift check (v4, light)

Run once per section or page, right after it is built.

1. Run `python tools/design_audit.py` (contrast, 14px minimum, spacing grid). Any failure is a FAIL here.
2. Open the app (Streamlit) with a sample profile loaded and, for data-dependent pages, the real `data/role_skills.csv`. Screenshot at 1280px and 390px width. If no screenshot can be produced, stop and say so; do NOT judge from code or text alone. Ask for a pasted screenshot.
3. Read `.claude/skills/skillfolio-design/SKILL.md` and `docs/design/UI_BRIEF.md` (v4 sections).
4. For each rule, mark PASS, FAIL or NOT SEEN with evidence (what is on screen, where):
   - Surface is light warm off-white with white cards, 1px soft border, 10px radius. Any dark surface, gradient, glow, blur or glass is a FAIL.
   - Fonts: Inter only. Any serif, italic emphasis word or mono face is a FAIL.
   - Amber appears only as a fill (progress, chart line, selected tab, nav marker), never as text. Primary button is dark ink with white text.
   - Status is never colour alone (chip has an arrow and a word). AI impact is grey-brown, never red, green or amber.
   - Text contrast at least 7:1; body 16px, secondary 14px; no text smaller than 14px.
   - Count: hero(s), cards/rows, charts, numbers above the fold (limits: 1, 3, 1, 4). Three or more identical cards in a row?
   - Any banned jargon visible outside "Show details" and Methodology (list in skillfolio-design)?
   - Every number has a source or is clearly derived; one source line under each chart or table; forecasts say "estimate". Crowded chart labels use numbered bubbles with a name key.
   - Overlap, clipping, horizontal scroll at 390px; default-Streamlit leftovers (blue focus, beige or white boxes, default tables); 8px grid.
   - Matches the reference's composition and restraint without copying it.
5. Output an inline verdict table plus a short list of concrete fixes ranked by effect on readability. Save the full audit as `docs/design/qa/<page>-<YYYYMMDD-HHMM>.md`.
6. Offer to apply the fixes. Never edit files unprompted.
