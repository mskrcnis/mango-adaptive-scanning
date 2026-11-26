# Isolated methodology revision

This completed diagnostic round preserves version 1. It uses only development
seasons 1–3 and does not update the original external evaluation or application.

Run from the project root:

    .venv/bin/python revisions/methodology_v2/run.py all --resume
    .venv/bin/python revisions/methodology_v2/run.py verify
    .venv/bin/python -m pytest -q revisions/methodology_v2/test_revision.py

The fit, report, and status commands are also available. fit --pilot
executes the first real-data case. Completed valid checkpoints are always reused;
changed dependencies invalidate affected results. The environment is the
original project-local environment and environment.lock.txt in the root.

- protocol.md: registered scope, estimands, thresholds and limitations.
- decision_report.md: interpretation and complete primary tables.
- verification_report.md: independent numerical and preservation checks.
- RUN_STATUS.md: chronological execution and recovery record.
- results/registration.json: exact fitting dependencies and case list.
- results/checkpoints/: fold-local subset models, OOF predictions, stopping
  models, calibration mappings, operating points and provenance.
- results/policy_predictions.csv.gz: paired per-scan development outcomes for
  every policy and fixed-length control.
- results/predictor_metrics.csv, policy_metrics.csv, threshold_curves.csv,
  paired_comparisons.csv, endpoint_rows.csv, endpoint_summary.csv: complete
  scored tables, including unfavorable comparisons.
- figures/: standalone PNG and PDF scientific plots.
- v1_preservation.json: hashes of pre-existing scientific files. Root
  RUN_STATUS.md is intentionally excluded so the follow-up can be recorded.

The revision was motivated by inspection of the completed study, including its
external results. It is exploratory even though new fitting excludes seasons
4 and 5. A revised method needs fresh independent evaluation.
