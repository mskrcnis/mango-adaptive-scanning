# Complete dataset-based mango paper

This revision consolidates the existing study into a full research manuscript and supplement. Every mango observation comes from the official Mendeley version-3 dataset. No new field data, physical scanner or harvest decision threshold is required to complete this computational paper.

The paper evaluates dry-matter prediction versus simulated spectral acquisition. Its central findings are that the adaptive objective did not demonstrate an advantage, that matched predictor replacement did not explain the original partial-scan gap, and that better fixed-channel design improved the exact-budget comparison on the primary PLS bank. Generalization limits and negative sensitivities are reported alongside the favorable results.

## Deliverables

- `output/pdf/Mango_Dataset_Study.pdf`: complete manuscript for author review.
- `output/pdf/Mango_Dataset_Supplement.pdf`: detailed methods, complete scored comparisons, ablations and evidence inventory.
- `output/Mango_Dataset_Paper_Source.zip`: self-contained TeX/figure/table source package with an internal SHA-256 manifest.
- `verification_report.md`: executed numerical, preservation, compilation, visual and archive checks.
- `results/tables_*.csv` and `results/evidence_cells.json`: reconstructed numerical evidence and provenance.
- `evidence_tables/`: copies of original result tables indexed by original, v2 and v3 analysis stage.

The original model runs, original manuscript and all frozen candidates remain unchanged. `prior_preservation.json` records their hashes. The final candidate's tuning minimum is not used as an accuracy result, and fold-specific fixed-six results are not assigned to that candidate.

## Reproduce within the original workspace

From `/home/mskr/Research/Agro/Mango`:

```bash
.venv/bin/python revisions/dataset_paper_v5/run.py all --resume
```

Stages are `report`, `compile`, `package`, `isolated`, `verify` and `status`. The reporting stage reuses current hash-verified evidence or independently recomputes it from saved scored prediction exports. It never fits a model, loads raw spectra or performs new external scoring. Existing reports use saved assays only to recompute already evaluated quantities.

The original environment and model reproduction commands remain in the root README and the v2/v3/v4 revision READMEs. This paper build requires NumPy, pandas, matplotlib and pypdf in the existing `.venv`, plus pdfLaTeX and BibTeX. Missing full research inputs prevent numerical reproduction but do not prevent compilation of the source package.

Exact document-build dependencies are recorded in `environment.json` and `requirements-paper.txt`. The added pypdf dependency is for PDF inspection only. `evidence_tables/manifest.json` maps each copied table to its original project-relative path, as used in the supplement's evidence inventory.

## Compile the standalone source package

Extract the ZIP into an empty directory and run:

```bash
bash build_pdfs.sh
```

This compiles both documents using only the archive contents and installed TeX packages. An isolated extraction/compilation is executed during verification. The full model checkpoints, raw dataset and third-party article PDFs are not duplicated into this manuscript-source archive. The reporting scripts reference the preserved workspace for numerical reproduction; they are not standalone model-training code.

## Scope and interpretation

``External seasons'' in older filenames means seasons 4 and 5 held out from original fitting within the same public dataset. It does not mean another dataset or a requirement for new fruit collection. Those benchmarks were used in earlier local work and are disclosed as reused. The v2/v3 follow-ups are exploratory because seasons 1–3 had already been examined.

Digitized manufacturer profiles are fixed assumptions of the existing finite-band simulation. No physical energy, timing, signal-to-noise or field performance was measured. Harvest timing motivates the application, but the available labels support dry-matter regression, not a validated pick/wait endpoint. These are scope boundaries, not outstanding required experiments.

Author names, affiliations, contributions, funding and competing-interest declarations require author input before submission. No journal acceptance, established methodological originality, public repository release or submission is claimed.

## Resuming interrupted work

Read `RUN_STATUS.md`, then run the reporting-only command above. Current numerical evidence and compiled PDFs are reused by hash. The visual review is bound to the PDF bytes and must be repeated if their source changes. The handoff integrity manifest is a snapshot; operational verification logs can change on a later rerun.

To repeat the full before/after byte-preservation proof after the completed build:

```bash
.venv/bin/python revisions/dataset_paper_v5/verify_resume.py
```

## Expanded related work

Section 1.1 now provides a thematic comparison of the mango-calibration, fixed-selection, adaptive-acquisition and evaluation literature. The main paper cites 30 references, including 26 journal/proceedings articles. `literature_expansion_sources.md` records the primary sources, access levels and supported claims for the added literature. `verify_references.py` checks citation coverage and the compiled bibliography; within the original workspace it also verifies that manuscript prose and data outside Section 1.1 are unchanged from the preserved preceding delivery. The checks run as part of `run.py all --resume`.
