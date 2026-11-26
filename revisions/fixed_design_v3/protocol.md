# Fixed-subset and fixed-order study: revision 3

This exploratory follow-up was authorized after revision 2. All three development
seasons have already been inspected in earlier work. No fresh confirmatory claim
is possible from them. External seasons 4 and 5 are excluded from this round.
Preserve version 1 and revision 2 byte for byte, apart from the append-only root
RUN_STATUS.md. No new model is deployed or substituted into the original app.

## Scope locked before new design fitting

Reuse the original leave-one-development-season-out partitions and four disjoint
roles: core fitting, bank design, calibration, held-season evaluation. For each
held season, keep the two eight-LED banks swap_mid (primary) and uniform
(sensitivity). Initial LEDs remain local bank endpoints 0 and 7. There are exactly
64 reachable masks, including full bank, and 720 possible orders of the other
six LEDs. No bank search or change in initial channels is included.

Use subset-specific PLS (min(6, observed count) components, autoscaling) as primary
and standardized ridge (alpha 10) as sensitivity. Hyperparameters are fixed.
Fit design predictors on float32 optical values/assays, consistent with version 2;
evaluate design squared errors against the original development assay values.
All selection is deterministic; seed replication would not provide independent
evidence. Ridge has its own design selections, so across-family results do not
isolate predictor family at matched subsets.

## Design-only selection

Use only the reserved design populations: 9, 9 and 6 groups (998, 953 and 857
scans) for held seasons 1, 2 and 3, respectively. Generate leave-one-population-out
predictions for every reachable mask: each design target group is excluded from
its scaler/model fit. This retains 8, 8 and 5 training groups per design fold.
Select using pooled scan mean squared error; all scans have equal weight.
Record unequal population and source-season sizes explicitly. Selection minima
are tuning evidence, not unbiased performance estimates.

For each bank/family, independently:

1. Select the fixed subset for each depth 2–8 with lowest design OOF MSE; exact
   ties use lexicographically sorted local acquired indices. These seven subsets
   need not be nested and are separate fixed-budget scanners.
2. Enumerate all 720 orders beginning with the two fixed endpoint readings.
   Select the order with minimum sum of design OOF MSE over prefixes of depths
   2–7 (equal depth weights); exact ties use lexicographic complete order.
   The full-bank cost is constant and is excluded from this sum.
3. Retain revision 2's catalog-only farthest-spacing order as the control.
   Retain every mask score and every candidate-order score, and the top-two
   margins. Do not add an order or subset after seeing evaluation outcomes.

Complete all six bank/outer-season designs and write a hash lock before loading
core/calibration/held prediction arrays. A separate process performs evaluation.
Selection APIs accept design data only, with exact row/group provenance.

## Evaluation after design lock

Reuse the hash-verified version-2 PLS/ridge predictions for all 64 masks, rather
than refitting an unchanged model. Core targets are the original three-fold
grouped OOF predictions; calibration and held predictions came from models fitted
only on core groups. The design groups remain excluded from those fits. Verify
every row, mask and endpoint against the source artifact.

Score all fixed lengths 2–8 along the catalog and selected nested orders, and
all seven separately selected fixed subsets. The primary fixed-budget contrast
is selected order minus catalog order RMSEP at exactly four readings, separately
for each held season on the primary PLS bank. Selected fixed-four subset versus
catalog fixed-four is a second prespecified contrast. Depth six is a prespecified
engineering sensitivity. These are exact-budget comparisons.

For context, repeat revision 2's stopping-only comparison on both nested orders.
Keep the same logistic learner, group-disjoint isotonic calibration, two labels,
training effort, threshold grid (0:0.05:1), scientific four-reading target and
separate engineering screen. Only the order changes. Both objectives for an order
share identical predictions and acquired-state features. The scientific
objective comparison is inconclusive at an achieved reading gap above 0.25.
Never interpret independently selected, nonnested fixed subsets as one trajectory.

Screen fixed-four, fixed-six and the calibration-selected engineering policies
against their own same-family full-bank RMSEP +0.25 percentage points and at most
six mean readings. Also give absolute errors and primary-bank full PLS alongside
the weaker bank references. Relative-screen success alone does not show adequate
absolute accuracy or a benefit from adaptation.

Report every held season and both banks/families. Use paired harvest-population
bootstrap intervals (1000 draws, seed 42) for registered comparisons; these are
conditional on the fitted/selected design and sampled populations, not confidence
over future seasons or repeated design selections. No multiple-comparison
correction is claimed. Show bank/order membership and selection stability across
outer folds without choosing a universal winning configuration using held labels.
Repeated development use makes the whole follow-up exploratory.

## Bound, safeguards and handoff

One complete fixed-design round; no additional tuning, new learner, new initial
pair, noise model or catalog search in response to scores. Report negative,
inconclusive and favorable results equally. Do not force a low-cost policy when
accuracy is worse. Physical validation and a genuinely new seasonal dataset
remain outside this software-only evaluation.

Hash data, source cases, protocol and selection code before fitting. Atomic
checkpoints cover each design fold, selected design and evaluation case. Record
failures and resume without refitting complete stages. Tests must cover grouped
fit/scaler isolation, non-design-data perturbation invariance, exhaustive-search
optimality and ties, nonnested subsets, hidden-channel masking, source prediction
replay, full-bank identity, preservation and resume. Independently reconstruct
selection scores, evaluated metrics and selected paired intervals.

Entry point from the root:

    .venv/bin/python revisions/fixed_design_v3/run.py all --resume

Commands design, evaluate, report, verify and status are available separately.
RUN_STATUS.md records progress; decision_report.md and verification_report.md
are the final handoff. No external scoring, publication or hardware purchase.
