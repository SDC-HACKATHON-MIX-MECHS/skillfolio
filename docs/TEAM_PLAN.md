# SDC Hackathon 2026 — Domain 1 Team Plan

**Domain:** The Aiversecity Future-Ready Workforce · **Round:** Preliminary (Phase 1, online)
**Deadline:** Sun 25 Oct 2026, 08:00 — **we submit Sat 24 by 9 pm**
**Platform:** Replit (compulsory) + public GitHub repo

---

## 1. The challenge in one paragraph

Build an AI-powered web app that **tracks AI advancement** to predict which skills and jobs will **rise or decline**, **matches people to future roles**, generates **personalised reskilling pathways**, and shows how each role and skill connects to the **17 UN SDGs**.

### The 6 must-haves (all must be in the proposal; the demo must show the most important one working)

| # | Feature | What judges expect |
|---|---|---|
| 1 | Skills profile intake | CV upload, form or questionnaire |
| 2 | AI-trend signal layer | At least one **updatable** source of AI / job-market trends, with **source and date shown**. Hard-coded lists don't count |
| 3 | Future-role matching | Ranked roles with an **explainable** match score and a clear skills gap |
| 4 | Reskilling pathway | Ordered learning plan with estimated time, free / low-cost resources (incl. HRD Corp-claimable) |
| 5 | SDG mapping | Every role and skill tagged to ≥1 SDG; show how the user's path contributes |
| 6 | Handling uncertainty | More than one future scenario (e.g. moderate vs fast AI disruption); predictions labelled as estimates |

### Hard rules
- Public, open or **synthetic** data only — no real CVs or personal data.
- If we use an LLM, **say which one**. Every recommendation **cites a source**. The system must **never invent** jobs, courses or statistics.
- AI **supports** career decisions; it doesn't replace human judgement or make hiring decisions.
- Out of scope: course content, payments, real recruitment integrations.

### How we're scored (preliminary)

| Criterion | Weight | What wins it |
|---|---|---|
| Innovation & Creativity | 30% | One sharp user + moment of need. Go beyond "upload a CV and ask a chatbot". Originality in how trend signals become skill forecasts, how scenarios are modelled, or how SDG links change choices |
| Problem-Solution Fit | 25% | Covers the whole chain + explains all 6 must-haves + keeps humans in charge |
| Feasibility of Build | 25% | Live rough version of the key feature — **"the trend signal layer feeding role matching"** — backed by GitHub. Name our hardest risk + fallback |
| Clarity of Proposal | 20% | Problem → approach → expected outcome. A stranger could explain it back. Follows the format and length limits |

### Event timeline
- **19–25 Oct** · Phase 1 (online): Preliminary Round ← we are here
- 25–28 Oct · Judging / shortlisting
- 28–30 Oct · Phase 2 (online): Upgrading Round — top 15 teams per domain
- 31 Oct · Final: 24-hour physical hackathon at XMUM
- 1 Nov · Final pitching & closing ceremony

Preliminary scores don't carry forward, so we build in a way that lets us bolt on extras in Phase 2.

---

## 2. Our 6 idea options (we vote at kickoff)

All 6 use the same engine underneath:

**profile → trend data → skill forecast → role match → learning plan → SDG tags**

About 70% of the work is identical whichever we pick. The idea decides **who** it's for, the **hook** judges remember, and the **wow moment** in the demo. Roles (section 4) stay the same.

### Idea 1 — Pivot Compass *(working name: HalaTuju)*
- **Pitch:** "AI shouldn't replace Aisyah — it should show her where to go next."
- **Who:** A Malaysian worker in a job AI is changing (e.g. accounts clerk), the moment their company announces it's bringing in AI.
- **User sees:** (1) enters skills via form or sample CV → (2) which of their skills are rising/falling, with source + date → (3) ranked future roles with match % and missing skills → (4) ordered course plan (hours, cost, free / HRD Corp) tagged to SDGs.
- **Wow moment:** Press "Refresh trend data" → her role rankings change live.
- **Build:** one public job-posting source + a public AI-exposure dataset; a "momentum score" per skill; match % = how much of a role's skills you already have; LLM reads the CV and writes explanations.
- **Extra work:** none (baseline). **Risk:** closest to "upload CV, get jobs" — least original.

