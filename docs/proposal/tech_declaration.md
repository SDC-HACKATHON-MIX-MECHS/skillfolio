# SkillFolio — Technical Tools Declaration (draft v1)

> Draft for the team, 24 Oct 2026. Follows the official template "SDC Hackathon: Technical Tools Declaration", section for section and in its order.
> Final file: one PDF named `SDC2026_TeamName_TechDeclaration.pdf`, submitted together with the proposal. Items marked **[TO FILL]** or **[CONFIRM]** need a teammate's answer; remove this note before export.
> Versions are the ones installed and tested on 24 Oct 2026. The RunPod items describe branch `feat/runpod-skill-match`, which must be merged and deployed before submission.

---

## 1. Team and Project Overview

| Field | Answer |
|---|---|
| Team Name | **[TO FILL]** |
| Project / Solution Name | SkillFolio |
| Name (Leader) | **[TO FILL]** |
| Email & Phone (Leader) | **[TO FILL]** |
| University Affiliation(s) | **[TO FILL]** |
| Live Prototype URL | **[TO FILL once the Replit deployment opens on a phone]** |
| Code Repository URL (public / access granted to judges) | https://github.com/SDC-HACKATHON-MIX-MECHS/skillfolio (public) |

---

## 2. Architecture & Technology Stack

### 2.1 System Architecture Overview *(max 200 words)*

SkillFolio is a Python web app. The user interface is a Streamlit multipage app hosted on Replit, which the user opens in a phone or laptop browser. The interface calls our own engine (plain Python), which computes skill forecasts, the user's skill portfolio, role matches, a course plan and the SDG link.

The engine reads no database server. Its data is versioned CSV and JSON files in the Git repository: our skill, role and course catalogues and dated market snapshots. A separate pipeline builds each snapshot from the Hacker News Algolia API, the Anthropic Economic Index and O*NET, then saves it as a dated file. The app only calls the Hacker News API when the user presses "Refresh data".

One AI model is used. If the user pastes a resume and leaves "Also use our AI model" ticked, the app sends the text and our skill catalogue to a RunPod Serverless GPU endpoint running the open embedding model BAAI/bge-small-en-v1.5. It returns skill IDs from our catalogue only. If RunPod fails or times out, keyword rules are used instead. The user's profile lives only in the browser session. See the block diagram in the proposal, section 3.1.

*(196 / 200 words)*

### 2.2 Languages, Frameworks & Libraries

