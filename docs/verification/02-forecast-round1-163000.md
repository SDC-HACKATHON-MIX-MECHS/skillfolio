# Verifier report — Lane A Step 1 (engine/forecast.py), branch engine/core, 20 Oct 2026

(Saved by the orchestrator: the verifier agent returns its report as text. Scratch scripts: scratchpad/verify/step1/.)

SUMMARY: 6 verified / 3 failed / 0 unverifiable (claim 4 split into 4a/4b)
BASELINE: clean main = 5 passed / 21 xfailed / 0 failed / 0 skipped (git archive export)

## Claim 1 — 12 passed, 15 xfailed; baseline 5/21: VERIFIED
`12 passed, 15 xfailed in 0.17s EXIT=0`; main export `5 passed, 21 xfailed`. 26 → 27 tests (6 markers removed + 1 new).

## Claim 2 — 7 forecast tests run unmarked and pass: VERIFIED
All 7 PASSED; remaining @todo markers only on non-forecast tests; no conftest/pytestmark.

## Claim 3 — tests catch wrong implementations: FAILED
Killed: centred/expanding/full-window/leading smoothing, sign-flipped momentum, swapped interval, constant vol, midpoint/zero-threshold/swapped trajectory, uncentred/sign-flipped shift, shift on unknown exposure, None in mean (both), scenario ignored/λ swapped, is_estimate False, several thin variants.
Survived: thin threshold anywhere in (0.83, 30], <=3, median/min/last-month thin rules; mean_is_median; momentum not annualised / full-series window / linear not log / z=1.96 / no eps / zero-width interval; vol not annualised / levels not logs / population std / std of log levels; traj `>=`; interval not shifted by scenario; index or momentum from raw (unsmoothed) shares.
Root issue: no test pins any number; tests check signs/directions/edges only.

## Claim 4a — formulas implemented as SPEC 5.1: VERIFIED (independent numpy/pandas impl matches to 4 d.p.)

## Claim 4b — no undocumented/incorrect deviations: FAILED
1. Partial-head smoothing (documented; spec should state edge rule). Matters a lot on 6-month fixture (+302.8% vs +378.9%).
2. Index rebased on first non-zero ŝ (documented; spec says ŝ_first); late-appearing skill → index up to 6126.6.
3. ε = 0.5/max(total_posts,1) (undocumented guard).
4. n<3 → (0,0,0) zero-width interval; label then decided by scenario shift alone (undocumented) — fix code + spec.
5. Momentum window min(12, len) (undocumented).
6. Volatility uses smoothed[-24:] = 23 changes; spec ambiguous.
7. Volatility sample std ddof=1 (undocumented).
8. Volatility log floor 1e-4 not in spec, comment falsely cites SPEC 5.1; inconsistent with momentum ε; dominates sparse skills (vol 301–370%).
9. Volatility <2 changes → 0.0 reads as riskless.
10. ē = mean of known exposures; unknown → no shift (spec says "all skills").
11. Spec "thin data → interval shown wider" not implemented and not owned by any lane.
12. Empty series → ZeroDivisionError.
13. forecast_skill direct call with unknown scenario + exposure None silently passes.
14. Spec defect reproduced: ε varies with each month's total_posts → all-zero skill with shrinking threads gets r=+0.468 [+0.457,+0.479] "rising".
15. OLS on 3-month rolling mean → autocorrelated residuals → SE/80% band understated.

## Claim 5 — independent recomputation of shown table: VERIFIED (no mismatch beyond rounding; same interpretation choices)
ē=0.433333. Moderate: rising +302.7632% (+271.4469..+336.7197) vol 9.5220% proj +305.0965% rising; flat 0 / +0.3333% stable; falling −70.2039% (−74.7505..−64.8386) vol 16.2772% proj −72.8706% declining. Fast: +309.7632% / +1.0000% / −78.2039%.

## Claim 6 — SkillForecast keys and types: VERIFIED (exposure nullable and passed through uncast, e.g. int 0)

## Claim 7 — robustness: FAILED
(a) realistic 25 months fine. (b) length 1–2: zero-width interval, label from exposure alone, vol 0, thin False. (c) all-zero skill positive momentum; "rising" when threads shrink 400→208. (d) unknown scenario → clear KeyError. Extra: late-appearing skill index 6126.6; empty series ZeroDivisionError.

## Claim 8 — only forecast.py and test_engine_spec.py changed: VERIFIED
`2 files changed, 103 insertions(+), 15 deletions(-)`; other-path diff empty. test file working copy CRLF (normalised on commit).

## Traps
0 skipped; baseline measured; tests not vacuous but magnitude-blind; one artifact drift (false "see SPEC 5.1" comment); no regressions.

## Not checked
Real 25-month snapshot (none yet); statsmodels (not installed; numpy cross-check used); lane C display of thin/greyed/large index values.
