"""Pure data shaping for the Home dashboard. No Streamlit import, so every function here is unit-tested.

Inputs come from `engine.api.analyse` (plain dicts); outputs are plain lists/dicts the UI helpers render.
"""

from __future__ import annotations

SPARK_CAP = 400.0                      # a skill that appears late has a huge index; cap it so sparklines stay readable
RANGES = {"6M": 6, "1Y": 12, "All": None}   # months shown on the demand chart; None = every month in the snapshot
DEFAULT_RANGE = "1Y"


def basket_index(weights: dict[str, float], indices: dict[str, list[float]],
                 skip: set[str] | frozenset[str] = frozenset(), months: int | None = None) -> tuple[list[float], list[str]]:
    """Weighted demand index of a skill basket over a window; every skill starts the window at 100.

    `weights` is {skill_id: portfolio weight}; `indices` is {skill_id: that skill's demand index} (engine
    forecast "index", one value per snapshot month). `months` = window length (None = every month): each skill's
    index is cut to the last months + 1 points and rebased so its first point is 100, then the skills are
    averaged with their weights. A skill is left out (and returned in the second value) when it is in `skip`
    (e.g. thin data), has no index, an index shorter than the longest one, or no demand at the window start.
    The remaining weights are renormalised to sum to 1. Returns ([], left_out) when nothing is usable.
    This is MARKET DEMAND for the skills, not a history of the user's own score.
    """
    n = max((len(v) for v in indices.values()), default=0)
    usable: dict[str, list[float]] = {}
    left_out: list[str] = []
    for skill_id, weight in weights.items():
        idx = indices.get(skill_id) or []
        window = rebase(slice_range(list(idx), months)) if len(idx) == n and n else []
        if skill_id in skip or weight <= 0 or not window or window[0] <= 0:
            left_out.append(skill_id)
        else:
            usable[skill_id] = window
    total = sum(weights[s] for s in usable)
    if not usable or total <= 0:
        return [], left_out
    length = len(next(iter(usable.values())))
    series = [sum(weights[s] * w[i] for s, w in usable.items()) / total for i in range(length)]
    return series, left_out


def slice_range(series: list, months: int | None) -> list:
    """The last `months` months of a series: months + 1 points, so the first point is the starting level."""
    if months is None or len(series) <= months + 1:
        return list(series)
    return list(series[-(months + 1):])


def rebase(series: list[float], base: float = 100.0) -> list[float]:
    """Scale a series so its first value equals `base`. A non-positive first value returns a copy unchanged."""
    if not series or series[0] <= 0:
        return list(series)
    k = base / series[0]
    return [v * k for v in series]


def pct_change(series: list[float]) -> float | None:
    """Last / first - 1 as a fraction, or None when it can't be computed."""
    if len(series) < 2 or series[0] <= 0:
        return None
    return series[-1] / series[0] - 1


def spark_values(index: list[float] | None, cap: float = SPARK_CAP) -> list[float]:
    return [min(float(v), cap) for v in (index or [])]


def holdings(result: dict) -> list[dict]:
    """The user's skills for the Holdings list, biggest weight first.

    Each row: skill_id, level (1..3), weight, projected (12-month estimate, fraction), thin (bool),
    exposure (0..1 or None), index (demand index list, may be empty), trajectory ("rising"/"stable"/"declining").
    """
    forecasts = result["forecasts"]
    rows = []
    for s in result["skills"]:
        f = forecasts.get(s["skill_id"], {})
        rows.append({
            "skill_id": s["skill_id"], "level": s["level"], "weight": s["weight"], "projected": s["projected"],
            "thin": bool(s["thin_data"]), "exposure": s["exposure"], "index": f.get("index", []),
            "trajectory": f.get("trajectory"),
        })
    return sorted(rows, key=lambda r: (-r["weight"], r["skill_id"]))


