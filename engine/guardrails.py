"""Never show an ID we can't source (SPEC 5.6)."""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def known_ids(rows: list[dict], key: str) -> set[str]:
    return {row[key] for row in rows}


def keep_known(items: list[dict], key: str, allowed: set[str]) -> list[dict]:
    """Drop items whose `key` isn't in `allowed`, logging what was dropped."""
    kept = [item for item in items if item.get(key) in allowed]
    dropped = [item.get(key) for item in items if item.get(key) not in allowed]
    if dropped:
        log.warning("guardrail dropped unknown %s: %s", key, dropped)
    return kept
