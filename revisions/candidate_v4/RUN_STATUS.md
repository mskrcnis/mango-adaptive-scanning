# Candidate v4: preparation completed; independent validation outstanding

Completed the authorized research-candidate freeze and prospective validation preparation. The intended aims are a paper documenting capabilities and limitations, and eventual support for mango harvest timing.

- Fixed candidate centers: **720, 760, 820, 890, 910, 940 nm**.
- Completed 94 leave-population-out selection folds across 15 allowed subsets using development seasons 1–3 only; fitted the candidate and eight-channel/full-spectrum comparison models on the same 10,243 development scans.
- All 96 checkpoints and the immutable inference bundle are saved. Selection scores are tuning evidence, not new independent accuracy estimates.
- **22 software tests and 1,115 verification checks passed; zero failures.** Normal six-channel CLI, three-model replay and copied-bundle execution succeeded.
- Full workflow resume exited successfully and preserved all 246 protected candidate files byte for byte. All 1,185 earlier scientific files remain unchanged. External seasons were not rescored.
- Prepared a prospective validation protocol, paper-claim guidance and 13 empty collection/custody/analysis templates. New field data, collection/precision/SOP commitments, physical instrument validation and a justified cultivar/market harvest rule remain outstanding. No validated pick/wait recommendation exists.

Final verification: `verification_report.md` and `results/verification.json`.
Resume evidence: `results/resume_verification.json`.
Delivery integrity snapshot: `results/integrity_manifest.json` (report/proof hashes describe this handoff and can change on a later verification run).
Candidate lock: `frozen/manifest.json`; no silent refitting or repairs are allowed.
Prospective study readiness: `validation/readiness.json`; collection-study registration remains pending.

Resume from the project root:

    .venv/bin/python revisions/candidate_v4/run.py all --resume

To repeat the full before/after resume proof:

    .venv/bin/python revisions/candidate_v4/verify_resume.py

Changing the frozen candidate or fitting dependencies requires a new revision. New validation must use independently documented observations; original seasons 1–5 are ineligible for that new cohort.

## Execution history

- 2026-11-26 09:38:16 +0530: Started cv_000

- 2026-11-26 09:38:16 +0530: Completed cv_000 in 0.07s

- 2026-11-26 09:38:16 +0530: Real-data pilot complete: one of 94 registered folds; no selection yet.

- 2026-11-26 09:38:31 +0530: Reused cv_000

- 2026-11-26 09:38:31 +0530: Started cv_001

- 2026-11-26 09:38:31 +0530: Completed cv_001 in 0.06s

- 2026-11-26 09:38:31 +0530: Started cv_002

- 2026-11-26 09:38:31 +0530: Completed cv_002 in 0.06s

- 2026-11-26 09:38:31 +0530: Started cv_003

- 2026-11-26 09:38:31 +0530: Completed cv_003 in 0.06s

- 2026-11-26 09:38:31 +0530: Started cv_004

- 2026-11-26 09:38:31 +0530: Completed cv_004 in 0.07s

- 2026-11-26 09:38:31 +0530: Started cv_005

- 2026-11-26 09:38:31 +0530: Completed cv_005 in 0.07s

- 2026-11-26 09:38:31 +0530: Started cv_006

- 2026-11-26 09:38:31 +0530: Completed cv_006 in 0.07s

- 2026-11-26 09:38:31 +0530: Started cv_007

- 2026-11-26 09:38:32 +0530: Completed cv_007 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_008

- 2026-11-26 09:38:32 +0530: Completed cv_008 in 0.06s

- 2026-11-26 09:38:32 +0530: Started cv_009

- 2026-11-26 09:38:32 +0530: Completed cv_009 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_010

- 2026-11-26 09:38:32 +0530: Completed cv_010 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_011

- 2026-11-26 09:38:32 +0530: Completed cv_011 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_012

- 2026-11-26 09:38:32 +0530: Completed cv_012 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_013

