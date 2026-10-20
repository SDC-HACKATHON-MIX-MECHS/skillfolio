# Verifier report — Lane A Step 1 re-check after fixes (engine/core, uncommitted), 20 Oct 2026

(Saved by the orchestrator; the verifier returns its report as text. Scratch work: scratchpad/verify/step1-recheck/ — mut2.py, run_mutants.py, mutants.out, equiv.py, probe.py, recompute2.py.)

SUMMARY: 5 verified / 2 failed / 0 unverifiable (claim 2: 5 of 6 sub-claims verified, 2(a) failed)
BASELINE: main = 5 passed / 21 xfailed; pre-fix = 12 / 15; now = 20 / 15

## Claim 1 — 20 passed, 15 xfailed, 0 failed: VERIFIED
`20 passed, 15 xfailed in 0.18s, exit=0`; main export 5/21; pre-fix copy 12/15.

## Claim 2 — fixed behaviour: FAILED (2a), 2b–2f VERIFIED
2(a) FAILED: ε fix works (momentum = vol = 0, thin True) but a zero-data skill has a zero-width interval, so the scenario shift alone decides its label when |λ(e−ē)| > 5%:
  e_never=0.7/e_steady=0.2 fast → projected [−0.075,−0.075] declining thin=True
  e_never=0.2/e_steady=0.7 fast → projected [+0.075,+0.075] rising thin=True
  Fuzz: 3338 zero-post skills with ≥3 months, 685 labelled non-stable. Same for perfectly flat data at n=3.
  The test only passes because both skills have exposure 0.4 (shift 0).
2(b) VERIFIED: 1–2 month histories stable/thin/history=n — but projected = −shift (non-zero, zero-width), undocumented.
2(c) VERIFIED: empty series → stable, thin, history 0, index [].
2(d) VERIFIED: volatility uses ln(ŝ+ε) with same ε as momentum; no 1e-4 floor; no false spec citations. Direct volatility(smoothed) call defaults eps=0 → ValueError on zero share.
2(e) VERIFIED: unknown scenario → KeyError even with exposure None.
2(f) VERIFIED: exposure int→float, None→None.

## Claim 3 — tests meaningful: FAILED
102 mutants, 80 killed, 22 survived. Previously reported survivor classes all killed now (thin threshold, momentum magnitude, vol formula, interval not shifted, traj >=, mean-is-median, raw-vs-smoothed, per-month ε, missing history guard, guard <2, thin missing history clause, vol without ε, population std).
Equivalent survivors (fine): history_from_len_months, history_from_counts, forecast_all_no_scenario_check (differs only with zero skills).
Non-equivalent survivors (19): momentum window (full/24/6/first-12 — golden fixture has only 6 months), volatility window (12/full/25), ε denominator (min/last month — fixture totals constant), demand-index rebase rules (first-value guarded, head not zeroed, all-zero→100), history guard <4 and MIN_HISTORY=4 and thin history clause <4 (no n=3 test), thin cutoff 2.84–2.9, thin as mean over non-zero months, unknown exposure constant offset (test checks fast==moderate, not projected==momentum).

## Claim 4 — SPEC §5.1 states every rule: VERIFIED (all 11 rules present), remaining mismatches:
1. Stated guarantees ("never-mentioned skill shows no trend", "scenario alone never decides a label") false for ≥3-month zero-post or perfectly flat skills when |λ(e−ē)| > 5%.
2. Short-history projected = −λ(e−ē) undocumented (contract calls only momentum placeholders).
3. ε fallback 0.5 when no months / mean ≤ 0 undocumented.
4. "Half a post" 0.5 hard-coded, not in config.py (SPEC §5 says all tunables in config).
5. SPEC §5.2 covariance uses Δ ln ŝ without ε — inconsistent with §5.1 volatility; one-skill σ_p ≠ v; zeros → −inf.

## Claim 5 — independent recomputation of GOLDEN/PROJECTED: VERIFIED
ε=0.0025, ē=0.433333; rising 3.027632 [2.714469, 3.367197] vol 0.092976 index [100,110,120,140,160,180]; flat 0; falling −0.702039 [−0.747505, −0.648386] vol 0.159463; projected moderate 3.050965/0.003333/−0.728706, fast 3.097632/0.010000/−0.782039.

## Claim 6 — keys/types/strict JSON match contract: VERIFIED (key order too; 8000 fuzz runs, 0 errors)

## Claim 7 — robustness: VERIFIED
Realistic 25 months sensible; late-appearing index max 6126.59 (documented; capping assigned to lane C); month with total_posts=0 OK; forecast_all unknown scenario → clear KeyError.

## Claim 8 — diff touches only the 6 named files: VERIFIED
HEAD=main=b52036d; M contracts/README.md, docs/SPEC.md, docs/TASKS.md, engine/config.py, engine/forecast.py, tests/test_engine_spec.py; ignored .pytest_cache, .vscode/settings.json. test file CRLF in working tree (normalised on commit).

## Traps
0 skipped; baseline taken; 19 behaviour-changing mutants survive; test comment cites a scratch report not in the repo; no regressions; .pytest_cache updated.

## Not checked
Existence of the cited scratch report from inside the repo; Methodology page caveat (app work); contract-violating inputs.
