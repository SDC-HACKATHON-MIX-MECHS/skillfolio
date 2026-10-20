SUMMARY: 6 verified / 1 failed / 1 partial / 0 unverifiable across claims 1–8. Claim 5 failed on its old-gamma half. Claim 7 is partial because one SPEC sentence is wrong. Claim 6 passes on counts and the equivalence judgement, but the gap probe found surviving mutants (see its note).
BASELINE: no pre-change test count could be taken non-destructively. The forecast mutation baseline (67 mutants, 65 killed) matches the README and was re-run.

(The verifier could not write this file itself, so its report was returned in chat and is saved here as returned. Subject: `engine/portfolio.py`, Step 2, staged on branch `engine/portfolio`.)

## CLAIM 1: full suite 202 passed, 14 xfailed
VERDICT: VERIFIED
COMMAND: `uv run pytest -q` with `UV_PROJECT_ENVIRONMENT=C:/Users/jaiyd/.venvs/skillfolio`
OUTPUT: `202 passed, 14 xfailed in 0.54s`
NOTE: 0 failed, 0 skipped. The `@todo` marker was removed only from `test_portfolio_weights_follow_levels`.

## CLAIM 2: engine/portfolio.py implements SPEC 5.2
VERDICT: VERIFIED
- Weights are level/sum(levels). Empty profiles, duplicate skills, levels outside 1/2/3 and bool levels are rejected.
- Growth clamps thin-data skills to ±`config.THIN_GROWTH_CAP`.
- Exposure is renormalised over known skills and is None when none are known.
- Covariance is `12 * Σ(a-μ)(b-μ) / (count-1)`. Off-diagonals are multiplied by `1 - COVARIANCE_SHRINKAGE`. It uses a 24-month window of `smooth()` output and `forecast.epsilon`.
- Volatility is `sqrt(max(0, w'Cw))`. Diversification is `1 - Σw²`. Readiness is `growth - gamma/2 * vol²`.
- Independent recompute (claim 4) matches to 5.6e-17.

## CLAIM 3: goldens come from an engine-free script and reproduce byte-for-byte
VERDICT: VERIFIED
```
IDENTICAL
232e3a12...e5d920 *tests/fixtures/golden_portfolio.json
232e3a12...e5d920 */scratchpad/golden_orig.json
```
- `independent_portfolio.py` imports json, sys, pathlib, numpy, pandas and `independent_expected`, and asserts `"engine" not in sys.modules`. `independent_expected.py` imports json, sys, pathlib, numpy, pandas. Neither imports `engine`.

## CLAIM 4: independent recompute for Aina and Ravi, both scenarios
VERDICT: VERIFIED
```
aina moderate: R=+0.1240 vol=0.3417 E=0.1863 D=0.8194 (thin: powerbi, statistics)
aina fast:     R=+0.2321 vol=0.3417 E=0.1863 D=0.8194
ravi moderate: R=+0.2082 vol=0.3946 E=0.3521 D=0.7654
ravi fast:     R=+0.1917 vol=0.3946 E=0.3521 D=0.7654
MAX ABS DIFF 5.551115123125783e-17
```
(numpy `np.cov` ddof=1; `engine.forecast` used only for smooth, epsilon and `forecast_all`.)

## CLAIM 5: RISK_AVERSION recalibration numbers
VERDICT: FAILED on the old-gamma statement, VERIFIED on the new-gamma statement

| profile / scenario / risk | penalty/R new | penalty/R old | old readiness |
|---|---|---|---|
| aina moderate low | 0.706 | 2.824 | -0.2262 |
| aina moderate medium | 0.353 | 1.412 | -0.0511 |
| aina moderate high | 0.118 | 0.471 | +0.0656 |
| aina fast low | 0.377 | 1.509 | -0.1181 |
| **aina fast medium** | 0.189 | **0.754** | **+0.0570** |
| aina fast high | 0.063 | 0.251 | +0.1738 |
| ravi moderate low | 0.561 | 2.244 | -0.2589 |
| ravi moderate medium | 0.280 | 1.122 | -0.0254 |
| ravi moderate high | 0.093 | 0.374 | +0.1303 |
| ravi fast low | 0.609 | 2.437 | -0.2755 |
| ravi fast medium | 0.305 | 1.219 | -0.0419 |
| ravi fast high | 0.102 | 0.406 | +0.1138 |