- 2026-11-26 09:38:32 +0530: Completed cv_013 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_014

- 2026-11-26 09:38:32 +0530: Completed cv_014 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_015

- 2026-11-26 09:38:32 +0530: Completed cv_015 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_016

- 2026-11-26 09:38:32 +0530: Completed cv_016 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_017

- 2026-11-26 09:38:32 +0530: Completed cv_017 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_018

- 2026-11-26 09:38:32 +0530: Completed cv_018 in 0.06s

- 2026-11-26 09:38:32 +0530: Started cv_019

- 2026-11-26 09:38:32 +0530: Completed cv_019 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_020

- 2026-11-26 09:38:32 +0530: Completed cv_020 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_021

- 2026-11-26 09:38:32 +0530: Completed cv_021 in 0.07s

- 2026-11-26 09:38:32 +0530: Started cv_022

- 2026-11-26 09:38:33 +0530: Completed cv_022 in 0.07s

- 2026-11-26 09:38:33 +0530: Started cv_023

- 2026-11-26 09:38:33 +0530: Completed cv_023 in 0.05s

- 2026-11-26 09:38:33 +0530: Started cv_024

- 2026-11-26 09:38:33 +0530: Completed cv_024 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_025

- 2026-11-26 09:38:33 +0530: Completed cv_025 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_026

- 2026-11-26 09:38:33 +0530: Completed cv_026 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_027

- 2026-11-26 09:38:33 +0530: Completed cv_027 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_028

- 2026-11-26 09:38:33 +0530: Completed cv_028 in 0.05s

- 2026-11-26 09:38:33 +0530: Started cv_029

- 2026-11-26 09:38:33 +0530: Completed cv_029 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_030

- 2026-11-26 09:38:33 +0530: Completed cv_030 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_031

- 2026-11-26 09:38:33 +0530: Completed cv_031 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_032

- 2026-11-26 09:38:33 +0530: Completed cv_032 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_033

- 2026-11-26 09:38:33 +0530: Completed cv_033 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_034

- 2026-11-26 09:38:33 +0530: Completed cv_034 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_035

- 2026-11-26 09:38:33 +0530: Completed cv_035 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_036

- 2026-11-26 09:38:33 +0530: Completed cv_036 in 0.05s

- 2026-11-26 09:38:33 +0530: Started cv_037

- 2026-11-26 09:38:33 +0530: Completed cv_037 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_038

- 2026-11-26 09:38:33 +0530: Completed cv_038 in 0.06s

- 2026-11-26 09:38:33 +0530: Started cv_039

- 2026-11-26 09:38:34 +0530: Completed cv_039 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_040

- 2026-11-26 09:38:34 +0530: Completed cv_040 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_041

- 2026-11-26 09:38:34 +0530: Completed cv_041 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_042

- 2026-11-26 09:38:34 +0530: Completed cv_042 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_043

- 2026-11-26 09:38:34 +0530: Completed cv_043 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_044

- 2026-11-26 09:38:34 +0530: Completed cv_044 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_045

- 2026-11-26 09:38:34 +0530: Completed cv_045 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_046

- 2026-11-26 09:38:34 +0530: Completed cv_046 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_047

- 2026-11-26 09:38:34 +0530: Completed cv_047 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_048

- 2026-11-26 09:38:34 +0530: Completed cv_048 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_049

- 2026-11-26 09:38:34 +0530: Completed cv_049 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_050

- 2026-11-26 09:38:34 +0530: Completed cv_050 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_051

- 2026-11-26 09:38:34 +0530: Completed cv_051 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_052

- 2026-11-26 09:38:34 +0530: Completed cv_052 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_053

- 2026-11-26 09:38:34 +0530: Completed cv_053 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_054

- 2026-11-26 09:38:34 +0530: Completed cv_054 in 0.05s

- 2026-11-26 09:38:34 +0530: Started cv_055

