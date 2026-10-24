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
| Replit Project    | [TO FILL]                                      |
| Live Demo         | [TO FILL]                                      |
| RunPod Endpoint   | https://api.runpod.ai/v2/r0ykxnttw93erm        |
| Slide Deck        | [TO FILL]                                      |
| Demo Video        | [TO FILL]                                      |

---

## Overview

### Problem

AI is changing which skills employers want faster than career advice can keep up. In 2024, 66.0% of Malaysian graduates aged 24 and under worked in jobs below their qualifications (DOSM, Graduates Statistics 2024). A fresh graduate with a few hundred learning hours a year has no way to tell which skills are growing, which roles they could realistically reach, or which courses are worth their time, and chatbots that answer this can invent jobs, courses and numbers.

### Solution

SkillFolio treats a person's skills like an investment portfolio and AI as the market. It reads real, dated job posts (Hacker News "Who is hiring", 25 months) and AI-exposure data (Anthropic Economic Index, O*NET) to estimate how demand for each skill is moving under two AI scenarios. It then ranks the roles a person can reach with an explainable fit score, and builds an ordered plan of free courses that moves them closer fastest. An open AI model on a RunPod GPU reads the user's resume and suggests skills they describe without naming. Every number shows its source and date, forecasts are labelled as estimates, and the app can only recommend roles, skills and courses from its own verified lists, so it cannot invent them. The person makes the decision.

### Key Features

- **Resume to skills** — paste a resume; keyword matching plus an embedding model on RunPod suggest skills from our catalogue of 73, and the user confirms each one.
- **Skill Market (AI-trend signal)** — every skill's job-post demand trend, a 12-month estimate with a range, and its AI exposure, from a dated snapshot that can be refreshed.
- **Role matching** — ranked roles with a fit score, the skills that count towards it, the biggest missing skill, and the SDGs each role serves.
- **Learning plan** — free courses in order, with hours and HRD Corp status; "Apply plan" shows the fit and AI exposure change live.
- **Two AI futures** — every number re-runs under a moderate and a fast AI-disruption scenario.

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
├── docs/                    # Specification, design notes, proposal
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

1. Open the [Replit Project]([TO FILL]), or import this repository via **Create Repl → Import from GitHub**.
2. Open the **Secrets** tab (🔒) and add the variables listed in `.env.example`:
   - `RUNPOD_API_KEY`
   - `RUNPOD_ENDPOINT_ID`
3. Click **Run**. Replit uses the `.replit` file to start `streamlit run app/Home.py`.

Without the two secrets the app still runs; the resume step then uses keyword matching only.

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
- **Secrets:** the RunPod API key and endpoint ID are stored in Replit Secrets, never in the code.

📄 Proof of use: [`submission/SDC2026_MIXMECHS_Replit_POU.pdf`](submission/SDC2026_MIXMECHS_Replit_POU.pdf)

## How We Use RunPod *(Required)*

- **Workload:** resume-to-skills matching. The open embedding model `BAAI/bge-small-en-v1.5` compares each resume sentence with a plain description of each of our 73 skills and returns the closest ones, so "built dashboards for senior management" suggests Power BI even though the resume never names it.
- **Setup:** `runpod/handler.py` is deployed as a **RunPod Serverless Endpoint** on a 16 GB GPU, built from `runpod/Dockerfile` with the model baked into the image (0 always-on workers, so it costs nothing when idle).
- **Integration:** the Replit app sends requests to the endpoint using `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID` (`app/runpod_client.py`). The model can only rank skill ids we send it, and if the endpoint is slow or down the app falls back to keyword matching.

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

- **Keeping every number honest.** We fixed data contracts and tests first, so no role, course or statistic can enter the app without a source and date, and the app cannot recommend anything outside its own lists.
- **Matching resumes by meaning.** Comparing resume sentences with lists of tool names gave noisy results; writing one plain sentence about the work each skill involves made the embedding model accurate.
- **Small, real data.** About 250 job posts a month is enough for clear trends in common skills but not rare ones, so thin-data skills are greyed out and never given a trend.
- **Deploying on RunPod.** The first worker never started because the default 5 GB disk was too small for GPU PyTorch; raising it to 20 GB fixed it.

## Future Improvements

- [ ] Add a Malaysian job source so non-tech skills (marketing, accounting, supply chain) get real trends
- [ ] Use the RunPod model to read job posts as well, so trend counts catch skills described without their name
- [ ] Verify HRD Corp claimability for each course
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

- [ ] Team name, domain (Domain 1 / Domain 2) and SDG track filled in
- [ ] Slide deck link added
- [ ] Demo video link added
- [ ] Replit used, with proof of use in `submission/`
- [ ] RunPod used, with proof of use in `submission/`
- [ ] Preliminary submission completed (`SDC2026_MIXMECHS_Preliminary.pdf`)
- [ ] Technology declaration completed (`SDC2026_MIXMECHS_TechDeclaration.pdf`)
- [ ] Submission files renamed with your team name (replace `TeamName` with `MIXMECHS`)
- [ ] "How to Run" steps verified
- [ ] No API keys or secrets committed to the repository

## License

This project is licensed under the [Apache License 2.0](LICENSE).
