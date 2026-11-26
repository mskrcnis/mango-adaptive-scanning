# Independent audit plan for methodology revision 2

Scope: development seasons 1–3 only. This is a post-v1 methodological diagnostic,
not a fresh external validation. No v1 file is edited by this audit. Hashing protected
files for preservation does not parse their contents as research observations.

## Findings checked before revision fitting

The existing development CSV contains 10,243 scans in 94 harvest populations.
The saved assignments are exhaustive and pairwise disjoint in both rows and
populations, including the separate bank-design partition.

| Held season | Fit rows/groups | Design rows/groups | Calibration rows/groups | Validation rows/groups |
|---|---:|---:|---:|---:|
| 1 | 4,003 / 46 | 998 / 9 | 1,328 / 14 | 3,914 / 25 |
| 2 | 5,656 / 51 | 953 / 9 | 2,271 / 15 | 1,363 / 19 |
| 3 | 3,054 / 29 | 857 / 6 | 1,366 / 9 | 4,966 / 50 |

Read-only inspection of the 12 saved development bundles (swap_mid seeds 42/7/99
and uniform seed 42, each held season) passed 108 checks: fitting and calibration
row order equals the saved assignments; OOF groups align with those rows; all 64
masks and prediction shapes are present; full-mask OOF predictions equal the
bank reference exactly; the held season is absent from fitting; and all inner
folds contain whole, disjoint populations matching their recorded provenance.
These are checks of the source artifacts, not a completed v2 verification.

Important implementation facts established by reading the current source:

- Actual v1 training used equal scan weights (`group_equal_weight=False`).
- Full-mask masked predictions dispatch to the bank PLS. The old neural network
  was trained only on nonterminal masks; depth-eight equality is structural.
- V1 predictor fitting casts channel values and assays to float32. Its saved OOF
  predictions are also float32. New subset PLS fitting must reproduce the input
  precision; a small saved-OOF rounding difference is distinct from model drift.
- The saved OOF mask order is combinatorial, not acquisition order. Exact mask
  tuples must map the common path to prediction columns.
- V1's learned fixed order uses core-fitting OOF gains. V2's catalog-only order
  avoids selecting a target row's path with that row's assay.
- V1 `calibrate()` follows separate adaptive paths. V2 requires calibration on
  the same fixed path for both stopping objectives.

## Required checks and acceptance evidence

| Area | Concrete acceptance check |
|---|---|
| Preservation | Compare all pre-existing scientific artifact hashes before/after and after resume; forbid missing/changed files and unexpected new files under protected v1 directories. Only the explicitly allowed root status append and runtime caches are excluded. |
| Scope | Runtime open guard rejects sealed source/labels, external features and prior scored results before bytes are read. Read audit contains only development, metadata, catalog/profile and selected development-checkpoint paths. No revision function calls a v1 workflow stage. |
| Dependencies | Registration hash equals its canonical dependency map; every current dependency matches, including catalog JSON, profile CSVs, development CSV, metadata, saved fold assignments, predictor sources and fitting implementation. Every checkpoint hash and dependency is current. |
| Partitions | Reconstruct IDs from the development CSV and saved v1 assignments; verify identical ordering, four-way population disjointness, complete development coverage, held-season identity, and the same inner fold IDs for all compared families/seeds. |
| Exact masks | There are 64 unique endpoint-containing masks. Depth counts 2–8 are 1/6/15/20/15/6/1. Every model selects only columns in its mask; no full-spectrum row normalization enters subset predictors. |
| OOF targets | Each subset model's fit and target IDs exactly match its saved inner partition. Their group intersection is empty. All fS, fB and fF controller targets are out of fold for the target population; scaler statistics are fit only on the matching predictor fitting rows. |
| Common order | Independently reconstruct farthest-center-first order with lower-center/index ties. It contains each installed channel exactly once, begins with the same two endpoints and is shared across families and objectives. |
| Endpoint | Every path ends at its own full-bank predictor. MLP hybrid and PLS endpoints agree exactly after the documented float32 OOF rounding reconciliation; ridge uses its own full-bank model. Verify newly fit full PLS against saved full PLS. |
| Observed information | At every depth, feature mask matches the path and unread feature values are zero after masking. Replace unread raw values with extreme values/NaNs and require identical predictions/probabilities; measured zero remains distinguishable from missing. |
| Matched stopping | Both logistic models use identical feature rows, six states per scan, capacity, optimization settings, class/scan weights and acquisition order. Only the target reference changes. Verify positive counts directly from saved OOF predictions and assays. |
| Signed labels | Recompute eS−eB and eS−eF with the strict >0.5 event, preserving negative gains. Do not interpret either model-relative reference as a noiseless oracle. |
| Selection | Reconstruct all 21 calibration thresholds and both deterministic selection rules from calibration paths only, including tie breaks and infeasible fallback. Held-season outcomes never select thresholds, family, order or seed. |
| Predictions | Independently apply first probability ≤ threshold, forcing depth-eight termination. Match exported per-row prediction, reading count, bank/rich reference and identifiers; enforce a unique complete row set for each policy. |
| Metrics | Recompute RMSEP, MAE, signed prediction-minus-assay bias, R², pulse summaries, large-error counts and conditional/unconditional missed-correction rates. Early-stop count is the conditional denominator; no early stops gives an undefined conditional rate. |
| Predictor summaries | `all_masks` means pooled scan×mask RMSEP/MAE/bias; `common_order` has one mask per depth. Verify scan/mask counts. A mean of per-mask RMSEs is a different statistic and must not silently replace the pooled definition. |
| Decomposition | For every validation scan, verify (eMLP7−ePLS8)=(eMLP7−ePLS7)+(ePLS7−ePLS8), including signs and exact shared depth-seven mask. |
| Comparison | Pair by season/bank/seed/family/row ID; use the same cluster draws across policies. Report achieved pulse differences and enforce the 0.25-reading comparability qualification. Fixed-four comparisons use the same predictor family and common mask. |
| Interpretation | Brier scores target different events across objectives. Full-bank missed-correction targets differ across predictor families. Neither quantity directly ranks objective/family quality without that qualification. |
| Resume | Re-run the complete revision command and compare bytes of completed checkpoints and research outputs. Status/log timestamps may append; scientific outputs may not change. Failed/incomplete artifacts cannot pass a completed checkpoint hash check. |

`verify.py` performs independent artifact, path, selection, exported metric and
decomposition reconstruction after reporting. The synthetic tests exercise
hidden-value invariance and boundary conditions. A pass in either component does
not by itself establish the other component's pass, nor establish external
generalization or physical-device performance.
