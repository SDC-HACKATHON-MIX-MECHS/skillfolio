SUMMARY: 8 PASS / 0 FAIL / 1 PARTIAL (claim 7: harness numbers match, but one extra mutant survives).

(Returned in chat by the verifier and saved here as returned, lightly condensed. Subject: staged change on branch `engine/portfolio` that multiplies the trend standard error by `SE_INFLATION = 1.9`, regenerates the goldens, edits two fixture skills, and lowers `RISK_AVERSION` to 0.75/0.375/0.125.)

1. Full suite: PASS. `205 passed, 14 xfailed in 0.55s`.
2. forecast.py diff is only the SE_INFLATION multiplication in `trend()` plus its docstring; config.py adds SE_INFLATION and changes RISK_AVERSION: PASS.
3. Independence and byte-exact goldens: PASS. No `engine` import in either generator; `cmp` reported `same` for golden_30m, golden_3m, golden_example, golden_flat6 and golden_portfolio.
4. Independent recompute of the real snapshot (own numpy lstsq, s x 1.9): PASS.
```
prior k 58 mu 0.07178132977464284 tau2 0.049765533515051676 tau 0.22308189867188166
moderate skills 73 max abs diff 2.22e-15 counts {'stable': 60, 'rising': 10, 'declining': 3} mismatches []
fast     skills 73 max abs diff 2.22e-15 counts {'stable': 55, 'rising': 12, 'declining': 6} mismatches []
engine thin_data count 15 (thin flags match for all 73)
```
5. Calibration: PASS. Penalty/growth at 0.75/0.375/0.125 (aina moderate .450/.225/.075; aina fast .225/.113/.038; ravi moderate .608/.304/.101; ravi fast .768/.384/.128), range 0.0376-0.7675, none above 1, lowest readiness +0.0177. With 6/3/1: 8 of 12 cells above 1, max 6.14, readiness negative in those 8. With the previous 1.5/0.75/0.25: ravi moderate low 1.217, ravi fast low 1.535. The calibration test would fail on the previous gamma.
6. Fixture changes preserve intent: PASS. noisy_early moderate stable / fast declining; noisy_up and noisy_down point estimates beyond +/-5% with intervals straddling zero, stable; shift_up/shift_down differ between scenarios. No stale comments in make_snapshots.py or tests.
7. Mutation: PARTIAL.
```
mutants: 72  killed: 70   survivors: shrink_applied_without_history reference_needs_no_history   (forecast)
mutants: 65  killed: 65   survivors: none                                                       (portfolio)
```
Ten extra verifier mutants around the inflation were all killed (inflate only in momentum(); after shrinkage; only inside B; sqrt(1.9); floor compared on un-inflated s; floor scaled; prior from plain s; only n >= 12; 1.89; tau floor scaled). One SURVIVED: a `momentum()` that uses the de-inflated band (`half = INTERVAL_Z * s / SE_INFLATION`) passed the full suite, because the only tests that call `momentum()` check the sign, `low <= r <= high` and r, never the band width. `momentum()` is not used by `forecast_all`, so impact is low, but it is a test gap. Its docstring did not say that s includes the inflation.
8. Docs: PASS (nothing false). Plain-s measurement: tau 0.2825, mu 0.0658 (so "was tau 0.28" is true); plain-s label counts moderate 42/19/12 and fast 36/22/15. Minor: TASKS.md still said "tune gamma, alpha" (a plan item).
9. Edge cases: PASS. 3-month history gives a finite s exactly 1.9x the plain value; flat series s ~ 6.6e-16 with B exactly 1.0; zero-post series g = s = 0; no non-finite values on four snapshots and both scenarios; every thin skill stable.
NOT CHECKED: no test-count baseline against HEAD; app-side use; the simulation behind the 1.9 constant was not reproduced by the verifier (the lead re-ran it afterwards: plain band covers ~48%, x1.9 covers ~76%).
Follow-up after this round: added `test_plain_momentum_interval_uses_the_inflated_uncertainty`, the mutant `momentum_band_deinflated` (forecast harness now 73 mutants, 71 killed, same two equivalent survivors), a docstring line in `momentum()`.
