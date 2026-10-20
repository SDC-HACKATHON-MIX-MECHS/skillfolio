"""Builds the illustrative snapshots used by the forecast golden tests. Pure Python, deterministic.

Run:  python tests/fixtures/make_snapshots.py      (rewrites snapshot_30m.json and snapshot_3m.json)

These are NOT real data. They exist so every rule in docs/SPEC.md section 5.1 changes at least
one number: window sizes (12 / 24 / full), epsilon (mean vs min vs last month), late-appearing
skills, thin-data cutoffs, unknown exposure.
"""

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
MONTHS = 30


def month_label(i: int) -> str:
    year, month = divmod(2024 * 12 + 4 + i, 12)
    return f"{year}-{month + 1:02d}"


TOTALS = [round(190 + 70 * math.sin(0.9 * m) + 3 * m) for m in range(MONTHS)]


def from_share(fn):
    counts = [round(fn(m) * TOTALS[m]) for m in range(MONTHS)]
    return counts


def u_turn(m):  # falls for 18 months then rises: 12-month trend is up, whole-series trend is flat
    return 0.20 - 0.12 * (m / 17) if m <= 17 else 0.08 + 0.12 * ((m - 17) / 12)


def noisy_early(m):  # loud early, calmer later: volatility depends on the window
    amplitude = 0.08 if m < 6 else 0.04 if m < 18 else 0.005
    return 0.10 + amplitude * (-1) ** m


def late_riser(m):  # absent for 15 months, then climbs
    return 0.0 if m < 15 else 0.01 + 0.11 * ((m - 15) / 14)


def unknown_exp(m):
    return 0.05 + 0.10 * (m / (MONTHS - 1))


SPARSE_PATTERN = [2, 0, 3, 1, 0, 4, 1, 2, 0, 1]  # mean 1.4 posts a month

SKILLS = {
    # skill: (counts, exposure)
    "u_turn": (from_share(u_turn), 0.30),
    "noisy_early": (from_share(noisy_early), 0.55),
    "late_riser": (from_share(late_riser), 0.15),
    "sparse": ([SPARSE_PATTERN[m % 10] for m in range(MONTHS)], 0.65),
    "sparse_clumpy": ([12 if m % 6 == 2 else 0 for m in range(MONTHS)], 0.50),  # mean 2.0, but 12 in busy months
    "just_under": ([3] * 29 + [0], 0.0),                                        # mean 2.9 -> thin; known exposure of exactly 0.0 must count in the average
    "exactly_3": ([6 if m % 2 == 0 else 0 for m in range(MONTHS)], 0.45),       # mean 3.0 -> not thin
    "all_zero": ([0] * MONTHS, 0.90),
    "unknown_exp": (from_share(unknown_exp), None),
    # flat and well-observed, so the interval is narrow and the scenario shift decides the label:
    "shift_up": (from_share(lambda m: 0.30), 0.10),     # sheltered: fast scenario lifts it clear of +5%, moderate does not
    "shift_down": (from_share(lambda m: 0.30), 1.0),    # most exposed: fast scenario pushes it below -5%, moderate does not
    "faded": ([5] * 18 + [0] * 12, 0.40),               # mean 3.0 overall (not thin) but silent for the last 12 months
}


def build(totals, skills, note):
    return {
        "_note": note,
        "is_example": True,
        "snapshot_date": "2026-01-01",
        "retrieved_at": "2026-01-01T00:00:00Z",
        "sources": [{"id": "example", "name": "Illustrative fixture", "url": "https://example.org", "licence": "n/a", "retrieved_at": "2026-01-01T00:00:00Z"}],
        "months": [{"month": month_label(i), "story_id": 0, "url": "https://example.org", "total_posts": t} for i, t in enumerate(totals)],
        "skills": {
            sid: {
                "counts": counts,
                "shares": [c / t for c, t in zip(counts, totals)],
                "exposure": exposure,
                "exposure_n_occupations": 0 if exposure is None else 5,
                "exposure_method": None if exposure is None else "example",
            }
            for sid, (counts, exposure) in skills.items()
        },
    }


if __name__ == "__main__":
    note = "ILLUSTRATIVE FIXTURE for forecast tests. Made-up numbers, not real data."
    (HERE / "snapshot_30m.json").write_bytes((json.dumps(build(TOTALS, SKILLS, note), indent=1) + "\n").encode("utf-8"))
    three = {
        "rising3": ([10, 12, 16], 0.40),
        "falling3": ([20, 16, 10], 0.40),
        "exposed3": ([30, 30, 30], 0.90),     # exactly flat, so the 3-month scenario shift alone moves its number and label
        "sheltered3": ([30, 30, 30], 0.10),
    }
    (HERE / "snapshot_3m.json").write_bytes((json.dumps(build([200, 200, 200], three, note), indent=1) + "\n").encode("utf-8"))
    print("totals:", TOTALS[:6], "... min", min(TOTALS), "max", max(TOTALS), "last", TOTALS[-1], "mean", sum(TOTALS) / MONTHS)
