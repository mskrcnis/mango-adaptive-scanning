# Frozen six-channel mango research candidate

The selected nominal centers are **720, 760, 820, 890, 910 and 940 nm**.
One six-channel PLS model and two comparison models are frozen after selection
and fitting using development seasons 1–3 only. The candidate estimates dry
matter; it does not give a validated instruction to harvest.

Read [decision_report.md](decision_report.md), [selection_protocol.md](selection_protocol.md),
[validation_protocol.md](validation_protocol.md) and [verification_report.md](verification_report.md).
[RUN_STATUS.md](RUN_STATUS.md) records execution and resumption status.

From the project root, reproduce the workflow without refitting complete work:

    .venv/bin/python revisions/candidate_v4/run.py all --resume

Run the actual sparse-input interface on three development examples:

    .venv/bin/python revisions/candidate_v4/predict.py --input revisions/candidate_v4/examples/development_channels.csv --mode candidate

The CSV requires exactly scan_id and led_720, led_760, led_820, led_890, led_910,
led_940. Feature column order is mapped by name. Values must be the frozen
finite-band apparent-absorbance representation, not point-wavelength absorbance
or uncalibrated photodiode intensity. Physical transfer has not been validated.
Extra features, outcomes and metadata are rejected. The output is dry matter in
percent fresh weight. There is no per-fruit confidence interval or pick/wait rule.

Explicit full-spectrum replay of the three comparison models:

    .venv/bin/python revisions/candidate_v4/predict.py --input revisions/candidate_v4/examples/development_spectra.csv --mode replay

The replay CSV has scan_id plus the 103 wavelength columns 684,687,...,990.
Replay constructs simulated channels offline; sparse candidate inference itself
does not require a full spectrum. Modes full_bank and rich accept the corresponding
exact feature columns in frozen/feature_schema.json. Add --output PATH to save
predictions. Examples are training-development rows and demonstrate software only.

Run contract tests:

    .venv/bin/python -m pytest -q revisions/candidate_v4/test_candidate.py

Execute full resume with before/after byte comparison and final verification:

    .venv/bin/python revisions/candidate_v4/verify_resume.py

The frozen/ directory contains portable JSON parameters, the NumPy/SciPy-only
inference module, exact integration weights, feature names, reference fitted
models, training row identities, selection protocol and hashes. The CLI can be
copied with that directory to a separate location; it has no fitting dependency.
environment.json records exact library versions. Original source/data remain
required to reproduce selection and fitting.

results/checkpoints/ contains 94 LOPO folds, one selection checkpoint and one
final-fit checkpoint with dependency/status metadata. results/selection_scores.csv
contains all 15 tuning scores. These are not independent validation estimates.
New fitting dependencies require a new revision; frozen files are not repaired
or silently overwritten. Earlier studies and their conclusions are preserved.

validation/ contains a readiness record, data dictionary and thirteen header-only
collection/custody/analysis templates. No new observations exist there. Descriptive
validation needs a frozen new-cohort sampling, precision, assay, QC and blinding
plan. Harvest claims additionally require justified cultivar/market maturity
criteria and an evaluated decision rule with field outcomes. The historical
0.25 percentage-point screen is not treated as an agricultural requirement.

Missing full-text comparisons still limit publication novelty claims; this freeze
does not resolve the prior-art audit. See ../../docs/literature_audit.md for the
established overlaps and unresolved journal methods. The negative adaptive
objective result remains part of the study.
