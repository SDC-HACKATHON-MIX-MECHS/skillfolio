# SkillFolio — instructions for AI agents (Replit Agent)

> Replit Agent reads this file when it works in the Repl. It is kept in the repository as part of our AI disclosure: it shows the rules the agent had to follow.

SkillFolio treats a person's skills like an investment portfolio. Each skill has a demand trend (return), a demand swing (risk) and an AI-exposure beta, computed from public, dated job-post data. It is a Streamlit app for the SDC Hackathon 2026, Domain 1 (the Aiversecity Future-Ready Workforce). **AI advises; the person decides.**

## Read first
1. `docs/SPEC.md` — what to build. §5 is the engine, **§6 is the screens**.
2. `contracts/README.md` — the exact shapes of every dict the engine returns.

## Your job
Build and polish the pages in `app/pages/` (and shared helpers in `app/ui.py`), one page at a time, in this order: Skill Market, Profile, My Portfolio, Matches, Rebalance Plan, Methodology. Start with **Skill Market**: it is the feature the judges named ("trend signal feeding role matching").

## Data and engine (already built, do not rewrite)
- Snapshot: `from engine.data import load_snapshot; snap = load_snapshot("latest")`
- Forecasts: `from engine.forecast import forecast_all; forecast_all(snap, scenario)` returns one SkillForecast dict per skill (keys in `contracts/README.md`).
- Matching, portfolio, pathway and the SDG lens come from `engine.api.analyse(...)`; never compute or fake those numbers in a page.
- The scenario is chosen in the sidebar by `app.ui.page_setup()` and stored in `st.session_state["scenario"]`, which is `"moderate"` or `"fast"`. Scenario names to show: `config.SCENARIOS[key]["label"]`.
- Skills, roles, courses and sample profiles come from the `load_*` functions in `engine/data.py`. Do not read CSV files directly.
- Allowed packages: `streamlit`, `pandas`, `numpy`, `plotly`, `requests`.

### What the SkillForecast fields mean
- Growth numbers are **fractions per year**: `0.12` means +12% a year. Show them as percentages.
- `momentum`, `momentum_low` and `momentum_high` are the damped yearly trend and its 80% range; they do **not** depend on the scenario. `momentum_raw` is the plain fitted trend, for transparency.
- `projected`, `projected_low` and `projected_high` **do** depend on the scenario. Use them for the headline growth number and the range band.
- `exposure` is 0–1, or `None` when unknown (then the scenario does not move that skill).
- `trajectory` is `"rising"`, `"stable"` or `"declining"`. For a `thin_data` skill `"stable"` means "not enough data", **not** "flat".
- `index` is the demand index (first month = 100) for the sparkline; `history_months` is its length.

## Hard rules
- **Never invent data.** No made-up jobs, courses, SDG links, statistics or sources. Everything shown comes from `data/` or the engine.
- **Do not edit** `engine/`, `tests/`, `pipeline/`, `data/` (CSV or snapshots), `contracts/` or `docs/` unless the task says so. They carry verified maths and sourced data.
- No LLM calls and no new dependencies without asking. The only secrets are `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` (Replit Secrets), used only through `app/runpod_client.py` for optional resume matching. Never add other keys, and never call RunPod outside that module.
- Every chart or table shows a caption: `Source: <source> · retrieved <snapshot date>`.
- Label every forecast as an **estimate**. Rows with `thin_data = true` are greyed out with a "low data" badge and never highlighted. Cap sparkline axes (a skill that appears late can have a huge index).
- Plain English, sentence case, phone-friendly layout (no wide tables without scrolling).
- Do not add pages or features that are not in `docs/SPEC.md`.
- **AI exposure** means "how much of this work already shows up in real AI use". It means the work is changing fastest, **not** that the job disappears. Put that one-line explanation in a tooltip wherever exposure is shown.
- Scenarios are a what-if, not a prediction; say so on the Methodology page.
- Wording supports a human decision: "evidence to help you decide", never "you should".
- **Empty states, not fake data:** `data/courses.csv` and `data/role_skills.csv` may be empty. Show a clear empty-state message.
- **Never call a web API when a page loads.** Only the **Refresh data** button may fetch, by calling `pipeline.build_snapshot.build(refresh_current_only=True)` and then reloading.
- No personal data: no name, age or gender fields. Profiles are synthetic.

## Design brief (the team may edit this, then ask the Agent to apply it)
- Calm, data-dense and easy to scan: a finance-dashboard feel without clutter. Metric cards for headline numbers; Plotly charts with consistent colours.
- One accent colour. Rising = green ▲, declining = red ▼, stable or low data = grey ●. Always pair colour with an arrow or text.
- The showpiece is **Apply plan** on the Rebalance page: after applying, the user's dot moves up-left on the risk/return chart and the AI-exposure gauge drops. Make it obvious and smooth.
- Change one thing per prompt, and check the page still follows the hard rules afterwards.

## Run and check
- Run: `streamlit run app/Home.py` (port 8501; already set in `.replit`).
- Tests: `python -m pytest -q` must stay green. Run it before finishing every task. If `pytest` is missing: `pip install -r requirements.txt`.
- Until real data is merged the app may show an "EXAMPLE DATA" banner. That is expected.

## Git
- Work on a branch named `app/<page>` (for example `app/skill-market`). Small commits. Pull before you push. Never force-push. Open a pull request into `main`.
- Say in the pull request that the Replit Agent was used (the hackathon requires AI disclosure).
