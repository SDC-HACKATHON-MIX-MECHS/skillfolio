# SkillFolio

> **Your skills are a portfolio. AI is the market.**

SDC Hackathon 2026 · Domain 1 — *The Aiversecity Future-Ready Workforce* · Team **SDC-HACKATHON-MIX-MECHS**

SkillFolio treats a person's skills like an investment portfolio. Every skill has a **demand trend** (return), a **demand swing** (volatility) and an **AI-exposure risk**, all computed from public, dated data. The app shows a fresh graduate or early-career switcher which future roles they can reach, and how to "rebalance" their learning hours into skills that are growing and harder for AI to replace — with every number sourced and dated and every role linked to the UN SDGs.

AI supports the decision. The person makes it.

**Status:** preliminary round build · internal deadline **Sat 24 Oct, 9 pm** · hard deadline **Sun 25 Oct, 08:00**

---

## Team

| GitHub | Lane |
|---|---|
| [@Curryraj](https://github.com/Curryraj) (Jaiydaan) | A — Lead + Engine |
| [@AhmedAtheek](https://github.com/AhmedAtheek) | _TBC_ |
| [@Kuhan06](https://github.com/Kuhan06) | _TBC_ |
| [@oscarongggggg](https://github.com/oscarongggggg) | _TBC_ |

Lanes: **A** Engine · **B** Data & Trends · **C** App & Replit · **D** Research, SDG & Pitch — see [docs/TEAM_PLAN.md](docs/TEAM_PLAN.md).

## Docs

- [docs/SPEC.md](docs/SPEC.md) — **what** we're building: the finance ↔ career model, formulas, screens, data sources
- [docs/TASKS.md](docs/TASKS.md) — **who builds what, by when**, and how we know it's done
- [docs/TEAM_PLAN.md](docs/TEAM_PLAN.md) — roles, sprint, Replit guide, risks, submission checklist
- [contracts/](contracts/) — the data shapes every lane builds against

## How we work

1. **Pull before you start.** `git pull origin main`
2. **Work on a branch** named after your lane: `data/hn-fetch`, `app/matches-page`, `pitch/sdg-table`…
3. **Small commits, push often.** Open a pull request into `main`; ask one teammate to glance at it.
4. **Never commit secrets.** API keys go in Replit **Secrets** or a local `.env` (already git-ignored).
5. **Never put invented data in the repo.** Every role, course and statistic needs a source URL. Unknown? Leave `TODO(D): cite`.
6. Tag issues with a lane label: `lane:engine`, `lane:data`, `lane:app`, `lane:pitch`, plus `blocked` when stuck.

From Wednesday night, `main` must always run.

## Running it

Stack: **Python 3.12 · Streamlit · pandas · Plotly**.

**On Replit:** Create App → Import from GitHub → `SDC-HACKATHON-MIX-MECHS/skillfolio` → **Run**. (`.replit` starts Streamlit on port 8501.)

**Locally** (with [uv](https://docs.astral.sh/uv/)):
```
uv sync
uv run pytest
uv run streamlit run app/Home.py
```
Until the first real data snapshot lands, the app runs on an illustrative fixture and shows an "EXAMPLE DATA" banner.

## Repo layout

```
app/          Streamlit pages (lane C)
engine/       forecasts, portfolio maths, matching, plan, SDG lens (lane A)
pipeline/     HN hiring posts + AI exposure -> dated snapshots (lane B)
data/         skills, roles, courses, sample profiles, snapshots
contracts/    data shapes + illustrative fixtures
tests/        data-integrity checks + acceptance tests per lane
docs/         spec, tasks, team plan
```

## Data sources

| Signal | Source | Licence |
|---|---|---|
| Skill demand over time | Hacker News "Ask HN: Who is hiring?" monthly threads via the [HN Algolia API](https://hn.algolia.com/api) | Public API |
| AI exposure by occupation | [Anthropic Economic Index](https://huggingface.co/datasets/Anthropic/EconomicIndex) — `labor_market_impacts/job_exposure.csv` | CC-BY |
| Skill ↔ occupation links | [O*NET 31.0 database](https://www.onetcenter.org/database.html) — Technology Skills (Hot Technology / In Demand flags) | CC BY 4.0 |
| Malaysian labour context | [data.gov.my](https://data.gov.my) API — `lfs_qtr` | Open data |

Known limit: Hacker News postings are global and tech-heavy, so SkillFolio targets grads moving into tech and data roles. Malaysian occupation data is a Phase 2 upgrade.

## AI disclosure

- **In the product:** no language model is required for the preliminary demo. If we add one (to read CV text into skills and phrase explanations), it will be named here, and it may only choose from our own skill / role / course lists.
- **While building:** AI coding assistants (e.g. Claude Code, Replit Agent) helped write code. All logic is reviewed by the team.

## Team agreement

Code is released under the [MIT licence](LICENSE). The project belongs equally to the four team members; any decision to continue it after the hackathon is made together.
