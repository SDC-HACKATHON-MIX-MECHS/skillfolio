# Verifier report — Lane A Step 1, second fix round (engine/core, uncommitted), 20 Oct 2026

(Saved by the orchestrator; the verifier returns its report as text. Scratch work: scratchpad/verify/round2-check/ — myimpl.py, check_golden.py, claim3.py, fuzz_diff.py, mutants.py, mutants2.py, run_mutants*.py, run_equiv.py, extreme.py.)

SUMMARY: 6 verified / 1 failed / 0 unverifiable (claims 5 and 8 verified with caveats)
BASELINE: main = 5 passed / 21 xfailed (measured via git archive); previous round 20/15 (as stated, not re-measured); now 51 passed / 15 xfailed. Delta +31 = the 31 tests in test_forecast_golden.py.

## Claim 1 — 51 passed, 15 xfailed, no forecast test xfailed: VERIFIED
All 15 XFAILs are non-forecast: 5 lane A (portfolio weights, match_pct, match caps, plan, skill_sdgs) + 10 lane B extract_skills. 0 skipped. Per file: data_integrity 5, engine_spec 20, extract_skills 10, forecast_golden 31.

## Claim 2 — goldens independent and reproducible: VERIFIED
independent_expected.py imports only json/sys/pathlib/numpy/pandas and asserts engine not imported. Regenerating goldens from scratch: byte-identical; snapshots regenerate identical. Verifier's own implementation from SPEC text only: ALL MATCH, 242 fields, worst diff 7.75e-14. Only unstated rule: OLS standard-error degrees of freedom n−2 (se_dof_n / se_dof_n1 would change goldens).

## Claim 3 — behaviour fixes (a)–(g): VERIFIED
(a) zero-post sweep 14112 cases, 0 non-stable/non-thin; fuzz 6000 snapshots / 54448 forecasts: thin_nonstable 0, wrongly_forced 0, mismatches vs own impl 0, max rel err 1.9e-14. (b) 1–2 month cases 4000, 0 violations (stable, thin, history=n, six numeric fields exactly 0.0). (c) exactly-3-month: 18/2997 "violations" are not defects — symmetric V-shaped series (e.g. counts [24,36,12]) have OLS slope exactly 0 with a wide interval. (d) empty series and zero-total months: no crash. (e) epsilon constant/config-driven/fallback 0.5 for [] and [0,0]. (f) volatility eps=0 with zero share → ValueError; one-arg call → TypeError. (g) unknown scenario → KeyError via forecast_all and forecast_skill incl. exposure None. Extra: 18000 extreme-scale forecasts, 0 exceptions, strict JSON OK.

## Claim 4 — broad mutation testing: FAILED
193 mutants (177 + 16): 162 killed, 31 survived (orchestrator's 25-mutant plug not used).
Killed: all momentum/volatility window variants; every epsilon definition; index rebasing variants; thin cutoffs 2…3.5 except 2.91–2.99; <= vs <; thin mean over non-zero/median/min/max/total; history guard <2/<4 in momentum, thin, label and config; unknown-exposure offset; scenario lambda lookups/signs; strict vs non-strict ±5%; z variants; sample vs population std; √12; raw vs smoothed; annualisation; interval not applied; thin→label forcing removed.
14 genuine test gaps (differ from real engine on fuzz/probe):
- shift_guard_ge4: no shift at history 3 untested (golden_3m exposures equal ē → shift 0).
- label_ignores_shift, label_shift_low_only: no fixture has a non-thin skill whose label depends on the scenario shift → SPEC claim "the scenario shift can move a label" untested.
- thin_last12; thin_cutoff_2.91 (2.91–2.99 pass); ebar_truthy_filter (known exposure 0.0 dropped from ē); eps_nonzero_months_mean; default_scenario_fast; scenario_guard_all_removed (empty-skills snapshot + bad scenario returns {}); vol_eps_default_zero / vol_eps_default_half (no one-arg TypeError test); skill_id_wrong, scenario_field_wrong, key_order_swap (no test on skill_id, scenario echo, key order — engine correct).
3 config-bypass survivors (equivalent only at today's config): eps_posts_hardcoded_in_fn, label_threshold_hardcoded, z_hardcoded_128 — "config-driven" untested.
14 behaviour-equivalent survivors (differential fuzz of 20000 snapshots × 2 scenarios): label_force_only_lowcount, label_force_hist_lt2, label_order_declining_first, thin_int_floor, ebar_fallback_half, vol_guard_removed, vol_guard_lt0, thin_empty_counts_big, thin_mean_over_months_len, history_from_months, history_from_counts, hist_months_field_months, ebar_only_enough_history (equivalent while len(counts)==len(shares)==len(months), guaranteed by contract), scenario_guard_case_insensitive (direct forecast_skill with "MODERATE" not probed).

## Claim 5 — SPEC/contract/code consistency: VERIFIED (caveats)
No hard contradiction. Consistent: epsilon definition + fallback; history rule (all zero); thin definition; label rule and "may and may not" paragraph; config names exist; covariance docstring; TASKS lane C row; contract key list/order.
Soft points: §5.2 does not state sample (n−1) covariance; §5.1 does not state OLS SE uses n−2; latent divergence if MOMENTUM_WINDOW_MONTHS < MIN_HISTORY_MONTHS; contract doesn't define history_months as series length or index for short history; SPEC prose hard-codes 3/12/24/1.28/5%.

## Claim 6 — keys, order, types, strict JSON: VERIFIED (54448 fuzz forecasts, 0 bad)

## Claim 7 — diff scope: VERIFIED
Modified contracts/README.md, docs/SPEC.md, docs/TASKS.md, engine/config.py, engine/forecast.py, engine/portfolio.py, tests/test_engine_spec.py; new tests/fixtures/ (6 files) + tests/test_forecast_golden.py. `git diff main --check` rc=0; CR count 0. Fixture JSON lacks trailing newline (harmless).

## Claim 8 — other defects: VERIFIED (no engine defect; test weaknesses)
Parametrisation holds (18+4+9); no hard-coded paths; tolerance rel 1e-7/abs 1e-9 adequate; fixture comments hold (just_under pins cutoff on one side only). Dead fixture content: golden_3m has both skills at exposure 0.40 = ē, so it never exercises the shift. No tests for scenario-changing a non-thin label, skill_id, scenario echo, key order, default scenario, one-arg volatility.

## Traps
0 skipped; baseline taken; with the feature deleted, new tests fail (label_force_removed: 6 failures incl. zero-post test; history<3 rule; cutoff 2.9 vs 3.0; epsilon; windows; rebase); no regressions.

## Not checked
portfolio.covariance behaviour (stub); app rendering of thin rows (lane C); a real snapshot (data/snapshots empty).
