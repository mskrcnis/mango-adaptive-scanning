# Methodology v2: independent verification

**PASS:** 84,145 numerical and artifact checks; 0 failures.

- All 12 development cases and 24 distinct linear-predictor checkpoints verified, including dependency and file hashes.
- All 1,352,076 exported policy predictions, all predictor/policy metrics, calibration choices and signed endpoint decompositions reconstructed.
- Primary paired population-bootstrap intervals reconstructed directly from resampled rows; all 378 primary validation-curve rows recomputed.
- All 917 protected version-1 files remain byte-identical; no new protected scientific files were created.
- External outcome/feature/scored-result opening was rejected before reading in three deliberate guard checks. No external season was loaded or rescored.
- Separate software-test execution: 22 tests passed, as recorded by the test agent. This numerical verifier does not rerun that suite.
- Root separately inspected the two generated scientific plots; this verifier checks their underlying numeric tables.

The completed original v1 analysis is preserved. This revision is exploratory development evidence. Its intervals do not turn reused development seasons into fresh external validation.

Completed full all --resume: all 86 snapshot scientific/model/report/figure files remained byte-identical. The root process recorded the before/after hashes in results/resume_verification.json.

Machine-readable checks: results/verification.json. Source: verify.py.
