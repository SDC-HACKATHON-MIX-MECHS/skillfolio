# Mutation check

A test suite is only as good as the wrong code it can catch. `plug/mutplug.py` holds 67 deliberately broken versions ("mutants") of `engine/forecast.py` (wrong operators, constants, formulas, hard-coded config values, wrong output keys). `run_all.sh` applies each one in memory, runs the whole suite, and reports which mutants the tests failed to catch.

```
bash tools/mutation/run_all.sh
```

**Expected today:** control exit code 0; 67 mutants, 65 killed; survivors `shrink_applied_without_history` and `reference_needs_no_history`, both **provably equivalent** (they change the code but never the result: damping a zero-history trend returns exactly 0, and the reference filter already excludes it).

**Rules**
- A surviving mutant is either *equivalent* (prove it: algebra, or a differential fuzz against the real engine) or a **test gap** (add a test that kills it).
- Classify by pytest's **exit code**, never by searching the output for "failed" (`xfailed` contains it). `run_all.sh` already does this.
- Nothing in the project is modified: the plug patches `engine.forecast` in memory when `MUT=<name>` is set.

**Adding a mutant:** add `"name": ("exact old source text", "replacement")` to `M` in `plug/mutplug.py`. The old text must occur in `engine/forecast.py` (otherwise the harness reports a problem).

**For a new module** (for example `engine/portfolio.py`): copy `mutplug.py`, change the module it patches and the mutant list, and aim for the same standard: every formula term, constant, boundary and output key has a mutant, and every survivor is explained.

Background: `docs/verification/` holds the independent verifier reports that used this harness.
