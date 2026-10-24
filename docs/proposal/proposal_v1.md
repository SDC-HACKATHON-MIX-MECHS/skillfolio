# SkillFolio — Phase 1 Preliminary Project Proposal (draft v1)

> Draft for the team, 22 Oct 2026. Follows the official template "SDC Hackathon Phase 1: Preliminary Project Proposal".
> Final file: one PDF named `SDC2026_TeamName_Preliminary.pdf`. Items marked **[TO FILL]** need a teammate's answer.
> Word counts are given after each limited answer.

---

## 1. Team and Project Overview

| Field | Answer |
|---|---|
| Team Name | **[TO FILL]** |
| Selected Domain | Domain 1: The Aiversecity Future-Ready Workforce Domain |
| Selected SDG Track (1–17) | SDG 4: Quality Education (main, target 4.4) · SDG 8: Decent Work and Economic Growth (target 8.5) |
| Project / Solution Name | SkillFolio |
| Name (Leader) | **[TO FILL]** |
| Email & Phone (Leader) | **[TO FILL]** |
| University Affiliation(s) | **[TO FILL]** |
| Number of Team Members | 4 |
| Public GitHub repository | https://github.com/SDC-HACKATHON-MIX-MECHS/skillfolio |
| Live prototype (Replit) | **[TO FILL once Jaiydaan publishes it and it opens on a phone]** |

---

## 2. Executive Summary & Problem Statement

### 2.1 The Problem Context *(max 250 words)*

AI is reshaping Malaysia's job market faster than career advice can keep up. In 2024, 32.2% of employed Malaysian graduates worked in jobs below their qualifications, and among those aged 24 and under the rate was 66.0% (DOSM, Graduates Statistics 2024). Science, Technology and Innovation Minister Chang Lih Kang has said that "more than 600,000 workers must undergo reskilling training within three to five years to remain relevant in the increasingly competitive job market" (Malay Mail, 7 January 2025).

Our user is a fresh graduate or early-career switcher, such as Aina, a business-analytics graduate in Kuala Lumpur. She has about 200 hours to spend on learning this year and a small budget. Everyone tells her to "learn AI", but nobody can tell her which skills are actually growing, which roles she could realistically reach, or which courses are worth her limited hours.

Today's tools fail her in three ways. Skills lists and career guides are static and out of date by the time they are published. One-time assessments ignore that AI's impact is uncertain and still moving. Chatbots answer confidently but can invent jobs, courses and statistics, with no sources.

The cost is personal and national: wasted learning hours, graduates stuck below their qualifications, and a workforce that reskills in the wrong direction. Choosing what to learn is an investment decision under uncertainty, but young people make it without data, without a sense of risk, and without seeing how their career could contribute to the Sustainable Development Goals.

*(248 / 250 words)*

### 2.2 The Proposed AI Solution *(max 300 words)*

SkillFolio treats a person's skills as an investment portfolio and AI as the market. For Aina, it estimates that demand for her current skills grows about 9.7% a year, rates their AI impact at 19 out of 100, and ranks Systems Analyst as her closest role at 68% Fit. A plan of two free courses, 35.5 hours in total, raises that Fit to 88%.

1. **Profile.** The user picks skills and levels, or pastes CV text that keyword rules and an optional embedding model map to our 73-skill catalogue, then sets hours, risk comfort and SDGs.
2. **Skill Market.** Each skill's demand trend comes from 7,961 dated Hacker News "Who is hiring" posts over 25 months. Its AI exposure is derived from the Anthropic Economic Index's occupation-level scores. A statistical model estimates momentum with a nominal 80% band, damps noisy trends, and re-runs under moderate and fast AI-disruption scenarios.
3. **Matches.** Roles are ranked by an explainable Fit score with a skills-gap list and the UN SDG target each role serves. The SDGs the user picks tilt the ranking.
4. **Plan.** A greedy optimiser orders free courses by their gain in Fit and outlook per learning hour, within the user's hours.

What sets SkillFolio apart is honesty. We tested our uncertainty band by simulation: the nominal 80% band covered only 48%, so we widened it to about 76%. Scenarios are labelled as what-ifs, skills with too little data are flagged rather than headlined, every number shows its source and date, and an ID allow-list means only catalogued roles and courses can appear. 855 automated tests check data and engine. SkillFolio informs; the user decides.

From the SDC workshops we use cloud hosting (Replit; a RunPod GPU for the embedding model) and data design (dated, versioned snapshots under written contracts).

*(299 / 300 words)*

---

## 3. Technical Architecture & Implementation Plan

### 3.1 Conceptual Tech Stack