### Idea 2 — Task X-Ray *(working name: TaskLens)*
- **Pitch:** "Jobs don't disappear. Tasks do."
- **Who:** Same worker, the moment they ask "Will AI take my job?"
- **User sees:** (1) describes their daily work → (2) job broken into tasks labelled **AI DOES IT / AI HELPS YOU / ONLY YOU** → (3) future roles built around their "only you" strengths → (4) course plan to fill the gaps, tagged to SDGs.
- **Wow moment:** Flip "slow AI" → "fast AI" and more of her tasks turn to "AI does it".
- **Build:** O*NET (free database of the tasks in ~1,000 jobs) + a public task-level AI-usage dataset (e.g. Anthropic Economic Index, which splits automation vs augmentation); a mapping table from Malaysian job titles (MASCO) to O*NET; LLM matches her description to O*NET's fixed task list.
- **Extra work:** medium (task mapping). **Risk:** task data is US-based — disclose it and show the Malaysian mapping.

### Idea 3 — Skill Portfolio *(working name: SkillFolio)*
- **Pitch:** "Your skills are a portfolio. AI is the market."
- **Who:** Fresh grads and career switchers deciding where to go next.
- **User sees:** (1) their skills like stocks, each with a trend line → (2) a "portfolio risk" meter (how much of their skill set AI could replace) → (3) roles that strengthen the portfolio → (4) course plan = "rebalancing" toward growing, safer skills, tagged to SDGs.
- **Wow moment:** Add a course to the plan → the risk meter drops live.
- **Build:** history over time, e.g. Hacker News "Who is hiring" monthly threads (free API, back to 2011) + any Malaysian source we find; per-skill growth (return) and swing (risk); slow vs fast AI = two "market conditions".
- **Extra work:** medium (time-series data). **Risk:** data is tech-heavy and global; the stock metaphor must feel serious.

### Idea 4 — Robust Path *(working name: AllWeather Careers)*
- **Pitch:** "We don't predict the future. We find the path that wins in most futures."
- **Who:** Grads / career switchers making a big, hard-to-undo choice.
- **User sees:** (1) profile tested against 3–4 futures (slow AI, fast AI, with/without green-economy push) → (2) roles ranked by how well they hold up across **all** futures → (3) badge "Holds up in 3 of 4 futures" → (4) course plan for the most robust role.
- **Wow moment:** A chart fanning out each role's outlook across the futures.
- **Build:** same engine run once per future; score each role on its worst / average case; each future's settings backed by a source (e.g. WEF reports).
- **Extra work:** low — and it can be added on top of any other idea. **Risk:** uncited future settings look made up.

### Idea 5 — Team Reskill Planner *(working name: LevyWise)*
- **Pitch:** "Every ringgit of your HRD Corp levy, spent on the skills your team will actually need."
- **Who:** HR / training managers planning next year's training budget. *(HRD Corp levy = the training fund Malaysian employers pay into and claim approved courses from.)*
- **User sees:** (1) uploads a made-up team skills sheet → (2) heatmap of the team's AI-exposed skills → (3) courses per person within budget → (4) click any employee for their plan; company-wide SDG summary.
- **Wow moment:** Change the budget → the plan re-optimises instantly.
- **Build:** same engine per employee, combined into a heatmap; simple optimiser for "future-readiness per ringgit".
- **Extra work:** high. **Risk:** must be about reskilling, never ranking people to fire; less personal demo.

