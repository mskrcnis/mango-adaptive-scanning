# JNIRS LaTeX manuscript edition

Prepared for **Journal of Near Infrared Spectroscopy**, Original Research Article, using the verified dataset-only manuscript v5. Scientific results, interpretations, complete supplementary tables and all 30 cited sources are retained. No model fitting or new seasonal evaluation was performed.

## Main files

- `main.tex`: journal-targeted manuscript, with editable LaTeX tables and four vector figures.
- `supplement.tex`: full supplementary methods and results, including 17 tables.
- `references.bib`: 30 cited sources with Sage Vancouver journal abbreviations.
- `author_details.tex`: author identity and author-dependent declaration fields to complete.
- `declarations.tex`: required journal declaration headings and AI-use disclosure.
- `output/pdf/Mango_JNIRS_Manuscript.pdf` and `Mango_JNIRS_Supplement.pdf`: compiled author-review documents.
- `output/Mango_JNIRS_LaTeX_Source.zip`: self-contained LaTeX/Overleaf source archive.
- `output/submission_files/`: named manuscript, supplement, individual vector figures, draft cover letter and supplement description.
- `verification_report.md`: executed checks and remaining author inputs.

## Compile locally or in Overleaf

Extract the source ZIP into an empty directory, then run:

```bash
bash build_pdfs.sh
```

This requires pdfLaTeX and BibTeX with standard TeX Live packages. Python and the original research workspace are not needed to compile either document. The two output PDFs appear in `output/pdf/`. The build runs BibTeX and three final LaTeX passes; unresolved references or errors must be corrected before submission.

For Overleaf, upload the ZIP as a new project, select **pdfLaTeX**, and use **main.tex** as the main document. Select **supplement.tex** separately to build the supplement. The class, both bibliography styles, `.bib`, `.bbl`, figures and included table files are supplied. Set the manuscript file back to `main.tex` when finished. No upload to Overleaf has been performed by this task.

The optional `prepare_figures.py` script requires Python, pandas and matplotlib; it regenerates Figure 2 from the included frozen CSV values. Its line/marker styles were changed to retain readability in monochrome. Figures 1, 3 and 4 retain the verified v5 PDF bytes. `figure_data/` supplies plotted data, and `evidence_tables/` contains the previously reported result tables.

The optional document verifier requires Python and `pypdf`. The packaging verifier uses Python's standard library plus `bash`, `pdflatex`, `bibtex`, `pdfinfo` and `pdftotext`. These verification tools are separate from the basic LaTeX compilation requirements.

## Journal formatting decisions and provenance

The live [JNIRS author instructions](https://journals.sagepub.com/author-instructions/jns) accept LaTeX and specify an unstructured abstract, at least five keywords, Sage Vancouver references and single-anonymized review. Authors therefore remain on the title page. The current guide gives no numerical full-article abstract limit or mandatory LaTeX layout.

This edition uses `Review,sagev,times` with an author-side A4 review presentation in `jnirs_review.sty`. It retains Sage typography, presents a full-width title page, and removes fictitious publisher volume/issue/DOI metadata. These are layout choices, not additional journal mandates. The supplement uses a readable standalone A4 layout for its long and landscape tables; Sage publishes supplements as supplied.

The unchanged Sage class is version 1.20, 17 January 2017, recovered from a pinned Posit `rticles` mirror. The version matches the publisher-linked Overleaf demonstration. The current official ZIP could not be downloaded (HTTP 403), so byte-equivalence with that ZIP is not asserted. Exact URLs, commit and hashes are in `template_provenance/mirror_source.json`.

`sagev.bst` is retained unchanged. The documented local derivative `jnirs_sagev.bst` adds the missing conference-publication year output; it otherwise preserves the distributed Vancouver style. See `bibliography_audit.md`. Do not replace it with the original without checking conference dates in the compiled references.

## Scope and author completion

This source archive reproduces the documents. It does not contain the raw mango dataset, trained model checkpoints, replay application or complete model-training code. Those remain in the preserved research workspace. The public input dataset is DOI `10.17632/46htwnp833.3`; no new data collection or hardware experiment is required for this paper's stated computational scope.

Complete `AUTHOR_INPUTS.md` before submission. Author identities, funding, conflicts, contributions, access to complete research software, actual human review and the applicability of Sage's AI policy remain author decisions. The draft cover letter does not invent all-author approval or exclusivity declarations. No submission or public release has occurred.

## Resume and verify

Read `RUN_STATUS.md`. After source changes, run `bash build_pdfs.sh` and repeat the visual review because it is bound to exact PDF bytes. `verify_package.py` checks current files and, when the preserved v5 workspace is present, verifies its file hashes and retained numerical content. `package_sources.py` creates the source archive and named submission files. The final verification also builds the archive after extraction outside the project.
