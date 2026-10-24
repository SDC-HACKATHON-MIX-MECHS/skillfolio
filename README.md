# SkillFolio

> A web app that shows Malaysian fresh graduates and early-career switchers which future roles fit their skills, why, and what to learn next, using live job-market data and AI-exposure data.

---

## Team Information

| Field                  | Details                                     |
| ---------------------- | ------------------------------------------- |
| **Team Name**          | MIX MECHS                                   |
| **Team Domain**        | Domain 1 — The Aiversecity Future-Ready Workforce |
| **SDG Track (1–17)**   | SDG 4 — Quality Education (target 4.4); SDG 8 — Decent Work and Economic Growth (target 8.5) |
| **Team Leader**        | Jaiydaan Raj                                |
| **University**         | University of Southampton Malaysia          |
| **Number of Members**  | 4                                           |

## Links

| Resource          | Link                                           |
| ----------------- | ---------------------------------------------- |
| GitHub Repository | https://github.com/SDC-HACKATHON-MIX-MECHS/skillfolio |
| Replit Project    | https://replit.com/@WhiteDevil23/skillfolio    |
| Live Demo         | https://skillfolio.replit.app/                 |
| RunPod Endpoint   | https://api.runpod.ai/v2/r0ykxnttw93erm (API address, needs a key) |
| Slide Deck        | [docs/SDC2026_MIXMECHS_Slides.pdf](docs/SDC2026_MIXMECHS_Slides.pdf) |
| Demo Video        | [docs/demo/SDC2026_MIXMECHS_Demo.mp4](docs/demo/SDC2026_MIXMECHS_Demo.mp4) |

---

## Overview

### Problem

AI is changing which skills employers ask for faster than career advice can keep up, and graduates and career switchers have no way to track their own skills against it. In 2024, 66.0% of Malaysian graduates aged 24 and under were working in jobs below their qualifications (DOSM, Graduates Statistics 2024). Someone with a few hundred hours a year to learn can't tell which of their skills are in demand, which roles they could reach, or whether a course moved them closer. Chatbots that answer these questions can make up jobs, courses and numbers.

### Solution

SkillFolio turns a resume into a skill portfolio. The user pastes a resume and we build their portfolio from a list of 73 skills, each rated Basic, Working or Strong. We read 25 months of dated job posts (Hacker News "Who is hiring") and AI-exposure data (Anthropic Economic Index, O*NET) to estimate demand for each skill under two AI scenarios. The app ranks 20 roles by fit, builds an ordered plan of free courses, and updates the user's skill levels and fit as they mark courses finished. An open AI model on RunPod suggests skills that a resume describes without naming. Every number shows its source and date, forecasts are labelled as estimates, and the app can only recommend roles, skills and courses from our checked lists, so it can't make them up. The user makes the decision.

### Key Features

- **Resume to skills** — paste a resume; keyword matching, plus an AI model on RunPod when it is switched on, suggest skills from our 73, and the user confirms each one and sets a level.
- **Track your learning** — mark progress on each course; finishing one raises that skill's level and your fit. The Profile page shows plan progress, hours left and skill coverage.
- **Skill Market** — each skill's job-post demand trend, a 12-month estimate with a range, and its AI exposure, from a dated snapshot that can be refreshed.
- **Role matching** — 20 ranked roles with a fit score, the biggest missing skill, and the SDGs each role serves.
- **Learning plan** — free courses in order, with hours. "Apply plan" shows the fit and AI exposure change.
- **Two AI futures** — every number re-runs under a moderate and a fast AI scenario.

### Tech Stack

| Layer         | Technology                   |
| ------------- | ---------------------------- |
| Frontend      | Streamlit, Plotly            |
| Backend       | Python (pandas, NumPy): forecasting, matching and planning engine |
| Database      | Versioned CSV and JSON snapshots in Git, checked by tests against written data contracts |
| AI / Compute  | RunPod Serverless (GPU) running `BAAI/bge-small-en-v1.5` |
| Hosting / Dev | Replit                       |

---

## Project Structure

```
.
├── app/
│   ├── Home.py              # Application entry point (Streamlit)
│   ├── pages/               # Profile, Skill Market, My Portfolio, Matches, Learning plan, Methodology
│   ├── runpod_client.py     # Calls the RunPod endpoint; falls back to keyword matching
│   └── ...                  # Shared UI helpers and the stylesheet
├── engine/                  # Forecasts, portfolio maths, role matching, course planner, SDG mapping
├── pipeline/                # Fetches job posts and AI-exposure data, builds dated snapshots
├── data/                    # Skills, roles, courses, sample profiles, dated snapshots
├── runpod/
│   ├── handler.py           # RunPod serverless handler (GPU workload)
│   ├── skill_match.py       # Resume-to-skills matching logic
│   └── Dockerfile           # Image RunPod builds the endpoint from
├── contracts/               # Data shapes every file must follow
├── docs/                    # Specification, screenshots, demo video
├── submission/              # Required submission documents
├── tests/                   # Unit and app tests
├── .env.example             # Example environment variables
├── .gitignore
├── .replit                  # Replit run configuration
├── LICENSE
├── requirements.txt         # Python dependencies
└── README.md
```

### Architecture

```
User ──► Replit (Streamlit app + Python engine) ──► RunPod Endpoint (embedding model, GPU)
                │                                          │
                │◄──────────── suggested skill ids ◄───────┘
                │
                ├──► Dated snapshot (Hacker News job posts, Anthropic Economic Index, O*NET)
                │
                └──► Ranked roles, skills gap, learning plan, SDG links returned to user
```

