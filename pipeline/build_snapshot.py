"""Build a dated snapshot (SPEC 4.4-4.5). Lane B.

Run:  python -m pipeline.build_snapshot                 # full rebuild (25 months)
      python -m pipeline.build_snapshot --refresh-current  # only re-fetch the current month
Writes data/snapshots/YYYY-MM-DD.json and data/snapshots/latest.json (shape in contracts/README.md).
"""

from __future__ import annotations


def build(refresh_current_only: bool = False) -> str:
    """Fetch -> extract -> join exposure -> write snapshot. Returns the snapshot date written.
    The app's Refresh data button calls build(refresh_current_only=True)."""
    raise NotImplementedError("lane B")


if __name__ == "__main__":
    import sys

    print(build(refresh_current_only="--refresh-current" in sys.argv))
