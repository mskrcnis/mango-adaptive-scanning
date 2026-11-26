# Independent audit plan: development-only fixed design revision 3

This bounded study selects fixed subsets and nested acquisition orders using
only the existing design groups. It follows two completed analyses whose held
development seasons have already been inspected. Results are exploratory;
seasons 4 and 5 must not be loaded, rescored or described as fresh validation.
All existing v1/v2 files remain unchanged.

## Design sample limitations verified from the saved assignments

Only development row IDs, population IDs and season metadata were used for the
following inspection. No outcome values informed these observations.

| Outer held season | Design scans / populations | Design season composition | Largest population share of scans | LOPO fitting populations | LOPO target populations |
|---|---:|---|---:|---|---|
| 1 | 998 / 9 | S2: 40 scans / 1 population; S3: 958 / 8 | 23.85% | 8 in every fold | 1 in each of 9 folds |
| 2 | 953 / 9 | S1: 211 scans / 3 populations; S3: 742 / 6 | 24.97% | 8 in every fold | 1 in each of 9 folds |
| 3 | 857 / 6 | S1: 661 scans / 4 populations; S2: 196 / 2 | 32.21% | 5 in every fold | 1 in each of 6 folds |

Before any real fitting, the root revised the initial three-fold proposal to
leave-one-population-out (LOPO) design predictions. The inspected three-fold
proposal would have left only three fitting populations in one split; LOPO
retains five or eight. The design samples remain small and imbalanced.
Scan-weighted MSE emphasizes large populations and dominant seasons. The minimum
after searching subsets or 720 orders is selection evidence, not an unbiased
estimate of the selected design's performance.

## Selection independence

1. Reconstruct the existing four roles from saved row IDs: core fitting,
   bank design, calibration and outer held season. Require exhaustive
   development coverage and no population or row overlap. Preserve original
   source row order, IDs and the 103-channel grid.
2. Design LOPO scalers and PLS/ridge estimators are fitted solely on the design
   training folds. Exactly one target population is absent from its predictor's
   fitting rows. Record training/target row IDs and fold IDs, including exact
   once-only coverage of design rows. Hyperparameters are fixed.
   All six bank/outer-season selections must be hash-locked before any reused
   v2 case is opened by the separate evaluation stage.
3. Select from the 64 masks containing the fixed two endpoint LEDs. For each
   depth, minimize pooled design OOF squared error and use the documented
   lexicographic tie break. Never use calibration or outer outcomes to choose a
   mask, bank, family, variant or ordering.
4. Independently enumerate all 6! = 720 permutations of the remaining LEDs.
   Score only their prefix masks at depths 2–7 with the prescribed equal-depth
   sum of design OOF MSE. Depth 2 is constant; depth 8 is constant and excluded.
   Confirm selected order is the exact global optimum with deterministic ties.
5. Per-depth best subsets may be nonnested. They are fixed-budget controls and
   cannot be stitched into one acquisition trajectory. The designed order must
   be a genuine nested path: start at two endpoints, add exactly one previously
   unread channel, terminate at all eight, never revisit a channel.
6. If PLS and ridge select different designs, report family-specific selection.
   Their differences then combine predictor and design changes; do not describe
   them as a comparison of predictor families on identical inputs.

## Reusing predictor arrays safely

- Require exact hashes of reused v2 case files and their source dependencies.
  Reconstruct subset columns by boolean mask tuples, not assumed column numbers.
- Verify v2 core OOF fit/target groups and assay/row ordering. New stopping
  targets use core OOF fS/fB/fF only; no predictor is fitted on design target,
  calibration or outer validation rows.
- Use the same bank, predictor family, outer fitting rows, endpoint and held
  scans across catalog-order, designed-order and best-fixed-subset variants.
- Verify each path's full endpoint equals the same family's full-bank reference.
  The rich reference remains the saved OOF/final rich PLS, with matching rows.
- A design-group OOF predictor selects the design; a core-fitting predictor
  supplies deployment predictions. That transfer between disjoint training
  samples is intentional and should be stated.
- Observed-only stopping features must be reconstructed for the new masks.
  Reindexing the old seven catalog-order feature vectors is insufficient when
  a new mask did not occur on that old path.

## Stopping, scoring and uncertainty

- For each legitimate order, the two stopping objectives share features, six
  nonterminal states per scan, model capacity, effort and acquisition path.
  Labels are the strict signed-gain event greater than 0.5 percentage points.
- Fit logistic stopping models on core OOF targets only. Fit isotonic mappings
  and select operating thresholds on calibration groups only. Recompute the
  registered scientific/engineering choices and every tie break independently.
- Freeze all choices before evaluating the held season. An outer-held assay
  perturbation must not change selected masks/orders, model parameters,
  calibrators, thresholds, or precomputed predictions.
- Reconstruct exported predictions from selected masks or first-stop rules.
  Verify row-level pairing, pulses, family endpoint and rich reference before
  recomputing regression, conditional missed-correction and budget metrics.
- Compare fixed controls at the same exact budget and stopping methods with
  achieved-budget qualification. Report all three held seasons and both banks,
  including unsuccessful variants. Do not select a favorable seed or season.
- Bootstrap whole harvest populations with paired resamples. The interval is
  conditional on the frozen design and does not include uncertainty from
  repeating design selection. It does not erase prior reuse of held seasons.

## Preservation and failure checks

- Snapshot all pre-existing scientific v1 and v2 files before execution and
  verify hashes afterward. Writes belong exclusively under fixed_design_v3,
  apart from an explicitly authorized append to the root status log.
- Runtime guards reject external assays, features and previous scored results
  before opening them. Integrity-only hashing of protected files does not
  authorize parsing their outcomes.
- Checkpoint design folds, selected designs and stopping cases with hashes of
  code, protocol, split assignments, data, profiles and reused prediction arrays.
  Reject stale, incomplete or mismatched checkpoints.
- Tests should cover adversarial nonnested subset optima, every order's legal
  prefixes, tied scores, NaN/shape rejection, exact row alignment, group leakage,
  observed-only features, strict event boundaries and independent data-role
  perturbations.
- Complete a real interrupted/resumed or full resumed execution and compare
  checkpoint/result bytes. Preserve v1/v2 hashes separately from v3 resume
  hashes. Final status must distinguish source review, synthetic tests,
  executed numerical verification and scientific conclusions.
