# JNIRS manuscript preparation: final verification report

Prepared 26 November 2026 for **Journal of Near Infrared Spectroscopy**, Original Research Article. The journal conversion is complete for author review. The supplied author names, affiliations and correspondence details are included. Author-dependent declarations remain explicit fields. The repository is public; nothing has been submitted to a journal.

## Deliverables

| Item | Verified contents |
|---|---|
| `output/pdf/Mango_JNIRS_Manuscript.pdf` | 16 pages; 4 figures; 6 tables; 30 cited references; 7 keywords; unstructured abstract |
| `output/pdf/Mango_JNIRS_Supplement.pdf` | 28 portrait pages; all 17 supplementary tables and preserved methods/results |
| `output/Mango_JNIRS_LaTeX_Source.zip` | Self-contained LaTeX and BibTeX sources, Sage class/styles, editable tables, four vector figures, plotted data, supporting evidence tables, build scripts, documentation and checksum manifest |
| `output/submission_files/` | Named copies of both PDFs, four vector figures, draft cover letter and supplementary-item description |
| `author_details.tex` and `AUTHOR_INPUTS.md` | Central author fields and the remaining decisions before submission |

The source ZIP reproduces the documents without the research workspace. It is not the complete model-training repository: the raw input dataset, trained models, replay application and candidate CLI are not bundled. The manuscript and data-availability text make that distinction explicit.

## Journal requirements and implementation

The [JNIRS author instructions](https://journals.sagepub.com/author-instructions/jns) were checked during journal preparation. This edition uses the Sage class with `Review,sagev,times`, an author-side A4 review presentation, an unstructured abstract, seven keywords, superscript citations and Sage Vancouver references. Author names remain on the title page because review is single-anonymized. Required declaration headings, a supplemental-material statement and a draft cover letter are supplied. Figure 2 uses distinct markers and line styles; all four supplied graphics are vector PDFs.

The current instructions state no numerical full-article abstract limit or compulsory LaTeX column layout. The 253-word abstract is used; the A4 review layout is a preparation choice, not a journal mandate.

The official template ZIP returned HTTP 403. The unchanged Sage class, version 1.20 dated 17 January 2017, was recovered from a pinned public Posit `rticles` mirror; its version matches the publisher-linked Overleaf demonstration. Byte-equivalence to the currently blocked official ZIP is **not established**. URLs, pinned revision, original-file hashes and this limitation are recorded in `template_provenance/mirror_source.json` and `guideline_audit.md`.

The distributed `sagej.cls` and `sagev.bst` remain unchanged. The documented local derivative `jnirs_sagev.bst` adds one missing conference-year output line. Verified metadata corrections retain all 30 source identities, including the official NeurIPS page range for Shim et al. See `bibliography_audit.md`.

## Executed verification

| Verification | Result and evidence |
|---|---|
| Document/source checks | **33/33 passed**, `results/verification.json` |
| Independent content-preservation review | **30/30 current editorial checks passed**, `results/independent_content_review.json`. Earlier reviews remain available through their recorded Git revisions and checksums. |
| Full visual review | **44 pages covered**: all 28 supplement pages and main pages 1–13 inspected in the current layout; main pages 14–16 pixel-identical to their prior individually inspected renders |
| LaTeX and BibTeX diagnostics | No warnings, unresolved references, overfull boxes or underfull boxes in either final document |
| Reference integrity | All 30 unique sources cited and rendered in first-citation order; no uncited padding or duplicate keys/DOIs |
| Earlier-version preservation | All **364** snapshotted v5 files unchanged |
| Isolated source-archive build | **17/17 checks passed**; both PDFs reproduced byte for byte, with matching extracted text and page counts |

These checks overlap in scope and should not be added together as independent scientific validations. No model fitting, raw-spectra evaluation or new seasonal scoring was performed during this conversion. Earlier numerical audits are inherited through preserved sources and tables; they were not rerun or counted as new experiments.

The paper now presents one final study with descriptive analysis names in place of internal revision labels. Editorial prose, section headings and captions were revised; scientific quantities, comparisons, cited source identities and interpretation limits are retained. Post-benchmark exploratory timing, prior exposure to development seasons and the final model's tuning-only evidence remain explicit. The former operational inventory is replaced by concise data/code availability, retaining missing-value interpretation.

Both inline main tables, all 17 supplementary table headers and data, nine table-input files, five plotted-data CSVs and 23 copied evidence files retain their values. The supplementary role label “Final O” is now “Benchmark fit”; the four indicator symbols use a readable bold numeral instead of the previous malformed blackboard-bold glyph. All mathematical content is otherwise unchanged. Figures 1 and 3 retain their original bytes. Figure 2 retains the previously verified presentation and data. Figure 4 changes only two benchmark-season labels; all eight contrasts, their point estimates and intervals, and other chart geometry are unchanged.

The supplied author information appears in both documents. The supplement remains 28 portrait pages, reduced from 52 in the preceding layout edit; font sizes and row spacing are retained, and the final short table is kept together. The main manuscript remains 16 pages. Current visual reports bind their observations to the final PDF hashes.

The package builder verifies every ZIP member against its internal `SHA256SUMS`, extracts outside the research workspace, clears project-specific TeX search paths and compiles from the extracted files. It verifies exact PDF bytes, extracted text, page counts and unchanged source inputs, then checks all eight named submission-file copies. `results/package_inventory.json` records the exact final archive hash and all member hashes. These packaging reports remain outside the ZIP to avoid circular hashes.

The final unchanged rerun is recorded in `results/resume_verification.json`, including its current archive hash and before/after file comparisons. It is valid only when `passed` is true and its archive hash matches `results/package_inventory.json`. Resume commands are in `RUN_STATUS.md`; rebuilding after an edit requires refreshing the affected visual/content review.

## Scientific conclusion retained

The dataset supports conditional improvements from fixed-channel selection, while the proposed adaptive stopping objective did not establish an advantage. Unequal benchmark budgets, exploratory reuse of development seasons, unknown fruit identities, model-relative references and simulated optical responses remain visible limitations. No harvest decision, measured scanner performance, independent new-cohort validation or universally optimal six-channel device is claimed. Additional field or hardware work is outside this dataset-only paper's scope.

## Author completion and limits

Names, affiliations and correspondence are supplied, and software availability now links to the public repository. Complete the remaining `author_details.tex` fields for contributions, funding, competing interests, additional acknowledgements and the human verification actually performed. Confirm originality, all-author approval and any other submission declarations before using the draft cover letter.

The acknowledgements and cover letter disclose substantive Codex assistance. [Sage's AI policy](https://www.sagepub.com/journals/publication-ethics-policies/artificial-intelligence-policy) also contains restrictions whose application to this extensively assisted workflow is not resolved by a disclosure alone. The authors must assess that application and seek editorial clarification if needed before submission; this package does not certify eligibility or completed human review. `AUTHOR_INPUTS.md` quotes the relevant policy wording and explains the unresolved point.

The public repository is https://github.com/mskrcnis/mango-adaptive-scanning. No upload to Overleaf or a journal system, external message, author approval or acceptance is implied.
