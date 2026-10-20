"""Acceptance tests for lane B's skill matcher (SPEC 4.2). xfail until implemented.
Lane B: grow this to ~15 hand-labelled real posts."""

import pytest

from engine.data import load_skills
from pipeline import extract_skills

todo = pytest.mark.xfail(raises=NotImplementedError, reason="lane B: not implemented yet", strict=False)

CASES = [
    ("We use Python, PostgreSQL and AWS.", {"python", "postgres", "aws"}),
    ("Frontend in TypeScript + React; JavaScript experience a plus.", {"typescript", "react", "javascript"}),
    ("Senior Java engineer (Spring Boot).", {"java"}),
    ("Our stack: C++ and C# on .NET.", {"cpp", "csharp_dotnet"}),
    ("Go to our careers page to apply.", set()),
    ("Backend in Go and Rust.", {"golang", "rust"}),
    ("Excellent communication skills required.", set()),
    ("Machine learning engineer working on LLMs and RAG pipelines.", {"ml", "llm"}),
]


@todo
@pytest.mark.parametrize("text,expected", CASES)
def test_skills_in_text(text, expected):
    patterns = extract_skills.compile_aliases(load_skills())
    assert extract_skills.skills_in_text(text, patterns) == expected


@todo
def test_count_month_counts_posts_not_mentions():
    patterns = extract_skills.compile_aliases(load_skills())
    posts = [{"text": "Python Python Python"}, {"text": "Rust"}, {"text": "Python and Rust"}]
    result = extract_skills.count_month(posts, patterns)
    assert result["total_posts"] == 3
    assert result["counts"]["python"] == 2 and result["counts"]["rust"] == 2


@todo
def test_clean_html_unescapes():
    assert extract_skills.clean_html("C&#x2B;&#x2B; <p>and</p> TypeScript &#x2F; React") == "C++ and TypeScript / React"
