# Fixed-subset and acquisition-order follow-up

This is one completed, exploratory development-only revision of the mango study.
It preserves versions 1 and 2 and excludes external seasons 4 and 5. The
registered design procedure, including the six-reading engineering sensitivity,
is in [protocol.md](protocol.md). See [decision_report.md](decision_report.md)
for results and limits, and [verification_report.md](verification_report.md) for
independent checks. [RUN_STATUS.md](RUN_STATUS.md) is the resumption anchor.

Run from the project root using the existing scientific environment:

    .venv/bin/python revisions/fixed_design_v3/run.py all --resume

Individual commands are design, evaluate, report, verify and status. Complete
checkpoints are reused automatically; resume is explicit in the documented
command. Design and evaluation run in separate processes. The six design cases
must be locked before evaluation arrays can be opened. Do not delete or edit the
lock to select new channels after examining evaluation outcomes.

Software contract tests:

    .venv/bin/python -m pytest -q revisions/fixed_design_v3/test_design.py

Full resume with explicit before/after hashes, followed by independent verification:

    .venv/bin/python revisions/fixed_design_v3/verify_resume.py

Artifacts:

- results/checkpoints/: 48 design cross-validation folds, six complete designs,
  and six evaluation cases, each with atomic dependency metadata.
- results/registration.json and design_lock.json: input/code fingerprints and
  the complete pre-evaluation selection lock.
- results/design_subsets.csv and design_orders.csv: every candidate score;
  selected_designs.csv, design_composition.csv and selection_stability.csv:
  selection and population provenance.
- results/metrics.csv, predictions.csv.gz, threshold_curves.csv and
  comparisons.csv: all policies, predictions, frozen curves and comparisons.
- figures/: PNG and PDF versions of fixed-design curves and stopping curves.
- results/verification.json, software_tests.json, visual_verification.json and
  resume_verification.json: separate numerical, software, visual and resume
  evidence. integrity_manifest.json records final artifact hashes.
- prior_versions_preservation.json: protected original and v2 artifacts.

This revision reuses the verified v2 subset predictions and the root optical
simulation code. It is not a standalone data redistribution or a replacement for
the original app. Its findings support further validation of fixed acquisition;
they do not validate one universal LED device, physical savings, or a new
adaptive stopping advantage.