- 2026-11-26 09:38:34 +0530: Completed cv_055 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_056

- 2026-11-26 09:38:34 +0530: Completed cv_056 in 0.06s

- 2026-11-26 09:38:34 +0530: Started cv_057

- 2026-11-26 09:38:35 +0530: Completed cv_057 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_058

- 2026-11-26 09:38:35 +0530: Completed cv_058 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_059

- 2026-11-26 09:38:35 +0530: Completed cv_059 in 0.05s

- 2026-11-26 09:38:35 +0530: Started cv_060

- 2026-11-26 09:38:35 +0530: Completed cv_060 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_061

- 2026-11-26 09:38:35 +0530: Completed cv_061 in 0.07s

- 2026-11-26 09:38:35 +0530: Started cv_062

- 2026-11-26 09:38:35 +0530: Completed cv_062 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_063

- 2026-11-26 09:38:35 +0530: Completed cv_063 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_064

- 2026-11-26 09:38:35 +0530: Completed cv_064 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_065

- 2026-11-26 09:38:35 +0530: Completed cv_065 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_066

- 2026-11-26 09:38:35 +0530: Completed cv_066 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_067

- 2026-11-26 09:38:35 +0530: Completed cv_067 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_068

- 2026-11-26 09:38:35 +0530: Completed cv_068 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_069

- 2026-11-26 09:38:35 +0530: Completed cv_069 in 0.05s

- 2026-11-26 09:38:35 +0530: Started cv_070

- 2026-11-26 09:38:35 +0530: Completed cv_070 in 0.05s

- 2026-11-26 09:38:35 +0530: Started cv_071

- 2026-11-26 09:38:35 +0530: Completed cv_071 in 0.05s

- 2026-11-26 09:38:35 +0530: Started cv_072

- 2026-11-26 09:38:35 +0530: Completed cv_072 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_073

- 2026-11-26 09:38:35 +0530: Completed cv_073 in 0.06s

- 2026-11-26 09:38:35 +0530: Started cv_074

- 2026-11-26 09:38:36 +0530: Completed cv_074 in 0.06s

- 2026-11-26 09:38:36 +0530: Started cv_075

- 2026-11-26 09:38:36 +0530: Completed cv_075 in 0.06s

- 2026-11-26 09:38:36 +0530: Started cv_076

- 2026-11-26 09:38:36 +0530: Completed cv_076 in 0.06s

- 2026-11-26 09:38:36 +0530: Started cv_077

- 2026-11-26 09:38:36 +0530: Completed cv_077 in 0.06s

- 2026-11-26 09:38:36 +0530: Started cv_078

- 2026-11-26 09:38:36 +0530: Completed cv_078 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_079

- 2026-11-26 09:38:36 +0530: Completed cv_079 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_080

- 2026-11-26 09:38:36 +0530: Completed cv_080 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_081

- 2026-11-26 09:38:36 +0530: Completed cv_081 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_082

- 2026-11-26 09:38:36 +0530: Completed cv_082 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_083

- 2026-11-26 09:38:36 +0530: Completed cv_083 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_084

- 2026-11-26 09:38:36 +0530: Completed cv_084 in 0.06s

- 2026-11-26 09:38:36 +0530: Started cv_085

- 2026-11-26 09:38:36 +0530: Completed cv_085 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_086

- 2026-11-26 09:38:36 +0530: Completed cv_086 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_087

- 2026-11-26 09:38:36 +0530: Completed cv_087 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_088

- 2026-11-26 09:38:36 +0530: Completed cv_088 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_089

- 2026-11-26 09:38:36 +0530: Completed cv_089 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_090

- 2026-11-26 09:38:36 +0530: Completed cv_090 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_091

- 2026-11-26 09:38:36 +0530: Completed cv_091 in 0.05s

- 2026-11-26 09:38:36 +0530: Started cv_092

- 2026-11-26 09:38:37 +0530: Completed cv_092 in 0.06s