- New values: penalty share 6.3%–70.6%, inside 3%–90%; Readiness positive in all 12 cells.
- Old values: the penalty exceeded growth in 7 of the 8 low/medium cells, not all 8 (Aina/fast/medium was 0.754× growth, Readiness +0.057). The SPEC sentence "1.1–2.8× R and Readiness went negative" only describes the negative cells; the true old range over all 12 cells is 0.25–2.82×, Readiness negative in 7 of 12.

## CLAIM 6: mutation harnesses and mutant judgement
VERDICT: VERIFIED on the counts; both equivalence calls are right; the gap probe found surviving mutants.
```
control (no mutation) exit code: 0 (must be 0)
mutants: 60  killed: 60
survivors: none
harness problems: none
--
control (no mutation) exit code: 0 (must be 0)
mutants: 67  killed: 65
survivors: shrink_applied_without_history reference_needs_no_history
harness problems: none
```
Removed mutants are equivalent: the `level != int(level)` clause was redundant (`level not in (1,2,3)` already rejects 1.5); negating every monthly change leaves covariance unchanged (the verifier ran it as its own mutant `neg_changes`: suite rc=0).

Gap probe (verifier's own in-memory mutants; rc=0 means survived):

| mutant | result | comment |
|---|---|---|
| `no_max_clamp` (drop `max(0, …)`) | survived | equivalent for real PSD matrices, but untested |
| `tol_loose` (weights-sum tolerance 1e-9 to 0.05) | survived | tolerance magnitude untested |
| `tol_tight` (tolerance 1e-15) | survived | |
| `no_int_cast` | survived | output identical |
| means over `len(c)` instead of `count` | survived | equivalent after the ragged check |
| exposure filter `and weight > 0` | survived | weights are always > 0 |
| `count_if_n_removed`, `ids_sorted_in_cov`, `ragged_check_gt0`, `level_float_ok` | killed | |

No substantive rule lacks a test; the survivors are tolerance or defensive code. The real gap is NaN behaviour (edge cases 1 and 2), which neither tests nor mutants covered.

## CLAIM 7: docs consistent with code
VERDICT: PARTIAL
- SPEC 5.2 table rows and edge rules match the code (thin clamp, exposure renormalisation and null, covariance, D, readiness, gamma 1.5/0.75/0.25, zero covariance below 2 changes, ordering, error cases; "scaled by ¼" is correct).
- Wrong: the SPEC sentence about 6 · 3 · 1 (see claim 5).
- The SPEC 5.1 caveat "volatility is not clamped" matches the code; `contracts/README.md` note matches; `tools/mutation/README.md` commands and counts verified by running.

## CLAIM 8: no file outside the intended set changed; forecast.py untouched
VERDICT: VERIFIED. `git diff --cached --stat`: 12 files; `engine/forecast.py` unchanged; `git stash list` empty.
Side effect of the verifier: a first mutation run without `UV_PROJECT_ENVIRONMENT` created a git-ignored repo-local `.venv/`.

## EDGE CASES
1. **Bug:** a NaN share gives `covariance == [[nan]]`, and `metrics()` then returns `volatility: 0.0` and `readiness == growth` (1.5244), because `max(0.0, nan)` is 0.0: corrupt data silently becomes "zero risk".
2. A NaN `projected` on a thin skill is clamped to +0.05 (`{'growth': 0.05, ...}`).
3. An inf covariance gives volatility inf and readiness -inf with no error (visible, so acceptable).
4. Empty `months` still works (`epsilon([])` falls back to `EPSILON_POSTS`).
5. A negative share raises `ValueError: math domain error` (unhelpful message, still an error).
6. A float level of 2.0 is accepted; NaN and bool levels, duplicates, empty profiles and ragged series are rejected.

## NOT CHECKED
UI use of the metrics; matching/pathway/sdg (unimplemented); CI history; other Python or numpy versions.
