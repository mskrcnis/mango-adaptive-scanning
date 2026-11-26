# Fixed-subset and acquisition-order study: results

Completed one locked, development-only follow-up. Versions 1 and 2 are preserved. All channel choices used reserved design groups; all six bank/held-season designs were locked before source evaluation arrays were parsed. Seasons 4 and 5 were not loaded or rescored. These repeatedly used development seasons provide exploratory evidence.

The primary PLS bank supports improving fixed channel selection/order. The prespecified fixed-six procedure passes the relative engineering screen in all three seasons with 25% fewer simulated readings than the eight-channel reference. The proposed bank-reference stopping objective adds no demonstrated advantage. Prioritize a fixed-channel candidate for fresh validation; no universal configuration or deployment claim is established.

## Primary result: identical four-reading budgets

The design-selected PLS order lowers RMSEP relative to the catalog-only order in 3 of 3 held development seasons; 3 of 3 paired population-bootstrap intervals lie entirely below zero. These comparisons use exactly four readings on both sides, with the same fitted predictor family, initial channels and installed bank.

| Held season | Catalog order RMSEP | Designed order RMSEP | Selected fixed-four RMSEP | Full-bank RMSEP | Designed minus catalog [95% CI] |
|---|---:|---:|---:|---:|---:|
| 1 | 2.3717 | 2.0268 | 2.0268 | 1.2418 | -0.3450 [-0.5891, -0.1180] |
| 2 | 1.7702 | 1.1706 | 1.1706 | 1.2932 | -0.5996 [-0.8257, -0.3817] |
| 3 | 2.6223 | 2.0364 | 2.0364 | 1.2070 | -0.5858 [-0.7998, -0.3882] |

RMSEP is in dry-matter percentage points. Selected fixed-four subsets minimize their own design MSE; they can differ from the four-channel prefix of the globally selected nested order. The latter minimizes the sum of design MSE over depths 2–7, not four-channel error alone.

## Selected channels and repeatability across design splits

| Held season | Selected PLS order, nm | Independent fixed-four subset, nm | Independent fixed-six subset, nm |
|---|---|---|---|
| 1 | 720,940,910,890,820,760,800,780 | 720,890,910,940 | 720,780,800,890,910,940 |
| 2 | 720,940,910,890,820,780,800,760 | 720,890,910,940 | 720,780,800,890,910,940 |
| 3 | 720,940,910,890,820,760,800,780 | 720,890,910,940 | 720,760,800,890,910,940 |

Each row is a separate training-side design. No universal order or device was chosen from held outcomes. Selection is constrained to the two existing eight-channel banks and fixed endpoint pair; this is not a global wavelength optimum.

## Engineering screen at fixed budgets

The screen requires RMSEP no more than 0.25 pp above the same full-bank reference and at most six readings. Absolute errors remain relevant even when a relative screen passes.

| Held season | Designed fixed-four: RMSEP / pass | Selected fixed-four: RMSEP / pass | Selected fixed-six: RMSEP / pass |
|---|---:|---:|---:|
| 1 | 2.0268 / no | 2.0268 / no | 1.2154 / yes |
| 2 | 1.1706 / yes | 1.1706 / yes | 0.9670 / yes |
| 3 | 2.0364 / no | 2.0364 / no | 1.2075 / yes |

Primary-bank passes across the three held seasons: designed fixed-four 1/3; independently selected fixed-four 1/3; independently selected fixed-six 3/3.

The fixed-six result is a prespecified engineering sensitivity, not a claim that six readings is the optimum among all reported lengths. Its selected wavelengths differ across design splits. Absolute accuracy for this procedure is:

| Held season | Fixed-six RMSEP | Full-eight RMSEP | Fixed-six MAE | Signed bias | Scans with absolute error above 2 pp |
|---|---:|---:|---:|---:|---:|
| 1 | 1.2154 | 1.2418 | 0.9740 | -0.0163 | 9.1% |
| 2 | 0.9670 | 1.2932 | 0.7758 | -0.5581 | 3.2% |
| 3 | 1.2075 | 1.2070 | 0.9786 | +0.4351 | 8.5% |

No independently justified application tolerance or physical instrument measurement establishes deployment suitability. Fewer simulated readings do not establish measured energy, latency or hardware savings.

## Does stopping add evidence beyond a better fixed order?

The logistic stopping learner, two objective definitions and calibration rules are unchanged from revision 2. Catalog stoppers were reused only after exact feature/path checks; designed-order stoppers use core OOF targets and separate calibration groups.

