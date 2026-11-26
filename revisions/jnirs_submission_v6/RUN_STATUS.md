# JNIRS manuscript preparation: completed for author review

Completed 26 November 2026. Target: Journal of Near Infrared Spectroscopy, Original Research Article. Source: verified dataset-only paper v5 with all 30 cited references retained.

The 16-page manuscript, 52-page supplement, separate vector figures, draft cover letter and standalone LaTeX archive are under `output/`. Current journal requirements and template provenance are documented. The latest official template ZIP was access-blocked; the preserved Sage class was recovered from a pinned public mirror with the same version as the publisher-linked demonstration.

Verification: 30 document/source checks, 33 independent content checks, all 68 pages visually reviewed, and 17 isolated-package checks passed. Both PDFs compile without LaTeX or BibTeX warnings and reproduce byte for byte outside the research workspace. All 364 protected v5 files remain unchanged. No model fitting or seasonal rescoring occurred.

Read `verification_report.md`, `results/verification.json`, `results/independent_content_review.json` and `results/isolated_compilation.json` for the executed evidence. The final unchanged rerun is recorded in `results/resume_verification.json`; its pass and archive hash must match the current `results/package_inventory.json`.

## Resume or rebuild

From the research root:

```bash
bash revisions/jnirs_submission_v6/build_pdfs.sh
.venv/bin/python revisions/jnirs_submission_v6/verify_package.py
.venv/bin/python revisions/jnirs_submission_v6/package_sources.py
```

After extracting the source archive into an empty directory, `bash build_pdfs.sh` compiles both documents without Python or the research workspace. Overleaf: upload the ZIP, use pdfLaTeX and select `main.tex`; select `supplement.tex` separately for the supplement. No Overleaf upload has been performed.

Visual and independent content reviews are bound to exact hashes. An unchanged rebuild can be verified directly. If author fields, prose, figures or tables change, refresh the affected reviews and rebuild the archive; do not treat an old review as current. Do not fit models, alter earlier revisions or rescore seasons as part of journal formatting.

## Remaining author inputs

Complete `author_details.tex` and `AUTHOR_INPUTS.md`: identity, affiliations, correspondence, contributions, funding/conflicts, actual human review and software-access arrangements. Resolve the applicability of Sage's AI policy before deciding to submit. These are author decisions, not missing dataset analyses. The manuscript is prepared for author review, not certified ready for submission.

No submission, email, public release or all-author approval is claimed.
