# Fixed-subset/order revision 3: completed

Completed 2026-11-26T09:14:04+05:30. All computational stages and final verification passed.
No further fitting, threshold tuning or configuration selection is pending.

- Six locked design cases, 48 design cross-validation checkpoints and six evaluation cases completed.
- All 348 evaluation policies, 1,188,188 prediction rows, 2,016 threshold-curve rows and complete candidate searches retained.
- 19 software tests and 107,679 independent numerical/artifact checks passed; zero failures.
- Both figures visually inspected. Full resume exited 0 and preserved all 147 checked scientific/source/report/figure files byte for byte.
- All 1,024 protected version-1/version-2 files remain unchanged. External seasons 4 and 5 were not rescored.

Decision: design-selected fixed acquisition improves the primary PLS four-reading comparison. The prespecified fixed-six procedure passes the relative engineering screen in all three held development seasons. The proposed bank-reference stopping objective has no demonstrated advantage. Results remain exploratory; no universal LED configuration or deployment policy is promoted. Fresh seasonal and physical validation remains unperformed.

Read decision_report.md and verification_report.md. Resume from the project root:

    .venv/bin/python revisions/fixed_design_v3/run.py all --resume

To repeat the byte-preservation proof:

    .venv/bin/python revisions/fixed_design_v3/verify_resume.py

Machine-readable evidence is under results/: verification.json, software_tests.json, visual_verification.json, resume_verification.json and integrity_manifest.json. Initial execution read audits are retained separately from resume read audits.

## Execution log

- 2026-11-26 09:00:55 +0530: Started design_s1_swap_mid

- 2026-11-26 09:00:55 +0530: Started designfold_s1_swap_mid_0

- 2026-11-26 09:00:55 +0530: Completed designfold_s1_swap_mid_0 in 0.1s

- 2026-11-26 09:00:55 +0530: Started designfold_s1_swap_mid_1

- 2026-11-26 09:00:55 +0530: Completed designfold_s1_swap_mid_1 in 0.1s

- 2026-11-26 09:00:55 +0530: Started designfold_s1_swap_mid_2

- 2026-11-26 09:00:55 +0530: Completed designfold_s1_swap_mid_2 in 0.1s

- 2026-11-26 09:00:55 +0530: Started designfold_s1_swap_mid_3

- 2026-11-26 09:00:55 +0530: Completed designfold_s1_swap_mid_3 in 0.1s

- 2026-11-26 09:00:55 +0530: Started designfold_s1_swap_mid_4

- 2026-11-26 09:00:55 +0530: Completed designfold_s1_swap_mid_4 in 0.1s

- 2026-11-26 09:00:55 +0530: Started designfold_s1_swap_mid_5

- 2026-11-26 09:00:55 +0530: Completed designfold_s1_swap_mid_5 in 0.1s

- 2026-11-26 09:00:55 +0530: Started designfold_s1_swap_mid_6

- 2026-11-26 09:00:56 +0530: Completed designfold_s1_swap_mid_6 in 0.1s

- 2026-11-26 09:00:56 +0530: Started designfold_s1_swap_mid_7

- 2026-11-26 09:00:56 +0530: Completed designfold_s1_swap_mid_7 in 0.1s

- 2026-11-26 09:00:56 +0530: Started designfold_s1_swap_mid_8

- 2026-11-26 09:00:56 +0530: Completed designfold_s1_swap_mid_8 in 0.1s

- 2026-11-26 09:00:56 +0530: Completed design_s1_swap_mid in 1.5s

- 2026-11-26 09:01:45 +0530: Dependencies amended; old registration retained; stale checkpoints will rerun.

- 2026-11-26 09:01:45 +0530: Started design_s1_swap_mid

- 2026-11-26 09:01:45 +0530: Started designfold_s1_swap_mid_0

- 2026-11-26 09:01:45 +0530: Completed designfold_s1_swap_mid_0 in 0.2s

- 2026-11-26 09:01:45 +0530: Started designfold_s1_swap_mid_1

- 2026-11-26 09:01:45 +0530: Completed designfold_s1_swap_mid_1 in 0.1s

- 2026-11-26 09:01:45 +0530: Started designfold_s1_swap_mid_2

