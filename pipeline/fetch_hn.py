"""Download HN "Ask HN: Who is hiring?" threads (SPEC 4.1). Lane B.

Run:  python -m pipeline.fetch_hn --months 25
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://hn.algolia.com/api/v1"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "hn"
TITLE_RE = re.compile(r"^Ask HN: Who is hiring\? \((\w+) (\d{4})\)$")
REQUEST_GAP_SECONDS = 1.0
HN_ITEM_URL = "https://news.ycombinator.com/item?id={}"
MONTHS = {name: i for i, name in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}

_last_request = 0.0


def _get_json(url: str) -> dict:
    """GET a JSON URL, keeping at least REQUEST_GAP_SECONDS between requests."""
    global _last_request
    wait = REQUEST_GAP_SECONDS - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": "skillfolio-hackathon/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    finally:
        _last_request = time.monotonic()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def list_threads(months: int = 25) -> list[dict]:
    """Newest-first [{story_id, month: 'YYYY-MM', title, url}] for the last `months` hiring threads.

    GET {API}/search_by_date?tags=story,author_whoishiring&query="who is hiring"&hitsPerPage=50
    (paginate with &page=N); keep titles matching TITLE_RE.
    """
    threads, page = [], 0
    while len(threads) < months:
        params = urllib.parse.urlencode({
            "tags": "story,author_whoishiring",
            "query": '"who is hiring"',
            "hitsPerPage": 50,
            "page": page,
        })
        data = _get_json(f"{API}/search_by_date?{params}")
        for hit in data["hits"]:
            m = TITLE_RE.match(hit.get("title") or "")
            if m and m.group(1) in MONTHS:
                story_id = int(hit["objectID"])
                threads.append({
                    "story_id": story_id,
                    "month": f"{m.group(2)}-{MONTHS[m.group(1)]:02d}",
                    "title": hit["title"],
                    "url": HN_ITEM_URL.format(story_id),
                })
        page += 1
        if page >= data.get("nbPages", 0):
            break
    threads.sort(key=lambda t: t["month"], reverse=True)
    return threads[:months]


def fetch_thread(story_id: int) -> list[dict]:
    """GET {API}/items/{story_id} -> top-level children with non-empty text: [{id, created_at, text}]."""
    data = _get_json(f"{API}/items/{story_id}")
    return [
        {"id": c["id"], "created_at": c.get("created_at"), "text": c["text"]}
        for c in data.get("children", [])
        if c.get("text")
    ]


def fetch(months: int = 25, refresh_current: bool = True) -> list[Path]:
    """Write data/raw/hn/YYYY-MM.json for each month; skip cached months except the current one."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    current = datetime.now(timezone.utc).strftime("%Y-%m")
    paths = []
    for thread in list_threads(months):
        path = RAW_DIR / f"{thread['month']}.json"
        is_current = thread["month"] == current
        if path.exists() and not (is_current and refresh_current):
            paths.append(path)
            continue
        posts = fetch_thread(thread["story_id"])
        path.write_text(json.dumps({
            "story_id": thread["story_id"],
            "month": thread["month"],
            "url": thread["url"],
            "retrieved_at": _now_iso(),
            "posts": posts,
        }), encoding="utf-8")
        print(f"{thread['month']}  {len(posts):4d} posts  {thread['title']}")
        paths.append(path)
    return paths


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download HN 'Who is hiring?' threads.")
    parser.add_argument("--months", type=int, default=25)
    args = parser.parse_args()
    print(f"{len(fetch(args.months))} months in {RAW_DIR}")
