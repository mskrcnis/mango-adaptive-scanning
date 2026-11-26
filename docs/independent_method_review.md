# Independent implementation review before external scoring

Reviewed `docs/protocol.md`, `config/experiment.json`, the training, prediction,
evaluation, workflow, static-baseline and external-scoring modules, and the
separate Walsh reference on 26 November 2026. This is a bounded code/method
review, not independent experimental replication or hardware validation.

Three recoverable issues were identified and corrected before opening external
assays. The preliminary run and the amendment are preserved by the main workflow.

| Finding | Correction and reviewed evidence |
|---|---|
| Supervised correlation/Ridge bank proposals originally used all outer-fitting labels before inner prediction cross-fitting. Thus a target group's label could influence its selected feature bank even when the target-producing predictor excluded that group. | A separate 15% of non-calibration training groups, seed 2718, now constructs banks. These groups are excluded from model training and target generation for every bank rule. `get_bundle` passes only design-group readings and labels to `bank_rules`. The same correction applies to ideal and static bank membership. |
| The development dependency key originally omitted the forward-emulator source. | `registration` now includes the SHA-256 of `mango/optics.py`. The final scorer additionally checks live runtime modules against frozen copies and verifies profile hashes. |
| Sparse selection originally standardized all fitting observations before internal grouped LassoCV. | Explicit grouped alpha evaluation now fits a fresh StandardScaler in each inner fitting fold and applies it to that fold's held observations. Only the final selected-alpha refit uses all supplied fitting observations. The static artifact retains group splits, candidate losses, chosen alpha and warning counts. |

The revised real-data partitions were independently executed for all three
held-season folds and the final development fit. Fit, bank-design, calibration
and validation groups are pairwise disjoint and jointly exhaust development
rows. Results are saved in `data/literature/review_split_verification.json`.
The model agent's `tests/test_pipeline.py` additionally checks invariance of
candidate banks after replacing all non-design features/outcomes, and tracks
each actual scaler fit to ensure exclusion of its inner validation groups.

The following boundaries are supported by the reviewed code:

- Inner target-producing predictors, scalers and target statistics use only
  their fitting groups; final controllers use the resulting held-group targets.
- Partial prediction, gain prediction and conditional look-ahead mask unobserved
  readings before scaling. Synthetic future observations use training covariance
  conditioned on observed coordinates. Full-bank prediction dispatches to the
  same bank reference used by the error-gap definition.
- Proposed and single-reference controllers share architecture, action targets,
  training counts, seeds and initial channels. Their different stop losses share
  a network trunk, so they may learn different action estimates; this is an
  effect of the joint objective rather than an independently held-fixed action
  head. Comparisons remain matched in training capacity and effort.
- The external scorer loads locked artifacts, generates/cache-locks nominal,
  ideal and response-perturbed predictions before parsing external outcomes,
  and performs no fitting or threshold selection. The ideal analysis has its
  own development-selected operating index. Sensitivities retain frozen physical
  policy parameters and are explicitly transfer perturbations.
- Undefined early-stop conditional rates cannot satisfy engineering selection.
  Cluster intervals are suppressed when fewer than five populations exist;
  such intervals would not quantify variation over future seasons in any case.

The compact CNN is a generic secondary model. The separately added
`mango/walsh_reference.py` follows the verified author architecture and schedule,
with its raw-input/local-split/PyTorch adaptations disclosed in
`docs/walsh_reference.md`. Its development-only smoke verified finite prediction,
group-disjoint early stopping and exact prediction preservation across joblib
serialization (`data/literature/walsh_smoke.json`). Full experimental results are
owned by the run ledger; this review does not mark those fits or external scoring
complete.

Remaining interpretation limits are substantive: bank/rich prediction gaps
combine optical and estimator differences; the population grouping cannot prove
fruit-level identity isolation where identifiers are missing; the same external
seasons were used in earlier local work; base-10 apparent absorbance is a
documented conventional assumption rather than a verified firmware logarithm
base; and digitized typical curves with flat detector/reference response are
offline optical models. The numerical response profiles are distinct, but noise,
timing, energy, calibration drift and physical repeatability require measurements.
The literature audit identifies overlap and inaccessible full methods; it does
not establish absolute originality or patentability.
