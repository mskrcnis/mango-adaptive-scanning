# Historical full-workspace workflow

This is the original local-workspace README preserved at public-release preparation. It predates later revisions and public publication. It describes the full research workspace, including files intentionally omitted from Git. Use the root README for supported public-clone commands. Historical no-release statements below refer to the original preparation stage.

# Adaptive mango spectral scanning

This local research package tests whether a scanner benefits from learning the
assay-error correction available from finishing its installed LED bank, separately
from the bank's loss against a richer spectrum. Read `decision_report.md` and
`verification_report.md` after the workflow completes. This is an offline optical
replay study, not a validated physical scanner.

## Run

From this directory:

```bash
python3 run_project.py smoke
python3 run_project.py all --resume
python3 run_project.py status
python3 run_project.py verify
python3 run_project.py replay --example
python3 run_project.py app
```

Open `http://127.0.0.1:8765` for the local application. Stop it with Ctrl-C.
`python3 run_project.py app --self-test` exercises the HTTP interaction and exits.

```bash
python3 run_project.py replay --manual --trace-output results/manual_trace.json
python3 run_project.py all --resume --data-path /path/to/NAnderson2020MendeleyMangoNIRDataV3.csv
python3 run_project.py report
```

Manual mode accepts only the requested emitter's reference-normalized apparent
absorbance reading. The demo uses one real development scan, with its assay
omitted. The controller does not need a full-spectrum CSV. The reporting command
regenerates the manuscript, tables and figures from saved results without fitting.

## Environment and time

`run_project.py` creates/reuses `.venv`. On this workstation it uses the existing
scientific Python installation via a project-local venv with inherited packages;
the exact Python, base path, CUDA and package versions are recorded in
`results/environment.json`. This does not modify the base environment. On a clean
host it obtains project-local Python 3.8.20 through `uv` if needed, creates an
isolated venv and installs `requirements.txt`. `uv==0.9.29` is bootstrapped locally
if unavailable. `environment.lock.txt` is the complete audit export of this
workstation; the minimal pinned install input is `requirements.txt`. A GPU is optional; CUDA is used
when available and CPU fallback is implemented. Four CPU threads are requested.
LaTeX (`pdflatex`, `bibtex`) and Poppler are needed for compiled PDF verification.

The measured initial real-data pilot took approximately 46 seconds per bank/fold
on the RTX 3090. The full workflow includes six banks, three outer seasons, multiple
seeds, calibration, controls, static and CNN baselines, and final models. Its exact
attempt times are recorded in `results/run_ledger.jsonl`. Long jobs checkpoint each
bank/fold/seed and policy trajectory. Interrupting `all` is safe; rerun with
`--resume`. Failed/running attempts remain in the ledger and are not complete.
Changing a dependency invalidates descendants, with stale checkpoints archived.
Once frozen, external evaluation resumes without refitting; incompatible runtime
changes raise an integrity error instead of silently revising results.

## Data and experimental boundaries

The official dataset is [Mendeley Data version 3](https://data.mendeley.com/datasets/46htwnp833/3),
DOI `10.17632/46htwnp833.3`, CC BY 4.0. The original CSV SHA-256 is
`1e0e450417ed96b47b3808556706afa84a2e6441a76e380a8b64b18d85fddee1`.
An offline override must match this checksum; a different dataset cannot silently
reuse locked models. Provider records/listings are cached for offline provenance.

There are 10,243 development scans from seasons 1--3, 1,448 external season-4 scans,
and 320 season-5 scans. These are scans, not verified unique fruits. Missing fruit
IDs require harvest-population grouping; season 5 has only two populations.
Separate groups are used for bank design, model fitting and calibration, and a
whole season is held out in each development fold. External assays are isolated
under `data/sealed/`. Operating points and all prediction artifacts are frozen
before external outcome access. A prior neighboring study used the same external
benchmarks; this known reuse is explicitly disclosed.

Ten digitized manufacturer LED curves support an eight-LED bank, starting with two
readings and targeting four. Typical data-sheet traces, flat detector response and
conventional base-10 absorbance are modeling assumptions. The manufacturer's
manual does not explicitly identify the logarithm base. Simulated pulse counts
are not energy or hardware timing. Nominal Gaussian/response-shift and ideal-point
analyses are separately labeled. A new physical validation remains necessary.

## Artifacts

- `config/experiment.json`, `docs/protocol.md`, `results/protocol_lock.json`:
  registered rules and exact dependencies, including the pre-external leakage repair.
- `results/development_scores.csv`, `development_frontier.csv`, `selection.json`:
  all candidates and the separate scientific/engineering operating points.
- `results/frozen/`: models, scalers, calibration, catalog, code snapshot and
  immutable hash manifest; no external assays in the replay fixture.
- `results/external_predictions.csv`, `external_metrics.csv`, `frozen_curves.csv`:
  paired per-scan predictions, results and fixed-grid trade-offs.
- `results/external_uncertainty.json`, `calibration.json`,
  `external_traces.jsonl.gz`, `action_diagnostics.json`: uncertainty and mechanisms.
- `results/selected_bank_parts.csv`, `calibrator_summary.json`,
  `paired_examples.json`, `reference_agreement_errors.csv`: exact installed parts,
  calibration mappings, paired examples and errors despite reference agreement.
- `results/independent_numerical_audit.json`, `final_resume_verification.json`:
  independent saved-table arithmetic and unchanged protected hashes after the
  complete normal resume command.
- `figures/`: publication PNG/PDF figures.
- `manuscript/main.tex`, `main.pdf`, `references.bib`, `supplement.pdf`:
  author-review manuscript and complete comparison supplement.
- `docs/literature_audit.md`, `docs/independent_method_review.md`,
  `results/data_audit/DATA_AUDIT.md`: checked evidence and limitations.
- `decision_report.md`, `verification_report.md`, `RUN_STATUS.md`: conclusions,
  executed checks and resume history.

No public repository release, submission, hardware purchase or patent filing is
performed. The manuscript leaves author identities and declarations for author
confirmation. Paper overlap already includes early/full-model loss gaps,
conditional acquisition and adaptive spectroscopy; this study cannot establish
absolute originality or patentability.
