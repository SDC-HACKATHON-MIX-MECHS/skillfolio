# SkillFolio — Phase 1 Preliminary Project Proposal (draft v1)

> Draft for the team, 21 Oct 2026. Follows the official template "SDC Hackathon Phase 1: Preliminary Project Proposal".
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

---

## 2. Executive Summary & Problem Statement

### 2.1 The Problem Context *(max 250 words)*

Malaysia's young graduates are entering a job market that AI is reshaping faster than career advice can keep up. In 2024, 32.2% of Malaysian graduates worked in jobs below their qualifications, and for graduates aged 24 and under the rate was 66.0% (DOSM, Graduates Statistics 2024). At the same time, the Minister of Science, Technology and Innovation has said more than 600,000 workers must reskill within three to five years as AI changes their work (MOSTI, January 2025).

Our user is a fresh graduate or early-career switcher, such as Aina, a 23-year-old business-analytics graduate in Kuala Lumpur. She has about 200 hours to spend on learning this year and a small budget. Everyone tells her to "learn AI", but nobody can tell her which skills are actually growing, which roles she could realistically reach, or which courses are worth her limited hours.

Today's tools fail her in three ways. Skills lists and career guides are static and out of date by the time they are published. One-time assessments ignore that AI's impact is uncertain and still moving. Chatbots answer confidently but can invent jobs, courses and statistics, with no sources.

The cost is personal and national: wasted learning hours, graduates stuck in underemployment, and a workforce that reskills in the wrong direction. Choosing what to learn is an investment decision under uncertainty, but young people make it without data, without a sense of risk, and without seeing how their career could contribute to the Sustainable Development Goals.

*(247 / 250 words)*

### 2.2 The Proposed AI Solution *(max 300 words)*

SkillFolio treats a person's skills like an investment portfolio and AI as the market. It is a web app that takes the user from "who I am today" to a ranked set of reachable future roles and an ordered, costed learning plan in a few minutes.

1. **Profile.** The user picks skills and levels, or pastes CV text that is matched against our skills catalogue, then sets their learning hours, risk comfort and the SDGs they care about.
2. **Skill Market.** Every skill is shown like a stock. Its demand trend comes from real, dated job postings (about 8,000 Hacker News "Who is hiring" posts over 25 months) and its AI exposure from the Anthropic Economic Index. A statistical forecasting model estimates each skill's momentum with an 80% range, damps noisy trends, and re-runs everything under two scenarios: moderate and fast AI disruption.
3. **Portfolio and matches.** The app scores the user's growth, AI exposure, volatility and diversification, then ranks future roles with an explainable match score, a skills-gap list, and the SDG each role serves.
4. **Rebalancing plan.** An optimiser picks free and low-cost courses, in order, that improve the user's position most per learning hour within their budget. Pressing "Apply plan" shows the user's AI exposure fall and their match rise.

Every number shows its source and date, forecasts are labelled as estimates, and the app can only recommend roles and courses from our verified catalogue, so it cannot invent them. SkillFolio supports decisions; it never decides for the user.

From the SDC workshops we use **cloud hosting** (deployed on Replit), **data and database design** (dated, versioned data snapshots with fixed data contracts) and **GenAI responsibly**: an optional language-model layer may only map CV text to known skills and phrase explanations of engine output.

*(296 / 300 words)*

---

## 3. Technical Architecture & Implementation Plan

### 3.1 Conceptual Tech Stack

| Layer | Technology |
|---|---|
| Front end | Streamlit 1.66 (Python) multipage web app, Plotly 7 charts, mobile-friendly layout |
| Engine | Python 3.12, pandas, NumPy: skill forecasts (log-linear trend, shrinkage toward the average, scenario shift), portfolio metrics, role matching, greedy course planner, SDG allocation |
| Data pipeline | Python + Requests: HN Algolia API → skill extraction (alias matching) → dated JSON snapshots |
| Data store | Versioned CSV and JSON files in Git: skills, roles, role-skill weights, courses, profiles, snapshots. Every file follows a written data contract and is checked by automated tests |
| Data sources | Hacker News "Who is hiring" (HN Algolia API), Anthropic Economic Index job exposure (CC-BY), O*NET 31.0 Technology Skills (CC BY 4.0), Malaysia Labour Force Survey (data.gov.my), UN SDG targets |
| Hosting | Replit (development and public deployment) |
| Quality | pytest test suite (data integrity, engine specification, extractor accuracy), GitHub pull requests |
| AI tools | Statistical forecasting in the engine; optional LLM only for CV-to-skill mapping and explanations **[TO CONFIRM: which model, if any]** |

**System block diagram**

```
 HN Algolia API ─┐
 Anthropic EI ───┼─► pipeline/ ─► dated snapshot (JSON) ─┐
 O*NET 31.0 ─────┘                                       │
                                                          ▼
 User (phone / laptop) ─► Streamlit app on Replit ─► engine/ ─► forecasts · portfolio · matches · plan · SDG lens
                                ▲                        │
                                └── charts, sources, ◄───┘
                                    dates, estimates      ▲
                       verified catalogues (data/*.csv) ──┘
                       skills · roles + SDG targets · 55 courses
```

