# JNIRS manuscript preparation: completed for author review

Completed 26 November 2026. Target: Journal of Near Infrared Spectroscopy, Original Research Article. Source: verified dataset-only analyses with all 30 cited references retained.

The 16-page manuscript, 28-page supplement, separate vector figures, draft cover letter and standalone LaTeX archive are under `output/`. Current journal requirements and template provenance are documented. The latest official template ZIP was access-blocked; the preserved Sage class was recovered from a pinned public mirror with the same version as the publisher-linked demonstration.

Verification: 33 document/source checks, 30 current independent editorial preservation checks, all 44 pages covered by current visual inspection or exact pixel matches, and 17 isolated-package checks passed. Earlier conversion and editorial audits remain available through their recorded Git revisions and checksums. Both PDFs compile without LaTeX or BibTeX warnings and reproduce byte for byte outside the research workspace. All 364 protected v5 files remain unchanged. No model fitting or seasonal rescoring occurred.

The latest editorial update presents one final study without internal manuscript revision labels. Descriptive method names replace those labels in headings, prose, captions and Figure 4; numerical results, cited sources and essential evaluation limits are retained. All 17 supplementary table headers and data are unchanged apart from the descriptive “Benchmark fit” row label. Four indicator glyphs were corrected for readability. The supplied authors, concise data/code availability and compact page layout are retained.

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

Supplied identities, affiliations and correspondence are included; software availability links to the public repository. Complete `author_details.tex` and `AUTHOR_INPUTS.md` for contributions, funding/conflicts and actual human review. Resolve the applicability of Sage's AI policy before deciding to submit. These are author decisions, not missing dataset analyses. The manuscript is prepared for author review, not certified ready for submission.

The repository is public at https://github.com/mskrcnis/mango-adaptive-scanning. No journal submission, email or all-author approval is claimed.
