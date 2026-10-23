# RunPod worker: resume-to-skills matching

**What runs here:** the open embedding model `BAAI/bge-small-en-v1.5` on a RunPod Serverless GPU. The app sends resume text and our
skill catalogue (one plain sentence per skill, `app/skill_descriptions.py`). The worker returns the catalogue skills whose description is
closest to some sentence of the resume. It can only rank skill ids it was sent, so it cannot invent a skill.

**Files:** `skill_match.py` (the logic, tested in `tests/test_runpod_match.py`), `handler.py` (loads the model, starts the worker),
`Dockerfile`, `requirements.txt`. The app side is `app/runpod_client.py`; on any error or timeout the app falls back to keyword matching.

## Deploy (RunPod console)

1. **Serverless → New Endpoint → GitHub repo** → this repository, branch `main`.
2. **Dockerfile path** `runpod/Dockerfile`, **build context** `.` (repo root).
3. **GPU:** 16 GB. **Active workers 0**, **max workers 1**, **idle timeout 5 s**, **execution timeout 60 s**.
4. After the build, copy the **Endpoint ID**; create an **API key** (Settings → API Keys).
5. Put both in `.env` locally and in **Replit Secrets** as `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`.

Test it:

```bash
curl -X POST https://api.runpod.ai/v2/$RUNPOD_ENDPOINT_ID/runsync \
  -H "Authorization: Bearer $RUNPOD_API_KEY" -H "Content-Type: application/json" \
  -d '{"input": {"task": "match_skills", "text": "Built dashboards for senior management.",
       "skills": [{"skill_id": "powerbi", "text": "Building dashboards and reports for managers in Microsoft Power BI."}]}}'
```

## How the threshold was chosen (24 Oct 2026)

Five made-up resumes, scored on CPU with the same model. At a cosine cut-off of **0.73**, top 6:

| Resume | Suggested |
|---|---|
| Business analyst (dashboards, spreadsheets, queries) | Power BI 0.78, Excel 0.76, data analysis 0.74, SQL 0.74 |
| Developer (mobile app, REST API, relational DB, cloud, tests) | AWS, Azure, Google Cloud, Postgres, testing (0.78-0.82) |
| Unrelated (shelter volunteer, badminton, cooking) | nothing (best 0.55) |

Known limits: it suggests all three clouds for "a cloud server", and our catalogue has no marketing skills, so a marketing resume gets
nothing. Suggestions are shown as suggestions; the user removes wrong ones.
