#!/bin/bash
# Mutation check: runs every deliberately broken version in a plug (default plug/mutplug.py = engine/forecast.py;
# also mutplug_portfolio, mutplug_matching, mutplug_sdg, mutplug_api, mutplug_pathway) against the test suite. A mutant is KILLED when the suite fails.
# Run from anywhere:
#
#   bash tools/mutation/run_all.sh [mutplug | mutplug_portfolio | mutplug_matching | mutplug_sdg | mutplug_api | mutplug_pathway]
#
# IMPORTANT: classify by pytest's EXIT CODE (1 = tests failed = killed, 0 = survived, anything else =
# harness problem). A mutant whose target text is missing (or occurs a different number of times than
# declared), or whose mutated source does not compile or load, is a HARNESS PROBLEM, never a kill: the plug
# checks every target up front (plug/_mutcheck.py) and, if one is bad when a mutant is applied, exits with
# rc 97, which is reported under "harness problems" below. Never search the output for the word "failed": "xfailed" contains it, which once made
# every mutant look killed.
#
# Needs the project's Python environment (e.g. `uv sync`, or UV_PROJECT_ENVIRONMENT pointing at it).
HERE="$(cd "$(dirname "$0")" && pwd)"
PLUG="${1:-mutplug}"   # plug module to run: mutplug (engine/forecast.py) or mutplug_portfolio (engine/portfolio.py)
cd "$HERE/../.." || exit 9
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$HERE/plug"
if command -v uv >/dev/null 2>&1; then RUN="uv run"; else RUN=""; fi

names=$($RUN python -c "import $PLUG as p; print(' '.join(p.MUTANTS))") || exit 9
$RUN python -c "import $PLUG as p, _mutcheck as c, sys; sys.exit(1 if c.check_plug(p) else 0)" || { echo "harness problems: bad mutation targets (see above); fix the plug first"; exit 9; }
$RUN pytest -q -p "$PLUG" -p no:cacheprovider tests >/dev/null 2>&1
echo "control (no mutation) exit code: $? (must be 0)"

killed=0; surv=""; bad=""
for m in $names; do
  MUT=$m $RUN pytest -q -p "$PLUG" -p no:cacheprovider tests >/dev/null 2>&1
  rc=$?
  case $rc in
    1) killed=$((killed + 1)) ;;
    0) surv="$surv $m" ;;
    *) bad="$bad $m(rc=$rc)" ;;   # includes 97 = bad target found while applying
  esac
done
echo "mutants: $(echo $names | wc -w)  killed: $killed"
echo "survivors:${surv:- none}"
echo "harness problems:${bad:- none}"
