# Registered evaluation protocol

This protocol is saved before predictive model selection. The machine-readable
configuration is `config/experiment.json`. Registration becomes complete when the
data/catalog hashes and exact fold assignments are saved in
`results/protocol_lock.json`, before the first development fit.

## Observation and reuse boundary

The observation is a spectral scan, not a verified unique fruit. Provider v3 lacks
fruit IDs. All records of each documented season/population stay together. Seasons
1–3 are development; seasons 4 and 5 are evaluated separately after artifact lock.
Earlier local work in `../Pratyu` scored the same external releases. Its numerical
results are not consulted here, but these seasons are reused benchmarks and are
not a newly collected independent replication. Exact cross-partition spectral
duplicates are audited without exposing external assays; any removal occurs on
the fitting side and is logged. No identities are inferred from assay equality.

## Optical scope

Use original apparent absorbance and intensity-domain finite-band integration,
with bin widths and a flat detector/reference response because a calibrated
response curve is unavailable. Include only profiles with at least 95% of modeled
mass inside 684–990 nm. Typical data-sheet traces and Gaussian approximations are
separate analyses; neither represents measured hardware. Primary candidate choice
is based on distinct verified component profiles. Eight installed LEDs and a
target of four charged readings are primary when more than eight candidates are
eligible. Two bank endpoint channels are initially measured for every policy.

## Model separation

Leave one whole development season out. In the remaining seasons reserve 20% of
harvest groups using seed 31415 for probability and threshold calibration. Within
the fitting groups use three-fold grouped cross-fitting to generate every
controller's partial/reference/gain target. Scalers and all reference predictors
are fitted only within the corresponding fitting partition. Controller inputs are
acquired channel readings and a binary mask. Missing placeholders are zero after
training-side scaling and independent of unacquired readings. All-installed
predictions dispatch to the frozen bank reference. Final bundles use the same
train/calibration split scheme on all development seasons.

The proposed stop label is `|y-fS|-|y-fB| > 0.50`; the matched single-reference
label uses `|y-fS|-|y-fF| > 0.50`. Their action targets remain the same signed
one-step absolute-error reduction. BCE and signed MSE heads have separately scaled
losses. Every scan receives equal total training weight over sampled/enumerated
masks. We retain negative gains. A second full-spectrum CNN checks the dependence
of bank-loss conclusions on the rich reference; it is an adapted implementation,
not an exact reproduction of the authors' original split.

## Search and operating points

At most six candidate-bank construction rules share the same catalog and full
evaluation table. These comprise evenly spaced/catalog-only alternatives and
training-only feature selection proposals. Each held-out season uses candidate
construction from its fitting data only. The final bank repeats the chosen rule
on final fitting data. Catalog-only evenly spaced selection is the independent
bank sensitivity. All capacity and initialization comparisons are matched within
bank. Hardware ablations select from the identical evaluated candidate table by
full-bank error alone, sequential error alone, or the proposed constraints.

The primary scientific operating point minimizes the absolute difference between
mean development pulses and four, then worst-season RMSEP, then lower threshold.
Each controller gets its own development-selected operating point. The separate
engineering operating point requires all development seasons to satisfy material
missed-correction rate <=10%, bank-loss rate <=10%, policy RMSEP <= rich RMSEP+0.25,
and mean pulses <=4. Undefined missed rates cannot satisfy screening. Feasible
choices minimize pulses, then worst-season RMSEP. If none passes, minimize maximum
normalized violation, then worst-season RMSEP, then mean pulses. Do not relax any
criterion. Also retain a mean-season RMSEP bank-selection sensitivity.

Probability threshold grid: 0 to 1 in increments of 0.05. Disjoint calibration
fits an isotonic mapping using complete sequential acquisition paths. The
uncertainty threshold uses training-calibration quantiles; fixed-length paths use
2–8 pulses. Fixed order is fitted using training-only expected one-step gains;
random order is seeded. The non-greedy comparator is a two-step look-ahead using
training-only conditional estimates of unseen readings, explicitly an approximation
and not an implementation of acquisition-conditioned oracle. Static physical
PLSR/SVR/MLP budgets and ideal point 4/8/16 benchmarks are separately identified.

## Refinement and stopping the search

Pilot one development fold after software smoke tests to estimate cost. Initial
epochs and exact implementation choices are recorded in the protocol lock.
Allow at most two documented development-only refinement rounds for calibration,
rare labels or mask/path mismatch; apply comparable effort to both objectives.
Record every attempt and failure. Full model checkpoints are keyed by fold, bank
rule and seed; trained methods and calibration share the same deterministic
dependency key. No external-result-driven model changes are allowed.

## External estimands and uncertainty

The primary estimand is paired RMSEP(proposed)-RMSEP(single-reference), separately
in each external season, at their common development-targeted pulse budgets.
The mechanism outcome is material missed corrections among early stops, with
counts, denominator, unconditional rate, early-stop coverage and pulse use.
An achieved external mean-budget gap >0.25 pulse makes the primary comparison
budget-confounded; show the full frozen error/pulse curves without test tuning.
Report absolute full-bank and rich-reference errors and signed gain distributions.
Report Brier scores and reliability on visited states separately from final scans.

Use paired bootstrap of entire harvest populations (1000 replicates, seed 42)
only where at least five groups are present. Season 5 has two populations:
suppress population-level confidence intervals and show each group. These are
within-sampled-season analyses, not uncertainty over future harvest seasons.
Stochastic seeds 7/42/99 are reported separately, never cherry-picked or conflated
with group uncertainty. Profile shifts +/-3 nm and width factors 0.9/1.1 are
engineering perturbations, not asserted manufacturer tolerances unless documented.

Prototype screening requires <=0.25 pp RMSEP increase relative to full bank and
at least 25% fewer mean readings in each season. These are illustrative engineering
criteria, not grower specifications. Statistical improvements do not establish
hardware energy, speed, repeatability, clinical/agronomic utility or patentability.

## Lock and corrections

Before external loading, hash code snapshot, data, fold assignments, catalog,
models/scalers/calibrators, thresholds, seeds, tolerance and operating points.
The isolated external scorer only loads these artifacts and never calls fitting
or selection. Defects discovered later retain original artifacts and receive
versioned all-method corrections. Reporting-only runs cannot fit models.

## Pre-external audit amendment: bank-design isolation

Before external scoring, independent code review identified that supervised bank
construction on all fitting labels could influence inner OOF target predictions.
The preliminary scores are retained under `results/attempts/pre_bank_design_split`.
Reserve 15% of the non-calibration training harvest groups (seed 2718) exclusively
for bank construction, and exclude these groups from model fits and all controller
target cross-fitting. Correlation and Ridge bank proposals use only this disjoint
design subset. Apply the same fit/design/calibration partition to every candidate
for a fair comparison. All affected preliminary fits are invalidated and rerun.
Outer validation seasons and both external seasons remain unseen by all choices.
This is a leakage repair, not a response to external predictive results.

The generic compact full-spectrum CNN remains a secondary reference. A separate
Walsh-architecture baseline uses the verified one-filter width-21 convolution,
36/18/12 ELU layers, train-side group validation and author-style learning schedule.
It is adapted to the present 103-channel inputs and grouped seasonal protocol.