---

## How to Run

### Option 1 — Run on Replit (Recommended)

1. Open the [Replit Project](https://replit.com/@WhiteDevil23/skillfolio), or import this repository via **Create Repl → Import from GitHub**.
2. Optional, to turn on the AI model: open the **Secrets** tab (🔒) and add the two variables listed in `.env.example` (`RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`, from your own RunPod endpoint). Your keys stay in Secrets and are never committed.
3. Click **Run**. Replit uses the `.replit` file to start `streamlit run app/Home.py`.

Without them the app runs fully; the resume step just uses keyword matching only.

### Option 2 — Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/SDC-HACKATHON-MIX-MECHS/skillfolio.git
cd skillfolio

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env            # then fill in your values

# 5. Run the app
streamlit run app/Home.py
```

### Run Tests

```bash
python -m pytest
```

---

## How We Use Replit *(Required)*

- **Development:** the team imported this GitHub repository into one Replit workspace and worked in it together; GitHub stays the source of truth through branches and pull requests.
- **Hosting:** the app is published with Replit Deployments at the Live Demo link above.
- **Secrets:** the optional RunPod keys go in Replit Secrets, never in the code.

📄 Proof of use: [`submission/SDC2026_MIXMECHS_Replit_POU.pdf`](submission/SDC2026_MIXMECHS_Replit_POU.pdf)

## How We Use RunPod *(Required)*

- **Workload:** resume-to-skills matching. The open embedding model `BAAI/bge-small-en-v1.5` compares each resume sentence with a plain description of each of our 73 skills and returns the closest ones, so "built dashboards for senior management" suggests Power BI even though the resume never names it.
- **Setup:** `runpod/handler.py` is deployed as a **RunPod Serverless Endpoint** on a 16 GB GPU, built from `runpod/Dockerfile` with the model baked into the image (0 always-on workers, so it costs nothing when idle).
- **Integration:** when `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` are set, the app sends requests to the endpoint (`app/runpod_client.py`). The model can only rank skill ids we send it, and if the endpoint is slow or down the app falls back to keyword matching. The public Replit demo runs without those two secrets, so its resume step uses keyword matching and nobody waits for a cold GPU start. The endpoint is deployed and tested; the proof of use shows live calls to it.

Example request:

```bash
curl -X POST https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"task": "match_skills", "text": "Built dashboards for senior management.", "skills": [{"skill_id": "powerbi", "text": "Building dashboards and reports for managers in Microsoft Power BI."}]}}'
```

📄 Proof of use: [`submission/SDC2026_MIXMECHS_Runpod_POU.pdf`](submission/SDC2026_MIXMECHS_Runpod_POU.pdf)

---

## Challenges & Learnings

- **Keeping every number honest.** We agreed data formats and tests first, so no role, course or number can enter the app without a source and date, and the app can't recommend anything outside its own lists.
- **Matching resumes by meaning.** Comparing resume sentences with tool names gave noisy results. Writing one plain sentence about the work behind each skill fixed it.
- **Small data.** About 250 job posts a month is enough for common skills but not rare ones, so rare skills get no trend.
- **Deploying on RunPod.** The first worker never started because the default 5 GB disk was too small for PyTorch. 20 GB fixed it.

## Known Limitations

- **Industries:** our 20 roles and 73 skills are tech and data. Other industries aren't covered yet.
- **Progress is self-reported:** users tick their own course progress, and a very short course can raise the fit score a lot.
- **Portfolios aren't saved:** a portfolio lasts one browser session.
- **Job data:** Hacker News posts are mostly US and remote tech jobs, not the Malaysian market. Skills with too few posts get no trend.
- **AI model:** it can suggest too much (all three clouds for "a cloud server"), and after a quiet spell the RunPod worker can take up to a minute to start. The app then uses keyword matching.
- **Forecasts are estimates under two AI scenarios, not predictions.**

## Future Improvements

- [ ] Saved portfolios, so users can return and keep updating their skills over time
- [ ] Add a Malaysian job source so non-tech skills (marketing, accounting, supply chain) get real trends
- [ ] Use the RunPod model to read job posts as well, so trend counts catch skills described without their name
- [ ] Bahasa Malaysia interface

## Team

| Name        | Role                | GitHub                                   |
| ----------- | ------------------- | ---------------------------------------- |
| Jaiydaan | Team Lead, Engine + RunPod | [@Curryraj](https://github.com/Curryraj) |
| Atheek | Data & Trends | [@AhmedAtheek](https://github.com/AhmedAtheek) |
| Kuhan | App & Replit | [@Kuhan06](https://github.com/Kuhan06)   |
| Oscar | Research, SDG & Pitch | [@oscarongggggg](https://github.com/oscarongggggg) |

---

## Submission Checklist

- [x] Team name, domain (Domain 1 / Domain 2) and SDG track filled in
- [x] Slide deck link added
- [x] Demo video link added
- [x] Replit used, with proof of use in `submission/`
- [x] RunPod used, with proof of use in `submission/`
- [ ] Preliminary submission completed (`SDC2026_MIXMECHS_Preliminary.pdf`)
- [ ] Technology declaration completed (`SDC2026_MIXMECHS_TechDeclaration.pdf`)
- [ ] Submission files renamed with your team name (replace `TeamName` with `MIXMECHS`)
- [x] "How to Run" steps verified
- [x] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).
