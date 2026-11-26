# Methodology revision 2 — completed

Completed the bounded development-only diagnostic round. Version 1 is preserved;
seasons 4 and 5 were not loaded or rescored. This revision is exploratory.

Resume/reproduce from the project root:

    .venv/bin/python revisions/methodology_v2/run.py all --resume
    .venv/bin/python revisions/methodology_v2/run.py verify

Evidence: decision_report.md, verification_report.md, results/verification.json,
results/resume_verification.json, and results/integrity_manifest.json.

Final checks: 12 cases, 24 distinct linear-model checkpoints, 22 software tests,
84,145 numerical/artifact checks, 917 preserved version-1 files and 86 unchanged
revision model/result/report/figure files across a full resume.

Decision: no revised adaptive policy is promoted. The primary-bank predictor
replacement did not improve identical four-reading predictions. Endpoint gains
have bank/order-dependent estimator and measurement contributions. The uniform
bank's relative engineering screen succeeds, but fixed-six also passes and has
lower error. Priority is a separately registered fixed-subset/order study, followed
by fresh independent seasonal and physical validation before deployment claims.

Implementation audit: the successful pilot was followed by added catalog,
metadata and saved-fold dependency hashes and explicit cross-seed identity
assertions. All affected pilot checkpoints were rerun before the full table;
no hyperparameter or threshold grid was changed in response to scores.

## Event log

- 2026-11-26 08:26:48 +0530: Started linear_s1_swap_mid_0

- 2026-11-26 08:26:49 +0530: Completed linear_s1_swap_mid_0 in 0.9s

- 2026-11-26 08:26:49 +0530: Started linear_s1_swap_mid_1

- 2026-11-26 08:26:50 +0530: Completed linear_s1_swap_mid_1 in 0.8s

- 2026-11-26 08:26:50 +0530: Started linear_s1_swap_mid_2

- 2026-11-26 08:26:50 +0530: Completed linear_s1_swap_mid_2 in 0.8s

- 2026-11-26 08:26:50 +0530: Started linear_s1_swap_mid_full

- 2026-11-26 08:26:52 +0530: Completed linear_s1_swap_mid_full in 1.2s

- 2026-11-26 08:26:52 +0530: Started case_s1_swap_mid_seed42

- 2026-11-26 08:26:52 +0530: Completed case_s1_swap_mid_seed42 in 0.7s

- 2026-11-26 08:26:52 +0530: All requested cases completed; reporting/verification are separate stages.

- 2026-11-26 08:27:47 +0530: Started linear_s1_swap_mid_0

- 2026-11-26 08:27:48 +0530: Completed linear_s1_swap_mid_0 in 0.9s

- 2026-11-26 08:27:48 +0530: Started linear_s1_swap_mid_1

- 2026-11-26 08:27:49 +0530: Completed linear_s1_swap_mid_1 in 0.9s

- 2026-11-26 08:27:49 +0530: Started linear_s1_swap_mid_2

- 2026-11-26 08:27:50 +0530: Completed linear_s1_swap_mid_2 in 0.9s

- 2026-11-26 08:27:50 +0530: Started linear_s1_swap_mid_full

- 2026-11-26 08:27:51 +0530: Completed linear_s1_swap_mid_full in 1.3s

- 2026-11-26 08:27:51 +0530: Started case_s1_swap_mid_seed42

- 2026-11-26 08:27:52 +0530: Completed case_s1_swap_mid_seed42 in 0.8s

- 2026-11-26 08:27:52 +0530: Started case_s1_swap_mid_seed7

- 2026-11-26 08:27:53 +0530: Completed case_s1_swap_mid_seed7 in 0.8s

- 2026-11-26 08:27:53 +0530: Started case_s1_swap_mid_seed99

- 2026-11-26 08:27:53 +0530: Completed case_s1_swap_mid_seed99 in 0.8s

- 2026-11-26 08:27:53 +0530: Started linear_s1_uniform_0

- 2026-11-26 08:27:54 +0530: Completed linear_s1_uniform_0 in 0.8s

- 2026-11-26 08:27:54 +0530: Started linear_s1_uniform_1

- 2026-11-26 08:27:55 +0530: Completed linear_s1_uniform_1 in 0.8s

- 2026-11-26 08:27:55 +0530: Started linear_s1_uniform_2

- 2026-11-26 08:27:56 +0530: Completed linear_s1_uniform_2 in 0.9s

- 2026-11-26 08:27:56 +0530: Started linear_s1_uniform_full