**Sponsor-provided GenAI API or cloud platform?** **[TO CONFIRM]** Yes: Replit (hackathon-provided Replit Core) for development and hosting the live prototype. No sponsor GenAI API is used yet.

### 3.2 Design-Thinking & Deployment Strategy *(max 200 words)*

**Empathise and define.** We started from one user and one moment: a graduate deciding where to spend about 200 learning hours. Malaysian data (DOSM, MOSTI) confirmed the problem, and we wrote five synthetic personas, from an AI-exposed accounts clerk to an engineering graduate aiming at renewable energy.

**Ideate.** We compared six concepts against the judging rubric and chose the portfolio metaphor because it makes risk, uncertainty and trade-offs intuitive.

**Prototype.** Before writing features, we fixed data contracts and acceptance tests so four people could build in parallel. Every rule (no invented courses, every number sourced and dated, no protected attributes in profiles) is enforced by automated tests.

**Test.** We run every persona through the engine to check rankings make sense, and we will do an outsider test: someone outside the team must explain the result back.

**Deploy.** The app runs on Replit from our public GitHub repository. Data refreshes write new dated snapshots, so the system keeps learning as AI moves, and the demo has a committed fallback snapshot. By Phase 2 we plan Malaysian job data, Bahasa Malaysia and Chinese interfaces, and an HR team view.

*(187 / 200 words)*

---

## 4. Preliminary Environmental & SDG Impact Framework

| Metric Category | Our Response |
|---|---|
| **Target SDG Sub-Target(s)** | **Target 4.4:** "By 2030, substantially increase the number of youth and adults who have relevant skills, including technical and vocational skills, for employment, decent jobs and entrepreneurship." Supporting: **Target 8.5:** "By 2030, achieve full and productive employment and decent work for all women and men, including for young people…" (UN SDG indicator framework) |
| **Current Problem Baseline** | 66.0% of Malaysian graduates aged 24 and under worked below their qualifications in 2024 (overall graduate rate: 32.2%, 1.60 million people) (DOSM, Graduates Statistics 2024). More than 600,000 workers must reskill within 3–5 years (MOSTI, Jan 2025). Today, a graduate has no tool that ties their learning hours to dated demand data: the planning baseline is 0% of recommendations backed by a cited, dated source. |
| **Core Measurable KPI** | (1) **Target-role match %** before vs after the recommended plan, within the user's own hour budget. (2) **Portfolio AI-exposure score** before vs after the plan. (3) **Share of recommendations with a cited, dated source** (roles, courses and numbers). (4) **Time from profile to plan**, and whether a test user can name a reachable role and their next course afterwards. |
| **Phase 2 Impact Target** | Across our 5 synthetic personas: **≥ 20% average increase** in target-role match % and **≥ 10% average reduction** in portfolio AI exposure within each persona's hour budget; **100%** of recommended roles, courses and numbers cited and dated; profile to plan in **under 3 minutes**, with **≥ 80%** of 10 outsider test users able to name a reachable role and their next course. |

**Sources**
- DOSM, *Graduates Statistics 2024* (released 31 Oct 2025): https://www.dosm.gov.my/uploads/release-content/file_20260401145140.pdf
- Malay Mail, "Mosti: AI disruption looms in Malaysia, 600,000 workers must reskill in three to five years", 7 Jan 2025: https://www.malaymail.com/news/malaysia/2025/01/07/mosti-ai-disruption-looms-in-malaysia-600000-workers-must-reskill-in-three-to-five-years/162368
- UN Statistics Division, SDG targets 4.4 and 8.5: https://unstats.un.org/sdgs/metadata/?Text=&Goal=4&Target=4.4 · https://unstats.un.org/sdgs/metadata/?Text=&Goal=8&Target=8.5
- Massenkoff & McCrory, *Labor market impacts of AI: A new measure and early evidence*, Anthropic, 5 Mar 2026: https://www.anthropic.com/research/labor-market-impacts

---

## 5. Eligibility & Readiness Checklist

- [ ] All team members have completed the mandatory GenAI, Database and Cloud Deployment upskilling workshops. **[CONFIRM WITH EVERY MEMBER]**
- [x] The project concept addresses a verified real-world problem mapped directly to one or more UN SDGs.
- [x] The proposed solution targets a functional, deployed application rather than a theoretical business case study.
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
| Anthropic Economic Index, `job_exposure.csv` | dataset | CC-BY |
| O*NET 31.0 Technology Skills | dataset | CC BY 4.0 |
| Malaysia Labour Force Survey (data.gov.my) | dataset | Malaysian open data |
| UN SDG targets (UN Statistics SDG API) | dataset | UN public data |
| Course catalogue (55 free courses from Coursera, Kaggle, Microsoft Learn, Cisco NetAcad, freeCodeCamp and others) | links and metadata only | Each provider's public listing |
| Pre-trained AI models | model | None in the prototype **[UPDATE if an LLM is added]** |

### 6.3 Employment-Related IP Conflicts
**No** **[CONFIRM WITH EVERY MEMBER]**.

---

## 7. Declaration

By submitting this proposal, the team leader confirms that the information provided is accurate to the best of the team's knowledge and that the project will be original work created during the SDC 2026 hackathon period.

[Signature] **[Leader]** · [Date]