- 2026-11-26 09:01:45 +0530: Completed designfold_s1_swap_mid_2 in 0.1s

- 2026-11-26 09:01:45 +0530: Started designfold_s1_swap_mid_3

- 2026-11-26 09:01:45 +0530: Completed designfold_s1_swap_mid_3 in 0.1s

- 2026-11-26 09:01:45 +0530: Started designfold_s1_swap_mid_4

- 2026-11-26 09:01:46 +0530: Completed designfold_s1_swap_mid_4 in 0.1s

- 2026-11-26 09:01:46 +0530: Started designfold_s1_swap_mid_5

- 2026-11-26 09:01:46 +0530: Completed designfold_s1_swap_mid_5 in 0.1s

- 2026-11-26 09:01:46 +0530: Started designfold_s1_swap_mid_6

- 2026-11-26 09:01:46 +0530: Completed designfold_s1_swap_mid_6 in 0.1s

- 2026-11-26 09:01:46 +0530: Started designfold_s1_swap_mid_7

- 2026-11-26 09:01:46 +0530: Completed designfold_s1_swap_mid_7 in 0.1s

- 2026-11-26 09:01:46 +0530: Started designfold_s1_swap_mid_8

- 2026-11-26 09:01:46 +0530: Completed designfold_s1_swap_mid_8 in 0.1s

- 2026-11-26 09:01:46 +0530: Completed design_s1_swap_mid in 1.4s

- 2026-11-26 09:01:46 +0530: Started design_s1_uniform

- 2026-11-26 09:01:46 +0530: Started designfold_s1_uniform_0

- 2026-11-26 09:01:46 +0530: Completed designfold_s1_uniform_0 in 0.1s

- 2026-11-26 09:01:46 +0530: Started designfold_s1_uniform_1

- 2026-11-26 09:01:47 +0530: Completed designfold_s1_uniform_1 in 0.1s

- 2026-11-26 09:01:47 +0530: Started designfold_s1_uniform_2

- 2026-11-26 09:01:47 +0530: Completed designfold_s1_uniform_2 in 0.1s

- 2026-11-26 09:01:47 +0530: Started designfold_s1_uniform_3

- 2026-11-26 09:01:47 +0530: Completed designfold_s1_uniform_3 in 0.1s

- 2026-11-26 09:01:47 +0530: Started designfold_s1_uniform_4

- 2026-11-26 09:01:47 +0530: Completed designfold_s1_uniform_4 in 0.1s

- 2026-11-26 09:01:47 +0530: Started designfold_s1_uniform_5

- 2026-11-26 09:01:47 +0530: Completed designfold_s1_uniform_5 in 0.1s

- 2026-11-26 09:01:47 +0530: Started designfold_s1_uniform_6

- 2026-11-26 09:01:47 +0530: Completed designfold_s1_uniform_6 in 0.1s

- 2026-11-26 09:01:47 +0530: Started designfold_s1_uniform_7

- 2026-11-26 09:01:47 +0530: Completed designfold_s1_uniform_7 in 0.1s

- 2026-11-26 09:01:47 +0530: Started designfold_s1_uniform_8

- 2026-11-26 09:01:47 +0530: Completed designfold_s1_uniform_8 in 0.1s

- 2026-11-26 09:01:48 +0530: Completed design_s1_uniform in 1.4s

- 2026-11-26 09:01:48 +0530: Started design_s2_swap_mid

- 2026-11-26 09:01:48 +0530: Started designfold_s2_swap_mid_0

- 2026-11-26 09:01:48 +0530: Completed designfold_s2_swap_mid_0 in 0.1s

- 2026-11-26 09:01:48 +0530: Started designfold_s2_swap_mid_1

- 2026-11-26 09:01:48 +0530: Completed designfold_s2_swap_mid_1 in 0.1s

- 2026-11-26 09:01:48 +0530: Started designfold_s2_swap_mid_2

- 2026-11-26 09:01:48 +0530: Completed designfold_s2_swap_mid_2 in 0.1s

- 2026-11-26 09:01:48 +0530: Started designfold_s2_swap_mid_3

- 2026-11-26 09:01:48 +0530: Completed designfold_s2_swap_mid_3 in 0.1s

- 2026-11-26 09:01:48 +0530: Started designfold_s2_swap_mid_4

