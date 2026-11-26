# JNIRS manuscript preparation: final verification report

Prepared 26 November 2026 for **Journal of Near Infrared Spectroscopy**, Original Research Article. The journal conversion is complete for author review. Author identities and author-dependent declarations remain explicit fields; nothing has been submitted or published.

## Deliverables

| Item | Verified contents |
|---|---|
| `output/pdf/Mango_JNIRS_Manuscript.pdf` | 16 pages; 4 figures; 6 tables; 30 cited references; 7 keywords; unstructured abstract |
| `output/pdf/Mango_JNIRS_Supplement.pdf` | 52 pages; all 17 supplementary tables and preserved methods/results |
| `output/Mango_JNIRS_LaTeX_Source.zip` | Self-contained LaTeX and BibTeX sources, Sage class/styles, editable tables, four vector figures, plotted data, supporting evidence tables, build scripts, documentation and checksum manifest |
| `output/submission_files/` | Named copies of both PDFs, four vector figures, draft cover letter and supplementary-item description |
| `author_details.tex` and `AUTHOR_INPUTS.md` | Central author fields and the remaining decisions before submission |

The source ZIP reproduces the documents without the research workspace. It is not the complete model-training repository: the raw input dataset, trained models, replay application and candidate CLI are not bundled. The manuscript and data-availability text make that distinction explicit.

## Journal requirements and implementation

The current [JNIRS author instructions](https://journals.sagepub.com/author-instructions/jns) were checked. This edition uses the Sage class with `Review,sagev,times`, an author-side A4 review presentation, an unstructured abstract, seven keywords, superscript citations and Sage Vancouver references. Author names remain on the title page because review is single-anonymized. Required declaration headings, a supplemental-material statement and a draft cover letter are supplied. Figure 2 uses distinct markers and line styles; all four supplied graphics are vector PDFs.

The current instructions state no numerical full-article abstract limit or compulsory LaTeX column layout. The 256-word abstract is retained; the A4 review layout is a preparation choice, not a journal mandate.

The official template ZIP returned HTTP 403. The unchanged Sage class, version 1.20 dated 17 January 2017, was recovered from a pinned public Posit `rticles` mirror; its version matches the publisher-linked Overleaf demonstration. Byte-equivalence to the currently blocked official ZIP is **not established**. URLs, pinned revision, original-file hashes and this limitation are recorded in `template_provenance/mirror_source.json` and `guideline_audit.md`.

The distributed `sagej.cls` and `sagev.bst` remain unchanged. The documented local derivative `jnirs_sagev.bst` adds one missing conference-year output line. Verified metadata corrections retain all 30 source identities, including the official NeurIPS page range for Shim et al. See `bibliography_audit.md`.

## Executed verification

| Verification | Result and evidence |
|---|---|
| Document/source checks | **30/30 passed**, `results/verification.json` |
| Independent scientific-content review | **33/33 passed**, `results/independent_content_review.json` and `content_review.md` |
| Full visual review | **68/68 pages inspected**; both hash-bound visual reports passed |
| LaTeX and BibTeX diagnostics | No warnings, unresolved references, overfull boxes or underfull boxes in either final document |
| Reference integrity | All 30 unique sources cited and rendered in first-citation order; no uncited padding or duplicate keys/DOIs |
| Earlier-version preservation | All **364** snapshotted v5 files unchanged |
| Isolated source-archive build | **17/17 checks passed**; both PDFs reproduced byte for byte, with matching extracted text and page counts |

These checks overlap in scope and should not be added together as independent scientific validations. No model fitting, raw-spectra evaluation or new seasonal scoring was performed during this conversion. Earlier numerical audits are inherited through preserved sources and tables; they were not rerun or counted as new experiments.

All scientific text, numerical claims, equations and limitations are preserved after enumerated editorial changes. Both inline main tables, all 17 supplement table blocks, nine table-input files and 23 copied evidence files match v5. Figures 1, 3 and 4 are byte-identical to v5. Figure 2's 210 curve rows and four operating-point rows match saved results within decimal round-trip tolerance; only its presentation changed. The independent audit records the complete comparisons.

The main PDF was rerendered after the final bibliography completion. Pages 1-15 had identical pixels to the previously inspected renders; page 16 was inspected again. The supplement remained byte-identical throughout that final change.

The package builder verifies every ZIP member against its internal `SHA256SUMS`, extracts outside the research workspace, clears project-specific TeX search paths and compiles from the extracted files. It verifies exact PDF bytes, extracted text, page counts and unchanged source inputs, then checks all eight named submission-file copies. `results/package_inventory.json` records the exact final archive hash and all member hashes. These packaging reports remain outside the ZIP to avoid circular hashes.

The final unchanged rerun is recorded in `results/resume_verification.json`, including its current archive hash and before/after file comparisons. It is valid only when `passed` is true and its archive hash matches `results/package_inventory.json`. Resume commands are in `RUN_STATUS.md`; rebuilding after an edit requires refreshing the affected visual/content review.

## Scientific conclusion retained

The dataset supports conditional improvements from fixed-channel selection, while the proposed adaptive stopping objective did not establish an advantage. Original unequal budgets, exploratory reuse of development seasons, unknown fruit identities, model-relative references and simulated optical responses remain visible limitations. No harvest decision, measured scanner performance, independent new-cohort validation or universally optimal six-channel device is claimed. Additional field or hardware work is outside this dataset-only paper's scope.

## Author completion and limits

Complete `author_details.tex` using actual author names, affiliations, correspondence, contributions, funding, competing interests, additional acknowledgements and the human verification actually performed. Decide how readers will access the complete research software and models. Confirm originality, all-author approval and any other submission declarations before using the draft cover letter.

The acknowledgements and cover letter disclose substantive Codex assistance. [Sage's AI policy](https://www.sagepub.com/journals/publication-ethics-policies/artificial-intelligence-policy) also contains restrictions whose application to this extensively assisted workflow is not resolved by a disclosure alone. The authors must assess that application and seek editorial clarification if needed before submission; this package does not certify eligibility or completed human review. `AUTHOR_INPUTS.md` quotes the relevant policy wording and explains the unresolved point.

No upload to Overleaf or a journal system, external message, public repository release, author approval or acceptance is implied.