| Layer | Technology |
|---|---|
| Front end | Streamlit 1.66 (Python) multipage web app, Plotly 7 charts, mobile-friendly layout |
| Engine | Python 3.12, pandas, NumPy: skill forecasts (log-linear trend, shrinkage toward the average, scenario shift), portfolio metrics, role matching, greedy course planner, SDG allocation |
| Data pipeline | Python + Requests: HN Algolia API → skill extraction (fixed alias rules) → dated JSON snapshots |
| Data store | Versioned CSV and JSON files in Git: 73 skills, 20 roles, curated role-skill lists, 52 courses, 5 synthetic profiles, dated snapshots. Every file follows a written data contract and is checked by automated tests |
| Data sources | Hacker News "Who is hiring" (HN Algolia API); Anthropic Economic Index occupation exposure (CC-BY), from which we derive skill exposure; O*NET 31.0 Technology Skills (CC BY 4.0); UN SDG targets, mapped to roles by hand |
| Hosting | Replit (development and public deployment); RunPod Serverless GPU for the embedding model (scales to zero when idle) |
| Quality | pytest suite (855 tests passing on 24 Oct 2026: data integrity, engine specification, extractor accuracy, resume matching), GitHub pull requests with review |
| AI in the product | Statistical forecasting and optimisation. For resume reading, an optional open embedding model (BAAI/bge-small-en-v1.5, MIT licence) on a RunPod Serverless GPU suggests skills by meaning. It can only return skill IDs from our catalogue, suggestions are shown on the next step for the user to remove any that are wrong, and if it is unavailable the app falls back to fixed keyword rules. SkillFolio stores no copy of the resume text. No generative language model is used |
| AI in development | Built with the help of Claude Code (Anthropic) and Replit Agent. The team reviewed all logic, and every change goes through tests and a pull request |

**System block diagram**

```
 HN Algolia API ─┐
 Anthropic EI ───┼─► pipeline/ ─► dated snapshot (JSON) ─┐
 O*NET 31.0 ─────┘                                       │
                                                          ▼
 User (phone / laptop) ─► Streamlit app on Replit ─► engine/ ─► forecasts · portfolio · matches · plan · SDG lens
                                │  ▲
        resume text (optional) ▼  │ catalogue skill IDs only
                      RunPod GPU: bge-small-en-v1.5 embedding model
                                ▲                        │
                                └── charts, sources, ◄───┘
                                    dates, estimates      ▲
                       verified catalogues (data/*.csv) ──┘
                       skills · roles + SDG targets · 52 courses
```

**Sponsor-provided GenAI API or cloud platform?** Replit, through the hackathon's Replit Core access, for development and hosting the live prototype. No sponsor GenAI API is used.

### 3.2 Design-Thinking & Deployment Strategy *(max 200 words)*

**Empathise and define.** We started from one user and one moment: a graduate deciding where to spend about 200 learning hours. We wrote five synthetic personas, from an AI-exposed accounts clerk to an engineering graduate aiming at renewable energy.

**Ideate and prototype.** We compared six concepts against the rubric and chose the portfolio metaphor because it makes risk and trade-offs intuitive. We fixed data contracts and acceptance tests first, so four people could build in parallel. Key rules are guarded by data tests and an ID allow-list.

**Test.** We run every persona through the engine, and outsiders will explain the result back to us.

**Hardest risk.** Our trend signal is narrow: Hacker News postings are global and tech-heavy, and role skill lists need human curation before rankings make sense. **Fallback:** committed, dated snapshots, so the demo never depends on a live API; a curated, closed catalogue of roles, skills and courses; the limit stated openly in the app; and Malaysian occupation data as a Phase 2 upgrade.

**Deploy.** The app runs on Replit from our public GitHub repository, and every data refresh writes a new dated snapshot.

*(187 / 200 words)*

---

## 4. Preliminary Environmental & SDG Impact Framework

| Metric Category | Our Response |
|---|---|
| **Target SDG Sub-Target(s)** | **Target 4.4:** "By 2030, substantially increase the number of youth and adults who have relevant skills, including technical and vocational skills, for employment, decent jobs and entrepreneurship." Supporting: **Target 8.5:** "By 2030, achieve full and productive employment and decent work for all women and men, including for young people…" (UN SDG indicator framework) |
| **Current Problem Baseline** | 32.2% of employed Malaysian graduates (1.60 million people) worked below their qualifications in 2024; for those aged 24 and under the rate was 66.0% (DOSM, Graduates Statistics 2024). More than 600,000 workers must undergo reskilling training within three to five years (Minister Chang Lih Kang, Malay Mail, 7 Jan 2025). |
| **Core Measurable KPI** | (1) **Fit gain:** a learner's Fit for their target role before vs after the plan, within their own hour budget. (2) **AI impact (0–100) and outlook score** before vs after, reported beside the Fit gain so trade-offs stay visible. (3) **Share of recommended roles, courses and numbers that carry a source and date.** (4) **Time from profile to plan.** |
| **Phase 2 Impact Target** | **Measured today** on the merged data (5 sample profiles × their top 3 roles, moderate scenario): Apply plan raises Fit by **41 points on average**, within each learner's own hours. AI impact stays about flat (**−0.3 points**), and the outlook score falls in **11 of 15** cases. **By Phase 2:** keep the average Fit gain at **≥ 40 points** while showing AI impact and outlook beside it on every plan; **100%** of recommended roles, courses and numbers sourced and dated; profile to plan in **under 3 minutes**, with **≥ 80%** of 10 outsider testers able to name a reachable role and their next course. |

