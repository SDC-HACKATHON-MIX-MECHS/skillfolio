"""Count which skills each month's job posts mention (SPEC 4.2). Lane B.

The same matcher is reused by the Profile page to read pasted CV text,
so it must not depend on HN-specific formatting.
"""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")

# Extra context rules for aliases that are also common English words.
# Keyed by the alias exactly as written in skills.csv.
_NOT_FOLLOWED_BY = {
    # "Go to our careers page", "Go ahead and apply" are not the language.
    "cs:Go": r"\s+(?:to|ahead|here|through|back|live|check|apply|visit|see)\b",
}


def clean_html(text: str) -> str:
    """html.unescape, replace tags with spaces, collapse whitespace."""
    text = _TAG_RE.sub(" ", html.unescape(text or ""))
    return _SPACE_RE.sub(" ", text).strip()


def _alias_regex(alias: str) -> re.Pattern:
    case_sensitive = alias.startswith("cs:")
    term = alias[3:] if case_sensitive else alias
    # Lookarounds instead of \b so aliases with symbols (c++, c#, .net, ci/cd) work.
    pattern = rf"(?<![\w]){re.escape(term)}(?![\w])"
    if alias in _NOT_FOLLOWED_BY:
        pattern += rf"(?!{_NOT_FOLLOWED_BY[alias]})"
    return re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)


def compile_aliases(skills: list[dict]) -> dict[str, list[re.Pattern]]:
    """skill_id -> regexes. Word boundaries; case-insensitive unless the alias starts with 'cs:'.
    Careful with aliases containing symbols (c++, c#, .net, ci/cd): escape them and use
    lookarounds instead of \\b."""
    return {s["skill_id"]: [_alias_regex(a) for a in s["aliases"]] for s in skills}


def skills_in_text(text: str, patterns: dict[str, list[re.Pattern]]) -> set[str]:
    """Skill IDs mentioned at least once in `text`."""
    return {skill_id for skill_id, regexes in patterns.items() if any(rx.search(text) for rx in regexes)}


def count_month(posts: list[dict], patterns: dict[str, list[re.Pattern]]) -> dict:
    """{'total_posts': n, 'counts': {skill_id: posts mentioning it}} - one count per post, not per mention."""
    counts = dict.fromkeys(patterns, 0)
    for post in posts:
        for skill_id in skills_in_text(clean_html(post["text"]), patterns):
            counts[skill_id] += 1
    return {"total_posts": len(posts), "counts": counts}