- 2026-11-26 08:27:57 +0530: Completed linear_s1_uniform_full in 1.4s

- 2026-11-26 08:27:57 +0530: Started case_s1_uniform_seed42

- 2026-11-26 08:27:58 +0530: Completed case_s1_uniform_seed42 in 0.7s

- 2026-11-26 08:27:58 +0530: Started linear_s2_swap_mid_0

- 2026-11-26 08:27:59 +0530: Completed linear_s2_swap_mid_0 in 1.1s

- 2026-11-26 08:27:59 +0530: Started linear_s2_swap_mid_1

- 2026-11-26 08:28:00 +0530: Completed linear_s2_swap_mid_1 in 1.1s

- 2026-11-26 08:28:00 +0530: Started linear_s2_swap_mid_2

- 2026-11-26 08:28:02 +0530: Completed linear_s2_swap_mid_2 in 1.1s

- 2026-11-26 08:28:02 +0530: Started linear_s2_swap_mid_full

- 2026-11-26 08:28:03 +0530: Completed linear_s2_swap_mid_full in 1.7s

- 2026-11-26 08:28:03 +0530: Started case_s2_swap_mid_seed42

- 2026-11-26 08:28:04 +0530: Completed case_s2_swap_mid_seed42 in 0.9s

- 2026-11-26 08:28:04 +0530: Started case_s2_swap_mid_seed7

- 2026-11-26 08:28:05 +0530: Completed case_s2_swap_mid_seed7 in 0.8s

- 2026-11-26 08:28:05 +0530: Started case_s2_swap_mid_seed99

- 2026-11-26 08:28:06 +0530: Completed case_s2_swap_mid_seed99 in 0.7s

- 2026-11-26 08:28:06 +0530: Started linear_s2_uniform_0

- 2026-11-26 08:28:07 +0530: Completed linear_s2_uniform_0 in 1.1s

- 2026-11-26 08:28:07 +0530: Started linear_s2_uniform_1

- 2026-11-26 08:28:08 +0530: Completed linear_s2_uniform_1 in 1.1s

- 2026-11-26 08:28:08 +0530: Started linear_s2_uniform_2

- 2026-11-26 08:28:09 +0530: Completed linear_s2_uniform_2 in 1.1s

- 2026-11-26 08:28:09 +0530: Started linear_s2_uniform_full

- 2026-11-26 08:28:11 +0530: Completed linear_s2_uniform_full in 1.7s

- 2026-11-26 08:28:11 +0530: Started case_s2_uniform_seed42

- 2026-11-26 08:28:12 +0530: Completed case_s2_uniform_seed42 in 0.8s

- 2026-11-26 08:28:12 +0530: Started linear_s3_swap_mid_0

- 2026-11-26 08:28:12 +0530: Completed linear_s3_swap_mid_0 in 0.7s

- 2026-11-26 08:28:12 +0530: Started linear_s3_swap_mid_1

- 2026-11-26 08:28:13 +0530: Completed linear_s3_swap_mid_1 in 0.7s

- 2026-11-26 08:28:13 +0530: Started linear_s3_swap_mid_2

- 2026-11-26 08:28:14 +0530: Completed linear_s3_swap_mid_2 in 0.7s

- 2026-11-26 08:28:14 +0530: Started linear_s3_swap_mid_full

- 2026-11-26 08:28:15 +0530: Completed linear_s3_swap_mid_full in 1.1s

- 2026-11-26 08:28:15 +0530: Started case_s3_swap_mid_seed42

- 2026-11-26 08:28:15 +0530: Completed case_s3_swap_mid_seed42 in 0.8s

- 2026-11-26 08:28:16 +0530: Started case_s3_swap_mid_seed7

- 2026-11-26 08:28:16 +0530: Completed case_s3_swap_mid_seed7 in 0.8s

- 2026-11-26 08:28:16 +0530: Started case_s3_swap_mid_seed99

- 2026-11-26 08:28:17 +0530: Completed case_s3_swap_mid_seed99 in 0.7s

- 2026-11-26 08:28:17 +0530: Started linear_s3_uniform_0

- 2026-11-26 08:28:18 +0530: Completed linear_s3_uniform_0 in 0.7s

- 2026-11-26 08:28:18 +0530: Started linear_s3_uniform_1

- 2026-11-26 08:28:18 +0530: Completed linear_s3_uniform_1 in 0.7s

- 2026-11-26 08:28:18 +0530: Started linear_s3_uniform_2

- 2026-11-26 08:28:19 +0530: Completed linear_s3_uniform_2 in 0.7s

