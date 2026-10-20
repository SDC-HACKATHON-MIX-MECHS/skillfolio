# SkillFolio — Build Spec

**Version:** v1 · 20 Oct 2026 · **Owner:** Jaiydaan (lane A) · **Status:** agreed direction (Idea 3), build in progress
**Deadline:** internal Sat 24 Oct 9 pm · hard Sun 25 Oct 08:00

> **Your skills are a portfolio. AI is the market.**

This document is the single source of truth for *what* we build. [TASKS.md](TASKS.md) says *who builds what, by when*. [../contracts/](../contracts/) defines the data shapes everyone builds against.

---

## 0. TL;DR — what exists by Saturday

A Streamlit web app on Replit where a fresh grad or early-career switcher:

1. **Enters their skills** (pick from a list, or paste CV text), their learning-hour budget and the SDGs they care about.
2. **Sees the Skill Market** — every skill as a "stock" with a demand trend built from real, dated job postings, its momentum, volatility and AI exposure, under two AI-disruption scenarios.
3. **Sees their portfolio** — expected growth, AI exposure, diversification, plotted against future roles on a risk/return chart.
4. **Gets matched** to future roles (the "funds") with an explainable match %, skill gaps and SDG tags.
5. **Gets a rebalancing plan** — courses in order, within their hour budget, that most improve their position per hour.

**The two wow moments:**
- Click **Apply plan** → their dot moves up-and-left on the chart, the AI-exposure gauge drops.
- Click **Refresh data** → a new dated snapshot loads and the skill tickers update.

**The single most important feature (what judges must see working live):** trend data → skill forecasts → role matching.

---

## 1. Problem, user and moment

**Problem (from the brief):** 56% of Malaysian professionals use AI at work but only 26% have had formal training (Hays Asia Salary Guide 2025); MOSTI says 600,000+ workers need reskilling within 3–5 years. Learning advice is static and out of date by the time it's published.

**User (synthetic persona for the demo):**
> **Aina, 23**, fresh business-analytics graduate in Kuala Lumpur. She has ~200 learning hours this year and a small budget. She knows Excel, some SQL and a little Python. Everyone tells her "learn AI", but nobody can tell her *which* skills are worth her hours, or which roles she could realistically reach.

Second persona: **Ravi, 27**, customer-service executive switching into tech.

**Moment of need:** the months after graduating (or deciding to switch), when she must choose where to invest limited learning time.

**She walks away with:** a ranked list of reachable future roles with explainable scores, an ordered course plan that fits her hours, and a clear view of how exposed her skill set is to AI — every number with a source and a date.

**Human in charge:** SkillFolio shows evidence and estimates. It never tells her what to do, never hires or rejects anyone, and labels every forecast as an estimate.

---

## 2. The model — finance ↔ career

| Finance | SkillFolio | How it's computed |
|---|---|---|
| Share price history | **Demand index** for a skill | Monthly share of HN "Who is hiring" posts that mention the skill, rebased to 100 |
| Expected return | **Momentum** | Annualised trend of the last 12 months (log-linear fit), with an 80% interval |
| Volatility | **Demand swing** | Annualised std dev of month-on-month log change, last 24 months |
| Market beta | **AI exposure** (0–1) | Anthropic Economic Index `observed_exposure` of the occupations that use the skill |
| Market regime / stress test | **Scenario** | Moderate vs Fast AI disruption shifts projected returns by exposure |
| Fund / ETF | **Future role** | A weighted bundle of skills (from O*NET In-Demand / Hot Technology flags) |
| Portfolio | **The user's skills** | Weights from self-rated level 1–3 |
| Risk tolerance | **Risk slider** | How much demand swing the user is willing to accept |
| Rebalancing | **Reskilling plan** | Greedy: best score gain per learning hour, within the hour budget |
| ESG screen | **SDG lens** | Roles tagged to SDGs with cited reasons; chosen SDGs tilt the ranking |

**How to read AI exposure (say this in the pitch):** exposure measures how much of an occupation's work already shows up in real AI usage. High exposure means the work is **changing fastest** — tasks are being automated *or* augmented — not that the job disappears. Like a stock's beta, it's sensitivity to the AI market, not a verdict. *(Lane B: confirm the exact definition from Anthropic's labour-market report and quote it on the Methodology page.)*

---

## 3. Data sources (all verified reachable on 20 Oct 2026)

