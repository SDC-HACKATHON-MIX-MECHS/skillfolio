# Independent verification reports

Each report comes from a separate "verifier" run that checks claims cold: it re-runs the tests, writes its own implementation from the SPEC text, fuzzes the code, breaks it on purpose, and attaches real output to every verdict. They are kept verbatim, so paths inside them point at scratch folders on the author's machine that no longer exist; the findings and numbers are what matter.

| # | File | Subject | Result |
|---|---|---|---|
| 1 | `01-scaffold-151100.md` | Repo scaffold: data, roles exposure, pages, docs consistency | 4 verified / 1 failed (documentation mismatches, fixed) |
| 2 | `02-forecast-round1-163000.md` | Step 1 forecast engine | 6 verified / 3 failed (weak tests, undocumented rules, zero-post skill labelled rising) |
| 3 | `03-forecast-round2-170857.md` | After fix round 1 | 5 verified / 2 failed (scenario could still label thin skills; 19 surviving mutants) |
| 4 | `04-forecast-round3-173343.md` | After fix round 2 | 6 verified / 1 failed (14 test gaps) |
| 5 | `05-forecast-round4-180752.md` | After test-only round 3 | 8 verified / 0 failed; safe to commit |
| 6 | `06-scenario-and-damping-200522.md` | Momentum damping and log-space scenarios on the real snapshot | 7 verified / 2 minor failed / 1 UI check impossible |
| 7 | `07-portfolio-step2-215207.md` | Step 2 portfolio engine (`engine/portfolio.py`) | 6 verified / 1 failed (SPEC sentence on old gamma wrong) / 1 partial; NaN bug found, fixed after the round (finite checks + 5 mutants + 2 tests: 65/65 killed) |
| 8 | `08-band-widening-220734.md` | Uncertainty bands widened (`SE_INFLATION = 1.9`), regenerated goldens, fixture tweaks, gamma 0.75/0.375/0.125 | 8 pass / 1 partial (one extra mutant survived: `momentum()` band width untested; test + mutant added, 73/71 killed) |

**Open finding from report 6:** the trend's standard error is about 1.9x too small because it is fitted on a 3-month rolling average, so the "80%" bands cover about 50%. Documented in `docs/SPEC.md` 5.1; fix still undecided.

Harness that produced the mutation numbers: `tools/mutation/`.
