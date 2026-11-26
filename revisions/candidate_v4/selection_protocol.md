# Final research-candidate selection and freeze

This is an authorized finalization following the completed exploratory v3 study,
not another held-season comparison or independent validation. The user's goals
are a research paper establishing the method's capabilities and limits, and
eventual support for mango harvest timing. The current artifact predicts dry
matter; it does not issue a validated pick/wait recommendation.

## Rule fixed before this finalization's fits

Use only the existing checksum-verified development.csv: seasons 1–3, 10,243
recorded spectra and 94 harvest populations. Fruit identities remain unknown.
Read it directly without the mixed-season metadata file. No external spectra,
assays or earlier prediction/results tables enter selection or fitting.
Separate preservation checks may hash earlier files as opaque bytes; those are
integrity operations, not parsing or scoring external outcomes.

Retain the v3 primary eight-channel bank: catalog indices 0,2,3,4,5,7,8,9;
nominal centers 720,760,780,800,820,890,910,940 nm. Retain endpoint channels 720
and 940 nm. Enumerate the 15 six-channel subsets containing both endpoints,
in lexicographic local-index order. No new bank, channel count, learner or
hyperparameter search is authorized by this finalization.

For each harvest population, fit each subset on all other development
populations and predict that population. All transform fitting excludes the
target population. Fit apparent-absorbance values and assays at the inherited
float32 boundary; calculate selection MSE against the original float64 assays.
Use autoscaled PLS with exactly six components, max_iter=500 and the inherited
sklearn tolerance. There is no sparse-spectrum SNV or derivative transform.

Pool squared errors with equal weight per scan across the 94 held-population
folds. Choose the minimum pooled MSE; exact ties use the lexicographically
sorted six local indices. Retain all 15 scores, all fold predictions and row/
group provenance. Report unequal scan and population representation by season.
The selected CV score is a tuning statistic, never new validation accuracy.
No selection by earlier held-season winners or manual wavelength vote is used.

## Final fit and comparison models

After selecting one subset, refit three models on the identical complete
development rows:

1. Selected six-channel PLS, six components and autoscaling.
2. Existing full-eight bank PLS, six components and autoscaling.
3. Inherited rich-spectrum PLS, twelve components, rowwise SNV, then a
   Savitzky–Golay second derivative (window 11, polynomial order 2, spacing
   3 nm), and autoscaling on the 103 channels 684:3:990 nm.

Using all development rows for both final selection and final fitting is
intentional for a future-test candidate. It does not reproduce v3's disjoint
design/core evaluation, nor produce a new unbiased development estimate.
Six components with six input variables is a full-rank linear fit when the
data have full rank; no latent dimension-reduction advantage is claimed.

The optical emulator and digitized manufacturer profiles are unchanged. Freeze
the exact normalized integration weights alongside the model parameters.
Flat detector/reference response and the inherited absorbance convention remain
simulation assumptions. Six-channel inference accepts exactly those six values;
full-spectrum transforms are used only by the rich-spectrum comparator.

## Lock, execution and verification

Write registration.json with source, protocol, data and optical-profile hashes
before the first real-data fit. Cache every LOPO fold atomically by dependency,
and retain a final selection checkpoint and final-model checkpoint. A completed
frozen bundle must never be silently overwritten or repaired: changed fitting
dependencies require a new revision. Reuse matching completed checkpoints.

Freeze portable model parameters, inference source, integration weights,
channel identities, model settings, fit-row provenance and the selection rule
under frozen/manifest.json. Include reference sklearn models for independent
parity checks. The local hash manifest is a reproducibility lock, not a public
timestamped preregistration or a cryptographic guarantee against an administrator.

Verify source/data fingerprints; 94 disjoint fitting/target populations; all
15 selection scores and tie rules; saved-model versus portable inference;
sparse-input boundaries; numerical finiteness; protected earlier versions;
normal CLI execution; and full resume byte preservation. Capture fit warnings.
Development replay examples test software, not out-of-sample performance.

## What this freeze does not settle

New independent seasonal populations, a fruit-identified validation cohort,
sample-size/precision justification, intended cultivar/region/market, a justified
harvest dry-matter threshold, acceptable prediction error, and physical optical
transfer remain unresolved. The accompanying validation protocol distinguishes
descriptive scientific validation from application acceptance. Missing practical
tolerances do not prevent this research-candidate freeze or descriptive future
error estimation. They do prevent a validated harvest recommendation.

Seasons 4–5 have already been examined in earlier work and cannot become a new
confirmatory test. Physical calibration using new labeled fruits creates a new
development version requiring a separate later validation cohort. No harvesting
benefit, energy saving, latency improvement or novelty claim follows from this
software freeze. Preserve every earlier study and its negative adaptive result.
