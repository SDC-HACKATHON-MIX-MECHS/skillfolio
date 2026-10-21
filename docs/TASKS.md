# SkillFolio — What each of us builds

Read [SPEC.md](SPEC.md) first (15 min). This page says **who builds what, by when, and how we know it's done**.

**Deadlines:** whole journey works end to end **Thu 22, 9 pm** · feature freeze **Fri 23 night** · submit **Sat 24, 9 pm** (hard deadline Sun 25, 08:00).

| Lane | Owner | You own these files | You hand over |
|---|---|---|---|
| **A — Engine** | @Curryraj (Jaiydaan) | `engine/forecast.py` `portfolio.py` `matching.py` `pathway.py` `sdg.py` `config.py` `guardrails.py` `data.py` | SkillForecast, PortfolioMetrics, Match, PlanResult dicts |
| **B — Data & Trends** | _assign_ | `pipeline/*` · `data/skills.csv` · `data/snapshots/` | dated snapshot JSON, `role_skills.generated.csv` |
| **C — App & Replit** | _assign_ | `app/*` · `.replit` | the working app on a public Replit link |
| **D — Research, SDG & Pitch** | _assign_ | `data/roles.csv` (SDG columns) · `data/courses.csv` · `data/profiles/` · proposal · demo script | proposal, demo, verified SDG + course data |

Everyone builds against [`contracts/`](../contracts/README.md). **Until the real thing exists, use the example fixture** (`contracts/examples/`): the app already falls back to it and shows an "EXAMPLE DATA" banner. Nobody waits for anybody.

---

## Everyone — first 30 minutes

