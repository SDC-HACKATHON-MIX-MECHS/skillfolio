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
| [@Curryraj](https://github.com/Curryraj) (Jaiydaan) | A — Team Lead, Engine + RunPod |
| [@AhmedAtheek](https://github.com/AhmedAtheek) (Atheek) | B — Data & Trends |
| [@Kuhan06](https://github.com/Kuhan06) (Kuhan) | C — App & Replit |
| [@oscarongggggg](https://github.com/oscarongggggg) (Oscar) | D — Research, SDG & Pitch |

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

**On Replit:** see [Run on Replit](#run-on-replit) below.

**Locally** (with [uv](https://docs.astral.sh/uv/)):
```
uv sync
uv run pytest
uv run streamlit run app/Home.py
```
Until the first real data snapshot lands, the app runs on an illustrative fixture and shows an "EXAMPLE DATA" banner.

## Run on Replit

Replit is required for the hackathon. The GitHub repo stays the source of truth; Replit imports it and publishes the demo link.

**One-time setup**
1. **GitHub org owner:** allow the Replit app to read the org (Org → Settings → Third-party access / GitHub Apps). Without this, the import cannot see the repo.
2. **One teammate** (the one who redeems the hackathon's Replit Core): Create App → **Import from GitHub** → `SDC-HACKATHON-MIX-MECHS/skillfolio`, branch `main`.
3. Press **Run**. `.replit` and `.streamlit/config.toml` start Streamlit on port 8501 (Replit maps it to port 80). If packages are not installed, open **Shell** and run `pip install -r requirements.txt`.
4. Invite the other three teammates as collaborators (Core allows up to 5). Everyone can then work in the same workspace.

**Working together**
- GitHub is where work lands: use branches (`app/<page>`, `engine/<topic>`) and pull requests into `main`. In Replit use the **Git** pane; **pull before you push**.
- The **Replit Agent** may build and polish Streamlit pages in `app/` (lane C) on its own branch. It reads [`replit.md`](replit.md) for the rules: no invented data, hands off `engine/`, `tests/`, `pipeline/` and `data/`. Disclose its use in the pull request and in the proposal.
- Never put keys in code. If we ever add one, store it in Replit **Secrets**.

**Publishing the demo**
1. Merge everything into `main`, pull in Replit, press Run and click through all pages.
2. **Deploy / Publish** (Autoscale is fine). Open the public link on a phone.
3. Do this by **Friday night** and re-check on Saturday before submitting.

**Things to know**
- A published app's disk is temporary. The committed snapshot in `data/snapshots/` is the source of truth; a "Refresh data" button on a published app cannot save anything permanently.
- Autoscale can sleep between visits, so open the link before a live demo to wake it.
- Backup: keep a screen recording of the demo in `docs/demo/`.

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

- **In the product:** forecasts, matching and plans are statistics, not AI models. Resume reading can optionally use the open embedding model [`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5) (MIT) on a RunPod Serverless GPU ([`runpod/README.md`](runpod/README.md)). It can only return skill IDs from our catalogue, the user sees each suggestion and can remove it, and on any error the app falls back to keyword rules. SkillFolio stores no copy of the resume text. No generative language model is used.
- **While building:** Claude Code (Anthropic) helped write code, tests, data files and documents; Replit Agent helped build pages. All logic is reviewed by the team and passes the test suite and pull-request review.

## Team agreement

Code is released under the [Apache License 2.0](LICENSE) (copyright notice in [NOTICE](NOTICE)). The project belongs equally to the four team members; any decision to continue it after the hackathon is made together.