- 2026-11-26 09:38:37 +0530: Started cv_093

- 2026-11-26 09:38:37 +0530: Completed cv_093 in 0.05s

- 2026-11-26 09:38:37 +0530: Started selection

- 2026-11-26 09:38:37 +0530: Completed selection in 0.04s

- 2026-11-26 09:38:37 +0530: All 94 LOPO folds complete; one fixed-six candidate selected by the locked rule.

- 2026-11-26 09:38:42 +0530: Started models

- 2026-11-26 09:38:42 +0530: Completed models in 0.29s

- 2026-11-26 09:38:42 +0530: Candidate and both references frozen: 720, 760, 820, 890, 910, 940 nm.

- 2026-11-26 09:38:50 +0530: Candidate report and real development software examples generated; no accuracy claim added.

- 2026-11-26 09:43:47 +0530: Reused cv_000

- 2026-11-26 09:43:47 +0530: Reused cv_001

- 2026-11-26 09:43:47 +0530: Reused cv_002

- 2026-11-26 09:43:47 +0530: Reused cv_003

- 2026-11-26 09:43:47 +0530: Reused cv_004

- 2026-11-26 09:43:47 +0530: Reused cv_005

- 2026-11-26 09:43:47 +0530: Reused cv_006

- 2026-11-26 09:43:47 +0530: Reused cv_007

- 2026-11-26 09:43:47 +0530: Reused cv_008

- 2026-11-26 09:43:47 +0530: Reused cv_009

- 2026-11-26 09:43:47 +0530: Reused cv_010

- 2026-11-26 09:43:47 +0530: Reused cv_011

- 2026-11-26 09:43:47 +0530: Reused cv_012

- 2026-11-26 09:43:47 +0530: Reused cv_013

- 2026-11-26 09:43:47 +0530: Reused cv_014

- 2026-11-26 09:43:47 +0530: Reused cv_015

- 2026-11-26 09:43:47 +0530: Reused cv_016

- 2026-11-26 09:43:47 +0530: Reused cv_017

- 2026-11-26 09:43:47 +0530: Reused cv_018

- 2026-11-26 09:43:47 +0530: Reused cv_019

- 2026-11-26 09:43:47 +0530: Reused cv_020

- 2026-11-26 09:43:47 +0530: Reused cv_021

- 2026-11-26 09:43:47 +0530: Reused cv_022

- 2026-11-26 09:43:47 +0530: Reused cv_023

- 2026-11-26 09:43:47 +0530: Reused cv_024

- 2026-11-26 09:43:47 +0530: Reused cv_025

- 2026-11-26 09:43:47 +0530: Reused cv_026

- 2026-11-26 09:43:47 +0530: Reused cv_027

- 2026-11-26 09:43:47 +0530: Reused cv_028

- 2026-11-26 09:43:47 +0530: Reused cv_029

- 2026-11-26 09:43:47 +0530: Reused cv_030

- 2026-11-26 09:43:47 +0530: Reused cv_031

- 2026-11-26 09:43:47 +0530: Reused cv_032

- 2026-11-26 09:43:47 +0530: Reused cv_033

- 2026-11-26 09:43:47 +0530: Reused cv_034

- 2026-11-26 09:43:47 +0530: Reused cv_035

- 2026-11-26 09:43:47 +0530: Reused cv_036

- 2026-11-26 09:43:47 +0530: Reused cv_037

- 2026-11-26 09:43:47 +0530: Reused cv_038

- 2026-11-26 09:43:47 +0530: Reused cv_039

- 2026-11-26 09:43:47 +0530: Reused cv_040

- 2026-11-26 09:43:47 +0530: Reused cv_041

- 2026-11-26 09:43:47 +0530: Reused cv_042

- 2026-11-26 09:43:47 +0530: Reused cv_043

- 2026-11-26 09:43:47 +0530: Reused cv_044

