# Dataset-only manuscript consolidation: completed

Latest revision completed 2026-11-26: expanded Section 1.1 at the user's request. The main paper now has 30 genuinely cited references, including 26 journal or proceedings articles, and approximately 1,100 words of related-work synthesis across six themes. Fifteen additional research papers were verified against primary sources; an existing ensemble-model reference is now cited. Bibliography and source/claim evidence are in `manuscript/references.bib` and `literature_expansion_sources.md`.

## Current deliverables

- Main paper: `output/pdf/Mango_Dataset_Study.pdf` (17 pages).
- Supplement: `output/pdf/Mango_Dataset_Supplement.pdf` (53 pages; 17 tables and 1,237 displayed rows).
- Standalone source archive: `output/Mango_Dataset_Paper_Source.zip` (86 files), successfully compiled after extraction outside the workspace.
- Final checks: `verification_report.md` and `results/verification.json` report all 31 delivery checks passed.
- Reference audit: all 30 cited records render; all keys/DOIs are unique; no uncited padding. Manuscript prose/data outside Section 1.1 remain unchanged. Only the first table's float placement was adjusted to keep it below Related Work.
- Visual review: all 17 revised main-paper pages inspected. All 53 freshly rendered supplement pages match the previously inspected renders byte for byte.
- Resume proof: all 93 checked delivery files unchanged after a complete reporting workflow resume.
- Earlier scientific artifacts: all 1,301 protected files unchanged. The pre-expansion paper delivery is archived in `review_history/before_related_work_expansion.zip`.
- Numerical audits remain valid: 1,507 primary checks across 85,198 numeric values and 188 policy cells; 19,183 supplementary checks across 5,733 numeric values. These are reporting checks, not new performance experiments.
- Final delivery integrity snapshot: `results/integrity_manifest.json`.

No new model fitting, raw-data analysis, seasonal scoring or data collection was performed for the literature revision. Dataset-only completion remains the authorized scope. New fruit collection, hardware experiments and harvest thresholds are outside the completion requirements. The adaptive advantage remains unsupported; favorable fixed-design findings retain their stated evaluation limits. Author identity and declarations remain author inputs before submission. No submission is claimed.

## Resume

```bash
.venv/bin/python revisions/dataset_paper_v5/run.py all --resume
```

To repeat the before/after byte-preservation proof:

```bash
.venv/bin/python revisions/dataset_paper_v5/verify_resume.py
```

The full workflow includes the new reference audit. Current evidence and PDFs are reused by hash. Visual review must be refreshed if PDF content changes. The integrity manifest is a final delivery snapshot; it excludes itself, mutable status/log files, rendering scratch files and compilation caches.
