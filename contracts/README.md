# Data contracts

These are the shapes every lane builds against. **If you need to change one, say so in the group chat first** — someone else is probably reading it.

Files in [`examples/`](examples/) are **illustrative fixtures for development and tests only — not real data**. They use `example.org` links and made-up numbers so nobody mistakes them for real figures. The app must show an "EXAMPLE DATA" banner if it ever loads them.

Owner key: **A** engine · **B** data · **C** app · **D** research/pitch.

---

## CSV files in `data/`

### `skills.csv` — canonical skills (owner B)

| Column | Type | Example | Notes |
|---|---|---|---|
| `skill_id` | slug | `python` | stable ID used everywhere |
| `name` | text | `Python` | display name |
| `ticker` | 2–5 capital letters or digits | `PY`, `K8S` | unique; shown on the Skill Market |
| `category` | text | `language` | language, data, analytics, ai, cloud, devops, frontend, backend, database, security, design, product, business, hardware, green, domain, mobile, engineering |
| `aliases` | `\|`-separated | `python` | matched with word boundaries, case-insensitive; prefix `cs:` for case-sensitive (e.g. `cs:Go`) |
| `onet_examples` | `\|`-separated | `Python` | exact O*NET Technology Skills `Example` names (B fills from the O*NET file) |
| `proxy_soc_codes` | `\|`-separated | `43-4051` | only when no O*NET example fits; 6-digit SOC codes |

### `roles.csv` — future roles, the "funds" (owners A + D)

| Column | Type | Example | Notes |
|---|---|---|---|
| `role_id` | slug | `data_scientist` | |
| `title` | text | `Data Scientist` | |
| `role_type` | `future` \| `origin` | `future` | `origin` = typical starting jobs for switchers, shown for comparison |
| `soc_code` | 6-digit SOC | `15-2051` | must exist in `job_exposure.csv` |
| `onet_title` | text | `Data Scientists` | as in the source |
| `ai_exposure` | 0–1 | `0.4605` | `observed_exposure` from `aei_job_exposure` |
| `exposure_source` | source ID | `aei_job_exposure` | |
| `sdgs` | `\|`-separated ints | `9\|8` | ≥1 required |
| `sdg_rationale` | text | `Data science drives…` | one sentence, plain English |
| `sdg_source_url` | URL | `https://sdgs.un.org/goals/goal9` | D refines to target level where possible |
| `description` | text | | one line shown on Matches |

### `role_skills.csv` — what each role is made of (owners A + D, seeded by B)

| Column | Type | Example | Notes |
|---|---|---|---|
| `role_id` | slug | `data_scientist` | |
| `skill_id` | slug | `python` | must exist in `skills.csv` |
| `weight` | 1–3 | `3` | importance (3 = O*NET In Demand, 2 = Hot Technology, 1 = useful) |
| `required_level` | 1–3 | `2` | 1 basic · 2 working · 3 strong |
| `source` | text | `onet_in_demand` | `onet_in_demand` \| `onet_hot` \| `team` |

### `courses.csv` — the only courses SkillFolio may recommend (owner D)

| Column | Type | Example | Notes |
|---|---|---|---|
| `course_id` | slug | `sql_basics_x` | |
| `title` | text | | exactly as on the provider page |
| `provider` | text | | |
| `url` | URL | | must load; checked by D |
| `skill_id` | slug | `sql` | the skill it teaches |
| `level_out` | 1–3 | `2` | level reached after finishing |
| `hours` | number | `12` | provider's estimate |
| `cost_rm` | number | `0` | 0 = free (audit/free tier) |
| `hrdc_claimable` | `yes` \| `no` \| `unknown` | `unknown` | `yes` only with a source |
| `prereq_skill_id` | slug or empty | | |
| `prereq_level` | 1–3 or empty | | |
| `verified_on` | date | `2026-10-21` | when D last opened the URL |

---

## JSON shapes

### Profile — `data/profiles/*.json` (owner D; app creates the same shape)

```json
{
  "profile_id": "aina",
  "display_name": "Aina (synthetic)",
  "synthetic": true,
  "headline": "Fresh business-analytics graduate, Kuala Lumpur",
  "hours_budget": 200,
  "budget_rm": 300,
  "risk_tolerance": "medium",
  "sdg_interests": [8, 13],
  "skills": [{"skill_id": "excel", "level": 3}, {"skill_id": "sql", "level": 2}]
}
```
`risk_tolerance`: `low` | `medium` | `high`. Levels 1–3. No age, gender or other protected fields.

### Snapshot

File: `data/snapshots/YYYY-MM-DD.json` (owner B), copied to `latest.json`.