### Idea 6 — Green Pivot *(working name: GreenPivot)*
- **Pitch:** "Find the future job where your skills do the most good."
- **Who:** Grads and career switchers who want meaningful work; Malaysia's energy-transition plan (NETR) is creating green jobs.
- **User sees:** (1) picks the SDGs they care about → (2) the "green skills" they already have → (3) roles ranked by fit × future demand × SDG impact → (4) course plan toward the top role.
- **Wow moment:** Change which SDGs you care about → the ranking reshuffles.
- **Build:** ESCO (free EU skills database that labels "green" and "digital" skills) + a role→SDG table with a cited reason for every link; SDG weights in the ranking.
- **Extra work:** low–medium (mostly research + citations). **Risk:** SDG scores look like opinion unless cited.

### Quick comparison *(judgement calls, not measurements)*

| Idea | Original | Doable in 5 days | Demo wow | Extra work |
|---|---|---|---|---|
| 1 Pivot Compass | ★★ | ★★★ | ★★ | — |
| 2 Task X-Ray | ★★★ | ★★ | ★★★ | Medium |
| 3 Skill Portfolio | ★★★ | ★★ | ★★★ | Medium |
| 4 Robust Path | ★★ (★★★ as add-on) | ★★★ | ★★ | Low |
| 5 Team Planner | ★★ | ★ | ★★ | High |
| 6 Green Pivot | ★★ | ★★★ | ★★ | Low–medium |

### Recommendation
- **Idea 2 (Task X-Ray)**, using Idea 4's "holds up in X of 4 futures" badge for the scenarios feature.
- **Backup:** Idea 3 (Skill Portfolio) for the most memorable pitch.
- **Save for Phase 2:** Ideas 5 and 6 are the "good-to-have" features — perfect upgrades if we're shortlisted.
- **Rule:** one user, one hook, one wow moment. Don't mix three ideas.

---

## 3. The pitch (template — swap in the chosen idea)

**30 seconds:**
> 56% of Malaysian professionals already use AI at work, but only 26% have had any formal training (Hays 2025), and MOSTI says 600,000+ workers need reskilling within 3–5 years. Workers like Aisyah hear "AI is coming" — but nobody tells them *what* to learn, or *for which job*. [Our app] watches public AI and job-market signals, forecasts which skills are rising or falling under different disruption scenarios, matches her to future roles she can actually reach, and gives her a step-by-step plan of free and HRD Corp-claimable courses — every number sourced and dated, every role linked to the SDGs. It doesn't decide for her. It shows her the evidence so she can.

**Three differentiators:**
1. **Living** — it re-forecasts when the data changes, and we show it live.
2. **Honest** — scenarios with ranges, dated citations, and a closed catalog so the AI can't invent jobs or courses.
3. **Purposeful** — the SDG link changes recommendations, not just labels.

**3-minute structure:**

| Time | Beat | Scores |
|---|---|---|
| 0:00–0:30 | Hook: Aisyah's story + the two stats | Clarity |
| 0:30–1:00 | Why existing tools fail (static lists, one-time tests, chatbots that invent jobs) | Innovation |
| 1:00–2:15 | Live demo, ending in the wow moment | Feasibility, Fit |
| 2:15–2:40 | Trust: dated sources, transparent scoring, what the AI does and doesn't do, hardest risk + fallback | Feasibility |
| 2:40–3:00 | Impact + Phase 2 roadmap. Close: *"AI shouldn't replace Aisyah. It should show her where to go next."* | Fit, Clarity |

---

## 4. Roles — one owner per lane

| Lane | Owner | Owns | Must-haves | Done by Fri 23 night |
|---|---|---|---|---|
| **A. Lead + Engine** | Jaiydaan | Coordination + final calls; skill forecast, match scoring, scenarios, AI guardrails | 3, 6, parts of 1 & 4 | Profile + trend data → ranked roles with explainable score, gaps, citations, under 2 scenarios |
| **B. Data & Trends** | _TBC at kickoff_ | Trend data pull + `refresh_trends.py`, dated snapshots, skills/role taxonomy, course catalog | 2, catalog for 4 | ≥1 live updatable source with URL + retrieval date; refresh writes a new dated snapshot |
| **C. App & Replit** | _TBC at kickoff_ | The Replit app: intake, radar, matches, pathway, scenario toggle, source/date badges; publishing | UI for 1–6 | A new user goes profile → matches → pathway in under 3 min on the published link |
| **D. Research, SDG & Pitch** | _TBC at kickoff_ | Persona research, SDG table (reason + source), 5 synthetic profiles, proposal, demo script, submission rules, timekeeping | 5, proposal for all 6 | Proposal within limits; SDG table complete; demo script rehearsed |

