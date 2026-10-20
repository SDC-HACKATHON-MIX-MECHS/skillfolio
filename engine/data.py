"""Loaders for the CSV / JSON files in data/ (shapes in contracts/README.md)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
EXAMPLE_SNAPSHOT = ROOT / "contracts" / "examples" / "snapshot.example.json"

_INT_FIELDS = {"weight", "required_level", "level_out", "prereq_level"}
_FLOAT_FIELDS = {"ai_exposure", "hours", "cost_rm"}
_LIST_FIELDS = {"aliases", "onet_examples", "proxy_soc_codes"}


def _parse(row: dict) -> dict:
    out = {}
    for key, value in row.items():
        value = (value or "").strip()
        if key == "sdgs":
            out[key] = [int(v) for v in value.split("|") if v]
        elif key in _LIST_FIELDS:
            out[key] = [v for v in value.split("|") if v]
        elif key in _INT_FIELDS:
            out[key] = int(value) if value else None
        elif key in _FLOAT_FIELDS:
            out[key] = float(value) if value else None
        else:
            out[key] = value
    return out


def read_csv(name: str) -> list[dict]:
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return [_parse(row) for row in csv.DictReader(f)]


def load_skills() -> list[dict]:
    return read_csv("skills.csv")


def load_roles() -> list[dict]:
    return read_csv("roles.csv")


def load_role_skills() -> list[dict]:
    return read_csv("role_skills.csv")


def load_courses() -> list[dict]:
    return read_csv("courses.csv")


def load_profile(profile_id: str) -> dict:
    return json.loads((DATA / "profiles" / f"{profile_id}.json").read_text(encoding="utf-8"))


def list_profiles() -> list[str]:
    return sorted(p.stem for p in (DATA / "profiles").glob("*.json"))


def list_snapshots() -> list[str]:
    """Snapshot dates available, newest first (excludes latest.json)."""
    return sorted((p.stem for p in SNAPSHOTS.glob("*.json") if p.stem != "latest"), reverse=True)


def load_snapshot(date: str = "latest") -> dict:
    """Load a snapshot by date. Falls back to the example fixture if no real snapshot exists yet."""
    path = SNAPSHOTS / f"{date}.json"
    if not path.exists():
        path = EXAMPLE_SNAPSHOT
    return json.loads(path.read_text(encoding="utf-8"))
