# Methodology revision 2: development-only controlled comparisons

Authorized after review of version 1. This is an exploratory methodological
revision motivated by the completed study, including its external results.
Seasons 4 and 5 are not fresh validation sets and will not be loaded or rescored.
No version-1 model, result, manuscript, or application is replaced. A successful
development result would still require a new independent harvest season.

## Locked scope before new fitting

Reuse the official checksum-validated data and optical emulator, seasons 1–3,
the three saved leave-one-season-out partitions, and their disjoint fitting,
bank-design, and calibration harvest groups. Use the prior primary `swap_mid`
bank and catalog-only `uniform` bank without searching for another bank. The
primary case is swap_mid, seed 42. Repeat swap_mid with existing seeds 7 and 99;
uniform is the independent-bank sensitivity at seed 42. Seed variability applies
to reused MLP predictions; PLS, ridge, partitions and logistic fits are deterministic.

1. **Exact-subset prediction diagnostic.** Enumerate all 64 masks containing the
   same two endpoint LEDs. Compare the existing masked MLP with subset-specific
   PLS (min(6, number of channels) components, autoscaling) and ridge (training
   StandardScaler, alpha=10). No hyperparameter search. Every training-target
   prediction uses exactly the existing three grouped inner folds; scalers and
   models are fitted within the matching training partition. Validation and
   calibration predictions use the same outer fitting rows. Existing MLP outputs
   at depth 8 are explicitly labelled the MLP-to-PLS hybrid, never a raw full-mask
   MLP: the old MLP was not trained on that mask. PLS is the primary consistent
   predictor family and ridge a prespecified sensitivity. Full PLS reproduces fB.
2. **Endpoint decomposition.** At depth 7 on the common order, compute signed
   absolute-error differences, scan by scan:
   (e_MLP7 - e_PLS8) = (e_MLP7 - e_PLS7) + (e_PLS7 - e_PLS8).
   Report both components, without assuming positivity or calling model-relative
   gains irreducible optical information. Also report complete error-by-depth
   curves and equal-mask summaries over the enumerated subsets.
3. **Stopping-only contrast.** Use the same fixed order for all predictors and
   objectives. Start with the lowest/highest center; repeatedly choose the unread
   center with largest minimum distance from acquired centers, ties by lower
   center/index. This is catalog-only, independent of every target assay. For
   each predictor family separately, train two logistic stopping models with
   identical observed-only input values/masks, rows, effort and fixed order.
   Labels are |y-fS|-|y-fB| > 0.5 versus |y-fS|-|y-fF| > 0.5. Here fB is that
   family's full-bank predictor (PLS for hybrid) and fF the saved rich PLS.
   There is no action head or shared acquisition objective. Each scan contributes
   the same six nonterminal states. Equal scan weights match the actual v1 fit.
   References are model-relative comparators, not error-free oracles.
4. **Calibration and decisions.** Fit isotonic mappings on disjoint calibration
   groups along the entire common path. The same calibration set selects a
   threshold from 0,0.05,...,1; its apparent performance is tuning evidence only.
   Outer held-season outcomes are excluded from every choice. Scientific point:
   closest mean reading count to 4, then lowest calibration RMSEP, then lowest
   threshold. Separate prototype screen: RMSEP <= own full-bank RMSEP+0.25 pp
   and mean readings <=6 (25% saving); choose fewest readings then RMSEP. Mark
   an infeasible fallback explicitly. This is the two-condition prototype screen,
   not the stricter multi-constraint v1 search. Include all fixed lengths 2–8 and
   all frozen threshold curves. A >0.25-reading achieved difference prevents an
   unqualified scientific objective comparison. Report missed-material-correction
   counts, denominator and rate; Brier scores refer to each model's own event.
5. **Evidence and stopping.** Report every held season separately, paired harvest-
   group bootstrap intervals (1000 draws, seed 42) for primary comparisons where
   at least five groups exist, and seeds separately. Comparisons with fixed-four
   are also budget-qualified. Do not pick a winning seed/fold/threshold on held
   outcomes. Execute this one bounded diagnostic round; do not add learned
   ordering or refit a deployment application based on a favorable subset.

## Reproducibility and verification

All files reside in this revision directory except an appended root RUN_STATUS
entry. Hash existing scientific artifacts before work and verify preservation.
Hash data, saved source bundles, protocol and implementation into dependencies;
checkpoint each predictor fold and each stopping case atomically. Changed fitting
dependencies invalidate descendants; completed checkpoints do not rewrite on
resume. Record read paths and reject external outcome/feature loading at runtime.
Test hidden-channel invariance, measured-zero/missing distinction, group splits,
exact endpoint agreement, signed decomposition, stopping termination, target
definition, and threshold selection. Independently recompute scored quantities.
Run a complete resume and verify that checkpoint and result bytes are unchanged.

Launch: `.venv/bin/python revisions/methodology_v2/run.py all --resume`.
Verification: `.venv/bin/python revisions/methodology_v2/run.py verify`.
The revision's RUN_STATUS.md records finer-grained progress and recovery commands.
