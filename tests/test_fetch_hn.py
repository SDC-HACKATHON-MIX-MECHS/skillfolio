"""Tests for pipeline.fetch_hn using saved API responses (no live API calls)."""

import json

from pipeline import fetch_hn

SEARCH_PAGE = {
    "nbPages": 1,
    "hits": [
        {"objectID": "49922569", "title": "Ask HN: Who is hiring? (October 2026)"},
        {"objectID": "49922568", "title": "Ask HN: Who wants to be hired? (October 2026)"},
        {"objectID": "49522897", "title": "Ask HN: Who is hiring? (September 2026)"},
        {"objectID": "1", "title": "Ask HN: Who is hiring? (Remote edition)"},
    ],
}

ITEM = {
    "id": 49922569,
    "children": [
        {"id": 10, "created_at": "2026-10-01T15:00:00Z", "text": "Acme | Python dev | Remote"},
        {"id": 11, "created_at": "2026-10-01T15:01:00Z", "text": None},  # deleted post
        {"id": 12, "created_at": "2026-10-01T15:02:00Z", "text": "Beta | Rust | Onsite",
         "children": [{"id": 13, "text": "reply, not a job ad"}]},
    ],
}


def fake_get_json(calls):
    def _get(url):
        calls.append(url)
        return SEARCH_PAGE if "search_by_date" in url else ITEM
    return _get


def test_list_threads_keeps_only_hiring_threads(monkeypatch):
    monkeypatch.setattr(fetch_hn, "_get_json", fake_get_json([]))
    threads = fetch_hn.list_threads(months=25)
    assert [t["month"] for t in threads] == ["2026-10", "2026-09"]
    assert threads[0] == {
        "story_id": 49922569,
        "month": "2026-10",
        "title": "Ask HN: Who is hiring? (October 2026)",
        "url": "https://news.ycombinator.com/item?id=49922569",
    }


def test_fetch_thread_returns_top_level_posts_with_text(monkeypatch):
    monkeypatch.setattr(fetch_hn, "_get_json", fake_get_json([]))
    posts = fetch_hn.fetch_thread(49922569)
    assert [p["id"] for p in posts] == [10, 12]
    assert set(posts[0]) == {"id", "created_at", "text"}


def test_fetch_writes_raw_months_and_uses_cache(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(fetch_hn, "_get_json", fake_get_json(calls))
    monkeypatch.setattr(fetch_hn, "RAW_DIR", tmp_path)

    paths = fetch_hn.fetch(months=2, refresh_current=False)
    assert sorted(p.name for p in paths) == ["2026-09.json", "2026-10.json"]
    raw = json.loads((tmp_path / "2026-10.json").read_text(encoding="utf-8"))
    assert set(raw) == {"story_id", "month", "url", "retrieved_at", "posts"}
    assert raw["retrieved_at"].endswith("Z")
    assert len(raw["posts"]) == 2

    calls.clear()
    fetch_hn.fetch(months=2, refresh_current=False)
    assert not any("/items/" in url for url in calls)  # both months served from cache