- 2026-11-26 09:01:48 +0530: Completed designfold_s2_swap_mid_4 in 0.1s

- 2026-11-26 09:01:48 +0530: Started designfold_s2_swap_mid_5

- 2026-11-26 09:01:49 +0530: Completed designfold_s2_swap_mid_5 in 0.1s

- 2026-11-26 09:01:49 +0530: Started designfold_s2_swap_mid_6

- 2026-11-26 09:01:49 +0530: Completed designfold_s2_swap_mid_6 in 0.1s

- 2026-11-26 09:01:49 +0530: Started designfold_s2_swap_mid_7

- 2026-11-26 09:01:49 +0530: Completed designfold_s2_swap_mid_7 in 0.1s

- 2026-11-26 09:01:49 +0530: Started designfold_s2_swap_mid_8

- 2026-11-26 09:01:49 +0530: Completed designfold_s2_swap_mid_8 in 0.1s

- 2026-11-26 09:01:49 +0530: Completed design_s2_swap_mid in 1.4s

- 2026-11-26 09:01:49 +0530: Started design_s2_uniform

- 2026-11-26 09:01:49 +0530: Started designfold_s2_uniform_0

- 2026-11-26 09:01:49 +0530: Completed designfold_s2_uniform_0 in 0.1s

- 2026-11-26 09:01:49 +0530: Started designfold_s2_uniform_1

- 2026-11-26 09:01:49 +0530: Completed designfold_s2_uniform_1 in 0.1s

- 2026-11-26 09:01:49 +0530: Started designfold_s2_uniform_2

- 2026-11-26 09:01:49 +0530: Completed designfold_s2_uniform_2 in 0.1s

- 2026-11-26 09:01:49 +0530: Started designfold_s2_uniform_3

- 2026-11-26 09:01:50 +0530: Completed designfold_s2_uniform_3 in 0.1s

- 2026-11-26 09:01:50 +0530: Started designfold_s2_uniform_4

- 2026-11-26 09:01:50 +0530: Completed designfold_s2_uniform_4 in 0.1s

- 2026-11-26 09:01:50 +0530: Started designfold_s2_uniform_5

- 2026-11-26 09:01:50 +0530: Completed designfold_s2_uniform_5 in 0.1s

- 2026-11-26 09:01:50 +0530: Started designfold_s2_uniform_6

- 2026-11-26 09:01:50 +0530: Completed designfold_s2_uniform_6 in 0.1s

- 2026-11-26 09:01:50 +0530: Started designfold_s2_uniform_7

- 2026-11-26 09:01:50 +0530: Completed designfold_s2_uniform_7 in 0.1s

- 2026-11-26 09:01:50 +0530: Started designfold_s2_uniform_8

- 2026-11-26 09:01:50 +0530: Completed designfold_s2_uniform_8 in 0.1s

- 2026-11-26 09:01:50 +0530: Completed design_s2_uniform in 1.2s

- 2026-11-26 09:01:50 +0530: Started design_s3_swap_mid

- 2026-11-26 09:01:50 +0530: Started designfold_s3_swap_mid_0

- 2026-11-26 09:01:50 +0530: Completed designfold_s3_swap_mid_0 in 0.1s

- 2026-11-26 09:01:50 +0530: Started designfold_s3_swap_mid_1

- 2026-11-26 09:01:51 +0530: Completed designfold_s3_swap_mid_1 in 0.1s

- 2026-11-26 09:01:51 +0530: Started designfold_s3_swap_mid_2

- 2026-11-26 09:01:51 +0530: Completed designfold_s3_swap_mid_2 in 0.1s

- 2026-11-26 09:01:51 +0530: Started designfold_s3_swap_mid_3

- 2026-11-26 09:01:51 +0530: Completed designfold_s3_swap_mid_3 in 0.1s

- 2026-11-26 09:01:51 +0530: Started designfold_s3_swap_mid_4

- 2026-11-26 09:01:51 +0530: Completed designfold_s3_swap_mid_4 in 0.1s

- 2026-11-26 09:01:51 +0530: Started designfold_s3_swap_mid_5

- 2026-11-26 09:01:51 +0530: Completed designfold_s3_swap_mid_5 in 0.1s