- 2026-11-26 09:43:47 +0530: Reused cv_045

- 2026-11-26 09:43:47 +0530: Reused cv_046

- 2026-11-26 09:43:47 +0530: Reused cv_047

- 2026-11-26 09:43:47 +0530: Reused cv_048

- 2026-11-26 09:43:47 +0530: Reused cv_049

- 2026-11-26 09:43:47 +0530: Reused cv_050

- 2026-11-26 09:43:47 +0530: Reused cv_051

- 2026-11-26 09:43:47 +0530: Reused cv_052

- 2026-11-26 09:43:47 +0530: Reused cv_053

- 2026-11-26 09:43:47 +0530: Reused cv_054

- 2026-11-26 09:43:47 +0530: Reused cv_055

- 2026-11-26 09:43:47 +0530: Reused cv_056

- 2026-11-26 09:43:47 +0530: Reused cv_057

- 2026-11-26 09:43:47 +0530: Reused cv_058

- 2026-11-26 09:43:47 +0530: Reused cv_059

- 2026-11-26 09:43:47 +0530: Reused cv_060

- 2026-11-26 09:43:47 +0530: Reused cv_061

- 2026-11-26 09:43:47 +0530: Reused cv_062

- 2026-11-26 09:43:47 +0530: Reused cv_063

- 2026-11-26 09:43:47 +0530: Reused cv_064

- 2026-11-26 09:43:47 +0530: Reused cv_065

- 2026-11-26 09:43:47 +0530: Reused cv_066

- 2026-11-26 09:43:47 +0530: Reused cv_067

- 2026-11-26 09:43:47 +0530: Reused cv_068

- 2026-11-26 09:43:47 +0530: Reused cv_069

- 2026-11-26 09:43:47 +0530: Reused cv_070

- 2026-11-26 09:43:47 +0530: Reused cv_071

- 2026-11-26 09:43:47 +0530: Reused cv_072

- 2026-11-26 09:43:47 +0530: Reused cv_073

- 2026-11-26 09:43:47 +0530: Reused cv_074

- 2026-11-26 09:43:47 +0530: Reused cv_075

- 2026-11-26 09:43:47 +0530: Reused cv_076

- 2026-11-26 09:43:47 +0530: Reused cv_077

- 2026-11-26 09:43:47 +0530: Reused cv_078

- 2026-11-26 09:43:47 +0530: Reused cv_079

- 2026-11-26 09:43:47 +0530: Reused cv_080

- 2026-11-26 09:43:47 +0530: Reused cv_081

- 2026-11-26 09:43:47 +0530: Reused cv_082

- 2026-11-26 09:43:47 +0530: Reused cv_083

- 2026-11-26 09:43:47 +0530: Reused cv_084

- 2026-11-26 09:43:47 +0530: Reused cv_085

- 2026-11-26 09:43:47 +0530: Reused cv_086

- 2026-11-26 09:43:47 +0530: Reused cv_087

- 2026-11-26 09:43:47 +0530: Reused cv_088

- 2026-11-26 09:43:47 +0530: Reused cv_089

- 2026-11-26 09:43:47 +0530: Reused cv_090

- 2026-11-26 09:43:47 +0530: Reused cv_091

- 2026-11-26 09:43:47 +0530: Reused cv_092

- 2026-11-26 09:43:47 +0530: Reused cv_093

- 2026-11-26 09:43:47 +0530: Reused selection

- 2026-11-26 09:43:47 +0530: All 94 LOPO folds complete; one fixed-six candidate selected by the locked rule.

- 2026-11-26 09:43:47 +0530: Reused intact frozen candidate; no fitting occurred.

- 2026-11-26 09:43:48 +0530: Candidate report and real development software examples generated; no accuracy claim added.

- 2026-11-26T09:46:33+05:30: Candidate preparation complete; final verification and full resume passed. Independent field and harvest-decision validation remain unperformed.
