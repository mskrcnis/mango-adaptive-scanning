# Development-only methodology revision: results

All three development seasons were evaluated with the other seasons supplying fitting, bank-design and calibration groups. This revision follows inspection of version 1, including its external findings; it is exploratory. Seasons 4 and 5 were not loaded or rescored. Version 1 remains the completed original analysis.

## Decision from this bounded round

The controlled results do not establish the masked MLP as the main cause of the earlier accuracy gap. At four identical readings, replacing it with PLS or ridge does not improve the primary common-order point estimates in any held season; all paired 95% intervals include zero. Averaging over every reachable four-channel subset gives small, mixed changes. The earlier comparison against a different fixed four-channel bank therefore cannot be attributed to predictor family alone.

Most of the mean seventh-to-eighth improvement persists when both predictions use PLS. The estimator-switch concern was worth testing, but it accounts for only part of this pipeline's endpoint gain. This conclusion is conditional on the registered order, which reads centers 720, 940, 820, 890, 760, 780, 800 and 910 nm in the primary bank. Wavelength spacing was chosen for assay independence, not predictive optimality; these results do not rule out a better development-designed fixed subset or order.

The isolated bank-reference stopping objective shows no demonstrated practical advantage in this round. Its primary target-budget comparisons remain budget-incomparable in all three held seasons, and its engineering points fail at least one prototype condition in every season. No revised model is promoted. Preserve the evaluation framework; prioritize a separately registered, design-group-only fixed-subset/order study before adding controller complexity. New independent seasonal and physical measurements remain necessary.

## Matched prediction at exactly four readings

These are the same channel subsets, acquisition order, fitting rows and held scans. RMSEP is in dry-matter percentage points. PLS and ridge hyperparameters were fixed before this round.

| Held development season | Masked MLP | Subset PLS | Subset ridge |
|---|---:|---:|---:|
| 1 | 2.3304 | 2.3717 | 2.3718 |
| 2 | 1.7400 | 1.7702 | 1.7828 |
| 3 | 2.4573 | 2.6223 | 2.5842 |

The full-mask MLP entry is the existing hybrid's PLS dispatch; it is not a trained full-mask MLP result. All-mask summaries pool squared errors over scans and equally weighted masks at each depth; they are distinct from the common-order results above.

## What accounts for the seventh-to-eighth improvement?

Signed mean reductions in absolute error: estimator replacement at seven readings plus the final measurement within the PLS family. Negative components are retained. These quantify this fitted pipeline and cannot establish irreducible optical information.

| Held season | Total hybrid improvement | MLP7 → PLS7 | PLS7 → PLS8 |
|---|---:|---:|---:|
| 1 | 0.9337 | 0.1277 | 0.8060 |
| 2 | 0.3772 | 0.0858 | 0.2914 |
| 3 | 1.0071 | 0.1013 | 0.9058 |

The endpoint explanation changes for the independent uniform bank:

| Held season | Total hybrid improvement | MLP7 → PLS7 | PLS7 → PLS8 |
|---|---:|---:|---:|
| 1 | 0.2999 | 0.3097 | -0.0098 |
| 2 | 0.3325 | 0.3451 | -0.0127 |
| 3 | 0.3249 | 0.3490 | -0.0241 |

For this bank/order, the final measurement slightly worsens mean absolute error within PLS, while replacing the estimator accounts for the positive hybrid endpoint improvement. Neither bank's decomposition should be generalized to an untested bank or order.

## Stopping objective with predictor and acquisition order fixed

Primary analysis uses the consistent subset-PLS predictor. Separate logistic heads see identical acquired readings and masks, and use identical training effort. Each threshold is selected exclusively on its outer training-side calibration groups. A positive budget difference means the bank-reference objective spends more.

| Held season | Bank-reference RMSEP / readings | Rich-reference RMSEP / readings | RMSEP difference [95% group CI] | Budget comparable? |
|---|---:|---:|---:|---|
| 1 | 2.3814 / 2.001 | 2.0250 / 4.515 | 0.3564 [0.1691, 0.6192] | No |
| 2 | 1.8128 / 2.002 | 1.7765 / 2.371 | 0.0362 [0.0154, 0.0599] | No |
| 3 | 2.4834 / 3.671 | 2.0538 / 4.736 | 0.4296 [0.2631, 0.6038] | No |

