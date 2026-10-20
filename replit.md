# SkillFolio — instructions for AI agents (Replit Agent)

SkillFolio treats a person's skills like an investment portfolio. Each skill has a demand trend (return), a demand swing (risk) and an AI-exposure beta, computed from public, dated job-post data. It is a Streamlit app for the SDC Hackathon 2026, Domain 1 (the Aiversecity Future-Ready Workforce). **AI advises; the person decides.**

## Read first
1. `docs/SPEC.md` — what to build. §5 is the engine, **§6 is the screens**.
2. `docs/TASKS.md` — who builds what. You are doing **lane C (the app)**.
3. `contracts/README.md` — the exact shapes of every dict the engine returns.

## Your job
Build and polish the pages in `app/pages/` (and shared helpers in `app/ui.py`), one page at a time, in this order: Skill Market, Profile, My Portfolio, Matches, Rebalance Plan, Methodology. Start with **Skill Market**: it is the feature the judges named ("trend signal feeding role matching").

## Data and engine (already built, do not rewrite)
- Snapshot: `from engine.data import load_snapshot; snap = load_snapshot("latest")`
- Forecasts: `from engine.forecast import forecast_all; forecast_all(snap, scenario)` returns one SkillForecast dict per skill (keys in `contracts/README.md`).
- Matching, portfolio and pathway are still being written by lane A. If a function raises `NotImplementedError`, show a short "coming soon" note instead of faking numbers.
- The scenario is chosen in the sidebar by `app.ui.page_setup()` and stored in `st.session_state["scenario"]`.

## Hard rules
- **Never invent data.** No made-up jobs, courses, SDG links, statistics or sources. Everything shown comes from `data/` or the engine.
- **Do not edit** `engine/`, `tests/`, `pipeline/`, `data/` (CSV or snapshots), `contracts/` or `docs/` unless the task says so. They carry verified maths and sourced data.
- No LLM calls, no API keys, no secrets, no new dependencies without asking.
- Every chart or table shows a caption: `Source: <source> · retrieved <snapshot date>`.
- Label every forecast as an **estimate**. Rows with `thin_data = true` are greyed out with a "low data" badge and never highlighted. Cap sparkline axes (a skill that appears late can have a huge index).
- Plain English, sentence case, phone-friendly layout (no wide tables without scrolling).
- Do not add pages or features that are not in `docs/SPEC.md`.

## Run and check
- Run: `streamlit run app/Home.py` (port 8501; already set in `.replit`).
- Tests: `python -m pytest -q` must stay green. Run it before finishing every task. If `pytest` is missing: `pip install -r requirements.txt`.
- Until real data is merged the app may show an "EXAMPLE DATA" banner. That is expected.

## Git
- Work on a branch named `app/<page>` (for example `app/skill-market`). Small commits. Pull before you push. Never force-push. Open a pull request into `main`.
- Say in the pull request that the Replit Agent was used (the hackathon requires AI disclosure).