**About the courses:** all 52 courses in the catalogue cost RM 0 and need no trial or payment. HRD Corp status is recorded for every course, but we have not yet found a source for any, so all are marked "unknown".

**Sources**
- DOSM, *Graduates Statistics 2024* (released 31 Oct 2025): https://www.dosm.gov.my/uploads/release-content/file_20260401145140.pdf
- Malay Mail, "Mosti: AI disruption looms in Malaysia, 600,000 workers must reskill in three to five years", 7 Jan 2025: https://www.malaymail.com/news/malaysia/2025/01/07/mosti-ai-disruption-looms-in-malaysia-600000-workers-must-reskill-in-three-to-five-years/162368
- UN Statistics Division, SDG targets 4.4 and 8.5: https://unstats.un.org/sdgs/metadata/?Text=&Goal=4&Target=4.4 · https://unstats.un.org/sdgs/metadata/?Text=&Goal=8&Target=8.5
- Anthropic Economic Index, `job_exposure.csv`: https://huggingface.co/datasets/Anthropic/EconomicIndex · method: Massenkoff & McCrory, *Labor market impacts of AI: A new measure and early evidence*, Anthropic, 5 Mar 2026: https://www.anthropic.com/research/labor-market-impacts
- Measured figures (Aina's line, Fit gain, AI impact, outlook, test count): SkillFolio repository, snapshot of 20 Oct 2026, `main` on 22 Oct 2026 (test count: `main` with the RunPod resume-matching branch, 24 Oct 2026)

---

## 5. Eligibility & Readiness Checklist

- [ ] All team members have completed the mandatory GenAI, Database and Cloud Deployment upskilling workshops. **[CONFIRM WITH EVERY MEMBER]**
- [x] The project concept addresses a verified real-world problem mapped directly to one or more UN SDGs.
- [ ] The proposed solution targets a functional, deployed application rather than a theoretical business case study. *(tick once the live Replit link opens on a phone)*
- [ ] All fields in this template have been completed within the word limits stated. *(tick once the [TO FILL] items are done)*

---

## 6. IP & Originality Declaration

### 6.1 Pre-Existing / Prior-Owned Work
**No** **[CONFIRM WITH EVERY MEMBER]**. All code, data files and documents were created during the hackathon period, from 20 Oct 2026.

### 6.2 Third-Party Code, Datasets, or Models
**Yes.**

| Name | Type | Licence |
|---|---|---|
| Streamlit 1.66 | code | Apache-2.0 |
| pandas 3.0 | code | BSD-3-Clause |
| NumPy 2.5 | code | BSD-3-Clause (with 0BSD, MIT, Zlib, CC0 parts) |
| Plotly 7.1 | code | MIT |
| Requests 2.34 | code | Apache-2.0 |
| pytest 9.1 | code (testing) | MIT |
| Hacker News "Who is hiring" posts via HN Algolia API | dataset | Public API |
| Anthropic Economic Index, `job_exposure.csv` (occupation exposure; our skill exposure is derived from it) | dataset | CC-BY |
| O*NET 31.0 Technology Skills | dataset | CC BY 4.0 |
| UN SDG target wording (targets mapped to roles by the team) | reference text | UN public data |
| Course catalogue (52 free courses from freeCodeCamp, Microsoft Learn, Kaggle, Cisco NetAcad, AWS Skill Builder, The Open University and others) | links and metadata only | Each provider's public listing |
| Claude Code (Anthropic) | AI development tool: helped write code, tests, data files, documents and this proposal | Anthropic terms of service |
| Replit Agent | AI development tool: helped write code | Replit terms of service |
| BAAI/bge-small-en-v1.5 (pre-trained embedding model, used unchanged for resume-to-skill matching) | model | MIT |
| sentence-transformers | code | Apache-2.0 |
| PyTorch | code | BSD-3-Clause |
| RunPod Python SDK, RunPod Serverless | code; cloud GPU platform | MIT; RunPod terms of service |

All AI-assisted output was reviewed by the team, checked by the automated tests and merged through pull requests.

### 6.3 Employment-Related IP Conflicts
**No** **[CONFIRM WITH EVERY MEMBER]**.

---

## 7. Declaration

By submitting this proposal, the team leader confirms that the information provided is accurate to the best of the team's knowledge and that the project will be original work created during the SDC 2026 hackathon period.

**Use of generative AI.** The team used **Claude Code (Anthropic)** throughout the hackathon to help write the code, tests, data files, documents and this proposal, and **Replit Agent** to help build app pages. The team set the direction, reviewed all AI-assisted output, and checked it with the automated test suite and pull-request review before merging. The only AI model inside the product is the open embedding model listed in 6.2.

[Signature] **[Leader]** · [Date]
