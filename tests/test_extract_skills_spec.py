"""Acceptance tests for the skill matcher (SPEC 4.2), on hand-labelled real posts."""

import pytest

from engine.data import load_skills
from pipeline import extract_skills

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

# Excerpts of real HN "Who is hiring?" posts (2024-11 .. 2026-10), labelled by hand (2026-10-20).
REAL_CASES = [
    ("Stack is Rails/React/Typescript/Postgres/Elasticsearch", {"ruby", "react", "typescript", "postgres"}),
    ("Full Stack Engineer who can transform python backend into a working MVP.", {"python"}),
    ("We're building the world's fastest change data capture (CDC) platform for Postgres.", {"postgres"}),
    ("CoVar is a small R&D company specializing in AI/ML and software", set()),
    ("You'll be working alongside peers who excel at navigating ambiguity", set()),
    ("optimization methods (AI) to build the financial rails of our future energy systems", set()),
    ("We're looking for someone deeply embedded in agentic engineering practice", {"ai_agents"}),
    ("iOS Engineer [Tech Stack: Swift, SwiftUI, UIKit, Mapbox] ++ Senior Security Engineer [SIEM, IDS/IPS]",
     {"swift_ios", "security"}),
    ("Tech stack: Kotlin, C#, Objective-C, Swift, AppKit, UIKit, SwiftUI, C, C++.",
     {"kotlin", "csharp_dotnet", "swift_ios", "cpp"}),
    ("Stack: AWS, Databricks/Spark, Python, PostgreSQL, Agentic AI.", {"aws", "spark", "python", "postgres", "ai_agents"}),
    ("Experience with LangGraph, LangChain, MCP, RAG, vector databases, or AI agents is a strong plus",
     {"llm", "ai_agents"}),
    ("building and operating industrial-size Battery Energy Storage Systems", {"energy_climate"}),
    ("automatically configures itself optimizing battery-life and location accuracy", set()),
    ("Stack: TypeScript everywhere. React, React Native, Node.js, NestJS, MongoDB.",
     {"typescript", "react", "nodejs", "mongodb"}),
    ("We are agile and always willing to roll up our sleeves", set()),
]
CASES += REAL_CASES


@pytest.mark.parametrize("text,expected", CASES)
def test_skills_in_text(text, expected):
    patterns = extract_skills.compile_aliases(load_skills())
    assert extract_skills.skills_in_text(text, patterns) == expected


def test_count_month_counts_posts_not_mentions():
    patterns = extract_skills.compile_aliases(load_skills())
    posts = [{"text": "Python Python Python"}, {"text": "Rust"}, {"text": "Python and Rust"}]
    result = extract_skills.count_month(posts, patterns)
    assert result["total_posts"] == 3
    assert result["counts"]["python"] == 2 and result["counts"]["rust"] == 2


def test_clean_html_unescapes():
    assert extract_skills.clean_html("C&#x2B;&#x2B; <p>and</p> TypeScript &#x2F; React") == "C++ and TypeScript / React"
