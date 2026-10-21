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


class RefreshError(RuntimeError):
    """A rebuild or refresh failed. The previous snapshot files are left unchanged."""


def refresh_latest(previous: dict, newest: dict, skills: list[dict], retrieved_at: str) -> dict:
    """Pure function: update `previous` snapshot with one freshly downloaded raw month.

    Older months' counts and every skill's exposure are reused, so no other download is
    needed. If `newest` is the snapshot's last month it is replaced; if it is a new month it
    is appended and the oldest month dropped beyond MONTHS. After changing aliases or adding
    skills in skills.csv, run a full rebuild instead so every month is counted the same way.
    """
    known = set(previous["skills"])
    added = [s["skill_id"] for s in skills if s["skill_id"] not in known]
    if added:
        raise ValueError(f"skills.csv has skills the last snapshot lacks ({', '.join(added)}); run a full rebuild")
    months = [dict(m) for m in previous["months"]]
    last = months[-1]["month"] if months else ""
    if newest["month"] < last:
        raise ValueError(f"newest thread {newest['month']} is older than the snapshot's last month {last}")

    counted = extract_skills.count_month(newest["posts"], extract_skills.compile_aliases(skills))
    total = counted["total_posts"]
    entry = {"month": newest["month"], "story_id": newest["story_id"], "url": newest["url"], "total_posts": total}
    replace = newest["month"] == last
    if replace:
        months[-1] = entry
    else:
        months.append(entry)
    drop = max(0, len(months) - MONTHS)

    snapshot_skills = {}
    for sid, prev in previous["skills"].items():
        n = counted["counts"].get(sid, 0)
        share = round(n / total, 4) if total else 0.0
        counts = prev["counts"][:-1] + [n] if replace else prev["counts"] + [n]
        shares = prev["shares"][:-1] + [share] if replace else prev["shares"] + [share]
        snapshot_skills[sid] = {**prev, "counts": counts[drop:], "shares": shares[drop:]}

    sources = [{**s, "retrieved_at": newest["retrieved_at"]} if s["id"] == HN_SOURCE["id"] else s
               for s in previous["sources"]]
    return {
        "snapshot_date": retrieved_at[:10],
        "retrieved_at": retrieved_at,
        "sources": sources,
        "months": months[drop:],
        "skills": snapshot_skills,
    }


def _full_build() -> dict:
    """Every month and both exposure sources (downloads whatever is not cached in data/raw/)."""
    # The current month is always re-fetched; older months come from the raw cache when present.
    paths = fetch_hn.fetch(months=MONTHS, refresh_current=True)
    raw_months = [json.loads(Path(p).read_text(encoding="utf-8")) for p in paths]

    downloaded = load_exposure.download_sources(force=False)
    skills = load_skills()
    onet = load_exposure.read_onet_tech(downloaded["onet_tech"]["path"])
    exposure = load_exposure.skill_exposure(
        skills, load_exposure.read_job_exposure(downloaded["aei_job_exposure"]["path"]), onet)
    load_exposure.write_role_skills_generated(load_exposure.generate_role_skills(load_roles(), skills, onet))

    hn_retrieved = max(m["retrieved_at"] for m in raw_months)
    sources = [{**HN_SOURCE, "retrieved_at": hn_retrieved}] + [
        {k: d[k] for k in ("id", "name", "url", "licence", "retrieved_at")} for d in downloaded.values()
    ]
    return assemble(raw_months, skills, exposure, sources, _now_iso())


def _refresh_current() -> dict:
    """Re-download only the newest hiring thread and update the latest snapshot (a few seconds)."""
    previous = json.loads((SNAPSHOTS / "latest.json").read_text(encoding="utf-8"))
    newest = fetch_hn.fetch_month(fetch_hn.list_threads(1)[0])
    return refresh_latest(previous, newest, load_skills(), _now_iso())


def _write(snapshot: dict) -> None:
    """Write YYYY-MM-DD.json and latest.json; temp file + rename so a failure never leaves half a file."""
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    tmp = SNAPSHOTS / ".snapshot.tmp"
    tmp.write_text(json.dumps(snapshot, indent=1), encoding="utf-8")
    out = SNAPSHOTS / f"{snapshot['snapshot_date']}.json"
    tmp.replace(out)
    shutil.copyfile(out, SNAPSHOTS / "latest.json")


def build(refresh_current_only: bool = False) -> str:
    """Fetch -> extract -> join exposure -> write snapshot. Returns the snapshot date written.
    The app's Refresh data button calls build(refresh_current_only=True).

    Refresh needs a real latest.json (committed in the repo); without one it does a full rebuild.
    Raises RefreshError (previous snapshot untouched) if a download or check fails.
    """
    latest = SNAPSHOTS / "latest.json"
    try:
        if refresh_current_only and latest.exists():
            snapshot = _refresh_current()
        else:
            snapshot = _full_build()
    except (OSError, ValueError, KeyError, IndexError) as exc:  # urllib errors are OSErrors
        raise RefreshError(f"Could not refresh data: {exc}") from exc
    _write(snapshot)
    return snapshot["snapshot_date"]


if __name__ == "__main__":
    import sys

    try:
        print(build(refresh_current_only="--refresh-current" in sys.argv))
    except RefreshError as exc:
        sys.exit(str(exc))
