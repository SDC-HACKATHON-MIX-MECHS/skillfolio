"""Calls our RunPod endpoint (runpod/handler.py) to suggest catalogue skills from resume text.

Needs RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID (Replit Secrets, or environment variables locally). Without them, or on ANY problem
(network, timeout, a cold GPU that takes too long, a bad reply), `suggest_skills` returns None and the app keeps its keyword matching.
Only skill ids from our own catalogue are ever returned.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from app.skill_descriptions import DESCRIPTIONS

API = "https://api.runpod.ai/v2"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"          # local only; git ignores it. Replit uses Secrets instead.
KEYS = ("RUNPOD_API_KEY", "RUNPOD_ENDPOINT_ID")
THRESHOLD = 0.73            # cosine similarity a resume sentence needs with a skill's description (tuned by hand, runpod/README.md)
TOP_K = 6
DEADLINE_S = 40             # a cold worker loads the model first; after this we give up and fall back
POLL_S = 1.5
MAX_TEXT_CHARS = 20_000


def _post(url, payload, headers, timeout):
    return requests.post(url, json=payload, headers=headers, timeout=timeout).json()


def _get(url, headers, timeout):
    return requests.get(url, headers=headers, timeout=timeout).json()


_now = time.monotonic
_sleep = time.sleep


def settings() -> dict:
    """The two keys: real environment variables (Replit Secrets) first, then KEY=value lines in a local .env file."""
    found = {}
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key.strip() in KEYS:
                found[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return {k: os.environ.get(k) or found.get(k, "") for k in KEYS}


def configured(env=None) -> bool:
    env = settings() if env is None else env
    return bool(env.get("RUNPOD_API_KEY") and env.get("RUNPOD_ENDPOINT_ID"))


def skill_texts(catalog: list[dict]) -> list[dict]:
    """What the model compares the resume with: a plain sentence about the work (app/skill_descriptions.py), or for a skill without
    one, its name and aliases."""
    out = []
    for s in catalog:
        text = DESCRIPTIONS.get(s["skill_id"]) or ". ".join(p for p in (s["name"], ", ".join(s.get("aliases") or [])) if p)
        out.append({"skill_id": s["skill_id"], "text": text})
    return out


def _matches(reply, known: set[str]) -> list[str] | None:
    if not isinstance(reply, dict) or reply.get("status") != "COMPLETED":
        return None
    output = reply.get("output")
    if not isinstance(output, dict) or not isinstance(output.get("matches"), list):
        return None
    ranked = sorted((m for m in output["matches"] if isinstance(m, dict) and m.get("skill_id") in known),
                    key=lambda m: -float(m.get("score") or 0))
    return list(dict.fromkeys(m["skill_id"] for m in ranked))


def suggest_skills(text: str, catalog: list[dict], env=None) -> list[str] | None:
    """Catalogue skill ids the model finds in `text`, best first; [] for empty text; None if the endpoint is off or failed."""
    env = settings() if env is None else env
    if not configured(env):
        return None
    text = (text or "").strip()[:MAX_TEXT_CHARS]
    if not text:
        return []
    known = {s["skill_id"] for s in catalog}
    headers = {"Authorization": f"Bearer {env['RUNPOD_API_KEY']}"}
    base = f"{API}/{env['RUNPOD_ENDPOINT_ID']}"
    payload = {"input": {"task": "match_skills", "text": text, "skills": skill_texts(catalog), "threshold": THRESHOLD, "top_k": TOP_K}}
    start = _now()
    try:
        reply = _post(f"{base}/runsync", payload, headers, DEADLINE_S)
        while isinstance(reply, dict) and reply.get("status") in ("IN_QUEUE", "IN_PROGRESS") and reply.get("id"):
            if _now() - start > DEADLINE_S:
                return None
            _sleep(POLL_S)
            job_id = reply["id"]
            reply = _get(f"{base}/status/{job_id}", headers, 10)
            if isinstance(reply, dict):
                reply.setdefault("id", job_id)
        return _matches(reply, known)
    except (OSError, ValueError, requests.RequestException, TypeError, KeyError):
        return None