```json
{
  "snapshot_date": "2026-10-20",
  "retrieved_at": "2026-10-20T07:12:03Z",
  "sources": [
    {"id": "hn_whoishiring", "name": "Hacker News — Ask HN: Who is hiring?", "url": "https://hn.algolia.com/api/v1", "licence": "Public API", "retrieved_at": "2026-10-20T07:12:03Z"},
    {"id": "aei_job_exposure", "name": "Anthropic Economic Index — job_exposure.csv", "url": "https://huggingface.co/datasets/Anthropic/EconomicIndex", "licence": "CC-BY", "retrieved_at": "2026-10-20T07:10:41Z"},
    {"id": "onet_tech", "name": "O*NET 31.0 Technology Skills", "url": "https://www.onetcenter.org/database.html", "licence": "CC BY 4.0", "retrieved_at": "2026-10-20T07:11:02Z"}
  ],
  "months": [
    {"month": "2026-10", "story_id": 49922569, "url": "https://news.ycombinator.com/item?id=49922569", "total_posts": 266}
  ],
  "skills": {
    "python": {
      "counts": [61],
      "shares": [0.2293],
      "exposure": 0.31,
      "exposure_n_occupations": 42,
      "exposure_method": "onet_tech"
    }
  }
}
```
`months` is oldest → newest; `counts[i]` and `shares[i]` line up with `months[i]`. (The Oct 2026 thread and its 266 posts are real; the Python numbers above are illustrative.)

- `exposure` may be `null` when no O*NET example or proxy SOC code maps to the skill; `exposure_method` is `"onet_tech"`, `"proxy"` or `null`.
- Optional `is_example: true` marks a fixture; the app shows the "EXAMPLE DATA" banner when it's present. Real snapshots omit it.
- Optional `_note` is a free-text comment for humans; code ignores it.

### SkillForecast — engine output per skill per scenario (owner A)

