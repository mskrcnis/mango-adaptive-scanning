# Mango adaptive versus fixed spectral acquisition

Research code, frozen inference artifacts, results and the LaTeX manuscript for **Adaptive versus fixed spectral acquisition for mango dry-matter prediction: a seasonal benchmark and controlled diagnosis**.

This is a dataset-based computational study prepared for the *Journal of Near Infrared Spectroscopy*. The proposed adaptive stopping objective did not demonstrate an advantage. Controlled exploratory comparisons support improvements from fixed-channel selection within the evaluated configurations. Optical channels are simulated; the work does not validate a physical scanner or a mango harvest decision.

## Paper and source package

- [Current JNIRS manuscript, 16 pages](revisions/jnirs_submission_v6/output/pdf/Mango_JNIRS_Manuscript.pdf)
- [Supplementary methods and results, 28 pages](revisions/jnirs_submission_v6/output/pdf/Mango_JNIRS_Supplement.pdf)
- [Self-contained LaTeX/Overleaf ZIP](revisions/jnirs_submission_v6/output/Mango_JNIRS_LaTeX_Source.zip)
- [Journal-conversion verification report](revisions/jnirs_submission_v6/verification_report.md)
- [Remaining author declarations and journal-policy review](revisions/jnirs_submission_v6/AUTHOR_INPUTS.md)

The manuscript presents one final study using descriptive analysis names, without internal manuscript revision labels, and retains all 30 references. It is an author-review draft, not an accepted or submitted article. The supplied author names, affiliations and correspondence details appear in both PDFs, and the data/code availability statements link to this public repository. Contributions, funding, conflicts, human review and author approval remain to be completed. The supplement retains all 17 tables in 28 portrait pages, with unchanged table fonts and results; its final section has been shortened to data and code availability. No journal submission is implied.

## Verify the public repository

From a clone, with Python 3.8 or later:

```bash
python3 scripts/verify_public_release.py
```

This standard-library check verifies the public file manifest, frozen bundles, manuscript PDFs and source-archive integrity. It does not rerun training or claim independent predictive validation. Release scope and excluded files are explained in [PUBLIC_RELEASE.md](PUBLIC_RELEASE.md).

## Build both PDFs

Install pdfLaTeX and BibTeX with standard TeX Live packages, then run:

```bash
bash revisions/jnirs_submission_v6/build_pdfs.sh
```

Alternatively, upload the source ZIP into Overleaf, choose pdfLaTeX and select `main.tex`; select `supplement.tex` separately for the supplement. Python, the raw dataset and model training are not needed to compile the documents. The source ZIP was independently compiled outside the research workspace and reproduced both delivered PDFs exactly. Other TeX installations may produce different PDF bytes while preserving the document; after intentional edits, regenerate the release manifest only after reviewing the change.

## Run the frozen six-channel candidate

The candidate uses channels centered nominally at **720, 760, 820, 890, 910 and 940 nm**. Its portable inference uses NumPy and SciPy; the complete frozen bundle is included so its integrity checks can run. The commands below use Python 3.11, compatible with these pinned package versions.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install numpy==1.24.3 scipy==1.10.1
.venv/bin/python revisions/candidate_v4/predict.py --input revisions/candidate_v4/examples/development_channels.csv --mode candidate
```

The examples are three development rows from the cited dataset and demonstrate software behavior, not new validation. Inputs are the exact frozen finite-band apparent-absorbance representation, not raw photodiode intensities. The interface rejects extra features, assay outcomes and metadata. See the [candidate documentation](revisions/candidate_v4/README.md) and [model card](revisions/candidate_v4/frozen/model_card.md).

The original adaptive replay application and its complete frozen model directory are also supplied. With the pinned scientific environment from `requirements.txt`, run `python3 run_project.py replay --example` or `python3 run_project.py app`. These demonstrate the original controller; the paper's conclusion does not recommend adaptive superiority.

## Research structure and provenance

| Location | Contents |
|---|---|
| `mango/`, `config/`, `tests/`, `run_project.py` | Original training, evaluation, optical simulation, replay application and software tests |
| `results/frozen/` | Original frozen models, code snapshot, calibration, selection and replay fixture |
| `revisions/methodology_v2/` | Matched-predictor and endpoint diagnosis |
| `revisions/fixed_design_v3/` | Design-only channel subsets and acquisition orders |
| `revisions/candidate_v4/` | Final candidate source, complete frozen bundle and inference interface |
| `revisions/dataset_paper_v5/` | Dataset-only reporting consolidation and expanded related work |
| `revisions/jnirs_submission_v6/` | Current journal edition, figures, supporting tables, PDFs and source ZIP |
| `data/catalog/`, `data/provenance/` | Numeric emitter profiles, source URLs, checksums and public dataset metadata |

The source dataset is *Mango DMC and spectra Anderson et al. 2020*, Mendeley Data version 3, [DOI 10.17632/46htwnp833.3](https://doi.org/10.17632/46htwnp833.3), released by Anderson, Walsh, Subedi and Hayes under CC BY 4.0. It contains 12,011 scans; fruit identities are not verified. The original CSV SHA-256 is `1e0e450417ed96b47b3808556706afa84a2e6441a76e380a8b64b18d85fddee1`.

The complete raw/processed spectral files, downloaded third-party articles/data sheets, training checkpoints, stale attempts and bulky prediction caches are excluded from Git. Source metadata and numerical profiles are retained with attribution. Training and historical full-workspace verification require those omitted inputs and artifacts. Historical `all --resume` commands are not immediate reproduction commands for a filtered clone. Read [PUBLIC_RELEASE.md](PUBLIC_RELEASE.md) before attempting a full rerun in a separate workspace.

## Interpretation and licensing

Original later-season results and subsequent exploratory development analyses remain separate. Reused seasons, unknown fruit identities, model-relative references and simulated optical responses bound the findings. Selection scores for the final candidate are tuning evidence. There is no validated pick/wait threshold or claim of measured hardware savings.

Public visibility does not grant a blanket software license. No open-source license has been selected for original project materials. Dataset and third-party components retain their own terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The Sage class is unchanged, and its source/provenance and the small bibliography-style derivative are documented in the journal package.