**If the team mix is different:** if everyone codes, D also builds the SDG view and a test harness. If only one person codes well, we use a single Streamlit app, B curates data in spreadsheets, and C does UX + demo + co-writes the proposal.

**How we work across lanes:**
- Each owner gets an **outcome, a done-definition and a deadline** — how you get there is your call.
- **Data contracts first (Tue):** we agree the JSON shapes so everyone can build in parallel on mock data — `Profile`, `Skill`, `TrendSignal {skill_id, source, source_url, retrieved_at, metric, value}`, `SkillForecast {skill_id, scenario, trajectory, score, range}`, `Role {skills[{id, weight}], sdgs[]}`, `Match {role_id, score, contributing[], gaps[], citations[]}`, `Course {url, hours, cost, hrdc_claimable}`, `PathwayStep`. They live in `/contracts/` with sample data.
- The engine (lane A) is the critical path, so D runs standups and timekeeping, and B backs up A if the engine slips.

---

## 5. Kickoff call — Tue 20 Oct (90 min)

Read section 2 before the call and come with your top 2 ideas and one reason each.

1. **Rubric read-through** (15 min) — we build to the rubric.
2. **Skills round** (10) — your strongest skill, hours you can give each day this week, any clashes (classes, exams). Confirm lane owners.
3. **Pick the idea** (30) — 2 min per idea, discuss, dot-vote; Jaiydaan breaks ties. Write the user, moment and pitch line as one sentence.
4. **Lock the demo slice** (10) — trend data → role matching, plus the wow moment.
5. **Stack + Replit** (15) — see section 6; decide who owns the main Replit app.
6. **First tasks** (10) — standup time, board, each owner says their Wednesday deliverable.

**How we decide:** small, reversible calls — the lane owner decides alone. Big, cross-lane calls (idea, stack, data contracts) — 10-minute timebox, then Jaiydaan decides and we all commit. Decisions go in `DECISIONS.md`.

---

## 6. Replit guide

Replit's free-plan limits are unclear (its pricing page doesn't list the free tier, and guides disagree on collaborators, publishing and scheduled jobs), so we use a setup that **works on any plan**.

1. **Setup (Tue):** create the public GitHub repo first → in Replit, **Import from GitHub** (Python template). Commit the Replit config so anyone can press **Run**. Ask organisers on Discord: what exactly "Replit compulsory" requires, whether there are credits, and the submission link format.
2. **GitHub is where the code lives; Replit is where it runs.**
   - If the owner has a paid plan or credits, invite teammates into the Replit app for live pairing.
   - Either way: work on your own branch (own Replit import or locally) → push → pull request → merge to `main`. The main Replit app pulls `main` and runs the demo.
   - Always pull before you push. Never two people editing the same file at once.
   - Use Replit's Git pane for commit / push, with a GitHub personal access token (not your password).
3. **Replit Agent — use it, but fence it:**
   - Good for: building screens from the `/contracts` JSON, boilerplate, deploy config, quick fixes. Use checkpoints to roll back.
   - **Never** let it generate data (jobs, courses, stats) — that breaks the "no invented" rule. Scoring logic stays hand-written and explainable.
   - Agent usage is limited on free plans — ration it to lane C and review every change before merging.