| ID | Source | Access | What we use | Volume / freshness | Licence |
|---|---|---|---|---|---|
| `hn_whoishiring` | Hacker News "Ask HN: Who is hiring? (Month YYYY)" threads | HN Algolia API, no key: `https://hn.algolia.com/api/v1` | Top-level comments = one job post each | ~230–270 posts/month in Aug–Oct 2026; one thread per month for years; current month grows daily | Public API |
| `aei_job_exposure` | Anthropic Economic Index — `labor_market_impacts/job_exposure.csv` | `https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/labor_market_impacts/job_exposure.csv` | `occ_code` (6-digit SOC, e.g. `15-2051`), `title`, `observed_exposure` | 756 occupations; dated releases (latest 2026-06-26) | CC-BY |
| `onet_tech` | O*NET 31.0 **Technology Skills** (inside the database zip) | `https://www.onetcenter.org/dl_files/database/db_31_0_csv.zip` (also `_excel`, `_text`) | `O*NET-SOC Code`, `Example`, `Hot Technology` (Y/N), `In Demand` (Y/N) | ~33k rows; flags derived from employer job postings | CC BY 4.0 |
| `my_lfs` | Malaysia Labour Force Survey, quarterly | `https://api.data.gov.my/data-catalogue/?id=lfs_qtr` | Latest labour force, unemployment rate (context panel only) | Quarterly since 2010 | Open data |

**API recipes (lane B):**
- List hiring threads: `GET /search_by_date?tags=story,author_whoishiring&query="who is hiring"&hitsPerPage=50` → keep titles matching `^Ask HN: Who is hiring\? \((\w+) (\d{4})\)$`.
- Get one thread with all posts: `GET /items/{story_id}` → `children[]` are the top-level posts (`id`, `created_at`, `text` as HTML). Skip children with empty `text` (deleted).
- Be polite: ≤1 request/second, cache raw months in `data/raw/hn/` (git-ignored), always re-fetch the **current** month (it keeps growing).

**Window:** the last **25 months** (e.g. Oct 2024 → Oct 2026) ≈ 6,000 posts.

**Known limit (state it in the proposal):** HN postings are global and tech-heavy, so SkillFolio targets grads moving into tech and data roles. Malaysian occupation-level data (OpenDOSM, TalentCorp MyCOL) is a Phase 2 upgrade.

---

## 4. Data pipeline (lane B)

```
fetch_hn.py ─► data/raw/hn/YYYY-MM.json ─► extract_skills.py ─┐
download job_exposure.csv + O*NET zip ─► load_exposure.py ─────┼─► build_snapshot.py ─► data/snapshots/YYYY-MM-DD.json
                                                               │                       └─► data/snapshots/latest.json
data/skills.csv (canonical skills + aliases) ──────────────────┘
```

1. **`pipeline/fetch_hn.py`** — finds the last 25 monthly threads, downloads each with `/items/{id}`, writes `data/raw/hn/YYYY-MM.json` = `{story_id, month, url, retrieved_at, posts:[{id, created_at, text}]}`.
2. **`pipeline/extract_skills.py`** — cleans HTML (`html.unescape`, strip tags), then for every skill in `data/skills.csv` checks if **any alias** appears (word-boundary regex; case-insensitive unless the alias starts with `cs:`). Counts **posts**, not mentions (a post mentioning Python 5 times counts once). `count_month` returns `{total_posts, counts: {skill_id: n}}`; `build_snapshot.py` turns these into `counts[]` and `shares[] = counts / total_posts` per skill.
   - Ambiguous aliases must be case-sensitive or context-anchored: `Go`, `R`, `Spark`, `SAP`, `Swift`, `Rails`, `Excel`, `grid`, `battery`, `payments`, `analytics`, `embedded`. Lane B keeps a test file with ~15 hand-labelled posts.
3. **`pipeline/load_exposure.py`** — joins skill → occupations → exposure:
   - Each skill row in `skills.csv` lists `onet_examples` (exact O*NET `Example` names, `|`-separated).
   - Find every O*NET occupation whose Technology Skills include one of those examples; take the first 7 chars of the O*NET-SOC code (`15-1252.00` → `15-1252`) and look up `observed_exposure`.
   - `skill.exposure` = mean over those occupations; record `exposure_n_occupations`. If a skill has no O*NET example (e.g. "Customer success"), use `proxy_soc_codes` from `skills.csv` instead and set `exposure_method = "proxy"`.
   - Also emits `data/role_skills.generated.csv`: for each role's SOC code, the O*NET tech skills flagged In Demand (weight 3) or Hot (weight 2) that map to our skills. Lane A/D curate this into `data/role_skills.csv` (≤10 skills per role).
