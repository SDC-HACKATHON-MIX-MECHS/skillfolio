---
name: skillfolio-design-qa
description: Design-drift check for a finished SkillFolio screen or section. Use after building or changing any page in app/ and before saying it is done. Screenshots the page, compares it with the skillfolio-design guardrails and the reference library, and returns a verdict table. Reports and offers fixes; never edits on its own.
---

# SkillFolio design-drift check

Run once per section or page, right after it is built.

1. Open the app (Streamlit) with a sample profile loaded and, for data-dependent pages, the real `data/role_skills.csv`. Screenshot the page at 1280px and 390px width. If no screenshot can be produced (pane hidden, timeouts), stop and say so; do NOT judge from code or text alone. Ask for a pasted screenshot.
2. Read `.claude/skills/skillfolio-design/SKILL.md` and the files in its `references/`.
3. For each rule below, mark PASS, FAIL or NOT SEEN with evidence (what is on screen, where):
   - Count: hero(s), cards/rows, charts, numbers above the fold (limits: 1, 3, 1, 4).
   - Three or more identical cards in a row? Is one element dominant?
   - Any banned jargon visible outside "Show details" and Methodology?
   - Text sizes and contrast (body 16px+, secondary 14px+, 4.5:1 minimum).
   - Decoration: gradients/glows beyond the single hero glow, glowing chips, emoji, stock phrases, fake proof.
   - Every number: has a source or is clearly derived; forecasts say "estimate".
   - Overlap, clipping, horizontal scroll at 390px; default-Streamlit leftovers (blue focus, white boxes, default tables).
   - Matches the reference's composition and restraint without copying it.
4. Output an inline verdict table plus a short list of concrete fixes ranked by effect on readability. Save the full audit as `docs/design/qa/<page>-<YYYYMMDD-HHMM>.md`.
5. Offer to apply the fixes. Never edit files unprompted.