| Held season | Designed bank-reference RMSEP / readings | Designed rich-reference RMSEP / readings | Paired RMSEP difference [95% CI] | Budget comparable? |
|---|---:|---:|---:|---|
| 1 | 2.0016 / 4.020 | 1.9629 / 4.115 | 0.0387 [-0.0273, 0.1382] | yes |
| 2 | 1.2147 / 3.839 | 1.1692 / 4.004 | 0.0455 [0.0075, 0.0913] | yes |
| 3 | 2.2410 / 3.747 | 1.8415 / 3.821 | 0.3995 [0.0787, 0.7775] | yes |

All three scientific comparisons are within the registered 0.25-reading margin, but their achieved budgets are not exactly equal. The bank-reference objective has higher RMSEP in all three seasons; the paired intervals exclude zero in seasons 2 and 3. This provides no support for its proposed advantage. Frozen threshold curves are descriptive and never used to retune held-season points.

| Held season | Bank-reference engineering RMSEP / readings | Both engineering conditions met? | Selected fixed-six RMSEP |
|---|---:|---|---:|
| 1 | 1.7492 / 4.602 | no | 1.2154 |
| 2 | 1.3017 / 3.585 | yes | 0.9670 |
| 3 | 1.2678 / 5.007 | yes | 1.2075 |

The adaptive engineering policies use fewer readings than fixed-six but have higher RMSEP. This is an accuracy versus acquisition-effort trade-off, not evidence of adaptive superiority at equal cost.

## Independent bank and ridge sensitivity

Every bank/family combination has its own design choices. Consequently these rows are complete pipeline sensitivities, not matched-subset predictor-family comparisons.

| Bank / predictor | Held season | Catalog fixed-four | Designed fixed-four | Selected fixed-four | Selected fixed-six | Full bank |
|---|---:|---:|---:|---:|---:|---:|
| uniform / pls | 1 | 2.2858 | 2.3428 | 2.3428 | 1.7243 | 1.9780 |
| uniform / pls | 2 | 1.7322 | 1.7118 | 1.7128 | 1.3708 | 1.3568 |
| uniform / pls | 3 | 2.3564 | 2.5049 | 2.2958 | 1.7081 | 2.1453 |
| swap_mid / ridge | 1 | 2.3718 | 2.3244 | 2.3244 | 2.2857 | 2.1740 |
| swap_mid / ridge | 2 | 1.7828 | 1.7400 | 1.7400 | 1.5969 | 1.5944 |
| swap_mid / ridge | 3 | 2.5842 | 2.5463 | 2.5463 | 2.3343 | 2.3339 |
| uniform / ridge | 1 | 2.2968 | 2.3093 | 2.3093 | 2.1822 | 2.1540 |
| uniform / ridge | 2 | 1.7508 | 1.7520 | 1.7520 | 1.5617 | 1.5599 |
| uniform / ridge | 3 | 2.4406 | 2.5262 | 2.5262 | 2.2564 | 2.2491 |

The large primary-bank PLS improvement is not consistently reproduced by the uniform bank or ridge sensitivity. These results do not establish a general advantage across optical designs or predictor families.

## Evidence limits and disposition

- Design folds contain only 9, 9 and 6 populations (998, 953 and 857 scans). Leave-one-population-out fitting retains 8, 8 and 5 training populations. Pooled scan MSE weights large populations and represented seasons more heavily; counts are retained in design_composition.csv.
- For the held-season-1 design, 958 of 998 scans are from season 3. The other design sets are also uneven. Exhaustive 64-subset/720-order minima are tuning results, not validation scores. Reported uncertainty is conditional on selected designs and fitted models.
- Confidence intervals resample complete harvest populations 1000 times with seed 42. They do not describe selection uncertainty, unknown fruit identities, future seasons, or multiplicity-adjusted evidence.
- All 64 masks and 720 orders per family/case are saved; all fixed lengths and frozen stopping curves are retained. No new bank, initial pair, learner, threshold grid or refinement was added after inspecting scores.
- Independently selected fixed subsets need not be nested. They are scored as separate fixed-budget devices, never passed off as an adaptive acquisition path.
- Full-bank and rich-spectrum references remain fitted-model comparators, not irreducible optical limits. Optical channels are simulated from documented emitter profiles, with the inherited detector/log-base limitations.

No revised deployment policy or universal LED configuration is promoted. The exact-budget fixed-design contrasts determine whether the earlier poor order was an avoidable source of error. Any selected configuration must be frozen using development data and evaluated on genuinely new seasonal and physical measurements before a confirmatory or hardware-performance claim.

## Reproduction and artifacts

Run .venv/bin/python revisions/fixed_design_v3/run.py all --resume. Separate design, evaluate, report, verify and status commands are available.

results/design_lock.json records the six complete designs before evaluation. results/design_subsets.csv and design_orders.csv retain the entire search. selected_designs.csv and selection_stability.csv record memberships and fold differences. metrics.csv, predictions.csv.gz, threshold_curves.csv and comparisons.csv retain every scored result. See verification_report.md for independent checks, preservation and resume evidence.
