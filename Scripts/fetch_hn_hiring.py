"""Fetch Hacker News "Ask HN: Who is hiring?" threads and count skill mentions per month.

Source: HN Algolia API (https://hn.algolia.com/api), public, no key needed.
Each monthly thread's top-level comments are job ads. For each month we record the
share of ads that mention each skill, and write one dated snapshot of TrendSignal records.

Usage:
    python Scripts/fetch_hn_hiring.py              # last 12 months
    python Scripts/fetch_hn_hiring.py --months 36

Output:
    data/snapshots/YYYY-MM-DD.json   (committed)
    data/raw/hn/<thread_id>.json     (cache of raw API responses, git-ignored)

Only counts are stored in the snapshot, never the ad text.
Standard library only, so it runs on Replit with no installs.
"""

import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://hn.algolia.com/api/v1"
HN_ITEM_URL = "https://news.ycombinator.com/item?id={}"
SOURCE = "Hacker News 'Ask HN: Who is hiring?' via HN Algolia API"

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "hn"
SNAPSHOT_DIR = ROOT / "data" / "snapshots"

# Starter skill list: skill_id -> regex. Placeholder until the shared skills
# taxonomy (Lane B) is agreed; IDs here should match it once it exists.
# Patterns are case-insensitive unless they start with (?-i).
SKILL_PATTERNS = {
    "python": r"\bpython\b",
    "javascript": r"\bjavascript\b|\bjs\b",
    "typescript": r"\btypescript\b",
    "react": r"\breact(?:\.?js)?\b(?!\s+native)",
    "nodejs": r"\bnode(?:\.?js)?\b",
    "java": r"\bjava\b(?!\s*script)",
    "go": r"\bgolang\b|(?-i:\bGo\b)(?=\s*[,/)|])",
    "rust": r"\brust\b",
    "sql": r"\bsql\b|\bpostgres(?:ql)?\b|\bmysql\b",
    "aws": r"\baws\b|\bamazon web services\b",
    "kubernetes": r"\bkubernetes\b|\bk8s\b",
    "docker": r"\bdocker\b",
    "terraform": r"\bterraform\b",
    "machine_learning": r"\bmachine learning\b|\bml\b",
    "llm": r"\bllms?\b|\blarge language models?\b|\bgenai\b|\bgenerative ai\b",
    "pytorch": r"\bpytorch\b",
    "data_engineering": r"\bdata engineer(?:ing)?\b",
}
COMPILED = {k: re.compile(p, re.IGNORECASE) for k, p in SKILL_PATTERNS.items()}

TAG_RE = re.compile(r"<[^>]+>")


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "skillfolio-hackathon/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def find_threads(months: int) -> list[dict]:
    """Return the newest `months` 'Who is hiring?' threads, newest first."""
    threads, page = [], 0
    while len(threads) < months:
        params = urllib.parse.urlencode({
            "tags": "story,author_whoishiring",
            "query": "Who is hiring",
            "hitsPerPage": 100,
            "page": page,
        })
        data = get_json(f"{API}/search_by_date?{params}")
        for hit in data["hits"]:
            if hit["title"].startswith("Ask HN: Who is hiring?"):
                threads.append(hit)
        page += 1
        if page >= data["nbPages"]:
            break
    return threads[:months]


def fetch_thread(thread_id: str) -> dict:
    """Fetch a thread with all comments, using the raw cache if present."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache = RAW_DIR / f"{thread_id}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    data = get_json(f"{API}/items/{thread_id}")
    cache.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(0.5)  # be polite to the API
    return data


def job_ads(thread: dict) -> list[str]:
    """Plain text of each top-level comment (one job ad each); skips deleted ones."""
    ads = []
    for child in thread.get("children", []):
        if child.get("text"):
            ads.append(TAG_RE.sub(" ", html.unescape(child["text"])))
    return ads


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--months", type=int, default=12)
    args = parser.parse_args()

    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    signals, summary = [], []

    for hit in find_threads(args.months):
        thread_id = hit["objectID"]
        period = hit["created_at"][:7]  # YYYY-MM
        ads = job_ads(fetch_thread(thread_id))
        if not ads:
            continue
        summary.append((period, len(ads)))
        print(f"{period}  {len(ads):4d} ads  {hit['title']}")

        for skill_id, rx in COMPILED.items():
            hits = sum(1 for ad in ads if rx.search(ad))
            signals.append({
                "skill_id": skill_id,
                "source": SOURCE,
                "source_url": HN_ITEM_URL.format(thread_id),
                "retrieved_at": retrieved_at,
                "metric": "share_of_job_posts",
                "value": round(hits / len(ads), 4),
                # Proposed additions to the TrendSignal contract:
                "period": period,
                "sample_size": len(ads),
            })

    snapshot = {
        "source": SOURCE,
        "api": API,
        "retrieved_at": retrieved_at,
        "metric_definition": "Fraction of top-level job ads in the month's thread "
                             "that mention the skill (regex match, case-insensitive).",
        "skill_patterns": SKILL_PATTERNS,
        "periods": [{"period": p, "sample_size": n} for p, n in summary],
        "signals": signals,
    }

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAPSHOT_DIR / f"{retrieved_at[:10]}.json"
    out.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"\nWrote {len(signals)} signals to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