- 2026-11-26 09:01:51 +0530: Completed design_s3_swap_mid in 0.9s

- 2026-11-26 09:01:51 +0530: Started design_s3_uniform

- 2026-11-26 09:01:51 +0530: Started designfold_s3_uniform_0

- 2026-11-26 09:01:51 +0530: Completed designfold_s3_uniform_0 in 0.1s

- 2026-11-26 09:01:51 +0530: Started designfold_s3_uniform_1

- 2026-11-26 09:01:51 +0530: Completed designfold_s3_uniform_1 in 0.1s

- 2026-11-26 09:01:51 +0530: Started designfold_s3_uniform_2

- 2026-11-26 09:01:52 +0530: Completed designfold_s3_uniform_2 in 0.1s

- 2026-11-26 09:01:52 +0530: Started designfold_s3_uniform_3

- 2026-11-26 09:01:52 +0530: Completed designfold_s3_uniform_3 in 0.1s

- 2026-11-26 09:01:52 +0530: Started designfold_s3_uniform_4

- 2026-11-26 09:01:52 +0530: Completed designfold_s3_uniform_4 in 0.1s

- 2026-11-26 09:01:52 +0530: Started designfold_s3_uniform_5

- 2026-11-26 09:01:52 +0530: Completed designfold_s3_uniform_5 in 0.1s

- 2026-11-26 09:01:52 +0530: Completed design_s3_uniform in 0.9s

- 2026-11-26 09:01:52 +0530: All six designs locked before source prediction access.

- 2026-11-26 09:02:24 +0530: Started evaluation_s1_swap_mid

- 2026-11-26 09:02:25 +0530: Completed evaluation_s1_swap_mid in 0.4s

- 2026-11-26 09:02:25 +0530: Started evaluation_s1_uniform

- 2026-11-26 09:02:25 +0530: Completed evaluation_s1_uniform in 0.4s

- 2026-11-26 09:02:25 +0530: Started evaluation_s2_swap_mid

- 2026-11-26 09:02:26 +0530: Completed evaluation_s2_swap_mid in 0.4s

- 2026-11-26 09:02:26 +0530: Started evaluation_s2_uniform

- 2026-11-26 09:02:26 +0530: Completed evaluation_s2_uniform in 0.4s

- 2026-11-26 09:02:26 +0530: Started evaluation_s3_swap_mid

- 2026-11-26 09:02:27 +0530: Completed evaluation_s3_swap_mid in 0.6s

- 2026-11-26 09:02:27 +0530: Started evaluation_s3_uniform

- 2026-11-26 09:02:27 +0530: Completed evaluation_s3_uniform in 0.4s

- 2026-11-26 09:02:27 +0530: All six evaluation cases completed from locked designs.

- 2026-11-26 09:05:21 +0530: Reporting complete: every locked subset/order and all 348 evaluation policies retained.

- 2026-11-26 09:12:27 +0530: Reused design_s1_swap_mid

- 2026-11-26 09:12:27 +0530: Reused design_s1_uniform

- 2026-11-26 09:12:27 +0530: Reused design_s2_swap_mid

- 2026-11-26 09:12:27 +0530: Reused design_s2_uniform

- 2026-11-26 09:12:27 +0530: Reused design_s3_swap_mid

- 2026-11-26 09:12:27 +0530: Reused design_s3_uniform

- 2026-11-26 09:12:27 +0530: All six designs locked before source prediction access.

- 2026-11-26 09:12:29 +0530: Reused evaluation_s1_swap_mid

- 2026-11-26 09:12:29 +0530: Reused evaluation_s1_uniform

- 2026-11-26 09:12:29 +0530: Reused evaluation_s2_swap_mid

- 2026-11-26 09:12:29 +0530: Reused evaluation_s2_uniform

- 2026-11-26 09:12:29 +0530: Reused evaluation_s3_swap_mid

- 2026-11-26 09:12:29 +0530: Reused evaluation_s3_uniform

- 2026-11-26 09:12:29 +0530: All six evaluation cases completed from locked designs.

- 2026-11-26 09:12:48 +0530: Reporting complete: every locked subset/order and all 348 evaluation policies retained.

- 2026-11-26T09:14:04+05:30: Final handoff complete; status and integrity manifest recorded.