4. **`pipeline/build_snapshot.py`** — writes the snapshot (shape in [contracts](../contracts/README.md#snapshot)), stamps `retrieved_at` (UTC ISO), lists every source with URL + licence + retrieval time, and copies it to `latest.json`.
5. **Refresh** — `python -m pipeline.build_snapshot --refresh-current` re-downloads only the current month and rebuilds. The app's **Refresh data** button calls the same function.

**Rule:** snapshots are committed to git (they're small); raw downloads are not.

---

## 5. Engine (lane A)

All tunable numbers live in `engine/config.py` and are shown on the Methodology page as **assumptions**.

### 5.1 Skill forecast (`engine/forecast.py`)

For each skill, monthly shares `s_1 … s_M` (M = 25 in a full snapshot), oldest first:

| Quantity | Exact rule | Notes |
|---|---|---|
| ε (epsilon) | `ε = EPSILON_POSTS / (average total_posts per month across the snapshot)`, `EPSILON_POSTS = 0.5` (in `config.py`); if the average is 0 or there are no months, `ε = EPSILON_POSTS` | half a post. **One constant for every month and skill**, so a skill that is never mentioned shows no trend even when monthly threads grow or shrink |
| Smoothed share | `ŝ_m` = trailing mean of the last 3 months of `s`; months 1 and 2 use the 1 or 2 months available | reduces month-to-month noise |
| Demand index | `I_m = 100 × ŝ_m / ŝ_base`, where `ŝ_base` = the first non-zero `ŝ`; months before it are 0; all-zero → all 0 | the sparkline. A skill that appears late can reach large index values — the app should cap the axis |
| Momentum `r` | OLS of `ln(ŝ_m + ε)` on month index over the last `n = min(12, M)` months → slope `b`, standard error `SE_b`; `r = e^(12b) − 1` | annual % change. Needs `n ≥ 3` |
| 80% interval | `r_low, r_high = e^(12(b ∓ 1.28·SE_b)) − 1`, where `SE_b = √(RSS / (n − 2)) / √Σ(x − x̄)²` — **n − 2 degrees of freedom**, n = months in the fit (so n ≥ 3) | shown as a band |
| Volatility `v` | sample std dev (divide by count − 1) of the month-on-month changes in `ln(ŝ_m + ε)` over the last 24 smoothed months (23 changes), × √12 | annualised; 0 when fewer than 2 changes |
| History | `history_months = M` | |
| Too little history | `history_months < 3` → `r = r_low = r_high = 0` **and** the scenario shift is 0, so `projected = projected_low = projected_high = 0`; `thin_data = true` | placeholders, not a forecast |
| Thin data flag | `history_months < 3` **or** the skill's mean posts per month (its `counts`, over **all** months, empty ones included) < 3 | **label is always Stable**; app (lane C) greys the row and shows a "low data" badge |

**Scenarios** (`config.SCENARIOS`):
```
projected r_s = r − λ_s × (e − ē)        # e = skill AI exposure; ē = average exposure of skills whose exposure is known
λ_moderate = 0.10    λ_fast = 0.30        # starting values — assumptions, displayed
```
Centring on `ē` means the scenario re-ranks skills (more exposed → lower, less exposed → higher) rather than shifting everything down. The interval (`r_s_low`, `r_s_high`) shifts by the same amount. A skill with **unknown** exposure (`null`) gets no shift and is left out of `ē`.

**Trajectory label** (per scenario): **Stable** if the skill is thin data · else **Rising** if `r_s_low > +5%` · **Declining** if `r_s_high < −5%` · else **Stable** (exactly ±5% is Stable). Every label carries an "estimate" tag.

**What the scenario may and may not do:** for skills with enough data, the scenario shift is an *assumption on purpose* and can move a label (its λ values are shown on the Methodology page). It can never create a label for a thin-data skill — a skill with too little history or almost no posts is always Stable, so we don't headline a number we can't trust. A thin skill with enough months still shows its (greyed) projected number, including the shift.

**Honest caveat (put on the Methodology page):** fitting a trend to a rolling average makes neighbouring months move together, so the 80% band is somewhat narrower than a strict statistical calculation would give. Treat it as indicative, not exact.

### 5.2 Portfolio (`engine/portfolio.py`)

User skills with levels `L_i ∈ {1,2,3}` → weights `w_i = L_i / ΣL`.

| Metric | Formula | Shown as |
|---|---|---|
| Expected growth `R` | `Σ w_i · r_s,i` | % per year (scenario-dependent) |
| AI exposure `E` | `Σ w_i · e_i` | gauge 0–100 |
| Volatility `σ_p` | `√(wᵀ Σ w)`, `Σ` = annualised (×12) **sample** covariance (divide by the number of changes − 1) of the monthly changes `Δ ln(ŝ + ε)` over the last 24 smoothed months — the same ε and window as §5.1 volatility, so a one-skill portfolio has `σ_p = v` — shrunk 50% toward its diagonal | % |
| Diversification `D` | `1 − Σ w_i²` | 0–100 |
| **Readiness** `U` | `R − (γ/2)·σ_p²` | headline score; `γ` from the risk slider (low 6 · medium 3 · high 1 — lane A tunes so neither term dominates on the sample profiles) |

### 5.3 Role matching (`engine/matching.py`)

A role is a bundle of skills `j` with importance weight `w_j ∈ {1,2,3}` and required level `req_j ∈ {1,2,3}` (`data/role_skills.csv`).

| Quantity | Formula |
|---|---|
| Match % `M` | `Σ_j w_j · min(L_j / req_j, 1) / Σ_j w_j` (with `L_j = 0` if the user lacks the skill) |
| Gaps | skills where `L_j < req_j`, sorted by `w_j` (high → low), then `req_j` (high → low) |
| Role growth `R_role` | `Σ_j ŵ_j · r_s,j` (normalised weights) |
| Role AI exposure | the role's own `ai_exposure` from `roles.csv` (direct SOC lookup) |
| SDG overlap `O` | `|role SDGs ∩ user SDGs| / max(1, |user SDGs|)` |
| **Rank score** | `M × (1 + R_role) × (1 + α·O)`, `α = 0.15` |

Every match returns its **contributions** (which skills earned credit, how much), **gaps**, and **citations** (snapshot date + source IDs). The UI shows the breakdown — no black box.

### 5.4 Reskilling plan (`engine/pathway.py`)

- Target role = the user's pick (default: top-ranked).
- Candidates = courses in `data/courses.csv` that teach a gap skill (`skill_id`), raising it to `level_out`.
- **Greedy loop:** while hours remain, pick the course with the highest `(ΔU + β·ΔM) / hours` among courses that fit the remaining hours and whose prerequisite (`prereq_skill_id`, `prereq_level`) is met; apply it; repeat. `β = 1.0`.
- Output: ordered steps (course, skill, hours, cost, link, HRD Corp flag, cumulative hours) and **before/after** for `M`, `R`, `E`, `σ_p`, `D`, `U`.
- Never recommends a course that isn't in `courses.csv`.

### 5.5 SDG lens (`engine/sdg.py`)

- Each **role** has ≥1 SDG in `roles.csv`, with a one-line reason and a source URL (lane D).
- Each **skill** gets SDG **4 (target 4.4 — relevant skills for decent jobs)** as a baseline, plus the SDGs of every role that weights it ≥2.
- **Impact allocation:** share of the user's portfolio weight linked to each SDG → donut chart, before and after the plan.
- The user's chosen SDGs tilt the ranking via `α` (5.3), so the SDG link **changes choices**, not just labels.

### 5.6 Guardrails (`engine/guardrails.py`)

- Every skill / role / course ID that reaches the UI must exist in our CSVs; unknown IDs are dropped and logged.
- Every number on screen carries its source ID and snapshot date.
- Profiles have **no** age, gender, race or name-based fields used in scoring.
- Optional LLM (Phase 2 or if time allows): may only map CV text → skill IDs from `skills.csv` and phrase explanations from engine output. **Default without LLM:** CV text is matched with the same alias rules as the pipeline.

---

## 6. Screens (lane C, Streamlit multipage)

| Page | Must show | Must-haves covered |
|---|---|---|
| **Home** | One-line pitch, how it works in 3 steps, data freshness badge (snapshot date), Malaysian labour context card (`my_lfs`, with date) | 2 |
| **1 · Profile** | Skill picker with level 1–3 · or paste CV text → detected skills to confirm · hour budget · risk slider · SDG picker · "Load sample: Aina / Ravi" | 1 |
| **2 · Skill Market** | Ticker table: ticker, skill, sparkline (demand index + band), momentum, volatility, AI exposure, trajectory label. Scenario toggle (sidebar, global). **Refresh data** button. Source + date under the table | 2, 6 |
| **3 · My Portfolio** | Growth, AI-exposure gauge, volatility, diversification, Readiness. **Risk/return chart:** x = AI exposure, y = growth; roles as bubbles (size = match %), user as a highlighted dot | 3, 6 |
| **4 · Matches** | Top 5 roles: match %, rank-score breakdown, contributing skills, gaps, AI exposure, SDG badges with reasons + links, citations | 3, 5 |
| **5 · Rebalance Plan** | Target-role picker, ordered course list (hours, cost RM, link, HRD Corp flag, cumulative hours), before/after metrics, **Apply plan** → dot moves on the chart, gauge drops, SDG donut updates | 4, 5 |
| **Methodology** | Sources with URLs, licences and dates; formulas in plain English; assumption values from `config.py`; limits (HN is global/tech-heavy); AI disclosure; "estimates, not predictions" | all |

**Global rules:** scenario toggle in the sidebar affects every page · every chart has a caption `Source: … · retrieved YYYY-MM-DD` · forecasts labelled "estimate" · works on a phone (Streamlit default layout, no wide tables without scroll).

---

## 7. Must-have coverage

| # | Must-have | Where it lives |
|---|---|---|
| 1 | Skills profile intake | Profile page: picker + CV text matching (+ optional LLM) |
| 2 | AI-trend signal layer (updatable, source + date) | HN Algolia pipeline → dated snapshots; Refresh button; source captions |
| 3 | Future-role matching (explainable score + gap) | `matching.py`; Matches page breakdown |
| 4 | Personalised reskilling pathway (ordered, timed, free/low-cost) | `pathway.py`; Rebalance Plan page; `courses.csv` with hours, cost, HRD Corp flag |
| 5 | SDG mapping (role + skill, user contribution) | `roles.csv` SDG columns; `sdg.py`; badges + impact donut; SDG tilt in ranking |
| 6 | Handling uncertainty (≥2 scenarios, estimates) | Moderate/Fast toggle; 80% intervals; thin-data flags; "estimate" labels |

---

## 8. Demo script (≈2 min of the 3-min pitch)

1. **Home** (10 s) — "This is Aina. 200 hours. Which skills are worth them?" Point at the snapshot date.
2. **Profile** (10 s) — load sample Aina.
3. **Skill Market** (25 s) — rising vs declining skills from real postings; flip **Moderate → Fast AI**: exposed skills drop, others rise. Point at the source line.
4. **Portfolio** (20 s) — her dot vs the role "funds"; AI-exposure gauge.
5. **Matches** (25 s) — top role, open the breakdown: what counts, what's missing, SDG reason.
6. **Rebalance Plan** (20 s) — 190 hours of courses; **Apply plan** → dot moves up-left, gauge drops. *(wow)*
7. **Refresh data** (10 s) — new timestamp, tickers update. "It keeps learning as AI moves."

Backup: if live refresh fails, the snapshot dropdown switches between two committed snapshots.

---

## 9. Out of scope for the preliminary round (Phase 2 upgrades)

HR / team heatmap · Bahasa Malaysia + Chinese UI · Malaysian occupation data (OpenDOSM, MyCOL) · scheduled automatic refresh · fairness audit report · progress tracking and badges · LLM explanations.

---

## 10. Risks and fallbacks

| Risk | Fallback |
|---|---|
| HN API slow or down during demo | Committed snapshots; snapshot dropdown; app never calls the API on page load |
| Alias matching miscounts skills | Hand-labelled test posts; ambiguous aliases case-sensitive; thin-data flag |
| Scenario parameters look arbitrary | Shown openly as assumptions on Methodology; centred so they only re-rank; D cites the reasoning |
| Exposure misread as "job loss" | Plain-English definition on every exposure tooltip |
| Courses invented | Only rows with a fetched, working URL and `verified_on` date |
| Replit limits | Plain Streamlit, no paid features; screen recording in repo |

---

## 11. Definition of done (Sat 24 Oct, 9 pm)

- [ ] Live HN data → snapshot with today's date, committed
- [ ] All 7 pages work for both sample profiles, on desktop and phone
- [ ] Scenario toggle visibly changes Skill Market, Portfolio and Matches
- [ ] Apply plan moves the dot and drops the gauge
- [ ] Every number has a source + date; every role and skill has ≥1 SDG with a reason
- [ ] `pytest` green; repo public; README run steps work on a fresh Replit import
- [ ] Proposal covers all 6 must-haves, the hardest risk and its fallback
