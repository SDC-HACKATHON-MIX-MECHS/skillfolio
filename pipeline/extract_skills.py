"""Count which skills each month's job posts mention (SPEC 4.2). Lane B.

The same matcher is reused by the Profile page to read pasted CV text,
so it must not depend on HN-specific formatting.
"""

from __future__ import annotations

import re


def clean_html(text: str) -> str:
    """html.unescape, replace tags with spaces, collapse whitespace."""
    raise NotImplementedError("lane B")


def compile_aliases(skills: list[dict]) -> dict[str, list[re.Pattern]]:
    """skill_id -> regexes. Word boundaries; case-insensitive unless the alias starts with 'cs:'.
    Careful with aliases containing symbols (c++, c#, .net, ci/cd): escape them and use
    lookarounds instead of \\b."""
    raise NotImplementedError("lane B")


def skills_in_text(text: str, patterns: dict[str, list[re.Pattern]]) -> set[str]:
    """Skill IDs mentioned at least once in `text`."""
    raise NotImplementedError("lane B")


def count_month(posts: list[dict], patterns: dict[str, list[re.Pattern]]) -> dict:
    """{'total_posts': n, 'counts': {skill_id: posts mentioning it}} - one count per post, not per mention."""
    raise NotImplementedError("lane B")