- 2026-11-26 08:28:19 +0530: Started linear_s3_uniform_full

- 2026-11-26 08:28:20 +0530: Completed linear_s3_uniform_full in 1.1s

- 2026-11-26 08:28:20 +0530: Started case_s3_uniform_seed42

- 2026-11-26 08:28:21 +0530: Completed case_s3_uniform_seed42 in 0.9s

- 2026-11-26 08:28:21 +0530: All requested cases completed; reporting/verification are separate stages.

- 2026-11-26 08:30:14 +0530: Reporting complete: all 12 cases, exact-subset comparisons and frozen stopping decisions.

- 2026-11-26 08:32:16 +0530: Reporting complete: all 12 cases, exact-subset comparisons and frozen stopping decisions.

- 2026-11-26 08:33:51 +0530: Reporting complete: all 12 cases, exact-subset comparisons and frozen stopping decisions.

- 2026-11-26 08:35:21 +0530: Reused linear_s1_swap_mid_0

- 2026-11-26 08:35:21 +0530: Reused linear_s1_swap_mid_1

- 2026-11-26 08:35:22 +0530: Reused linear_s1_swap_mid_2

- 2026-11-26 08:35:22 +0530: Reused linear_s1_swap_mid_full

- 2026-11-26 08:35:22 +0530: Reused case_s1_swap_mid_seed42

- 2026-11-26 08:35:22 +0530: Reused case_s1_swap_mid_seed7

- 2026-11-26 08:35:22 +0530: Reused case_s1_swap_mid_seed99

- 2026-11-26 08:35:22 +0530: Reused linear_s1_uniform_0

- 2026-11-26 08:35:23 +0530: Reused linear_s1_uniform_1

- 2026-11-26 08:35:23 +0530: Reused linear_s1_uniform_2

- 2026-11-26 08:35:23 +0530: Reused linear_s1_uniform_full

- 2026-11-26 08:35:23 +0530: Reused case_s1_uniform_seed42

- 2026-11-26 08:35:23 +0530: Reused linear_s2_swap_mid_0

- 2026-11-26 08:35:24 +0530: Reused linear_s2_swap_mid_1

- 2026-11-26 08:35:24 +0530: Reused linear_s2_swap_mid_2

- 2026-11-26 08:35:24 +0530: Reused linear_s2_swap_mid_full

- 2026-11-26 08:35:24 +0530: Reused case_s2_swap_mid_seed42

- 2026-11-26 08:35:25 +0530: Reused case_s2_swap_mid_seed7

- 2026-11-26 08:35:25 +0530: Reused case_s2_swap_mid_seed99

- 2026-11-26 08:35:25 +0530: Reused linear_s2_uniform_0

- 2026-11-26 08:35:25 +0530: Reused linear_s2_uniform_1

- 2026-11-26 08:35:25 +0530: Reused linear_s2_uniform_2

- 2026-11-26 08:35:26 +0530: Reused linear_s2_uniform_full

- 2026-11-26 08:35:26 +0530: Reused case_s2_uniform_seed42

- 2026-11-26 08:35:26 +0530: Reused linear_s3_swap_mid_0

- 2026-11-26 08:35:26 +0530: Reused linear_s3_swap_mid_1

- 2026-11-26 08:35:26 +0530: Reused linear_s3_swap_mid_2

- 2026-11-26 08:35:27 +0530: Reused linear_s3_swap_mid_full

- 2026-11-26 08:35:27 +0530: Reused case_s3_swap_mid_seed42

- 2026-11-26 08:35:27 +0530: Reused case_s3_swap_mid_seed7

- 2026-11-26 08:35:27 +0530: Reused case_s3_swap_mid_seed99

- 2026-11-26 08:35:27 +0530: Reused linear_s3_uniform_0

- 2026-11-26 08:35:28 +0530: Reused linear_s3_uniform_1

- 2026-11-26 08:35:28 +0530: Reused linear_s3_uniform_2

- 2026-11-26 08:35:28 +0530: Reused linear_s3_uniform_full

- 2026-11-26 08:35:28 +0530: Reused case_s3_uniform_seed42

- 2026-11-26 08:35:28 +0530: All requested cases completed; reporting/verification are separate stages.

- 2026-11-26 08:35:52 +0530: Reporting complete: all 12 cases, exact-subset comparisons and frozen stopping decisions.

- 2026-11-26 08:39:07 +0530: Completed final verification, plot inspection and full resume. No required runnable stage remains in this bounded revision.