```json
{
  "skill_id": "python", "scenario": "fast",
  "momentum": 0.12, "momentum_low": 0.03, "momentum_high": 0.22, "momentum_raw": 0.19,
  "volatility": 0.18, "exposure": 0.31,
  "projected": 0.115, "projected_low": 0.025, "projected_high": 0.215,
  "trajectory": "stable", "thin_data": false, "history_months": 25, "is_estimate": true,
  "index": [100, 103.2, 98.7]
}
```
- `momentum` (with `momentum_low` / `momentum_high`) is the **damped** yearly growth: noisy trends are pulled toward the all-skill average (SPEC 5.1). `momentum_raw` is the plain fitted trend, for transparency; the two are equal when there are fewer than 5 well-observed skills to estimate the average from. The scenario never changes `momentum`; it only changes `projected*` (`projected = (1 + momentum) × e^(−λ·(exposure − average exposure)) − 1`).
- `history_months` is the number of monthly values in the skill's series (`len(shares)`); `index` always has that many entries, whatever the history (the example above shortens `index` to 3 entries to keep it readable).
- `exposure` is a float, or `null` when unknown (then there's no scenario shift).
- `trajectory` is `"rising"`, `"stable"` or `"declining"`.
- When `history_months < 3`, `momentum`, `momentum_raw`, its interval, `volatility` and `projected` / `projected_low` / `projected_high` are all `0.0` placeholders, `trajectory` is `"stable"` and `thin_data` is `true` — show "low data", not a trend.
- `thin_data` is also `true` when the skill's mean posts per month (its `counts`, over all months, empty ones included) is below 3. Then `trajectory` is always `"stable"`, but the numbers are real and should be shown greyed.

### Match — engine output per role (owner A)

```json
{
  "role_id": "data_scientist", "title": "Data Scientist",
  "match_pct": 0.5, "role_growth": 0.09, "ai_exposure": 0.4605, "sdg_overlap": 0.5,
  "rank_score": 0.5859,
  "contributions": [{"skill_id": "sql", "weight": 3, "user_level": 2, "required_level": 2, "credit": 1.0}],
  "gaps": [{"skill_id": "ml", "weight": 3, "user_level": 0, "required_level": 2}],
  "sdgs": [9, 8],
  "citations": [{"source_id": "hn_whoishiring", "snapshot_date": "2026-10-20"}, {"source_id": "aei_job_exposure", "snapshot_date": "2026-10-20"}, {"source_id": "onet_tech", "snapshot_date": "2026-10-20"}]
}
```
`match_pct` = (3 × 1.0 + 3 × 0) / (3 + 3) = 0.5 · `rank_score` = 0.5 × (1 + 0.09) × (1 + 0.15 × 0.5) = 0.5859. `gaps` are sorted by `weight` (high → low), then `required_level` (high → low), then `skill_id`. `contributions` hold the skills with some credit, sorted by `weight`, then `credit` (high → low), then `skill_id`; a partly met skill is in both lists. `citations` are the demand data (`hn_whoishiring`), the role's exposure source, and one entry per distinct source in the role's skill rows (`onet_in_demand` / `onet_hot` appear as `onet_tech`; a hand-curated row with source `team` appears as `team`). Rules for growth, ties and which roles are ranked are in SPEC 5.3.

### PathwayStep — engine output (owner A)

```json
{"order": 1, "course_id": "sql_basics_x", "skill_id": "sql", "hours": 12, "cost_rm": 0,
 "url": "https://example.org/course", "hrdc_claimable": "unknown",
 "gain_per_hour": 0.0041, "cumulative_hours": 12}
```

### PortfolioMetrics — engine output (owner A)

```json
{"growth": 0.07, "ai_exposure": 0.38, "volatility": 0.14, "diversification": 0.71, "readiness": 0.04}
```
`ai_exposure` is `null` when none of the profile's skills has a known exposure (the gauge should then show "n/a"). `growth` counts a thin-data skill at most ±5% (SPEC 5.2).

### Analysis: `engine.api.analyse(profile, snapshot, scenario)` (owner A, the app's single front door)

One call returns everything a page needs, as plain JSON-able data. Pages call this and read the result instead of importing the other engine modules.

```python
from engine import api
from engine.data import load_profile, load_snapshot

result = api.analyse(load_profile("aina"), load_snapshot("latest"), "moderate")   # scenario: "moderate" | "fast"
```

```json
{
  "profile_id": "aina", "scenario": "moderate", "snapshot_date": "2026-10-20",
  "skills": [{"skill_id": "excel", "level": 3, "weight": 0.25, "projected": 0.337, "thin_data": false, "exposure": 0.0818, "sdgs": [4]}],
  "dropped_skills": [],
  "portfolio": {"growth": 0.097, "ai_exposure": 0.186, "volatility": 0.342, "diversification": 0.819, "readiness": 0.075},
  "matches": [],
  "sdg_allocation": [{"sdg": 4, "share": 1.0}],
  "forecasts": {"python": {"...": "a SkillForecast for every skill in the snapshot, for this scenario"}},
  "warnings": ["role_skills has no rows, so roles cannot be matched yet"]
}
```
This is the real output today for Aina on the 2026-10-20 snapshot: `data/role_skills.csv` is still empty, so there are no matches and every skill has only the baseline SDG 4 (the donut is one 100% slice). Once the file is filled, `matches` holds Match objects and `sdgs` / `sdg_allocation` list the roles' SDGs too.
- `skills` has one row per scored profile skill, in profile order (`weight` = level / sum of levels, `projected` = that skill's growth under the scenario, `sdgs` = baseline 4 first). A skill the snapshot has no data for is dropped (and logged); its id is listed in `dropped_skills`.
- `portfolio` is the PortfolioMetrics shape; `matches` is the top 5 Match objects (see above), best first; `sdg_allocation` is the donut: shares sum to 1, ordered by share then SDG number (SDG 4 is the baseline and is always the largest, possibly tied).
- `forecasts` is every SkillForecast for the chosen scenario: use it for the Skill Market page so it never disagrees with the portfolio. `analyse` needs a profile with at least one scorable skill, so before a profile exists the Skill Market can call `engine.forecast.forecast_all(snapshot, scenario)` directly (the numbers are the same) and join names and tickers from `data/skills.csv`.
- **Whenever `matches` is empty, `warnings` says why** (no rows in `data/role_skills.csv`, or no future role has skills listed). Show the warning, never an empty chart without a reason. `profile_id` is `null` when the profile has none.
- Errors, all `ValueError` with a message that names the problem: a profile without a `skills` list of `{skill_id, level}` entries, a level outside 1..3 or a repeated skill (checked for dropped skills too), no skill left after dropping, `risk_tolerance` not one of low/medium/high, `sdg_interests` not a list of integers 1..17 (a list of strings such as `["8"]` is an error, not silently zero overlap), a snapshot without `snapshot_date`. An unknown scenario is a `KeyError`. `risk_tolerance` defaults to "medium"; `sdg_interests` to none (`null` also means none).
- Optional keyword arguments: `roles=` and `role_skills=` replace what is read from `data/` (an explicit empty list is respected); `top_n=` sets how many matches come back (default 5, `None` = every ranked role, for the roles-as-bubbles chart). Match objects carry SDG numbers only: join `sdg_rationale` and `sdg_source_url` from `data/roles.csv` by `role_id` for the badges and links.
- The scenario toggle is just the `scenario` argument: call again, it takes a few milliseconds on the real snapshot.

### PlanResult — `engine.pathway.plan` output (owner A)

```json
{
  "steps": [{"order": 1, "course_id": "sql_basics_x", "skill_id": "sql", "hours": 12, "cost_rm": 0,
             "url": "https://example.org/course", "hrdc_claimable": "unknown",
             "gain_per_hour": 0.0041, "cumulative_hours": 12}],
  "before": {"growth": 0.07, "ai_exposure": 0.38, "volatility": 0.14, "diversification": 0.71, "readiness": 0.04, "match_pct": 0.5},
  "after":  {"growth": 0.09, "ai_exposure": 0.33, "volatility": 0.12, "diversification": 0.75, "readiness": 0.07, "match_pct": 0.67},
  "hours_used": 12
}
```
`before` / `after` are PortfolioMetrics plus the target role's `match_pct`.
