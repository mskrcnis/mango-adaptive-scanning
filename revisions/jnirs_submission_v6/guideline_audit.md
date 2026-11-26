# JNIRS submission-guideline audit

Verified 26 November 2026. Journal-specific instructions take precedence over generic Sage and template guidance. This is a formatting/submission audit, not an assertion that the authors have approved submission or that the journal has accepted the work.

## Journal-specific requirements

| Item | Verified requirement or absence of a stated limit |
|---|---|
| Article type | Original Research Article appropriate; also letters, reviews, short communications, technical notes (≤1,500 words), perspectives, editorials. |
| Review | Single-anonymized: retain authors/affiliations. Author reviewer nominations are not accepted. |
| Abstract | Unstructured: purpose, findings, conclusions. No numerical word limit found. |
| Keywords | At least five; maximum unspecified. |
| Length/layout | Full-article length, columns, line numbers and figures-at-end are not prescribed. |
| References | Sage Vancouver; citation/reference correspondence required. |
| Files | Word preferred; LaTeX accepted. Cover letter, manuscript, figures, applicable supplements. |
| Submission metadata | Authors/affiliations, correspondence, submitting-author ORCID, figure/table/word counts, funding. |

Source: [JNIRS author instructions](https://journals.sagepub.com/author-instructions/jns). Technical-note limits do not apply to this full article.

## LaTeX implementation and template provenance

Chosen header: `\documentclass[Review,sagev,times]{sagej}`. This is a defensible submission layout, **not a journal-mandated option combination**. The publisher-linked template documents `Review` as single-column, 12 pt, 156 × 234 mm; `times` selects Times and `sagev` selects superscript-numbered Vancouver citations. `doublespace` is optional. The template's ordinary A4 layout is two-column, 10 pt. Its abstract excludes reference citations and keywords are comma-separated. Source: [Sage template on Overleaf](https://www.overleaf.com/latex/templates/a-demonstration-of-the-latex2e-class-file-for-sage-publications/jcdyknyjrkzb).

Use `\cite{key}` and the supplied Vancouver `.bst`; do not retain author-year citation output. On this case-sensitive filesystem the recovered filename is lowercase, so use `\bibliographystyle{sagev}`. Author surnames can remain in prose where useful. Upload the compiled PDF as well as sources, bibliography and bibliography style. The Sage FAQ explicitly supports PDF line art for pdfLaTeX. Sources: [Sage LaTeX FAQ](https://journals.sagepub.com/pb-assets/cmscontent/LaTex_Frequently_Asked_Questions-1729666020.pdf), [Sage Vancouver reference style](https://www.sagepub.com/docs/default-source/rp-pages/info-for-authors/sage_vancouver_reference_style_1.pdf).

The [current official template ZIP](https://www.sagepub.com/docs/default-source/rp-pages/info-for-authors/sage-latex-template.zip?sfvrsn=54789065_1), linked by [Sage's manuscript-preparation page](https://www.sagepub.com/journals/information-for-authors/preparing-your-manuscript), returned HTTP 403 to local download requests. The public Overleaf template is readable, but its project-creation link requires login. **No successful download or SHA-256 of that official ZIP is claimed.**

Recovered unchanged files from the public [Posit rticles source repository](https://github.com/rstudio/rticles):

| Local file under `template_provenance/` | Embedded version | SHA-256 |
|---|---|---|
| `sagej.cls` | 2017/01/17 v1.20 | `4e736e371937216f5d1ef4470c2357c844755e0ebbade8888f0b94b8a17c9793` |
| `sagev.bst` | 1.00, 27 July 2013 | `113da1cae672949bb2e496e095507e3897a7e20206ac7186e0870b9ee63abfaa` |

Exact download URLs, pinned repository revision and byte checks are in `template_provenance/mirror_source.json`. The class version agrees with the publisher-linked 2017 Overleaf demonstration; equivalence to the currently blocked ZIP has **not** been established. Preserve the class unchanged and its copyright/rules-of-use header. This mirror fallback permits compilation without misrepresenting provenance.

## Artwork and supplements

Use editable LaTeX tables and separately supplied graphics. Generic Sage guidance specifies at least 300 dpi for raster artwork and 800 dpi for line art; it prefers EPS graphs in general, while its pdfLaTeX FAQ specifically prefers PDF line art and JPEG photographs. Existing vector PDF plots therefore need no raster conversion. Number figures in citation order; ensure plots remain distinguishable without color. The generic Word placement instruction does not establish a LaTeX figures-at-end requirement. Source: [Sage manuscript and artwork guidance](https://www.sagepub.com/journals/information-for-authors/preparing-your-manuscript).

Supplementary material is reviewed with the paper but published as supplied, without copyediting/typesetting/proofreading. Give each item a title and description and ensure it works independently. PDF, CSV, source code and other listed formats are supported; keep files below 10 MB where possible and avoid ZIP supplements where possible. This recommendation concerns published supplements, not a local source-package ZIP. Source: [Sage supplemental-material guidelines](https://www.sagepub.com/journals/information-for-authors/preparing-your-manuscript/supplemental-material-guidelines-for-authors).

## Declarations and author-dependent fields

Place **Statements and Declarations** after Acknowledgements and any Author Contributions section. Retain headings for Ethical considerations, Consent to participate, Consent for publication, Declaration of conflicting interests, Funding, and Data availability; state inapplicability where justified. Source: [Sage manuscript guidance](https://www.sagepub.com/journals/information-for-authors/preparing-your-manuscript). For this package, do not invent approval, consent, funding or authorship; keep author-dependent fields pending until supplied.

AI assistance affecting substantive text/references, research code, analysis or visualization requires disclosure at submission and in Methods or Acknowledgements; authors remain responsible for source verification. Suggestions on language/grammar/structure applied to authors' own work are exempt. The policy supplies no mandatory disclosure wording or tool/version/prompt fields. It also contains the broad prohibition “Generation of data or submission using a series of prompts.” Therefore disclosure alone must not be portrayed as certifying compliance for extensive AI preparation; the authors must review the actual assistance against the policy. AI cannot be an author. Third-party writing/editing assistance also belongs in Acknowledgements and the cover letter. Sources: [Sage AI policy](https://www.sagepub.com/journals/publication-ethics-policies/artificial-intelligence-policy) and [JNIRS instructions](https://journals.sagepub.com/author-instructions/jns).

## Scope of completion

Current public requirements and template options checked; usable class/style files recovered with hashes. The current official ZIP remains access-blocked. No submission, author approval, ethics determination or acceptance is implied. Unspecified requirements remain unresolved, including any additional fields displayed only during actual submission.

## Implemented review edition

The author-side `jnirs_review.sty` selects A4 and a 170mm text width while retaining the class Review typography. It uses a full-width title page and suppresses the generic fictitious volume, issue, year and DOI block. These are presentation choices permitted by the unspecific journal layout requirements. `sagej.cls` itself is byte-identical to the recovered distribution.

The original `sagev.bst` is also retained. `jnirs_sagev.bst` is a documented minimal derivative adding the missing year output in the conference-entry function; its license permits modification. All other bibliography formatting is unchanged. Narrative author names are explicit because the numeric BST does not expose author metadata to natbib textual citations. References retain all 30 sources and use verified journal abbreviations; see bibliography_audit.md.