Budget comparability requires an achieved mean-reading gap ≤0.25. Confidence intervals resample complete harvest populations (1000 draws); they describe sampled populations within a season, not new-season uncertainty. The calibration-selected target can transfer poorly. No threshold was changed to force a match on held outcomes.

## Engineering screen and fixed acquisition

| Held season | Bank-reference engineering RMSEP / readings | RMSEP increase vs full PLS | Both prototype conditions met? | Fixed-four RMSEP |
|---|---:|---:|---|---:|
| 1 | 1.2418 / 8.000 | 0.0000 | No | 2.3717 |
| 2 | 1.3571 / 7.383 | 0.0639 | No | 1.7702 |
| 3 | 2.0202 / 6.309 | 0.8132 | No | 2.6223 |

This screen requires at most +0.25 pp RMSEP versus full bank and at least 25% fewer readings. It does not certify the stricter v1 search constraints, physical energy savings, repeatability, or a deployable device. Calibration feasibility and held-season success are recorded separately in policy_metrics.csv.

## Independent-bank sensitivity

The uniform bank's bank-reference engineering policy passes both relative prototype conditions in all three held development seasons. This favorable sensitivity is retained. Its full-bank PLS comparator is weaker than the primary bank, especially in seasons 1 and 3; the pass therefore does not establish equivalent absolute accuracy or a general adaptive benefit.

| Held season | Uniform adaptive RMSEP / readings | Uniform full-bank RMSEP | Uniform fixed-six RMSEP |
|---|---:|---:|---:|
| 1 | 1.8826 / 5.940 | 1.9780 | 1.8722 |
| 2 | 1.3749 / 4.999 | 1.3568 | 1.2311 |
| 3 | 2.3708 / 4.708 | 2.1453 | 1.9208 |

Fixed-six PLS also passes both relative prototype conditions in all three seasons and has lower point-estimate RMSEP, with six readings for every scan. Adaptation saves about 0.06, 1.00 and 1.29 additional readings at RMSEP increases of about 0.010, 0.144 and 0.450 pp, respectively. Its reading count is comparable to the adaptive sensitivity in season 1 only; this is not an equal-budget superiority test in seasons 2 and 3. Every fixed length was included in advance; highlighting six here is descriptive and does not register it as a newly validated choice.

The uniform scientific stopping-objective comparison is budget-comparable only in season 2: the two-reference-minus-single RMSEP difference is approximately +0.008 pp, with a 95% population-bootstrap interval spanning zero. The other uniform seasons are budget-incomparable. Thus the independent bank supplies a conditional relative-screen success, without establishing objective superiority.

## Complete evidence and interpretation limits

- Two banks are retained: prior primary swap_mid and independent catalog-only uniform. All primary-bank seeds 42, 7 and 99 are included. Subset PLS/ridge and logistic fitting are deterministic; these repeated seeds vary the reused MLP predictions, not independent data samples.
- results/predictor_metrics.csv contains every subset-depth summary for training OOF, calibration and held data. Only held data support the seasonal performance assessment.
- results/policy_metrics.csv and policy_predictions.csv.gz retain all four frozen objective/operating-point policies and fixed lengths 2–8, for all predictors and cases.
- results/paired_comparisons.csv contains paired objective, fixed-four and exact-budget predictor differences; endpoint_summary.csv includes group confidence intervals on both endpoint components.
- results/threshold_curves.csv retains every calibration and held-season point on the fixed grid. Held curves are descriptive; they do not reselect a policy.
- Calibration mapping and threshold selection share reserved calibration groups. Held-season evaluation remains separate. Harvest groups substitute for missing verified fruit IDs.
- The stopping-only learner is logistic regression on observed values and masks. This controlled comparison tests that specified learner and common order; it does not establish that the label distinction cannot help a different calibrated learner.
- Rich-spectrum and full-bank errors remain model-relative comparisons. The finite-band LED emulator retains its documented optical approximations.

This round introduces no learned channel-order search and promotes no deployment model. Its results identify whether prediction quality or the stopping objective warrants further development. Any revised method requires fresh independent seasonal validation before a confirmatory claim.

## Reproduction

Run .venv/bin/python revisions/methodology_v2/run.py all --resume. Reporting alone uses the report command and cannot fit models. The verify command independently recomputes metrics, checks split provenance, and verifies preservation of version 1. See verification_report.md for executed checks.
