# Bounded SAGE Vancouver bibliography audit

Checked 26 November 2026. This review compares the preserved v5 `references.bib` with the supplied SAGE `sagev.bst`, checks the requested special source types, and verifies a journal-abbreviation map. It is not a repeat metadata or claim audit of all 30 sources. No earlier revision was edited, and no source needs to be removed or replaced on the evidence found.

## Primary style guidance

The [official SAGE Vancouver guide](https://www.sagepub.com/docs/default-source/rp-pages/info-for-authors/sage_vancouver_reference_style_1.pdf?sfvrsn=ebbf7887_2), linked from [SAGE's manuscript preparation page](https://www.sagepub.com/journals/information-for-authors/preparing-your-manuscript), specifies reference order by citation, Index Medicus journal abbreviations, compact initials in the rendered reference, and up to three author names followed by upright *et al.* where needed. Its thesis example identifies the degree type, institution, country and year. The preparation page asks authors to replace a preprint citation with the published version when one becomes available; it otherwise discourages preprint citations.

Keep complete author lists in BibTeX; `sagev.bst` performs the three-author truncation. The absence of spaces between initials is an **output** requirement: distinct given-name initials still need separate tokens in the BibTeX input.

## Concrete rendering findings and minimal corrections

A temporary-directory BibTeX smoke test used the actual v6 `sagev.bst` and the preserved v5 bibliography. The test did not modify project sources.

1. **Lost initials in `anderson2020`.** The existing `Anderson, N.T. and Walsh, K.B. and Subedi, P.P. and Hayes, C.H.` renders as `Anderson N, Walsh K, Subedi P et al.`. Change the input to:

   ```bibtex
   author = {Anderson, N. T. and Walsh, K. B. and Subedi, P. P. and Hayes, C. H.},
   ```

   The already spaced `anderson2021local` entry correctly renders `Anderson NT, Walsh KB, Flynn JR et al.`. This establishes the parsing issue without changing author identity.

2. **Compound family name in `jazbec2024`.** The existing `Veljkovi\'{c}, Tin Had\v{z}i` renders as `Veljković TH`. The [author's own publication list](https://stases.github.io/) identifies his cited surname as Hadži Veljković, including for this paper; the [official NeurIPS record](https://proceedings.neurips.cc/paper_files/paper/2024/hash/ea5a63f7ddb82e58623693fd1f4933f7-Abstract-Conference.html) gives the full name Tin Hadži Veljković. Use `Had\v{z}i Veljkovi\'{c}, Tin`, which renders the compound surname and the initial T.

3. **Missing conference publication years.** The supplied `sagev.bst` `inproceedings` function never calls `format.date`. The smoke test omitted 2023 from `covert2023` and 2024 from `jazbec2024`, despite populated `year` fields. The same function affects `valancius2024` and `shim2018`. The selected fix is a documented local derivative, `jnirs_sagev.bst`, adding `format.date "year" output.check` before `format.pages "pages" output.check` in that function. Preserve the downloaded `sagev.bst` unchanged. This fixes all four without embedding dates into titles or duplicating years in notes. Final compilation must check all four rendered years. This audit records the issue and proposed change; the root agent implements and verifies the derivative.

4. **Dataset repository omitted.** For `andersondata2024`, the `@misc` function ignores `publisher` and the style does not declare `version`. The original entry prints the version only because it also appears in `note`, and does not identify Mendeley Data. Add:

   ```bibtex
   howpublished = {Mendeley Data, version 3 [dataset]},
   ```

   The [official dataset record](https://data.mendeley.com/datasets/46htwnp833/3) verifies repository, four contributors, version 3, 6 February 2024, and DOI `10.17632/46htwnp833.3`. Keeping its DOI and version-specific URL preserves the exact data release. Protect the proper name in the title as `{Anderson}` if correcting the style's lowercase rendering. An optional shorter note is `Published 6 February 2024`; avoid repeating version unnecessarily.

5. **Preprint type is already explicit, but archive metadata needs care.** `baarc2026` currently renders the DOI, arXiv URL and preprint/version/date note. The style supports `eprint` and `archive`, not `archivePrefix`; with its fallback macro the eprint appears as the bare number `2610.32505`. No source-identity information is lost because the URL and DOI identify arXiv. For a clearer optional rendering, add `howpublished = {arXiv preprint arXiv:2610.32505v1}` and omit the redundant naked eprint output. Do not assign a journal or acceptance status without verified evidence.

6. **Thesis and corporate author render appropriately.** `walshthesis2024` renders as a Master of Research thesis, Central Queensland University, 2024, with its DOI and URL. The [institutional record](https://acquire.cqu.edu.au/articles/thesis/Deep_Learning_in_Estimation_of_Fruit_Attributes_Using_Near_Infrared_Spectroscopy/27208401) confirms a Master's by Research thesis. Its project-specific note about Chapter 3 can optionally be removed from the printed bibliography because it is explanatory manuscript context. `{{Roithner Lasertechnik}}` correctly preserves the corporate author; its missing year should not be replaced by an invented publication year. Retain the actual access date for the undated [catalog](https://www.roithner-laser.com/led_standard.html).

7. **Optional compacting only.** Journal entries generally contain both a DOI and the identical DOI-resolver URL. `sagev.bst` prints both. Removing only redundant `url = {https://doi.org/...}` fields would shorten the bibliography without removing DOI links. Keep distinct proceedings, repository, thesis and catalog URLs. This is an editorial option, not a correctness requirement.

## Verified journal-field map

Use the following text as `journal` values; do not change the proceedings `booktitle` values into journal names. NLM entries are preferred. For the two titles without a directly retrieved NLM abbreviation, the official horticultural society manual or ISSN record supports the stated form. Dots in the ISSN abbreviation are removed for consistent Vancouver presentation.

| Existing journal title | SAGE Vancouver field text | Primary abbreviation source |
|---|---|---|
| Computers and Electronics in Agriculture | `Comput Electron Agric` | [ASHS official style manual, journal abbreviation table](https://journals.ashs.org/fileasset/ASHSPubsStyleManualWeb2022.pdf) |
| Postharvest Biology and Technology | `Postharvest Biol Technol` | [NLM 9884964](https://www.ncbi.nlm.nih.gov/nlmcatalog/9884964) |
| Spectrochimica Acta Part A: Molecular and Biomolecular Spectroscopy | `Spectrochim Acta A Mol Biomol Spectrosc` | [NLM 9602533](https://www.ncbi.nlm.nih.gov/nlmcatalog/9602533) |
| Journal of Food Composition and Analysis | `J Food Compos Anal` | [ISSN 0889-1575](https://portal.issn.org/custom-search/print/0889-1575/public) |
| Food Chemistry | `Food Chem` | [NLM 7702639](https://www.ncbi.nlm.nih.gov/nlmcatalog/7702639) |
| Journal of Food Science | `J Food Sci` | [NLM 0014052](https://www.ncbi.nlm.nih.gov/nlmcatalog/0014052) |
| Sensors and Actuators B: Chemical | `Sens Actuators B Chem` | [NLM 101149755](https://www.ncbi.nlm.nih.gov/nlmcatalog/101149755) |
| Chemometrics and Intelligent Laboratory Systems | `Chemometr Intell Lab Syst` | [NLM 8711218](https://www.ncbi.nlm.nih.gov/nlmcatalog/8711218) |
| Journal of Chemometrics | `J Chemom` | [NLM 9882381](https://www.ncbi.nlm.nih.gov/nlmcatalog/9882381) |
| Analytica Chimica Acta | `Anal Chim Acta` | [NLM 0370534](https://www.ncbi.nlm.nih.gov/nlmcatalog/0370534) |
| Applied Spectroscopy | `Appl Spectrosc` | [NLM 0372406](https://www.ncbi.nlm.nih.gov/nlmcatalog/0372406) |
| Talanta | `Talanta` (unchanged) | [NLM 2984816R](https://www.ncbi.nlm.nih.gov/nlmcatalog/2984816R) |
| BMC Bioinformatics | `BMC Bioinformatics` (unchanged) | [NLM 100965194](https://www.ncbi.nlm.nih.gov/nlmcatalog/100965194) |
| Ecography | `Ecography` (unchanged) | [NLM 101187590](https://www.ncbi.nlm.nih.gov/nlmcatalog/101187590) |

In particular, NLM specifies **Chemometr** in `Chemometr Intell Lab Syst`; `Chemom` is not the retrieved NLM form for this journal.

## BAARC publication-status check

As of 26 November 2026, **no published successor was verified**. The [official arXiv abstract record](https://arxiv.org/abs/2610.32505) lists only v1, submitted 23 October 2026, and gives the arXiv-issued DOI; it supplies no journal reference, published-paper DOI or acceptance comment. The [v1 full text](https://arxiv.org/html/2610.32505v1) likewise identifies the arXiv version and date. Exact-title/identifier and author-plus-title searches did not locate a publisher successor. A live Crossref `works` query on the full title returned unrelated publications in its five highest-ranked matches and no matching published work.

This is a bounded negative search, not proof that publication is impossible or that the authors have no pending submission. Retain the explicitly labeled preprint and its current source key rather than inventing a successor. Recheck the arXiv record at actual journal submission, because SAGE prefers a published version when available.

## Final rendering checks for the root conversion

The final BibTeX warning for `shim2018` was resolved by adding pages 1368--1378. The [official NeurIPS metadata JSON](https://proceedings.neurips.cc/paper_files/paper/2018/file/e5841df2166dd424a57127423d276bbe-Metadata.json) supplies `page_first: 1368` and `page_last: 1378`, although the linked BibTeX export leaves its pages field empty. This is a verified metadata completion, not a change to the cited source or the scientific text.

- All 30 source keys remain cited and present exactly once in the reference list.
- `anderson2020` prints NT, KB and PP; `jazbec2024` prints Hadži Veljković T.
- The four proceedings entries visibly contain their publication years after the local style fix.
- The dataset prints Mendeley Data and version 3; the thesis and BAARC retain their distinct source types.
- Journal abbreviations match the table above; no conference paper is relabeled as a journal article.
- Superscript citation numbers and bibliography order are checked after the root agent replaces unsupported narrative `\citet` calls with explicit author text plus numeric citations.
