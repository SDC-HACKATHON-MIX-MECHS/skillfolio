"""The skill matcher that runs on the RunPod endpoint (runpod/skill_match.py), tested with a fake embedding function so no model,
GPU or network is needed. The real model is checked by hand (see runpod/README.md)."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

_PATH = Path(__file__).resolve().parents[1] / "runpod" / "skill_match.py"
_spec = importlib.util.spec_from_file_location("skill_match", _PATH)
sm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sm)

SKILLS = [{"skill_id": "powerbi", "text": "Power BI dashboards"}, {"skill_id": "sql", "text": "SQL queries"},
          {"skill_id": "excel", "text": "Excel spreadsheets"}]
AXES = {"dashboard": 0, "power bi": 0, "sql": 1, "quer": 1, "excel": 2, "spreadsheet": 2}


def fake_embed(texts):
    """One axis per skill: a text points along every axis whose keyword it mentions (unit length)."""
    out = []
    for t in texts:
        v = np.zeros(4)
        for word, axis in AXES.items():
            if word in t.lower():
                v[axis] = 1.0
        if not v.any():
            v[3] = 1.0                                   # unrelated text points somewhere else
        out.append(v / np.linalg.norm(v))
    return np.array(out)


def test_chunks_split_sentences_lines_and_bullets_and_drop_tiny_bits():
    text = "Built dashboards for management. Wrote SQL\n• Kept the team's Excel files tidy\n\n- ok\n"
    assert sm.chunks(text) == ["Built dashboards for management.", "Wrote SQL", "Kept the team's Excel files tidy"]


def test_chunks_are_capped_in_count_and_length():
    parts = sm.chunks(". ".join(f"sentence number {i} " + "x" * 600 for i in range(500)))
    assert len(parts) == sm.MAX_CHUNKS and all(len(p) <= sm.MAX_CHUNK_CHARS for p in parts)


def test_match_finds_skills_described_in_other_words_best_first():
    out = sm.match("Built dashboards for the managers. Kept spreadsheets up to date.", SKILLS, fake_embed, threshold=0.5)
    assert [o["skill_id"] for o in out] == ["powerbi", "excel"]
    assert all(0.5 <= o["score"] <= 1 for o in out)


def test_match_respects_threshold_and_top_k():
    text = "Dashboards. SQL queries. Excel spreadsheets."
    assert len(sm.match(text, SKILLS, fake_embed, threshold=0.5, top_k=2)) == 2
    assert sm.match("Went hiking and baked bread.", SKILLS, fake_embed, threshold=0.5) == []


def test_match_only_returns_ids_it_was_given():
    out = sm.match("Dashboards and SQL", SKILLS, fake_embed, threshold=0.1)
    assert {o["skill_id"] for o in out} <= {s["skill_id"] for s in SKILLS}


@pytest.mark.parametrize("job", [
    {}, {"input": None}, {"input": {"task": "nope"}}, {"input": {"task": "match_skills", "text": "", "skills": SKILLS}},
    {"input": {"task": "match_skills", "text": "SQL", "skills": []}},
    {"input": {"task": "match_skills", "text": "SQL", "skills": [{"skill_id": "x"}]}},
    {"input": {"task": "match_skills", "text": 5, "skills": SKILLS}},
])
def test_run_rejects_bad_input_with_an_error_not_an_exception(job):
    out = sm.run(job, fake_embed)
    assert set(out) == {"error"}


def test_run_returns_matches_and_the_model_name():
    out = sm.run({"input": {"task": "match_skills", "text": "Wrote SQL queries daily.", "skills": SKILLS, "threshold": 0.5}}, fake_embed)
    assert out["model"] == sm.MODEL_NAME and [m["skill_id"] for m in out["matches"]] == ["sql"]


def test_run_clamps_threshold_and_top_k():
    job = {"input": {"task": "match_skills", "text": "Dashboards. SQL. Excel.", "skills": SKILLS, "threshold": -5, "top_k": 999}}
    assert len(sm.run(job, fake_embed)["matches"]) <= sm.MAX_TOP_K