4. **Secrets:** API keys go in Replit **Secrets**, never in code. `.env` goes in `.gitignore`.
5. **Refreshing trend data:** `refresh_trends.py` (run from Shell or a "Refresh data" button) writes `data/snapshots/YYYY-MM-DD.json`; the app always shows the snapshot date. Scheduled jobs look paid-only, so they're roadmap, not something we depend on.
6. **Storage:** CSV / JSON (or SQLite) in the repo — works on any plan, and judges can inspect it.
7. **Stack:** Python for data + engine. UI in **Streamlit** (fastest, one app) unless lane C is fluent in React.
8. **Publish by Fri 23** and test on a phone. Backups: the dev URL while the app runs, plus screenshots and a screen recording in the repo.
9. **Disclose** the LLM we use in the product, and that Replit Agent helped build it, in the README and proposal.

---

## 7. Day-by-day sprint

| Day | A — Lead / Engine | B — Data | C — App / Replit | D — Research / Pitch | Checkpoint |
|---|---|---|---|---|---|
| **Tue 20** | Send ideas; run kickoff; draft data contracts | Shortlist sources for chosen idea | GitHub + Replit set up, Run works | Submission guide + Replit rules from Discord; persona one-liner | Decisions logged; contracts committed by midnight |
| **Wed 21** | Scoring on mock data → first real snapshot | 1 live source → dated snapshot; taxonomy + course CSV | 4 screens on mock data | 5 synthetic profiles; SDG table v1; proposal outline | Engine runs on real data |
| **Thu 22** | Match + gaps; 2 scenarios; AI parsing + guardrail | Refresh script | Wire screens to engine; scenario toggle; source/date badges | Proposal v1; SDG table final | **9 pm: whole journey works end to end (rough is fine)** |
| **Fri 23** | Pathway ordering; citations; tune on 5 profiles | 2nd source if time; backup snapshots | SDG view; publish; phone test; README | Proposal v2 reviewed by all; demo script v1 | Wow moment works; **night: FEATURE FREEZE** |
| **Sat 24** | Bug fixes only | Bug fixes only | Screenshots + recording | Rehearse ×2; outsider test; final checklist | **Submit by 9 pm** |
| **Sun 25** | Buffer only — deadline 08:00 | | | | |

---

## 8. Working rhythm

- **Daily 15-min standup** at a fixed time (e.g. 9 pm) + a short morning note in the group chat: *done / next / blocked*. Blockers get solved after standup by the people involved.
- **One source of truth:** GitHub repo + Project board (one issue per task, with owner + due date), `DECISIONS.md`, proposal in a shared doc.
- From Wed night, `main` must always be demo-able. Small pull requests; one teammate glances before merge.

---

## 9. Risks & fallbacks (these go in the proposal — judges score it)

| Risk | Fallback |
|---|---|
| Trend source unreliable or down during the demo | Dated snapshots in the repo; app shows "snapshot of <date>"; wow moment can switch between two stored snapshots |
| AI invents jobs, courses or stats | Closed catalog + ID check; AI never outputs entities itself; scoring is a transparent formula |
| Match scores look arbitrary | Show each skill's contribution; test on 5 synthetic profiles with expected results |
| Replit plan limits | GitHub-first workflow; dev-URL fallback; screen recording in repo |
| Scope creep / lead overloaded | Demo slice locked at kickoff; extras wait for Phase 2; B backs up A |
| Bias in recommendations | Profile never asks age or gender; fairness check on the roadmap |

---

## 10. Submission checklist (owner: D, Sat 24)

- [ ] Format and length limits from the submission guide met
- [ ] Problem → approach → outcome; user + what they walk away with in one line
- [ ] All 6 must-haves explained; "humans stay in charge" stated
- [ ] Hardest risk named, with fallback
- [ ] LLM disclosed (and Replit Agent use); data sources listed with dates; only public / synthetic data
- [ ] Public GitHub link; repo matches the demo; README with "Run on Replit" steps
- [ ] Replit app link works from a phone; screen recording as backup
- [ ] Submitted before Sat 24, 9 pm

---

### Still to confirm
- Lane owners B, C, D (kickoff)
- Submission guide: proposal format / length, demo video, where to submit (D, from Discord)
- What "Replit compulsory" exactly means, and whether credits are provided (D, from Discord)
- Data source access and licences for the chosen idea (B, Wed)
