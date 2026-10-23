"""Resume-to-skills matching that runs on the RunPod endpoint. Pure Python + numpy; the embedding function is passed in, so this
file is tested without a model (tests/test_runpod_match.py) and handler.py plugs in the real one.

The model only ever ranks the skill ids it is sent (our catalogue). It cannot invent a skill, a job or a number.
"""

from __future__ import annotations

import re

import numpy as np

MODEL_NAME = "BAAI/bge-small-en-v1.5"
DEFAULT_THRESHOLD = 0.73
MIN_THRESHOLD, MAX_THRESHOLD = 0.3, 0.99
DEFAULT_TOP_K, MAX_TOP_K = 6, 15
MAX_TEXT_CHARS = 20_000
MAX_CHUNKS = 200
MAX_CHUNK_CHARS = 300
MIN_CHUNK_CHARS = 4
_BULLET = re.compile(r"^[\s•\-\*·▪●>]+")
_SENTENCE_END = re.compile(r"(?<=[.!?;])\s+")


def chunks(text: str) -> list[str]:
    """Lines, then sentences inside each line, without bullet marks. Tiny bits are dropped; count and length are capped."""
    out = []
    for line in text.splitlines():
        for piece in _SENTENCE_END.split(_BULLET.sub("", line)):
            piece = piece.strip()
            if len(piece) >= MIN_CHUNK_CHARS:
                out.append(piece[:MAX_CHUNK_CHARS])
                if len(out) == MAX_CHUNKS:
                    return out
    return out


def _unit(vectors) -> np.ndarray:
    v = np.asarray(vectors, dtype=float)
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    return v / np.where(norms == 0, 1, norms)


def match(text: str, skills: list[dict], embed, threshold: float = DEFAULT_THRESHOLD, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """[{skill_id, score}] for skills whose description is close to some sentence of `text`, best first.
    score = the best cosine similarity between the skill's text and any one sentence."""
    parts = chunks(text[:MAX_TEXT_CHARS])
    if not parts or not skills:
        return []
    sims = _unit(embed(parts)) @ _unit(embed([s["text"] for s in skills])).T
    best = sims.max(axis=0)
    found = [{"skill_id": s["skill_id"], "score": round(float(b), 3)} for s, b in zip(skills, best) if b >= threshold]
    return sorted(found, key=lambda m: -m["score"])[:top_k]


def _bad(message: str) -> dict:
    return {"error": message}


def run(job, embed) -> dict:
    """The RunPod job body. Input: {"task": "match_skills", "text": str, "skills": [{"skill_id", "text"}], "threshold"?, "top_k"?}.
    Returns {"matches": [...], "model": MODEL_NAME} or {"error": "..."}; never raises on bad input."""
    data = job.get("input") if isinstance(job, dict) else None
    if not isinstance(data, dict):
        return _bad("input must be an object")
    if data.get("task") != "match_skills":
        return _bad("unknown task")
    text, skills = data.get("text"), data.get("skills")
    if not isinstance(text, str) or not text.strip():
        return _bad("text must be a non-empty string")
    if (not isinstance(skills, list) or not skills
            or not all(isinstance(s, dict) and isinstance(s.get("skill_id"), str) and isinstance(s.get("text"), str) for s in skills)):
        return _bad("skills must be a non-empty list of {skill_id, text}")
    try:
        threshold = min(MAX_THRESHOLD, max(MIN_THRESHOLD, float(data.get("threshold", DEFAULT_THRESHOLD))))
        top_k = min(MAX_TOP_K, max(1, int(data.get("top_k", DEFAULT_TOP_K))))
    except (TypeError, ValueError):
        return _bad("threshold and top_k must be numbers")
    return {"matches": match(text, skills, embed, threshold, top_k), "model": MODEL_NAME}
