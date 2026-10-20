# Verifier report — Lane A Step 1, third (test-only) round, engine/core, 20 Oct 2026

(Saved by the orchestrator; the verifier returns its report as text. Scratch work: scratchpad/verify/round3-check/.)

SUMMARY: 8 verified / 0 failed / 0 unverifiable. Recommendation: Step 1 safe to commit as-is; nothing blocks.
BASELINE: main = 5 passed / 21 xfailed (measured); round 2 = 51 / 15 (orchestrator's figure); now 83 passed / 15 xfailed / 0 skipped. Delta = 6 un-marked forecast tests + 9 new in test_engine_spec.py + 63 in test_forecast_golden.py. Engine code (forecast.py, config.py) identical to round 2.

1. Suite: 83 passed, 15 xfailed (5 lane A + 10 lane B), 0 skipped; reversed and 5 shuffled orders identical — VERIFIED.
2. Independence: independent_expected.py imports no engine code; snapshots and goldens regenerate byte-identical; verifier's own pure-Python implementation from SPEC §5.1 matches 352 fields (worst abs diff 2.5e-14); engine matches goldens under Python 3.11/3.12/3.13 — VERIFIED.
3. Round-2 gaps: all 14 genuine gaps and all 3 config-bypass survivors now killed. 322 mutants total: 179 of round-2's 193 now killed (was 162). 31 survivors, classified by 20,002 × 2 differential fuzz (two seeds): 28 equivalent or equivalent-in-practice; 3 minor genuine gaps:
   - label_rising_from_point (rising judged by point estimate, not lower bound at the call site; declining side pinned)
   - shift_clamped_02 (no fixture reaches |shift| > 0.2)
   - out_is_estimate_int (emits 1 instead of True; tests check truthiness)
   Also unreachable by monkeypatch / not config-tested: λ, momentum window, volatility window, smoothing window (DEFAULT_SCENARIO and SMOOTHING_MONTHS are bound as default args at import).
   Orchestrator's 51-mutant plug against the suite as verified: 48 killed, 3 survived (smoothing_window_hardcoded_3, momentum_window_hardcoded_12, vol_window_hardcoded_24).
4. Behaviour fuzz (40,000 snapshots, 358,998 forecasts): thin_nonstable 0; forced_stable_wrongly 0; hist12_bad 0; key/type/json bad 0; exceptions 0; thread sizes up to 4e12 — VERIFIED.
5. New tests meaningful: 63 golden tests, no silent parametrisation collapse; thin-cutoff sums 299/300 traced; no config leakage across reversed/shuffled runs; margins ≥ 0.004 (shift_down moderate high −0.0460; exposed3 moderate −0.0450); 21 hand-built wrong implementations — 19 tripped the target test, 2 did not (test_unknown_exposure… name over-promises; test_volatility_needs_epsilon… guard equivalent since log(0) raises anyway). Feature-deleted run: 78 failed, 5 passed — VERIFIED with caveats. Retuning λ requires updating LAMBDA in independent_expected.py and regenerating goldens.
6. SPEC/contract/code: no behavioural contradiction. Cosmetic nits (since fixed by the orchestrator, doc/comment-only): contract example history_months 25 beside 3-entry index; short-history bullet omitted volatility; "mean monthly post count" wording; _ols_slope docstring; all_zero fixture comment (>5% only under fast).
7. Diff scope: only the intended files; git diff --check clean; CR=0 everywhere; .vscode and .pytest_cache ignored — VERIFIED.
8. Nothing else wrong in forecast.py, fixtures or goldens — VERIFIED.

Not checked: pytest on 3.11/3.13 (numerics only), real snapshot (none yet), lane C rendering of thin rows, portfolio.covariance stub.

Notes from orchestrator, after the verifier ran (NOT independently verified):
- CORRECTION: the orchestrator's own mutant runs just before the verifier reported "0 survivors" because the detector matched the text "failed" inside "xfailed", so every mutant looked killed. The verifier's count (48 killed, 3 survived) was right.
- Five cosmetic doc/comment edits from item 6 were applied (SPEC thin row wording, contract example/short-history/thin bullets, _ols_slope docstring, fixture docstring).
- Three config-pinning tests were added (momentum window, volatility window, scenario lambda come from config). Re-run with an exit-code detector (1 = killed, 0 = survived): 86 passed / 15 xfailed; 51 mutants, 50 killed, 1 survivor: smoothing_window_hardcoded_3 (SMOOTHING_MONTHS and DEFAULT_SCENARIO are bound as default arguments at import time, so a test cannot reach them; equivalent at today's config; engine left unchanged so the verified code is what is committed).
