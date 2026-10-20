"""Download HN "Ask HN: Who is hiring?" threads (SPEC 4.1). Lane B.

Run:  python -m pipeline.fetch_hn --months 25
"""

from __future__ import annotations

import re
from pathlib import Path

API = "https://hn.algolia.com/api/v1"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "hn"
TITLE_RE = re.compile(r"^Ask HN: Who is hiring\? \((\w+) (\d{4})\)$")
REQUEST_GAP_SECONDS = 1.0


def list_threads(months: int = 25) -> list[dict]:
    """Newest-first [{story_id, month: 'YYYY-MM', title, url}] for the last `months` hiring threads.

    GET {API}/search_by_date?tags=story,author_whoishiring&query="who is hiring"&hitsPerPage=50
    (paginate with &page=N); keep titles matching TITLE_RE.
    """
    raise NotImplementedError("lane B")


def fetch_thread(story_id: int) -> list[dict]:
    """GET {API}/items/{story_id} -> top-level children with non-empty text: [{id, created_at, text}]."""
    raise NotImplementedError("lane B")


def fetch(months: int = 25, refresh_current: bool = True) -> list[Path]:
    """Write data/raw/hn/YYYY-MM.json for each month; skip cached months except the current one."""
    raise NotImplementedError("lane B")


if __name__ == "__main__":
    fetch()
