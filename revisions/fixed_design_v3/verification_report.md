# Fixed-design v3: independent verification

**PASS:** 107,679 numerical/artifact checks; 0 failures.

- All six design cases and six evaluation cases checked, including all 48 LOPO fold checkpoints and dependency hashes.
- Independently reconstructed every 64-mask search and 720-order search for both predictor families, including exact tie breaks.
- Checked all 768 exported mask rows, 8,640 order rows and 12 chosen designs against the saved search.
- Reconstructed all 348 policy metric rows, 1,188,188 per-scan predictions and 2,016 threshold-curve rows.
- All 96 paired comparison point estimates checked; 15 primary intervals reconstructed by expanding sampled populations into actual paired rows.
- All 1024 protected v1/v2 files remain unchanged. Guards reject external data, premature v2 result reads and writes to prior versions.
- Separate synthetic software suite: 19 tests passed with exit code 0; saved root execution evidence is in results/software_tests.json. This numerical verifier does not rerun that suite.

Completed full resume: all 147 snapshot scientific/model/report/figure files remained byte-identical (results/resume_verification.json).

These checks establish computational consistency and the declared data separation. The results remain exploratory because development seasons were reused; the intervals do not include repeated design selection or future-season uncertainty.

Machine-readable evidence: results/verification.json. Source: verify.py.
