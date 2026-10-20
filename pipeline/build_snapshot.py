"""Build a dated snapshot (SPEC 4.4-4.5). Lane B.

Run:  python -m pipeline.build_snapshot                 # full rebuild (25 months)
      python -m pipeline.build_snapshot --refresh-current  # only re-fetch the current month
Writes data/snapshots/YYYY-MM-DD.json and data/snapshots/latest.json (shape in contracts/README.md).
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from engine.data import SNAPSHOTS, load_roles, load_skills
from pipeline import extract_skills, fetch_hn, load_exposure

MONTHS = 25
HN_SOURCE = {
    "id": "hn_whoishiring",
    "name": "Hacker News — Ask HN: Who is hiring?",
    "url": fetch_hn.API,
    "licence": "Public API",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def assemble(raw_months: list[dict], skills: list[dict], exposure: dict[str, dict],
             sources: list[dict], retrieved_at: str) -> dict:
    """Pure function: raw HN months + exposure -> snapshot dict (contracts/README.md#snapshot)."""
    raw_months = sorted(raw_months, key=lambda m: m["month"])  # oldest -> newest
    patterns = extract_skills.compile_aliases(skills)
    counted = [extract_skills.count_month(m["posts"], patterns) for m in raw_months]

    snapshot_skills = {}
    for s in skills:
        sid = s["skill_id"]
        counts = [c["counts"][sid] for c in counted]
        shares = [round(n / c["total_posts"], 4) if c["total_posts"] else 0.0 for n, c in zip(counts, counted)]
        snapshot_skills[sid] = {"counts": counts, "shares": shares, **exposure[sid]}

    return {
        "snapshot_date": retrieved_at[:10],
        "retrieved_at": retrieved_at,
        "sources": sources,
        "months": [
            {"month": m["month"], "story_id": m["story_id"], "url": m["url"], "total_posts": c["total_posts"]}
            for m, c in zip(raw_months, counted)
        ],
        "skills": snapshot_skills,
    }


def build(refresh_current_only: bool = False) -> str:
    """Fetch -> extract -> join exposure -> write snapshot. Returns the snapshot date written.
    The app's Refresh data button calls build(refresh_current_only=True)."""
    # Both modes re-fetch the current month; a full rebuild also fills any missing months.
    paths = fetch_hn.fetch(months=MONTHS, refresh_current=True)
    raw_months = [json.loads(Path(p).read_text(encoding="utf-8")) for p in paths]

    downloaded = load_exposure.download_sources(force=False)
    skills = load_skills()
    exposure = load_exposure.skill_exposure(
        skills,
        load_exposure.read_job_exposure(downloaded["aei_job_exposure"]["path"]),
        load_exposure.read_onet_tech(downloaded["onet_tech"]["path"]),
    )
    if not refresh_current_only:
        rows = load_exposure.generate_role_skills(
            load_roles(), skills, load_exposure.read_onet_tech(downloaded["onet_tech"]["path"]))
        load_exposure.write_role_skills_generated(rows)

    retrieved_at = _now_iso()
    hn_retrieved = max(m["retrieved_at"] for m in raw_months)
    sources = [{**HN_SOURCE, "retrieved_at": hn_retrieved}] + [
        {k: d[k] for k in ("id", "name", "url", "licence", "retrieved_at")} for d in downloaded.values()
    ]
    snapshot = assemble(raw_months, skills, exposure, sources, retrieved_at)

    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    out = SNAPSHOTS / f"{snapshot['snapshot_date']}.json"
    out.write_text(json.dumps(snapshot, indent=1), encoding="utf-8")
    shutil.copyfile(out, SNAPSHOTS / "latest.json")
    return snapshot["snapshot_date"]


if __name__ == "__main__":
    import sys

    print(build(refresh_current_only="--refresh-current" in sys.argv))