| Name & Version | License | Purpose in Project |
|---|---|---|
| Python 3.12 (app); Python 3.11 in the `python:3.11-slim` Docker image (RunPod worker) | PSF License | Language for the app, engine, pipeline and tests; the official Docker Hub image is the worker's base |
| Streamlit 1.66.0 | Apache-2.0 | Web user interface (multipage app) |
| pandas 3.0.6 | BSD-3-Clause | Tables on the Matches, Rebalance Plan and Methodology pages |
| NumPy 2.5.4 | BSD-3-Clause (with 0BSD, MIT, Zlib, CC0 parts) | Similarity maths in the RunPod worker |
| Plotly 7.1.0 | MIT | Charts |
| Requests 2.34.2 | Apache-2.0 | Calls to the RunPod API from the app (the pipeline uses Python's built-in `urllib`) |
| pypdf 6.21.1 | BSD-3-Clause | Reads text from an uploaded PDF resume |
| pytest 9.1.1 | MIT | Automated tests (855) |
| sentence-transformers ≥ 3.0 (RunPod worker) | Apache-2.0 | Runs the embedding model on the GPU |
| PyTorch ≥ 2.3 (RunPod worker) | BSD-3-Clause | Model runtime on the GPU |
| runpod Python SDK ≥ 1.7 (RunPod worker) | MIT | Serverless worker entry point |
| Inter font (Google Fonts) | SIL Open Font License 1.1 | Interface typeface |

---

## 3. APIs & Cloud Services

### 3.1 External APIs

| API and Provider | Access Tier (free / paid / sponsor-provided) | Purpose in Project |
|---|---|---|
| Hacker News Search API, Algolia (`hn.algolia.com/api/v1`) | Free | Monthly "Who is hiring" job posts that give each skill's demand trend. Called by the data pipeline and by the "Refresh data" button |
| RunPod Serverless API (`api.runpod.ai/v2/…/runsync` and `…/status`) | **[TO FILL: paid / credits]** | Optional resume-to-skills matching with the embedding model |
| Google Fonts API (`fonts.googleapis.com`) | Free | Loads the Inter typeface in the user's browser |
| Hugging Face Hub (model and dataset downloads) | Free | Downloads the Anthropic Economic Index file for the pipeline and the bge-small model when the RunPod image is built; not called while the app runs |
| O*NET database download (`onetcenter.org`) | Free | Technology Skills file used by the pipeline to link skills to occupations |

### 3.2 Cloud Platforms & Deployment

| Service & Provider | Plan / Region | Purpose in Project |
|---|---|---|
| Replit (Deployments) | Replit Core through the hackathon **[CONFIRM]** / **[TO FILL region]** | Hosts the live Streamlit prototype; development workspace |
| RunPod Serverless | Pay-per-second GPU, 16 GB, 0 active workers (scales to zero), max 1 worker / **[TO FILL region]** | Runs the embedding model for resume matching |
| GitHub | Free (public organisation repository) | Source code, data files, pull-request review |

**How the prototype is deployed:** Replit imports the public GitHub repository and runs `streamlit run app/Home.py` (see `.replit`). RunPod builds `runpod/Dockerfile` from the same repository, with the model baked into the image. The RunPod key and endpoint ID are stored in Replit Secrets, never in the code.

---

## 4. AI Tools, Models & Datasets

### 4.1 AI Models Used in the Solution

| Model & Version | Source / Provider | License / Terms | Usage (pre-trained / fine-tuned / self-trained) |
|---|---|---|---|
| BAAI/bge-small-en-v1.5 | Beijing Academy of Artificial Intelligence, via Hugging Face | MIT | Pre-trained, used unchanged. Compares resume sentences with one-line skill descriptions; the match threshold (0.73) was set by the team on made-up resumes |

The forecasts, matching and course planner are our own statistical code, not trained models.

### 4.2 Datasets

| Dataset Name | Source / URL | Type (public / private / self-collected / synthetic) | Personal Data? (Y/N) | License |
|---|---|---|---|---|
| Hacker News "Who is hiring" posts (7,961 posts, 25 months) | https://hn.algolia.com/api | Public | N (only skill counts per month are kept) | Public API |
| Anthropic Economic Index, `job_exposure.csv` | https://huggingface.co/datasets/Anthropic/EconomicIndex | Public | N | CC-BY |
| O*NET 31.0 Technology Skills | https://www.onetcenter.org/database.html | Public | N | CC BY 4.0 |
| UN SDG targets (wording; mapped to roles by the team) | https://sdgs.un.org/goals | Public | N | UN public data |
| Course catalogue, 52 free courses (`data/courses.csv`) | Each provider's public course page | Self-collected | N | Links and metadata only |
| Skill, role and role-skill catalogues (`data/skills.csv`, `roles.csv`, `role_skills.csv`) | Our repository | Self-collected | N | Apache-2.0 (ours) |
| Sample profiles (Aina, Ravi, Mei, Hafiz, Priya) | `data/profiles/` | Synthetic | N | Apache-2.0 (ours) |
| Made-up resumes used to set the RunPod match threshold | `runpod/README.md`, `tests/test_runpod_match.py` | Synthetic | N | Apache-2.0 (ours) |

### 4.3 AI-Assisted Development Tools

**Did your team use any generative-AI tool to help create code, design, text, or other project material?** **Yes.**

| Tool & Version | Extent of Use (minor / moderate / major) | Used For |
|---|---|---|
| Claude Code 2.1 (Anthropic), with Claude Opus 5.5 and Claude Sonnet 5.5 | Major | Writing and reviewing code, tests, data files, documentation, this declaration and the proposal |
| Replit Agent (Replit) | **[CONFIRM: minor / moderate]** | Building and polishing Streamlit pages |

**[CONFIRM WITH EVERY MEMBER]** that no other generative-AI tool (for example ChatGPT, Gemini, Copilot or Canva AI) was used for code, text, slides or images.

**How the team reviewed, tested and took responsibility for AI-generated output** *(max 100 words)*

The team set every goal and decision; AI tools drafted code and text to our instructions. Every change went through a GitHub pull request reviewed by a team member, and the automated test suite (855 tests) had to pass before merging. Key results, such as forecasts, matching and the course planner, were checked by separate verification runs with recorded evidence in `docs/verification/`. Facts, sources, course links and numbers were checked against the original source. The team takes full responsibility for all submitted work.

*(83 / 100 words)*

---

## 5. Sponsor-Provided Resources

**Did your project use any official SDC sponsor-provided resource?** **Yes** **[CONFIRM that Replit Core access is a sponsor resource]**.

| Sponsor | Resource (API / credits / platform / data) | How It Was Used in the Project |
|---|---|---|
| Replit **[CONFIRM]** | Platform: Replit Core access | Development workspace and public hosting of the live prototype |

**Was the sponsor resource essential to the core functionality of the prototype, or could it be replaced?** *(max 100 words)*

Replit hosts the live prototype that judges open, so it is essential to the deployed version. It could be replaced: SkillFolio is a standard Streamlit app in a public GitHub repository, with no Replit-specific code, so it would also run on Streamlit Community Cloud, Render or any server with Python. The core logic, data and tests do not depend on Replit. No sponsor GenAI API is used.

*(67 / 100 words)*

---

## 6. Security, Privacy & Responsible Use

### 6.1 Data Handling & Privacy *(max 150 words)*

SkillFolio asks for no name, age, gender, email or account. A profile (skills, levels, hours, goals) lives only in server memory for the user's browser session and is gone when the session ends; nothing is written to disk or a database.

Users may paste or upload a resume. The text is read in memory to find skills and then discarded; the app keeps no copy. The app asks users to use a made-up or sample resume in this demo. The box "Also use our AI model" is ticked by default; then the text is sent once over HTTPS to our RunPod endpoint, which returns skill IDs and does not log the text. RunPod may hold job data briefly under its own terms. If the user unticks it, nothing leaves the app.

The RunPod key is kept in Replit Secrets, not in the code.

*(143 / 150 words)*

### 6.2 Known Limitations & Risks *(max 150 words)*

- **Wrong or missing skill suggestions.** The embedding model can over-suggest (all three cloud platforms for "a cloud server") and misses skills outside our 73-skill catalogue. Mitigation: it can only return catalogue IDs, suggestions are shown and removable, and keyword rules remain.
- **Single provider and cold starts.** RunPod scales to zero, so the first call can be slow. Mitigation: a 40-second timeout, then keyword matching; the app never depends on it.
- **Data bias.** Hacker News posts are global and tech-heavy, not Malaysian. Mitigation: stated on the Methodology page; thin-data skills are flagged.
- **Forecast uncertainty.** Mitigation: an uncertainty band tested by simulation and widened, scenarios labelled as what-ifs, and every number shown with its source and date.
- **Rate limits.** The Hacker News API is only called on "Refresh data".

*(132 / 150 words)*

---

## 7. Compliance & Readiness

- [ ] All APIs, cloud services, AI tools, models, and datasets used in the project are declared in this document. *(tick after the [CONFIRM] items are answered)*
- [x] All third-party code, datasets, and models are used in accordance with their licenses, and attribution is provided where required.
- [x] No API keys, passwords, or other credentials are exposed in the code repository, prototype, or this document. *(git history scanned 24 Oct 2026: `.env` was never committed; only fake test keys appear)*
- [x] Any use of generative-AI tools for development has been disclosed and reviewed by the team.
- [ ] Any use of official SDC sponsor resources has been declared in Section 5. *(tick after the Replit [CONFIRM])*
- [ ] The prototype described here is accessible to judges through the links provided in Section 1. *(tick once the live URL is filled and opens on a phone)*
- [ ] All fields in this template have been completed within the word limits stated. *(tick once the [TO FILL] items are done)*

---

## 8. Declaration

By submitting this document, the team leader confirms that the information provided is complete and accurate to the best of the team's knowledge, and that every API, cloud service, AI tool, dataset, model, and sponsor resource used in the project has been declared.

[Signature] **[Leader]** · [Date]