1. Accept the GitHub org invite / open https://github.com/SDC-HACKATHON-MIX-MECHS/skillfolio (you have **Write** access).
2. **Replit:** Create App → Import from GitHub → `SDC-HACKATHON-MIX-MECHS/skillfolio`. If Replit asks for org access, ping Jaiydaan to approve it (Org → Settings → Third-party access). Press **Run** — you should see the SkillFolio home page with the "EXAMPLE DATA" banner.
3. **Or locally:** install [uv](https://docs.astral.sh/uv/), then
   ```
   uv sync
   uv run pytest
   uv run streamlit run app/Home.py
   ```
4. Make a branch for your lane: `git checkout -b data/hn-fetch` (or `engine/…`, `app/…`, `pitch/…`).
5. Run `pytest`. Today you'll see `xfailed` tests — those are **your acceptance tests**. When your code works they show as `XPASS`: **then delete the `@todo` marker** on those tests so they count as real passes (and fail loudly if you break them later). Wrong code shows as a normal failure straight away.

**Rules:** pull before you start · small commits · PR into `main` · never commit keys · **never put a number, course or role in the repo without a source URL**.

---

## Lane A — Engine (Jaiydaan)

**Mission:** turn a snapshot + a profile into forecasts, portfolio metrics, ranked roles and a plan — every number explainable.

| When | Task | Done when |
|---|---|---|
| Tue | Data contracts agreed (this repo) ✅ | contracts/README.md committed |
| Wed | `forecast.py` on the example fixture | `tests/test_engine_spec.py` forecast tests pass |
| Wed | `portfolio.py` (weights, covariance, metrics) — **write the missing tests** for covariance and metrics (hand-checked 2-skill portfolio) | weights test + your new tests pass; Aina's metrics look sane on the real snapshot. **Watch:** `R = Σw·projected` must not let one thin-data skill with a huge projected growth dominate (exclude or cap thin skills), and recalibrate γ now that projected growth spreads over about −45% … +120% (SPEC 5.1) |
| Thu | Tests for `rank_roles`, `impact_allocation`, pathway prerequisites and `guardrails.keep_known` | new tests pass |
| Thu | `matching.py` + curate `role_skills.csv` with D (≤10 skills per role, from B's generated file) | match test passes; Aina's top 5 makes sense to the team |
| Thu | `sdg.py` | SDG test passes; every skill has ≥1 SDG |
| Thu 9 pm | **Integration checkpoint** with C | all pages show real engine output |
| Fri | `pathway.py`; tune α so neither term dominates on Aina and Ravi (λ is tuned: 0.5 / 1.5, SPEC 5.1; γ is tuned: 0.75 / 0.375 / 0.125, SPEC 5.2, re-check it if the forecast changes) | plan test passes; Apply plan visibly moves Aina's dot |
| Fri | Write the plain-English formula text for Methodology (with D) | page reviewed by the team |

## Lane B — Data & Trends

**Mission:** real, dated, refreshable demand data for every skill, plus AI exposure.

| When | Task | Done when |
|---|---|---|
| Wed AM | `fetch_hn.py`: list the last 25 threads, download posts, cache raw months | `data/raw/hn/` has 25 files; current month always re-fetched |
| Wed | `extract_skills.py`: HTML cleaning + alias matcher | `tests/test_extract_skills_spec.py` passes — including **"Go to our careers page" must NOT count as Go** (refine the `golang` alias) |
| Wed | Fill `onet_examples` in `skills.csv` from the O*NET 31.0 Technology Skills file (exact `Example` names) | every tech skill has ≥1 example or a `proxy_soc_codes` value |
| Wed PM | `load_exposure.py` + `build_snapshot.py` → **first real snapshot committed** | `data/snapshots/2026-10-2X.json` with `retrieved_at`, sources, 25 months |
| Thu | `role_skills.generated.csv` for A + D | file committed |
| Thu | `--refresh-current` + the function the app's Refresh button calls | re-running changes `retrieved_at` and the current month's counts |
| Thu | Add ~10 real hand-labelled posts to the extractor tests | ≥15 cases pass |
| Fri | Second snapshot on a different day (demo fallback); confirm what `observed_exposure` means in Anthropic's report, send D the quote | two snapshots in `data/snapshots/` |

**Watch out:** ambiguous aliases (`Go`, `R`, `Spark`, `SAP`, `Swift`, `Rails`, `Excel`, `grid`, `battery`, `payments`, `analytics`, `embedded`) — case-sensitive or context-anchored (same list as SPEC §4). Be polite to the API (≤1 request/second). Also write tests for `fetch_hn`, `load_exposure` and `build_snapshot` (use a small saved API response, not the live API).

## Lane C — App & Replit

**Mission:** a clean, fast, phone-friendly Streamlit app that tells the story in 2 minutes.

| When | Task | Done when |
|---|---|---|
| Tue/Wed | Replit import works for everyone; `Run` serves the app | each teammate has opened it on Replit |
| Wed | Profile page (picker, CV paste using `pipeline.extract_skills.skills_in_text`, samples, session state) | loading Aina fills the form |
| Wed | Skill Market on the example fixture: ticker table + sparklines (Plotly), scenario toggle; grey out `thin_data` skills with a "low data" badge; cap the sparkline axis (late-appearing skills can have huge index values) | flipping the toggle changes the table; thin skills are visibly greyed |
| Thu | My Portfolio: metric cards, AI-exposure gauge, risk/return chart | Aina's dot + role bubbles render |
| Thu | Matches: top 5 with breakdown, gaps, SDG badges + links | each match shows its citations |
| Thu 9 pm | **Integration checkpoint** with A on the real snapshot | whole journey works end to end |
| Fri | Rebalance Plan + **Apply plan** animation (dot moves, gauge drops); Refresh button; snapshot dropdown | the wow moment works 3 times in a row |
| Fri | Methodology page; phone test; **publish on Replit** | public link opens on a phone |
| Sat | Screenshots + 2-min screen recording into `docs/demo/` | files committed |

**Rules:** every chart has `Source: … · retrieved YYYY-MM-DD` · forecasts say "estimate" · never call the API on page load (only on Refresh).

## Lane D — Research, SDG & Pitch

**Mission:** make every SDG link and course real and cited, and make the story land.

| When | Task | Done when |
|---|---|---|
| Tue | Read the submission guide on Discord: proposal format, length, demo video?, where to submit · ask what "Replit compulsory" requires | answers posted in the group chat |
| Wed | Check every row of `roles.csv`: SDGs, one-line reason, source URL (target-level link where possible) | team agrees on the SDG table |
| Wed–Thu | `courses.csv`: 2–3 real free/low-cost courses for each skill in the top roles' gaps — open every URL, record hours, cost, HRD Corp status (`unknown` unless you find a source), `verified_on` | `tests/test_data_integrity.py` passes; ≥30 courses |
| Thu | Proposal v1 — problem → approach → outcome; all 6 must-haves (SPEC §7); hardest risk + fallback (SPEC §10); AI disclosure | shared with the team |
| Fri | Proposal v2 after review · demo script from SPEC §8 · Methodology text with A | everyone has read it |
| Sat | Rehearse ×2 · outsider test (someone outside the team explains it back) · submission checklist in TEAM_PLAN.md · **submit by 9 pm** | submitted |

---

## Integration points (put these in your calendar)

| When | Who | What |
|---|---|---|
| Wed 9 pm standup | all | first real snapshot exists; app runs on Replit for everyone |
| **Thu 9 pm** | all | **whole journey works end to end on real data — rough is fine** |
| Fri night | all | feature freeze; only fixes after this |
| Sat afternoon | all | two rehearsals, then submit |

## How we know we're done

The checklist in [SPEC.md §11](SPEC.md#11-definition-of-done-sat-24-oct-9-pm), plus `uv run pytest` shows **no xfails left** and no failures.
